"""Embedding generation task.

Finds recipes without embeddings and generates them using
sentence-transformers/all-MiniLM-L6-v2 (384-dimensional vectors).
"""
import logging
import os

from celery import Celery

app = Celery("worker")
app.config_from_object("worker.celeryconfig")

logger = logging.getLogger(__name__)

BATCH_SIZE = 64


@app.task(name="worker.tasks.embedder.embed_pending", bind=True)
def embed_pending(self) -> dict:
    """Generate embeddings for all recipes missing them."""
    import asyncio

    return asyncio.run(_embed_pending_async())


async def _embed_pending_async() -> dict:
    import os

    from sentence_transformers import SentenceTransformer
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error("DATABASE_URL not set")
        return {"embedded": 0, "error": "DATABASE_URL not set"}

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    total_embedded = 0
    async with session_factory() as session:
        while True:
            result = await session.execute(
                text("SELECT id, title, ingredients FROM recipes WHERE embedding IS NULL LIMIT :batch"),
                {"batch": BATCH_SIZE},
            )
            rows = result.fetchall()
            if not rows:
                break

            texts = []
            ids = []
            for row in rows:
                ingredient_names = _extract_ingredient_names(row.ingredients)
                combined = f"{row.title}. Ingredients: {', '.join(ingredient_names)}"
                texts.append(combined)
                ids.append(str(row.id))

            embeddings = model.encode(texts, batch_size=32, show_progress_bar=False)

            async with session.begin():
                for recipe_id, embedding in zip(ids, embeddings):
                    await session.execute(
                        text("UPDATE recipes SET embedding = CAST(:emb AS vector) WHERE id = :id"),
                        {"emb": str(embedding.tolist()), "id": recipe_id},
                    )

            total_embedded += len(ids)
            logger.info("Embedded %d recipes (total: %d)", len(ids), total_embedded)

    await engine.dispose()
    logger.info("Embedding task complete. Total: %d", total_embedded)
    return {"embedded": total_embedded}


def _extract_ingredient_names(ingredients: list | None) -> list[str]:
    if not ingredients:
        return []
    names = []
    for ing in ingredients:
        if isinstance(ing, dict):
            name = ing.get("name") or ing.get("canonical_name") or ""
            if name:
                names.append(name)
        elif isinstance(ing, str):
            names.append(ing)
    return names
