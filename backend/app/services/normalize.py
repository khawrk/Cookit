import asyncio
import json
import logging
import re
from typing import Any

import anthropic

from app.config import get_settings
from app.models.schemas import NormalizedIngredient

logger = logging.getLogger(__name__)
settings = get_settings()

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

NORMALIZE_SYSTEM_PROMPT = """
Normalise the following ingredient name(s) to canonical form.
Return ONLY a JSON array (one object per input), no markdown:
[
  {
    "canonical_name": "<lowercase, singular, no brand names>",
    "category": "<produce|dairy|protein|condiment|grain|spice|other>",
    "default_unit": "<count|g|ml|tbsp|tsp|cup|bunch>"
  }
]
"""

_semaphore = asyncio.Semaphore(5)
_BATCH_SIZE = 20


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


async def _normalize_batch(names: list[str]) -> list[NormalizedIngredient]:
    payload = json.dumps(names)
    async with _semaphore:
        response = await _call_with_retry(
            client.messages.create,
            model="claude-haiku-4-5-20251001",
            max_tokens=512,
            system=NORMALIZE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": f"Normalise these ingredients: {payload}"}],
        )

    raw_text = response.content[0].text
    cleaned = _strip_markdown_fences(raw_text)

    try:
        items: list[dict] = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse normalize response: %s\nRaw: %s", exc, cleaned)
        raise ValueError("Normalisation model returned invalid JSON") from exc

    results: list[NormalizedIngredient] = []
    for item_data in items:
        try:
            results.append(NormalizedIngredient.model_validate(item_data))
        except Exception as exc:
            logger.warning("Skipping invalid normalized item %s: %s", item_data, exc)
    return results


async def normalize_ingredient(name: str) -> NormalizedIngredient:
    results = await _normalize_batch([name])
    if not results:
        raise ValueError(f"Failed to normalize ingredient: {name}")
    return results[0]


async def normalize_batch(names: list[str]) -> list[NormalizedIngredient]:
    """Normalize a list of ingredient names, batching in groups of 20."""
    results: list[NormalizedIngredient] = []
    for i in range(0, len(names), _BATCH_SIZE):
        chunk = names[i : i + _BATCH_SIZE]
        batch_results = await _normalize_batch(chunk)
        results.extend(batch_results)
    return results
