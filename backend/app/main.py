import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, fridge, recipes
from app.config import get_settings
from app.core.database import engine

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Cookit backend starting up")
    yield
    await engine.dispose()
    logger.info("Cookit backend shut down")


_settings = get_settings()

app = FastAPI(title="Cookit API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _settings.allowed_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api")
app.include_router(fridge.router, prefix="/api")
app.include_router(recipes.router, prefix="/api")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
