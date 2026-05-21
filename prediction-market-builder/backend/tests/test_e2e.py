"""End-to-end tests covering full app lifecycle: startup, CRUD, teardown."""

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.main import app
from app.database import Base, get_session

test_engine = create_async_engine("sqlite+aiosqlite://", echo=False)
test_async_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_session():
    async with test_async_session() as session:
        yield session


@pytest.fixture
async def e2e_client():
    app.dependency_overrides[get_session] = override_get_session
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def test_health_endpoint(e2e_client):
    response = await e2e_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


async def test_strategy_full_lifecycle(e2e_client):
    response = await e2e_client.post("/api/strategies", json={
        "name": "E2E Strategy", "description": "e2e test", "mode": "chat",
    })
    assert response.status_code == 200
    sid = response.json()["id"]

    response = await e2e_client.get(f"/api/strategies/{sid}")
    assert response.status_code == 200
    assert response.json()["name"] == "E2E Strategy"

    response = await e2e_client.put(f"/api/strategies/{sid}", json={"name": "Updated"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated"

    response = await e2e_client.get("/api/strategies")
    assert response.status_code == 200
    ids = [s["id"] for s in response.json()]
    assert sid in ids

    response = await e2e_client.delete(f"/api/strategies/{sid}")
    assert response.status_code == 200

    response = await e2e_client.get(f"/api/strategies/{sid}")
    assert response.status_code == 404


async def test_template_full_lifecycle(e2e_client):
    response = await e2e_client.post("/api/strategies/templates", json={
        "name": "E2E Template", "config": {"mode": "chat"}, "tags": ["e2e"],
    })
    assert response.status_code == 200
    tid = response.json()["id"]

    response = await e2e_client.get(f"/api/strategies/templates/{tid}")
    assert response.status_code == 200
    assert response.json()["name"] == "E2E Template"

    response = await e2e_client.put(f"/api/strategies/templates/{tid}", json={"name": "Updated Template"})
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Template"

    response = await e2e_client.post(f"/api/strategies/templates/{tid}/apply")
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Template"

    response = await e2e_client.delete(f"/api/strategies/templates/{tid}")
    assert response.status_code == 200


async def test_nonexistent_returns_404(e2e_client):
    response = await e2e_client.get("/api/strategies/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Strategy not found"

    response = await e2e_client.get("/api/strategies/templates/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Template not found"

    response = await e2e_client.delete("/api/strategies/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Strategy not found"

    response = await e2e_client.put("/api/strategies/nonexistent-id", json={"name": "Nope"})
    assert response.status_code == 404
