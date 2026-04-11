import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import get_db
from app.core.security import create_access_token, get_password_hash
from app.main import app
from app.models.db import Base, User

TEST_DATABASE_URL = "postgresql+asyncpg://cookit:cookit@localhost:5432/cookit_test"

test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestSessionFactory = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session", autouse=True)
async def create_tables():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async with TestSessionFactory() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash=get_password_hash("testpass"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(client: AsyncClient, test_user: User) -> AsyncClient:
    token = create_access_token(str(test_user.id))
    client.cookies.set("access_token", token)
    return client


@pytest.fixture
def mock_anthropic(monkeypatch):
    mock = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '[{"item_name":"chicken breast","category":"protein","quantity":2,"unit":"count","confidence":0.95}]'
    mock_response = MagicMock()
    mock_response.content = [mock_content]
    mock.messages = MagicMock()
    mock.messages.create = AsyncMock(return_value=mock_response)
    monkeypatch.setattr("app.services.vision.client", mock)
    monkeypatch.setattr("app.services.normalize.client", mock)
    monkeypatch.setattr("app.services.recommend.client", mock)
    return mock
