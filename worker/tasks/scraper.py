"""Recipe scraper task using recipe-scrapers + httpx.

Do NOT use Scrapy here — it is synchronous and must never run in the FastAPI process.
This Celery task fetches and parses recipes from sitemap URLs using httpx + recipe-scrapers.
"""
import asyncio
import logging
import os
import sys
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from xml.etree import ElementTree

import httpx
from celery import Celery
from tenacity import retry, stop_after_attempt, wait_exponential

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

app = Celery("worker")
app.config_from_object("worker.celeryconfig")

logger = logging.getLogger(__name__)

HEADERS = {"User-Agent": "Cookit-Bot/1.0 (personal project; respectful crawler)"}
CRAWL_DELAY = 2.0  # seconds between requests per domain

CRAWL_SOURCES = [
    {
        "name": "allrecipes",
        "sitemap": "https://www.allrecipes.com/sitemap.xml",
        "max_recipes": 200,
    },
    {
        "name": "bbcgoodfood",
        "sitemap": "https://www.bbcgoodfood.com/sitemap.xml",
        "max_recipes": 200,
    },
    {
        "name": "food_com",
        "sitemap": "https://www.food.com/sitemap",
        "max_recipes": 200,
    },
]


def is_allowed(url: str, user_agent: str = "Cookit-Bot") -> bool:
    """Check robots.txt before fetching a URL."""
    parsed = urlparse(url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
    except Exception:
        return True  # if robots.txt unreachable, allow
    return rp.can_fetch(user_agent, url)


@retry(wait=wait_exponential(min=2, max=30), stop=stop_after_attempt(3))
async def _fetch(client: httpx.AsyncClient, url: str) -> str:
    resp = await client.get(url, headers=HEADERS, timeout=15, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _extract_urls_from_sitemap(xml_text: str) -> list[str]:
    """Parse a sitemap XML and return all <loc> URLs."""
    try:
        root = ElementTree.fromstring(xml_text)
    except ElementTree.ParseError:
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []
    # Handle sitemap index (links to sub-sitemaps) and regular sitemaps
    for loc in root.findall(".//sm:loc", ns):
        if loc.text:
            urls.append(loc.text.strip())
    return urls


async def _parse_recipe_url(client: httpx.AsyncClient, url: str) -> dict | None:
    """Fetch a recipe URL and parse it with recipe-scrapers. Returns None on failure."""
    from recipe_scrapers import scrape_html
    from recipe_scrapers._exceptions import NoSchemaFoundInWildMode, WebsiteNotImplementedError

    if not is_allowed(url):
        logger.debug("robots.txt disallows: %s", url)
        return None

    try:
        html = await _fetch(client, url)
    except Exception as exc:
        logger.warning("Failed to fetch %s: %s", url, exc)
        return None

    # Try supported parser first, fall back to wild_mode
    wild = False
    try:
        scraper = scrape_html(html, org_url=url)
    except (WebsiteNotImplementedError, Exception):
        try:
            scraper = scrape_html(html, org_url=url, wild_mode=True)
            wild = True
        except (NoSchemaFoundInWildMode, Exception) as exc:
            logger.debug("recipe-scrapers could not parse %s: %s", url, exc)
            return None

    try:
        title = scraper.title()
        ingredients = scraper.ingredients()
    except Exception:
        return None

    # Quality gate for wild_mode results
    if not title or len(ingredients) < 3:
        return None

    try:
        data = scraper.to_json()
    except Exception as exc:
        logger.warning("scraper.to_json() failed for %s: %s", url, exc)
        return None

    data["_wild_mode"] = wild
    data["_source_url"] = url
    return data


async def _save_recipe(session, url: str, data: dict) -> bool:
    """Persist a parsed recipe dict to the DB. Returns True if inserted."""
    from sqlalchemy import text

    from app.models.db import Recipe, RecipeIngredient
    from app.services.normalize import normalize_batch

    title = (data.get("title") or "").strip()
    raw_ingredients: list[str] = data.get("ingredients") or []
    instructions_list = data.get("instructions_list") or []
    instructions_str = data.get("instructions") or ""
    if not instructions_list and instructions_str:
        instructions_list = [s.strip() for s in instructions_str.split("\n") if s.strip()]

    if not title or len(raw_ingredients) < 3:
        return False

    # Dedup by source_url
    exists = await session.execute(
        text("SELECT 1 FROM recipes WHERE source_url = :url"), {"url": url}
    )
    if exists.fetchone():
        return False

    steps = [{"step_number": i + 1, "instruction": line} for i, line in enumerate(instructions_list)]
    ingredient_dicts = [{"name": ing} for ing in raw_ingredients]

    wild = data.get("_wild_mode", False)
    recipe = Recipe(
        title=title,
        source_url=url,
        ingredients=ingredient_dicts,
        steps=steps or [{"step_number": 1, "instruction": instructions_str}],
        cuisine=data.get("cuisine") or None,
        tags=data.get("tags") or None,
    )
    session.add(recipe)
    await session.flush()

    try:
        normalized = await normalize_batch(raw_ingredients)
    except Exception as exc:
        logger.warning("Normalization failed for %s: %s — using raw names", url, exc)
        normalized = None

    for idx, raw_name in enumerate(raw_ingredients):
        canonical = (
            normalized[idx].canonical_name
            if normalized and idx < len(normalized)
            else raw_name.lower()
        )
        session.add(RecipeIngredient(
            recipe_id=recipe.id,
            canonical_name=canonical,
            quantity=None,
            unit=None,
        ))

    if wild:
        logger.debug("Inserted wild_mode recipe: %s", url)

    return True


async def _crawl_source(source: dict, session_factory) -> int:
    """Crawl one source: fetch sitemap, parse recipe pages, save to DB."""
    from sqlalchemy.ext.asyncio import async_sessionmaker

    name = source["name"]
    sitemap_url = source["sitemap"]
    max_recipes = source.get("max_recipes", 100)
    inserted = 0

    async with httpx.AsyncClient(headers=HEADERS, timeout=30) as client:
        logger.info("[%s] Fetching sitemap: %s", name, sitemap_url)
        try:
            sitemap_xml = await _fetch(client, sitemap_url)
        except Exception as exc:
            logger.error("[%s] Sitemap fetch failed: %s", name, exc)
            return 0

        all_urls = _extract_urls_from_sitemap(sitemap_xml)

        # If it's a sitemap index, fetch sub-sitemaps (up to 3 to limit volume)
        recipe_urls: list[str] = []
        for u in all_urls:
            if "sitemap" in u.lower() and u.endswith(".xml"):
                try:
                    sub_xml = await _fetch(client, u)
                    recipe_urls.extend(_extract_urls_from_sitemap(sub_xml))
                except Exception:
                    pass
                if len(recipe_urls) >= max_recipes * 2:
                    break
            else:
                recipe_urls.append(u)

        if not recipe_urls:
            recipe_urls = all_urls

        # Filter to likely recipe URLs (skip sitemaps, indexes, non-recipe paths)
        recipe_urls = [
            u for u in recipe_urls
            if not u.endswith(".xml") and "recipe" in u.lower()
        ][:max_recipes * 2]  # fetch 2x to account for failures

        logger.info("[%s] Found %d candidate recipe URLs", name, len(recipe_urls))

        for url in recipe_urls:
            if inserted >= max_recipes:
                break

            await asyncio.sleep(CRAWL_DELAY)

            parsed = await _parse_recipe_url(client, url)
            if not parsed:
                continue

            async with session_factory() as session:
                async with session.begin():
                    saved = await _save_recipe(session, url, parsed)
                    if saved:
                        inserted += 1
                        logger.info("[%s] Saved recipe %d: %s", name, inserted, parsed.get("title", url))

    logger.info("[%s] Done. Inserted %d recipes.", name, inserted)
    return inserted


async def _crawl_all_async() -> dict:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set")
        return {"error": "DATABASE_URL not set"}

    engine = create_async_engine(database_url, echo=False)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    results = {}
    for source in CRAWL_SOURCES:
        count = await _crawl_source(source, session_factory)
        results[source["name"]] = count

    await engine.dispose()
    return results


@app.task(name="worker.tasks.scraper.crawl_all_sources", bind=True, max_retries=1)
def crawl_all_sources(self) -> dict:
    """Nightly task: crawl all recipe sources and persist new recipes."""
    return asyncio.run(_crawl_all_async())
