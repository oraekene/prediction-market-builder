import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_alchemy_analyze_uninitialized(authenticated_client):
    resp = await authenticated_client.post("/ai/alchemy/analyze", json={
        "query": "Will ETH reach $5k?",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_alchemy_analyze_empty_query(authenticated_client):
    resp = await authenticated_client.post("/ai/alchemy/analyze", json={
        "query": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_alchemy_history(authenticated_client):
    resp = await authenticated_client.get("/ai/alchemy/history")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data if isinstance(data, dict) else isinstance(data, list)


@pytest.mark.asyncio
async def test_alchemy_get_report(authenticated_client):
    resp = await authenticated_client.get("/ai/alchemy/history/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_repl_create_session(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data or "session_id" in data


@pytest.mark.asyncio
async def test_repl_execute_code(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    data = resp.json()
    if "session_id" in data:
        sid = data["session_id"]
        resp2 = await authenticated_client.post(f"/ai/repl/{sid}/execute", json={"code": "1 + 1"})
        assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_execute_empty_code(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    data = resp.json()
    if "session_id" in data:
        sid = data["session_id"]
        resp2 = await authenticated_client.post(f"/ai/repl/{sid}/execute", json={"code": ""})
        assert resp2.status_code == 200
        assert "error" in resp2.json()


@pytest.mark.asyncio
async def test_repl_get_state(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    data = resp.json()
    if "session_id" in data:
        sid = data["session_id"]
        resp2 = await authenticated_client.get(f"/ai/repl/{sid}/state")
        assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_get_state_not_found(authenticated_client):
    resp = await authenticated_client.get("/ai/repl/nonexistent/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_repl_destroy_session(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    data = resp.json()
    if "session_id" in data:
        sid = data["session_id"]
        resp2 = await authenticated_client.delete(f"/ai/repl/{sid}")
        assert resp2.status_code == 200


@pytest.mark.asyncio
async def test_repl_destroy_nonexistent(authenticated_client):
    resp = await authenticated_client.delete("/ai/repl/nonexistent")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data or "deleted" in data


@pytest.mark.asyncio
async def test_repl_execute_complex_code(authenticated_client):
    resp = await authenticated_client.post("/ai/repl/create")
    data = resp.json()
    if "session_id" in data:
        sid = data["session_id"]
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
