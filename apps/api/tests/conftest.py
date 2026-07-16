import os

# Must be set before any `app.*` import — app/config.py and app/database.py
# read the environment at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AUTH_DISABLED", "false")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "")

import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    """A fresh in-memory SQLite database per test, wired in place of the
    app's real database via dependency override — isolated from the actual
    apps/api/data/agentops.db file."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def _get_db():
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = _get_db
    try:
        async with session_factory() as session:
            yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
