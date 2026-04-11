"""Phase 1 seed script: populate the recipes table from TheMealDB API.

Run once on first deploy:
    cd backend
    python -m scripts.seed_recipes
"""
import asyncio
import logging
import sys

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Allow imports from backend root when run as a module
sys.path.insert(0, ".")

from app.config import get_settings
from app.models.db import Recipe, RecipeIngredient
from app.services.normalize import normalize_batch

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MEALDB_BASE = "https://www.themealdb.com/api/json/v1/1"


def _parse_ingredients(detail: dict) -> tuple[list[dict], list[str]]:
    """Extract ingredient dicts and raw name list from a MealDB detail record."""
    raw_ingredients = []
    ingredient_dicts = []
    for i in range(1, 21):
        name = (detail.get(f"strIngredient{i}") or "").strip()
        measure = (detail.get(f"strMeasure{i}") or "").strip()
        if name:
            raw_ingredients.append(name)
            ingredient_dicts.append({"name": name, "measure": measure})
    return ingredient_dicts, raw_ingredients


def _parse_steps(instructions: str) -> list[dict]:
    lines = [l.strip() for l in instructions.splitlines() if l.strip()]
    steps = []
    for idx, line in enumerate(lines, start=1):
        steps.append({"step_number": idx, "instruction": line})
    return steps or [{"step_number": 1, "instruction": instructions}]


async def seed_from_mealdb(session: AsyncSession) -> int:
    inserted = 0
    skipped = 0

    async with httpx.AsyncClient(timeout=20) as client:
        categories_resp = await client.get(f"{MEALDB_BASE}/categories.php")
        categories_resp.raise_for_status()
        categories = [c["strCategory"] for c in categories_resp.json()["categories"]]
        logger.info("Found %d categories", len(categories))

        for category in categories:
            filter_resp = await client.get(f"{MEALDB_BASE}/filter.php?c={category}")
            filter_resp.raise_for_status()
            meal_stubs = filter_resp.json().get("meals") or []
            logger.info("Category '%s': %d meals", category, len(meal_stubs))

            for stub in meal_stubs:
                meal_id = stub["idMeal"]
                source_url = f"https://www.themealdb.com/meal/{meal_id}"

                # Dedup check
                exists = await session.execute(
                    text("SELECT 1 FROM recipes WHERE source_url = :url"),
                    {"url": source_url},
                )
                if exists.fetchone():
                    skipped += 1
                    continue

                detail_resp = await client.get(f"{MEALDB_BASE}/lookup.php?i={meal_id}")
                detail_resp.raise_for_status()
                meals = detail_resp.json().get("meals")
                if not meals:
                    continue
                detail = meals[0]

                ingredient_dicts, raw_names = _parse_ingredients(detail)
                if not raw_names:
                    logger.warning("Skipping meal %s — no ingredients", meal_id)
                    continue

                steps = _parse_steps(detail.get("strInstructions") or "")

                tags_raw = (detail.get("strTags") or "").strip()
                tags = [t.strip() for t in tags_raw.split(",") if t.strip()] if tags_raw else []

                recipe = Recipe(
                    title=detail["strMeal"],
                    source_url=source_url,
                    ingredients=ingredient_dicts,
                    steps=steps,
                    cuisine=detail.get("strArea") or None,
                    tags=tags or None,
                )
                session.add(recipe)
                await session.flush()  # get recipe.id before adding ingredients

                # Normalize ingredient names via Haiku (batched)
                try:
                    normalized = await normalize_batch(raw_names)
                except Exception as exc:
                    logger.warning("Normalization failed for meal %s: %s — using raw names", meal_id, exc)
                    normalized = None

                for idx, raw_name in enumerate(raw_names):
                    canonical = normalized[idx].canonical_name if normalized and idx < len(normalized) else raw_name.lower()
                    session.add(RecipeIngredient(
                        recipe_id=recipe.id,
                        canonical_name=canonical,
                        quantity=None,
                        unit=None,
                    ))

                inserted += 1
                if inserted % 20 == 0:
                    await session.commit()
                    logger.info("Committed %d recipes so far (skipped %d duplicates)", inserted, skipped)

    await session.commit()
    logger.info("Seed complete. Inserted: %d, Skipped (duplicates): %d", inserted, skipped)
    return inserted


async def main() -> None:
    settings = get_settings()
    engine = create_async_engine(settings.database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as session:
        count = await seed_from_mealdb(session)

    await engine.dispose()
    logger.info("Done. Total new recipes: %d", count)


if __name__ == "__main__":
    asyncio.run(main())
