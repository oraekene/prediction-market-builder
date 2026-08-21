import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_search_uninitialized(client):
    import uuid
    email = f"search-{uuid.uuid4().hex[:8]}@test.com"
    register_resp = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "SearchTest123!",
    })
    if register_resp.status_code != 200:
        pytest.skip("Could not register test user")
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": email, "password": "SearchTest123!",
    })
    token = login_resp.json().get("access_token")
    if not token:
        pytest.skip("Could not get access token")
    from httpx import ASGITransport, AsyncClient
    from app.main import app
    auth_client = AsyncClient(transport=ASGITransport(app=app), base_url="http://test")
    auth_client.headers.update({"Authorization": f"Bearer {token}"})
    resp = await auth_client.post("/api/v1/search", json={
        "query": "prediction markets",
    })
    await auth_client.aclose()
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert data["total_found"] == 0


@pytest.mark.asyncio
async def test_search_with_depth(authenticated_client):
    resp = await authenticated_client.post("/api/v1/search", json={
        "query": "bitcoin price",
        "depth": "quick",
        "max_results": 5,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data


@pytest.mark.asyncio
async def test_search_with_category(authenticated_client):
    resp = await authenticated_client.post("/api/v1/search", json={
        "query": "Fed interest rate",
        "categories": ["news"],
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_empty_query(authenticated_client):
    resp = await authenticated_client.post("/api/v1/search", json={
        "query": "",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_search_status(authenticated_client):
    resp = await authenticated_client.get("/api/v1/search/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data or "error" in data


@pytest.mark.asyncio
async def test_search_unauthorized(client):
    resp = await client.post("/api/v1/search", json={"query": "test"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_search_status_unauthorized(client):
    resp = await client.get("/api/v1/search/status")
    assert resp.status_code == 401
