import pytest

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
    return orch


@pytest.mark.asyncio
async def test_strategy_engine_not_initialized(authenticated_client):
    resp = await authenticated_client.post("/api/strategies/evaluate", json={
        "nodes": [],
        "edges": [],
    })
    assert resp.status_code == 503
    data = resp.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_orchestrator_degraded_response(authenticated_client, init_orch):
    resp = await authenticated_client.post("/api/orchestrator/message", json={
        "message": "test",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data or "type" in data


@pytest.mark.asyncio
async def test_orchestrator_uninitialized_returns_503(authenticated_client):
    resp = await authenticated_client.get("/api/orchestrator/session/test")
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_orchestrator_skills_empty(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/skills")
    assert resp.status_code == 200
    data = resp.json()
    assert data["skills"] == []


@pytest.mark.asyncio
async def test_orchestrator_agents_empty(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["agents"] == []


@pytest.mark.asyncio
async def test_orchestrator_traces_empty(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/traces/default")
    assert resp.status_code == 200
    data = resp.json()
    assert data["traces"] == []


@pytest.mark.asyncio
async def test_orchestrator_goals_empty(authenticated_client, init_orch):
    resp = await authenticated_client.get("/api/orchestrator/goals")
    assert resp.status_code == 200
    data = resp.json()
    assert data["goals"] == []


@pytest.mark.asyncio
async def test_search_degraded(authenticated_client):
    resp = await authenticated_client.post("/api/v1/search", json={"query": "test"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["results"] == []
    assert data["total_found"] == 0


@pytest.mark.asyncio
async def test_analytics_returns_expected_shape(authenticated_client):
    resp = await authenticated_client.get("/api/analytics/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_trades" in data
    assert data["total_trades"] == 0
    assert data["winning_trades"] == 0


@pytest.mark.asyncio
async def test_risk_summary_returns_defaults(authenticated_client):
    resp = await authenticated_client.get("/api/risk/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert data["current_drawdown"] == 0.0
