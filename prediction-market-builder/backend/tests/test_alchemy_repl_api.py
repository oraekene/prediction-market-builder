import pytest
from unittest.mock import AsyncMock, MagicMock

from app.routers import alchemy as alchemy_router
from app.routers import repl as repl_router


@pytest.fixture(autouse=True)
def _reset_services():
    alchemy_router._alchemy_service = None
    repl_router._repl_service = None
    repl_router._session_owners.clear()
    yield
    alchemy_router._alchemy_service = None
    repl_router._repl_service = None
    repl_router._session_owners.clear()


@pytest.mark.asyncio
async def test_alchemy_analyze_uninitialized(authenticated_client):
    resp = await authenticated_client.post("/ai/alchemy/analyze", json={
        "query": "Will ETH reach $5k?",
    })
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_alchemy_analyze_empty_query(authenticated_client):
    alchemy_router._alchemy_service = MagicMock()
    resp = await authenticated_client.post("/ai/alchemy/analyze", json={
        "query": "",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_alchemy_history(authenticated_client):
    svc = MagicMock()
    svc.get_history.return_value = []
    alchemy_router._alchemy_service = svc
    resp = await authenticated_client.get("/ai/alchemy/history")
    assert resp.status_code == 200
    assert resp.json() == []


@pytest.mark.asyncio
async def test_alchemy_get_report(authenticated_client):
    svc = MagicMock()
    svc.get_report.return_value = None
    alchemy_router._alchemy_service = svc
    resp = await authenticated_client.get("/ai/alchemy/history/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_alchemy_analyze_ok(authenticated_client):
    report = MagicMock()
    report.model_dump.return_value = {"query": "test", "connections": []}
    svc = MagicMock()
    svc.analyze = AsyncMock(return_value=report)
    alchemy_router._alchemy_service = svc
    resp = await authenticated_client.post("/ai/alchemy/analyze", json={"query": "test"})
    assert resp.status_code == 200
    assert resp.json()["query"] == "test"


@pytest.fixture
def init_repl():
    from app.ai.repl_service import REPLService
    repl_router.init_repl(REPLService())
    return repl_router._repl_service


@pytest.mark.asyncio
async def test_repl_create_session(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    assert resp.status_code == 201
    data = resp.json()
    assert "session_id" in data


@pytest.mark.asyncio
async def test_repl_execute_code(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    sid = resp.json()["session_id"]
    resp2 = await authenticated_client.post(f"/ai/repl/{sid}/execute", json={"code": "1 + 1"})
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_execute_empty_code(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    sid = resp.json()["session_id"]
    resp2 = await authenticated_client.post(f"/ai/repl/{sid}/execute", json={"code": ""})
    assert resp2.status_code == 400


@pytest.mark.asyncio
async def test_repl_get_state(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    sid = resp.json()["session_id"]
    resp2 = await authenticated_client.get(f"/ai/repl/{sid}/state")
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_get_state_not_found(authenticated_client, init_repl):
    resp = await authenticated_client.get("/ai/repl/nonexistent/state")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_repl_destroy_session(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    sid = resp.json()["session_id"]
    resp2 = await authenticated_client.delete(f"/ai/repl/{sid}")
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_destroy_nonexistent(authenticated_client, init_repl):
    resp = await authenticated_client.delete("/ai/repl/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_repl_execute_complex_code(authenticated_client, init_repl):
    resp = await authenticated_client.post("/ai/repl/create")
    sid = resp.json()["session_id"]
    resp2 = await authenticated_client.post(f"/ai/repl/{sid}/execute", json={
        "code": "import math\nresult = math.sqrt(144)",
    })
    assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_unauthorized(client):
    resp = await client.post("/ai/repl/create")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_alchemy_unauthorized(client):
    resp = await client.post("/ai/alchemy/analyze", json={"query": "test"})
    assert resp.status_code == 401
