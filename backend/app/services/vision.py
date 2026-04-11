import asyncio
import base64
import json
import logging
import re
import uuid
from functools import wraps
from typing import Any

import anthropic
from fastapi import UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.schemas import DetectedItem, ScanResponse
from app.services import storage

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

    async with _semaphore:
        response = await _call_with_retry(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=VISION_SYSTEM_PROMPT,
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

    # Upsert into fridge_items
    saved_count = 0
    for item in detected:
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
                "item_name": item.item_name,
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
