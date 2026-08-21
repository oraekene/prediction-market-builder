import pytest

from app.main import app


@pytest.mark.asyncio
async def test_explainability_get_explanation_not_found(authenticated_client):
    resp = await authenticated_client.get("/api/explainability/nonexistent-id")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_explainability_post_explain(authenticated_client):
    resp = await authenticated_client.post("/api/explainability/explain", json={
        "features": {"odds": 0.6, "volume": 100000},
    })
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_explainability_post_explain_with_regime(authenticated_client):
    resp = await authenticated_client.post("/api/explainability/explain", json={
        "features": {"odds": 0.6, "volume": 100000},
        "regime_vector": [0.1, 0.2, 0.3],
    })
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_explainability_empty_features(authenticated_client):
    resp = await authenticated_client.post("/api/explainability/explain", json={
        "features": {},
    })
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_explainability_missing_body(authenticated_client):
    resp = await authenticated_client.post("/api/explainability/explain", json={})
    assert resp.status_code in (200, 503)


@pytest.mark.asyncio
async def test_explainability_get_session_aggregate_empty(authenticated_client):
    resp = await authenticated_client.get("/api/explainability/session/nonexistent/aggregate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["aggregate"] is None
    assert data["count"] == 0


@pytest.mark.asyncio
async def test_explainability_unauthorized(client):
    resp = await client.get("/api/explainability/test-id")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_explainability_post_unauthorized(client):
    resp = await client.post("/api/explainability/explain", json={"features": {}})
    assert resp.status_code == 401
