import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def _make_authenticated_client(email_suffix: str) -> AsyncClient:
    import asyncio
    from app.database import get_session
    from tests.conftest import override_get_session

    app.dependency_overrides.clear()
    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)

    async def _create():
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post("/api/auth/register", json={
                "email": f"strat-{email_suffix}@test.com",
                "password": "strongpassword123",
            })
            token = resp.json()["access_token"]
        return AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        )

    return asyncio.get_event_loop().run_until_complete(_create())


@pytest.mark.asyncio
async def test_list_strategies_empty(authenticated_client):
    resp = await authenticated_client.get("/api/strategies")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_create_strategy(authenticated_client):
    resp = await authenticated_client.post("/api/strategies", json={
        "name": "Test Strategy",
        "description": "A test strategy",
        "mode": "chat",
        "nodes": [],
        "edges": [],
        "risk_profile": {"max_drawdown": 0.1},
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Strategy"
    assert data["mode"] == "chat"
    assert data["status"] == "draft"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_strategy_minimal(authenticated_client):
    resp = await authenticated_client.post("/api/strategies", json={"name": "Minimal"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Minimal"
    assert data["nodes"] == []
    assert data["edges"] == []


@pytest.mark.asyncio
async def test_get_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "GetTest"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/strategies/{sid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetTest"


@pytest.mark.asyncio
async def test_get_strategy_not_found(authenticated_client):
    resp = await authenticated_client.get("/api/strategies/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "Original"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.put(f"/api/strategies/{sid}", json={"name": "Updated"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "ToDelete"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.delete(f"/api/strategies/{sid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"
    get_resp = await authenticated_client.get(f"/api/strategies/{sid}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_deploy_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "DeployTest"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.post(f"/api/strategies/{sid}/deploy")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_deploy_then_pause_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "PauseTest"})
    sid = create_resp.json()["id"]
    await authenticated_client.post(f"/api/strategies/{sid}/deploy")
    resp = await authenticated_client.post(f"/api/strategies/{sid}/pause")
    assert resp.status_code == 200
    assert resp.json()["status"] == "paused"


@pytest.mark.asyncio
async def test_pause_draft_strategy_fails(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "DraftPause"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.post(f"/api/strategies/{sid}/pause")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_resume_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "ResumeTest"})
    sid = create_resp.json()["id"]
    await authenticated_client.post(f"/api/strategies/{sid}/deploy")
    await authenticated_client.post(f"/api/strategies/{sid}/pause")
    resp = await authenticated_client.post(f"/api/strategies/{sid}/resume")
    assert resp.status_code == 200
    assert resp.json()["status"] == "active"


@pytest.mark.asyncio
async def test_resume_active_strategy_fails(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "ActiveResume"})
    sid = create_resp.json()["id"]
    await authenticated_client.post(f"/api/strategies/{sid}/deploy")
    resp = await authenticated_client.post(f"/api/strategies/{sid}/resume")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_archive_strategy(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "ArchTest"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.post(f"/api/strategies/{sid}/archive")
    assert resp.status_code == 200
    assert resp.json()["status"] == "archived"


@pytest.mark.asyncio
async def test_rollback_strategy_no_history(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "RollTest"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.post(f"/api/strategies/{sid}/rollback")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_get_strategy_history(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "HistTest"})
    sid = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/strategies/{sid}/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_version" in data
    assert "history" in data


@pytest.mark.asyncio
async def test_create_strategy_template(authenticated_client):
    resp = await authenticated_client.post("/api/strategies/templates", json={
        "name": "Test Template",
        "description": "A template",
        "config": {"mode": "chat", "nodes": []},
        "tags": ["trending", "momentum"],
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Test Template"
    assert data["tags"] == ["trending", "momentum"]


@pytest.mark.asyncio
async def test_list_strategy_templates(authenticated_client):
    await authenticated_client.post("/api/strategies/templates", json={"name": "T1", "config": {}})
    await authenticated_client.post("/api/strategies/templates", json={"name": "T2", "config": {}})
    resp = await authenticated_client.get("/api/strategies/templates")
    assert resp.status_code == 200
    assert len(resp.json()) >= 2


@pytest.mark.asyncio
async def test_apply_template(authenticated_client):
    tpl_resp = await authenticated_client.post("/api/strategies/templates", json={
        "name": "ApplyTpl",
        "config": {"mode": "chat", "nodes": [], "edges": []},
    })
    tid = tpl_resp.json()["id"]
    resp = await authenticated_client.post(f"/api/strategies/templates/{tid}/apply")
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "ApplyTpl"
    assert data["mode"] == "chat"


@pytest.mark.asyncio
async def test_apply_template_not_found(authenticated_client):
    resp = await authenticated_client.post("/api/strategies/templates/nonexistent/apply")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_evaluate_strategy_uninitialized(authenticated_client):
    from app.routers import strategies as strategies_router
    original = strategies_router._strategy_engine
    strategies_router._strategy_engine = None
    try:
        resp = await authenticated_client.post("/api/strategies/evaluate", json={
            "nodes": [],
            "edges": [],
        })
        assert resp.status_code == 503
    finally:
        strategies_router._strategy_engine = original


@pytest.mark.asyncio
async def test_get_template(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies/templates", json={
        "name": "GetTpl", "config": {},
    })
    tid = create_resp.json()["id"]
    resp = await authenticated_client.get(f"/api/strategies/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "GetTpl"


@pytest.mark.asyncio
async def test_get_template_not_found(authenticated_client):
    resp = await authenticated_client.get("/api/strategies/templates/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_template(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies/templates", json={
        "name": "OldTpl", "config": {},
    })
    tid = create_resp.json()["id"]
    resp = await authenticated_client.put(f"/api/strategies/templates/{tid}", json={"name": "NewTpl"})
    assert resp.status_code == 200
    assert resp.json()["name"] == "NewTpl"


@pytest.mark.asyncio
async def test_delete_template(authenticated_client):
    create_resp = await authenticated_client.post("/api/strategies/templates", json={
        "name": "DelTpl", "config": {},
    })
    tid = create_resp.json()["id"]
    resp = await authenticated_client.delete(f"/api/strategies/templates/{tid}")
    assert resp.status_code == 200
    assert resp.json()["status"] == "deleted"


@pytest.mark.asyncio
async def test_delete_template_not_found(authenticated_client):
    resp = await authenticated_client.delete("/api/strategies/templates/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_strategy_unauthorized(client):
    resp = await client.get("/api/strategies")
    assert resp.status_code in (401, 403)
