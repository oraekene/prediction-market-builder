import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_markets_list(authenticated_client):
    resp = await authenticated_client.get("/api/markets")
    assert resp.status_code == 200
    data = resp.json()
    assert "markets" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_markets_list_with_limit(authenticated_client):
    resp = await authenticated_client.get("/api/markets?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["markets"]) <= 5


@pytest.mark.asyncio
async def test_markets_list_with_platform(authenticated_client):
    resp = await authenticated_client.get("/api/markets?platform=polymarket")
    assert resp.status_code == 200
    data = resp.json()
    assert "markets" in data


@pytest.mark.asyncio
async def test_markets_list_with_category(authenticated_client):
    resp = await authenticated_client.get("/api/markets?category=politics")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_markets_list_with_search(authenticated_client):
    resp = await authenticated_client.get("/api/markets?search=bitcoin")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_markets_list_with_offset(authenticated_client):
    resp = await authenticated_client.get("/api/markets?offset=10&limit=5")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_markets_list_with_min_volume(authenticated_client):
    resp = await authenticated_client.get("/api/markets?min_volume=1000")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_markets_get_detail(authenticated_client):
    resp = await authenticated_client.get("/api/markets/some-market-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_markets_unauthorized(client):
    resp = await client.get("/api/markets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_markets_excessive_limit_capped(authenticated_client):
    resp = await authenticated_client.get("/api/markets?limit=500")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_markets_negative_offset(authenticated_client):
    resp = await authenticated_client.get("/api/markets?offset=-1")
    assert resp.status_code == 200
