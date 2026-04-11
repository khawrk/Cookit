import asyncio
import json
import logging
import re
import uuid
from typing import Any

import anthropic
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.db import FridgeItem
from app.models.schemas import RecommendationItem, RecommendResponse

logger = logging.getLogger(__name__)
settings = get_settings()

client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

_semaphore = asyncio.Semaphore(5)


def _strip_markdown_fences(s: str) -> str:
    return re.sub(r"```(?:json)?\s*|\s*```", "", s).strip()


async def _call_with_retry(fn, *args, max_retries: int = 3, **kwargs) -> Any:
    delay = 1.0
    for attempt in range(max_retries):
        try:
            return await fn(*args, **kwargs)
        except (anthropic.RateLimitError, anthropic.APIStatusError) as exc:
            if attempt == max_retries - 1:
                raise
            logger.warning("Anthropic retry (attempt %d): %s — %.1fs", attempt + 1, exc, delay)
            await asyncio.sleep(delay)
            delay *= 2


async def _strategy_a_sql(user_items: list[str], db: AsyncSession) -> list[dict]:
    """SQL overlap strategy."""
    result = await db.execute(
        text(
            """
            SELECT
                r.id::text,
                r.title,
                r.source_url,
                r.cuisine,
                COUNT(ri.id) FILTER (WHERE ri.canonical_name = ANY(:user_items)) AS matched,
                COUNT(ri.id) AS total,
                COUNT(ri.id) FILTER (WHERE ri.canonical_name = ANY(:user_items))::float
                    / NULLIF(COUNT(ri.id), 0) AS overlap_score
            FROM recipes r
            JOIN recipe_ingredients ri ON ri.recipe_id = r.id
            GROUP BY r.id, r.title, r.source_url, r.cuisine
            HAVING COUNT(ri.id) FILTER (WHERE ri.canonical_name = ANY(:user_items))::float
                / NULLIF(COUNT(ri.id), 0) >= 0.4
            ORDER BY overlap_score DESC
            LIMIT 20
            """
        ),
        {"user_items": user_items},
    )
    rows = result.mappings().all()
    candidates = []
    for row in rows:
        # Fetch matched vs missing ingredients
        matched_result = await db.execute(
            text(
                "SELECT canonical_name FROM recipe_ingredients WHERE recipe_id = :rid AND canonical_name = ANY(:items)"
            ),
            {"rid": row["id"], "items": user_items},
        )
        matched = [r[0] for r in matched_result.fetchall()]

        missing_result = await db.execute(
            text(
                "SELECT canonical_name FROM recipe_ingredients WHERE recipe_id = :rid AND canonical_name != ALL(:items)"
            ),
            {"rid": row["id"], "items": user_items},
        )
        missing = [r[0] for r in missing_result.fetchall()]

        candidates.append(
            {
                "recipe_id": row["id"],
                "title": row["title"],
                "source_url": row["source_url"],
                "cuisine": row["cuisine"],
                "overlap_score": float(row["overlap_score"] or 0),
                "cosine_score": 0.0,
                "ai_score": 0.0,
                "matched_ingredients": matched,
                "missing_ingredients": missing,
            }
        )
    return candidates


async def _strategy_b_vector(user_items: list[str], db: AsyncSession) -> list[dict]:
    """pgvector cosine similarity strategy."""
    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        query_text = ", ".join(user_items)
        embedding = model.encode(query_text).tolist()
    except Exception as exc:
        logger.warning("Embedding generation failed, skipping strategy B: %s", exc)
        return []

    result = await db.execute(
        text(
            """
            SELECT
                r.id::text,
                r.title,
                r.source_url,
                r.cuisine,
                1 - (r.embedding <=> CAST(:embedding AS vector)) AS cosine_score
            FROM recipes r
            WHERE r.embedding IS NOT NULL
            ORDER BY r.embedding <=> CAST(:embedding AS vector)
            LIMIT 20
            """
        ),
        {"embedding": str(embedding)},
    )
    rows = result.mappings().all()
    candidates = []
    for row in rows:
        matched_result = await db.execute(
            text(
                "SELECT canonical_name FROM recipe_ingredients WHERE recipe_id = :rid AND canonical_name = ANY(:items)"
            ),
            {"rid": row["id"], "items": user_items},
        )
        matched = [r[0] for r in matched_result.fetchall()]

        missing_result = await db.execute(
            text(
                "SELECT canonical_name FROM recipe_ingredients WHERE recipe_id = :rid AND canonical_name != ALL(:items)"
            ),
            {"rid": row["id"], "items": user_items},
        )
        missing = [r[0] for r in missing_result.fetchall()]

        candidates.append(
            {
                "recipe_id": row["id"],
                "title": row["title"],
                "source_url": row["source_url"],
                "cuisine": row["cuisine"],
                "overlap_score": 0.0,
                "cosine_score": float(row["cosine_score"] or 0),
                "ai_score": 0.0,
                "matched_ingredients": matched,
                "missing_ingredients": missing,
            }
        )
    return candidates


async def _strategy_c_ai(user_items: list[str]) -> list[dict]:
    """Claude Sonnet creative recommendation strategy."""
    top_items = user_items[:10]
    prompt = (
        f"I have these ingredients in my fridge: {', '.join(top_items)}.\n"
        "Suggest up to 5 recipes I could make. Return ONLY a JSON array:\n"
        '[{"title": "<recipe name>", "cuisine": "<cuisine>", "reasoning": "<why it works>", "score": <0.0-1.0>}]'
    )

    async with _semaphore:
        response = await _call_with_retry(
            client.messages.create,
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

    raw = _strip_markdown_fences(response.content[0].text)
    try:
        suggestions: list[dict] = json.loads(raw)
    except json.JSONDecodeError as exc:
        logger.error("Strategy C parse error: %s", exc)
        return []

    candidates = []
    for s in suggestions:
        candidates.append(
            {
                "recipe_id": None,
                "title": s.get("title", ""),
                "source_url": "",
                "cuisine": s.get("cuisine"),
                "overlap_score": 0.0,
                "cosine_score": 0.0,
                "ai_score": float(s.get("score", 0.5)),
                "matched_ingredients": user_items[:5],
                "missing_ingredients": [],
            }
        )
    return candidates


def _merge_and_rank(
    strategy_a: list[dict],
    strategy_b: list[dict],
    strategy_c: list[dict],
) -> list[RecommendationItem]:
    merged: dict[str, dict] = {}

    for item in strategy_a:
        key = item["recipe_id"] or item["title"]
        merged[key] = {**item, "overlap_score": item["overlap_score"]}

    for item in strategy_b:
        key = item["recipe_id"] or item["title"]
        if key in merged:
            merged[key]["cosine_score"] = item["cosine_score"]
        else:
            merged[key] = {**item}

    for item in strategy_c:
        key = item["title"]
        if key not in merged:
            merged[key] = {**item}
        else:
            merged[key]["ai_score"] = item["ai_score"]

    results = []
    for key, item in merged.items():
        final_score = (
            0.4 * item.get("overlap_score", 0)
            + 0.35 * item.get("cosine_score", 0)
            + 0.25 * item.get("ai_score", 0)
        )
        try:
            rec_id = uuid.UUID(item["recipe_id"]) if item.get("recipe_id") else uuid.uuid4()
        except (ValueError, TypeError):
            rec_id = uuid.uuid4()

        results.append(
            RecommendationItem(
                recipe_id=rec_id,
                title=item["title"],
                match_score=round(final_score, 4),
                matched_ingredients=item.get("matched_ingredients", []),
                missing_ingredients=item.get("missing_ingredients", []),
                cuisine=item.get("cuisine"),
                source_url=item.get("source_url", ""),
            )
        )

    results.sort(key=lambda r: r.match_score, reverse=True)
    return results[:20]


async def get_recommendations(user_id: uuid.UUID, db: AsyncSession) -> RecommendResponse:
    result = await db.execute(select(FridgeItem).where(FridgeItem.user_id == user_id))
    fridge_items = result.scalars().all()
    user_item_names = [item.item_name for item in fridge_items]

    if not user_item_names:
        return RecommendResponse(recommendations=[])

    # Run strategies A and B in parallel
    strategy_a_task = asyncio.create_task(_strategy_a_sql(user_item_names, db))
    strategy_b_task = asyncio.create_task(_strategy_b_vector(user_item_names, db))
    strategy_a_results, strategy_b_results = await asyncio.gather(strategy_a_task, strategy_b_task)

    combined_count = len(strategy_a_results) + len(strategy_b_results)

    # Strategy C only if A+B return fewer than 5 results
    strategy_c_results: list[dict] = []
    if combined_count < 5:
        strategy_c_results = await _strategy_c_ai(user_item_names)

    recommendations = _merge_and_rank(strategy_a_results, strategy_b_results, strategy_c_results)
    logger.info(
        "Recommendations for user %s: A=%d B=%d C=%d → %d final",
        user_id,
        len(strategy_a_results),
        len(strategy_b_results),
        len(strategy_c_results),
        len(recommendations),
    )
    return RecommendResponse(recommendations=recommendations)
