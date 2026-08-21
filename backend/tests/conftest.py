import os

os.environ.setdefault("SECRET_KEY", "test-secret-key-0123456789abcdef0123456789abcdef")
os.environ.setdefault("ENCRYPTION_KEY", "test-encryption-key-0123456789abcdef")

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool

from app.config import settings
settings.rate_limit_per_minute = 200

from app.main import app
from app.database import Base, get_session

# Import all models so they register in Base.metadata before table creation
from app.models.risk_template import RiskTemplate  # noqa: F401
from app.models.paper_wallet import PaperWallet  # noqa: F401, PaperOrder

# Create test DB with a sync engine so DDL is predictable
DB_PATH = os.path.join(os.path.dirname(__file__), ".pytest_test.db")
SYNC_URL = f"sqlite:///{DB_PATH}"
ASYNC_URL = f"sqlite+aiosqlite:///{DB_PATH}"

_sync_engine = create_engine(SYNC_URL, echo=False)
Base.metadata.create_all(_sync_engine)  # sync create happens once at import time

test_engine = create_async_engine(
    ASYNC_URL,
    echo=False,
    poolclass=NullPool,
    connect_args={"check_same_thread": False},
)
test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with test_async_session() as session:
        yield session


@pytest.fixture(autouse=True)
async def setup_database():
    yield
    # Clean up after each test - clear data but keep tables
    async with test_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())


@pytest.fixture
async def client():
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
async def authenticated_client():
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/auth/register", json={
            "email": "auth-test@test.com",
            "password": "strongpassword123",
        })
        data = resp.json()
        token = data["access_token"]
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {token}"}
    ) as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def low_rate_limit():
    from app.middleware.rate_limit import RateLimitMiddleware
    stack = app.middleware_stack
    old_limit = 60
    while stack:
        if isinstance(stack, RateLimitMiddleware):
            old_limit = stack.requests_per_minute
            stack.requests_per_minute = 3
            stack._requests.clear()
            break
        stack = getattr(stack, "app", None)
    yield
    stack = app.middleware_stack
    while stack:
        if isinstance(stack, RateLimitMiddleware):
            stack.requests_per_minute = old_limit
            break
        stack = getattr(stack, "app", None)


@pytest.fixture
async def session():
    async with test_async_session() as s:
        yield s
        await s.rollback()


@pytest.fixture
def sample_market():
    return {
        "platform": "polymarket",
        "platform_market_id": "test-123",
        "title": "Will candidate X win?",
        "current_odds": 0.65,
        "volume": 1000000,
        "status": "open",
    }
