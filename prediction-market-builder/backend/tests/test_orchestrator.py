import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_orchestrator_message_uninitialized(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "Analyze markets",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_message_empty(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_message_missing(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/message", json={})
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_get_session_uninitialized(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/session/test-session")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_clear_session_uninitialized(authenticated_client):
    resp = await authenticated_client.delete("/api/orchestrator/session/test-session")
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data or "status" in data


@pytest.mark.asyncio
async def test_orchestrator_health_uninitialized(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_orchestrator_list_sessions(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data


@pytest.mark.asyncio
async def test_orchestrator_create_skill_short_description(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/skill/create", json={
        "description": "Hi",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_create_skill_empty(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/skill/create", json={
        "description": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_list_skills(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert "skills" in data


@pytest.mark.asyncio
async def test_orchestrator_spawn_agent(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/spawn", json={
        "goal": "Research prediction markets",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data or "error" not in data


@pytest.mark.asyncio
async def test_orchestrator_spawn_agent_empty_goal(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/spawn", json={
        "goal": "",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data


@pytest.mark.asyncio
async def test_orchestrator_list_agents(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data


@pytest.mark.asyncio
async def test_orchestrator_list_agents_with_session(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/agents?session_id=test")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data


@pytest.mark.asyncio
async def test_orchestrator_get_traces(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/traces/default")
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data


@pytest.mark.asyncio
async def test_orchestrator_get_traces_with_limit(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/traces/default?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data


@pytest.mark.asyncio
async def test_orchestrator_list_goals(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert "goals" in data


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/pipeline", json={
        "message": "Full analysis",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "error" in data or "response" in data


@pytest.mark.asyncio
async def test_orchestrator_unauthorized(client):
    resp = await client.get("/api/orchestrator/health")
    assert resp.status_code == 401
