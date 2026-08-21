import pytest
from unittest.mock import AsyncMock, patch

from app.ai.hermes_sidecar import HermesSidecar
from app.ai.hermes_orchestrator import HermesOrchestrator
from app.ai.skill_creator import SkillCreator
from app.ai.tool_registry import ToolRegistry
from app.ai.watchdog import WatchdogService
from app.routers import orchestrator as orchestrator_router


@pytest.fixture(autouse=True)
def _reset_orchestrator():
    orchestrator_router._orchestrator = None
    orchestrator_router._watchdog = None
    orchestrator_router._skill_creator = None
    yield
    orchestrator_router._orchestrator = None
    orchestrator_router._watchdog = None
    orchestrator_router._skill_creator = None


@pytest.fixture
def init_orch():
    hermes = HermesSidecar({"available": False})
    registry = ToolRegistry()
    orch = HermesOrchestrator(hermes=hermes, tool_registry=registry)
    watchdog = WatchdogService()
    skill_creator = SkillCreator(tool_registry=registry)
    orchestrator_router.init_orchestrator(orch, watchdog, skill_creator)
    return orch, watchdog, skill_creator


@pytest.mark.asyncio
async def test_orchestrator_message_uninitialized(authenticated_client):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "Analyze markets",
    })
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_orchestrator_message_empty(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_orchestrator_message_ok(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "Analyze markets",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data or "type" in data


@pytest.mark.asyncio
async def test_orchestrator_get_session_uninitialized(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/session/test-session")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_orchestrator_get_session(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/session/test-session")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data


@pytest.mark.asyncio
async def test_orchestrator_clear_session(authenticated_client, init_orch):
    resp = await authenticated_client.delete("/api/orchestrator/session/test-session")
    assert resp.status_code == 200
    assert resp.json()["status"] == "cleared"


@pytest.mark.asyncio
async def test_orchestrator_health(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data


@pytest.mark.asyncio
async def test_orchestrator_list_sessions(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert "sessions" in data


@pytest.mark.asyncio
async def test_orchestrator_create_skill_short_description(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/skill/create", json={
        "description": "Hi",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_orchestrator_create_skill_ok(authenticated_client, init_orch):
    with patch.object(
        orchestrator_router._skill_creator,
        "create_skill_from_description",
        new=AsyncMock(return_value={
            "skill": {"id": "skill_test1", "name": "custom_test1", "description": "Test skill desc"},
            "response": "Skill created",
        }),
    ):
        resp = await authenticated_client.post("/api/orchestrator/skill/create", json={
            "description": "Alert when odds drop below threshold",
        })
    assert resp.status_code == 201
    assert resp.json()["skill"]["id"] == "skill_test1"


@pytest.mark.asyncio
async def test_orchestrator_list_skills(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert "skills" in data


@pytest.mark.asyncio
async def test_orchestrator_spawn_agent(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/spawn", json={
        "goal": "Research prediction markets",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert "agent_id" in data


@pytest.mark.asyncio
async def test_orchestrator_spawn_agent_empty_goal(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/spawn", json={
        "goal": "",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_orchestrator_list_agents(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data


@pytest.mark.asyncio
async def test_orchestrator_list_agents_with_session(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/agents?session_id=test")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data


@pytest.mark.asyncio
async def test_orchestrator_get_traces(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/traces/default")
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data


@pytest.mark.asyncio
async def test_orchestrator_get_traces_with_limit(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/traces/default?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "traces" in data


@pytest.mark.asyncio
async def test_orchestrator_list_goals(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert "goals" in data


@pytest.mark.asyncio
async def test_orchestrator_run_pipeline(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/pipeline", json={
        "message": "Full analysis",
    })
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_orchestrator_unauthorized(client):
    resp = await client.get("/api/orchestrator/health")
    assert resp.status_code == 401
