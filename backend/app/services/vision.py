import asyncio
import base64
import json
import logging
import re
import uuid
from typing import Any

import anthropic
from fastapi import UploadFile
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.db import ScanCorrection
from app.models.schemas import CorrectionEntry, CorrectionsResponse, DetectedItem, ScanResponse
from app.services import storage
from app.services.normalize import normalize_batch

logger = logging.getLogger(__name__)
settings = get_settings()

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

VISION_SYSTEM_PROMPT = """
You are a kitchen inventory assistant. Analyse the provided fridge photo and identify all visible food items.

Return ONLY a JSON array with no additional text, markdown, or explanation:
[
  {
    "item_name": "<canonical lowercase name>",
    "category": "<one of: produce|dairy|protein|condiment|leftover|beverage|other>",
    "quantity": <number>,
    "unit": "<count|g|ml|pack|bottle|jar|bunch|other>",
    "confidence": <0.0-1.0>
  }
]

Rules:
- Use canonical names: "chicken breast" not "raw chicken", "whole milk" not "milk"
- Estimate quantity conservatively when unclear
- Set confidence < 0.7 for partially visible or ambiguous items
- Do not invent items; only include what is clearly visible
"""

_semaphore = asyncio.Semaphore(5)


async def _fetch_recent_corrections(db: AsyncSession, user_id: uuid.UUID, limit: int = 5) -> list[ScanCorrection]:
    result = await db.execute(
        select(ScanCorrection)
        .where(ScanCorrection.user_id == user_id)
        .order_by(ScanCorrection.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


def _build_system_prompt(corrections: list[ScanCorrection]) -> str:
    if not corrections:
        return VISION_SYSTEM_PROMPT
    # Reverse so prompt reads oldest → newest (chronological)
    ordered = list(reversed(corrections))
    examples = []
    for c in ordered:
        orig = f'"{c.original_name}"'
        if c.original_quantity is not None:
            orig += f" ({c.original_quantity} {c.original_unit or ''})"
        corr = f'"{c.corrected_name}"'
        if c.corrected_quantity is not None:
            corr += f" ({c.corrected_quantity} {c.corrected_unit or ''})"
        examples.append(f"  - You detected {orig} → user corrected to {corr}")
    past_section = "\n\nPast corrections from this user (avoid repeating these mistakes):\n" + "\n".join(examples)
    return VISION_SYSTEM_PROMPT + past_section


async def save_corrections(
    db: AsyncSession, user_id: uuid.UUID, entries: list[CorrectionEntry]
) -> int:
    rows = [
        ScanCorrection(
            user_id=user_id,
            original_name=e.original_name,
            original_quantity=e.original_quantity,
            original_unit=e.original_unit,
            corrected_name=e.corrected_name,
            corrected_quantity=e.corrected_quantity,
            corrected_unit=e.corrected_unit,
        )
        for e in entries
    ]
    db.add_all(rows)

    # Also update fridge_items to reflect corrections
    for e in entries:
        await db.execute(
            text(
                """
                UPDATE fridge_items
                SET item_name  = :corrected_name,
                    quantity   = COALESCE(:corrected_quantity, quantity),
                    unit       = COALESCE(:corrected_unit, unit),
                    updated_at = now()
                WHERE user_id  = :user_id
                  AND item_name = :original_name
                """
            ),
            {
                "user_id": str(user_id),
                "original_name": e.original_name,
                "corrected_name": e.corrected_name,
                "corrected_quantity": e.corrected_quantity,
                "corrected_unit": e.corrected_unit,
            },
        )

    await db.commit()
    logger.info("Saved %d corrections for user %s", len(entries), user_id)
    return len(entries)


def _strip_markdown_fences(text: str) -> str:
    return re.sub(r"```(?:json)?\s*|\s*```", "", text).strip()


async def _call_with_retry(fn, *args, max_retries: int = 3, **kwargs) -> Any:
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
            if attempt == max_retries - 1:
                raise
            logger.warning("Anthropic API error (attempt %d): %s — retrying in %.1fs", attempt + 1, exc, delay)
            await asyncio.sleep(delay)
            delay *= 2


async def detect_items(file: UploadFile, db: AsyncSession, user_id: uuid.UUID) -> ScanResponse:
    file_bytes = await file.read()
    content_type = file.content_type or "image/jpeg"

    # Upload to S3 (fire-and-forget on failure — scan still proceeds)
    try:
        storage.upload_image(file_bytes, content_type)
    except Exception as exc:
        logger.warning("S3 upload failed, continuing without storage: %s", exc)

    b64_data = base64.b64encode(file_bytes).decode()

    # Inject past corrections as few-shot examples into the system prompt
    recent_corrections = await _fetch_recent_corrections(db, user_id)
    system_prompt = _build_system_prompt(recent_corrections)

    async with _semaphore:
        response = await _call_with_retry(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {"type": "base64", "media_type": content_type, "data": b64_data},
                        },
                        {"type": "text", "text": "Identify all food items in this fridge photo."},
                    ],
                }
            ],
        )

    raw_text = response.content[0].text
    cleaned = _strip_markdown_fences(raw_text)

    try:
        raw_items: list[dict] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse vision response: %s\nRaw: %s", exc, cleaned)
        raise ValueError("Vision model returned invalid JSON") from exc

    detected: list[DetectedItem] = []
    for item_data in raw_items:
        try:
            item = DetectedItem.model_validate(item_data)
            if item.confidence >= 0.5:
                detected.append(item)
        except Exception as exc:
            logger.warning("Skipping invalid item %s: %s", item_data, exc)

    # Normalize item names via Haiku so they match recipe_ingredients canonical names
    raw_names = [item.item_name for item in detected]
    try:
        normalized = await normalize_batch(raw_names)
        canonical_names = [n.canonical_name for n in normalized]
    except Exception as exc:
        logger.warning("Normalization failed, using raw names: %s", exc)
        canonical_names = raw_names

    # Upsert into fridge_items
    saved_count = 0
    for item, canonical_name in zip(detected, canonical_names):
        await db.execute(
            text(
                """
                INSERT INTO fridge_items (user_id, item_name, category, quantity, unit, source, confidence)
                VALUES (:user_id, :item_name, :category, :quantity, :unit, 'vision', :confidence)
                ON CONFLICT (user_id, item_name) DO UPDATE
                    SET quantity   = EXCLUDED.quantity,
                        category   = EXCLUDED.category,
                        source     = EXCLUDED.source,
                        confidence = EXCLUDED.confidence,
                        updated_at = now()
                """
            ),
            {
                "user_id": str(user_id),
                "item_name": canonical_name,
                "category": item.category,
                "quantity": item.quantity,
                "unit": item.unit,
                "confidence": item.confidence,
            },
        )
        saved_count += 1

    await db.commit()
    logger.info("Detected %d items, saved %d for user %s", len(detected), saved_count, user_id)
    return ScanResponse(detected=detected, saved_count=saved_count)
