import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_endpoint(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_no_auth_required(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_metrics_endpoint_removed(client):
    resp = await client.get("/metrics")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_metrics_requires_auth_for_other_routes(client):
    resp = await client.get("/api/strategies")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_rate_limit_does_not_block_normal(client):
    for _ in range(5):
        resp = await client.get("/health")
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_cors_headers(client):
    resp = await client.options("/health", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "GET",
    })
    assert resp.status_code == 200
    assert "access-control-allow-origin" in resp.headers


@pytest.mark.asyncio
async def test_cors_denied_for_unknown_origin(client):
    resp = await client.options("/health", headers={
        "Origin": "https://evil.com",
        "Access-Control-Request-Method": "GET",
    })
    allow_origin = resp.headers.get("access-control-allow-origin", "")
    assert "evil.com" not in allow_origin


@pytest.mark.asyncio
async def test_middleware_chain_includes_all(client):
    resp = await client.get("/health")
    headers = resp.headers
    assert "X-Request-ID" in headers
    assert "X-Content-Type-Options" in headers
