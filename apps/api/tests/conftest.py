import os

# Must be set before any `app.*` import — app/config.py and app/database.py
# read the environment at import time.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("AUTH_DISABLED", "false")
os.environ.setdefault("SESSION_SECRET_KEY", "test-secret-key")
os.environ.setdefault("OPENAI_API_KEY", "")
# The integration suite fires many requests in a tight loop against one
# shared in-process app instance — see app/middleware.py RateLimitMiddleware
# and its production default (120/60s). Not disabling the middleware
# itself, just giving tests enough headroom that suite growth doesn't flake.
os.environ.setdefault("RATE_LIMIT_MAX_REQUESTS", "100000")
# Settings.model_config reads apps/api/.env when present (real values for
# local manual chain testing) — env vars set here take precedence over
# that file (pydantic-settings), but only if set explicitly. Without this,
# a developer's local .env leaks a real chain_private_key into the "chain
# unconfigured" fallback tests and makes the suite non-hermetic.
os.environ.setdefault("CHAIN_PRIVATE_KEY", "")
os.environ.setdefault("REPORT_REGISTRY_CONTRACT_ADDRESS", "")
os.environ.setdefault("SERVICE_PRICING_CONTRACT_ADDRESS", "")
os.environ.setdefault("AGENTOPS_REGISTRY_CONTRACT_ADDRESS", "")

import pytest_asyncio  # noqa: E402
from eth_account import Account  # noqa: E402
from eth_account.messages import encode_defunct  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app import database  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def db_session():
    """A fresh in-memory SQLite database per test, wired in place of the
    app's real database both via the get_db dependency override (used by
    every request-scoped route) AND by swapping app.database's module-level
    async_session_factory (used by scan_service.run_scan and
    jobs/tasks.py, which open their own session directly since a
    BackgroundTasks-run pipeline outlives the request that started it — see
    scan_service.py's docstring). Without patching the latter too, a scan
    started through the real API would run its background pipeline against
    a second, table-less in-memory database and fail with "no such table"
    — isolated from the actual apps/api/data/agentops.db file either way.
    """
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
    original_session_factory = database.async_session_factory
    database.async_session_factory = session_factory
    try:
        async with session_factory() as session:
            yield session
    finally:
        app.dependency_overrides.pop(get_db, None)
        database.async_session_factory = original_session_factory
        await engine.dispose()


@pytest_asyncio.fixture
async def client(db_session):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def logged_in_client(client):
    """An AsyncClient already holding a valid session cookie for a freshly
    created workspace — the same wallet challenge-response flow
    test_auth_wallet.py exercises directly, factored out here so other
    integration tests (scan pipeline, marketplace invoke) don't each have
    to reimplement wallet login just to get an authenticated client."""
    account = Account.create()
    nonce_resp = await client.post("/api/v1/auth/wallet/nonce", json={"address": account.address})
    body = nonce_resp.json()
    signed = Account.sign_message(encode_defunct(text=body["message"]), private_key=account.key)
    resp = await client.post(
        "/api/v1/auth/wallet/verify",
        json={
            "address": account.address,
            "signature": signed.signature.hex(),
            "nonce": body["nonce"],
        },
    )
    assert resp.status_code == 200
    return client
