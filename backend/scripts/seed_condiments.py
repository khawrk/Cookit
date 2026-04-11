"""Seed the condiments_catalog table from db/seeds/condiments.csv."""
import asyncio
import csv
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CSV_PATH = Path(__file__).parent.parent.parent / "db" / "seeds" / "condiments.csv"


async def seed() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable not set")

    engine = create_async_engine(database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    rows: list[dict] = []
    with CSV_PATH.open() as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    async with session_factory() as session:
        async with session.begin():
            for row in rows:
                await session.execute(
                    text(
                        """
                        INSERT INTO condiments_catalog (name, category, default_unit)
                        VALUES (:name, :category, :default_unit)
                        ON CONFLICT (name) DO NOTHING
                        """
                    ),
                    {"name": row["name"], "category": row["category"], "default_unit": row["default_unit"]},
                )
    logger.info("Seeded %d condiments", len(rows))
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
