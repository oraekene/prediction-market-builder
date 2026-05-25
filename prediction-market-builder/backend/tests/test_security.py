import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_no_auth_token(client):
    resp = await client.get("/api/strategies")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_invalid_token(client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test",
                           headers={"Authorization": "Bearer invalidtoken123"}) as ac:
        resp = await ac.get("/api/strategies")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_expired_malformed_token(client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test",
                           headers={"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiJ0ZXN0In0.invalidsignature"}) as ac:
        resp = await ac.get("/api/strategies")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_empty_auth_header(client):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test",
                           headers={"Authorization": ""}) as ac:
        resp = await ac.get("/api/strategies")
        assert resp.status_code == 401


@pytest.mark.asyncio
async def test_sql_injection_login(client):
    resp = await client.post("/api/auth/login", json={
        "email": "' OR 1=1 --",
        "password": "' OR '1'='1",
    })
    assert resp.status_code in (401, 403, 422)


@pytest.mark.asyncio
async def test_xss_in_strategy_name(authenticated_client):
    resp = await authenticated_client.post("/api/strategies", json={
        "name": "<script>alert('XSS')</script>",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "<script>" in data["name"]


@pytest.mark.asyncio
async def test_large_payload(authenticated_client):
    resp = await authenticated_client.post("/api/strategies/evaluate", json={
        "nodes": [{"id": f"n{i}", "type": "performance", "position": {"x": i, "y": i}, "data": {"metric": "sharpe"}} for i in range(1000)],
        "edges": [],
    })
    assert resp.status_code in (200, 413, 422, 503)


@pytest.mark.asyncio
async def test_path_traversal(client):
    resp = await client.get("/api/strategies/../../etc/passwd")
    assert resp.status_code in (401, 403, 404, 422)


@pytest.mark.asyncio
async def test_duplicate_registration(client, session):
    from app.database import get_session
    from tests.conftest import override_get_session
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp1 = await ac.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "strongpassword123",
        })
        assert resp1.status_code == 200
        resp2 = await ac.post("/api/auth/register", json={
            "email": "dup@test.com", "password": "strongpassword123",
        })
        assert resp2.status_code in (400, 409)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_weak_password_registration(client, session):
    from app.database import get_session
    from tests.conftest import override_get_session
    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/auth/register", json={
            "email": "weak@test.com", "password": "ab",
        })
        assert resp.status_code in (200, 400, 422)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_security_headers(client):
    resp = await client.get("/health")
    assert resp.headers.get("X-Content-Type-Options") == "nosniff"
    assert resp.headers.get("X-Frame-Options") == "DENY"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
    assert resp.headers.get("Strict-Transport-Security") is not None
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"


@pytest.mark.asyncio
async def test_request_id_header(client):
    resp = await client.get("/health", headers={"X-Request-ID": "my-custom-id"})
    assert resp.headers.get("X-Request-ID") == "my-custom-id"


@pytest.mark.asyncio
async def test_request_id_generated(client):
    resp = await client.get("/health")
    rid = resp.headers.get("X-Request-ID")
    assert rid is not None
    assert len(rid) > 0


@pytest.mark.asyncio
async def test_unsupported_method(client):
    resp = await client.put("/health")
    assert resp.status_code == 405


@pytest.mark.asyncio
async def test_nonexistent_route(client):
    resp = await client.get("/api/nonexistent/route")
    assert resp.status_code == 404
