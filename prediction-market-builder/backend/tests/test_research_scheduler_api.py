import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone
from uuid import uuid4

from app.models.research_session import SessionStatus, SessionMode, CompositePreset
from app.routers import research as research_router


def make_mock_session(**overrides):
    now = datetime.now(timezone.utc)
    s = MagicMock()
    s.id = str(uuid4())
    s.user_id = "default"
    s.strategy_id = None
    s.status = SessionStatus.RUNNING
    s.mode = SessionMode.MANUAL
    s.trigger_type = "manual"
    s.composite_preset = CompositePreset.SHARPE_MAX
    s.current_iteration = 0
    s.total_kept = 0
    s.total_reverted = 0
    s.avg_sharpe = 0.0
    s.avg_win_rate = 0.0
    s.best_sharpe = 0.0
    s.best_win_rate = 0.0
    s.rlm_alpha_vector_id = None
    s.toto2_regime = None
    s.toto2_volatility = None
    s.tabpfn_top_features = None
    s.hypothesis_count = 0
    s.error_message = None
    s.created_at = now
    s.updated_at = now
    for k, v in overrides.items():
        setattr(s, k, v)
    return s


def make_mock_result(**overrides):
    now = datetime.now(timezone.utc)
    r = MagicMock()
    r.id = str(uuid4())
    r.iteration = 1
    r.hypothesis = "test_hypothesis"
    r.regime_at_time = "trending"
    r.backtest_trades = 10
    r.backtest_win_rate = 0.65
    r.backtest_sharpe = 1.5
    r.backtest_max_drawdown = -0.1
    r.backtest_total_pnl = 500.0
    r.tabpfn_probability = 0.7
    r.tabpfn_confidence = 0.6
    r.composite_score = 1.8
    r.verdict = "KEPT"
    r.git_commit_hash = None
    r.created_at = now
    for k, v in overrides.items():
        setattr(r, k, v)
    return r


@pytest.fixture
def mock_scheduler():
    original = research_router.scheduler
    mock = AsyncMock()
    research_router.scheduler = mock
    yield mock
    research_router.scheduler = original


@pytest.fixture
def no_scheduler():
    original = research_router.scheduler
    research_router.scheduler = None
    yield
    research_router.scheduler = original


# ── POST /api/research/run ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.post("/api/research/run")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_run_success(authenticated_client, mock_scheduler):
    session = make_mock_session()
    mock_scheduler.start_session.return_value = session
    response = await authenticated_client.post("/api/research/run")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["status"] == "started"
    mock_scheduler.start_session.assert_awaited_once()
    call_kwargs = mock_scheduler.start_session.call_args.kwargs
    assert call_kwargs["mode"] == SessionMode.MANUAL
    assert call_kwargs["trigger_type"] == "manual"


@pytest.mark.asyncio
async def test_run_concurrency_limit(authenticated_client, mock_scheduler):
    mock_scheduler.start_session.return_value = None
    response = await authenticated_client.post("/api/research/run")
    assert response.status_code == 429


# ── POST /api/research/run-continuous ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_run_continuous_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.post("/api/research/run-continuous")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_run_continuous_success(authenticated_client, mock_scheduler):
    session = make_mock_session()
    mock_scheduler.start_session.return_value = session
    response = await authenticated_client.post("/api/research/run-continuous")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["status"] == "started"
    call_kwargs = mock_scheduler.start_session.call_args.kwargs
    assert call_kwargs["mode"] == SessionMode.CONTINUOUS
    assert call_kwargs["trigger_type"] == "continuous"


@pytest.mark.asyncio
async def test_run_continuous_concurrency_limit(authenticated_client, mock_scheduler):
    mock_scheduler.start_session.return_value = None
    response = await authenticated_client.post("/api/research/run-continuous")
    assert response.status_code == 429


# ── POST /api/research/stop ────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_stop_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.post("/api/research/stop", params={"session_id": "test"})
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_stop_success(authenticated_client, mock_scheduler):
    mock_scheduler.stop_session.return_value = True
    response = await authenticated_client.post("/api/research/stop", params={"session_id": "sess-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"
    mock_scheduler.stop_session.assert_awaited_once_with("sess-1")


@pytest.mark.asyncio
async def test_stop_not_found(authenticated_client, mock_scheduler):
    mock_scheduler.stop_session.return_value = False
    response = await authenticated_client.post("/api/research/stop", params={"session_id": "bad-id"})
    assert response.status_code == 404


# ── POST /api/research/sessions ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_session_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.post("/api/research/sessions")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_create_session_success(authenticated_client, mock_scheduler):
    session = make_mock_session()
    mock_scheduler.start_session.return_value = session
    response = await authenticated_client.post("/api/research/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == session.id
    assert data["status"] == "created"


@pytest.mark.asyncio
async def test_create_session_concurrency_limit(authenticated_client, mock_scheduler):
    mock_scheduler.start_session.return_value = None
    response = await authenticated_client.post("/api/research/sessions")
    assert response.status_code == 429


# ── GET /api/research/sessions ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_sessions_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.get("/api/research/sessions")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_list_sessions_empty(authenticated_client, mock_scheduler):
    mock_scheduler.get_user_sessions.return_value = []
    response = await authenticated_client.get("/api/research/sessions")
    assert response.status_code == 200
    data = response.json()
    assert data["sessions"] == []
    assert data["total"] == 0


@pytest.mark.asyncio
async def test_list_sessions_with_data(authenticated_client, mock_scheduler):
    session = make_mock_session(
        id="list-sess-1",
        current_iteration=5,
        total_kept=3,
        avg_sharpe=1.2,
        best_sharpe=2.0,
    )
    mock_scheduler.get_user_sessions.return_value = [session]
    response = await authenticated_client.get("/api/research/sessions")
    assert response.status_code == 200
    data = response.json()
    assert len(data["sessions"]) == 1
    assert data["total"] == 1
    s = data["sessions"][0]
    assert s["id"] == "list-sess-1"
    assert s["status"] == SessionStatus.RUNNING.value
    assert s["mode"] == SessionMode.MANUAL.value
    assert s["current_iteration"] == 5


# ── GET /api/research/sessions/{session_id} ────────────────────────────────────


@pytest.mark.asyncio
async def test_get_session_detail_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.get("/api/research/sessions/test-id")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_session_detail_found(authenticated_client, mock_scheduler):
    session = make_mock_session(
        id="detail-sess-1",
        strategy_id="strat-a",
        current_iteration=10,
        total_kept=7,
    )
    mock_scheduler.get_session.return_value = session
    response = await authenticated_client.get("/api/research/sessions/detail-sess-1")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == "detail-sess-1"
    assert data["strategy_id"] == "strat-a"
    assert data["current_iteration"] == 10
    assert data["status"] == SessionStatus.RUNNING.value


@pytest.mark.asyncio
async def test_get_session_detail_not_found(authenticated_client, mock_scheduler):
    mock_scheduler.get_session.return_value = None
    response = await authenticated_client.get("/api/research/sessions/nonexistent")
    assert response.status_code == 404


# ── GET /api/research/sessions/{session_id}/results ────────────────────────────


@pytest.mark.asyncio
async def test_get_session_results_no_scheduler(authenticated_client, no_scheduler):
    response = await authenticated_client.get("/api/research/sessions/test-id/results")
    assert response.status_code == 503


@pytest.mark.asyncio
async def test_get_session_results_with_data(authenticated_client, mock_scheduler):
    result = make_mock_result(iteration=1, verdict="KEPT", composite_score=1.8)
    mock_scheduler.get_session_results.return_value = [result]
    response = await authenticated_client.get("/api/research/sessions/test-id/results")
    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["total"] == 1
    r = data["results"][0]
    assert r["iteration"] == 1
    assert r["verdict"] == "KEPT"
    assert r["composite_score"] == 1.8


@pytest.mark.asyncio
async def test_get_session_results_empty(authenticated_client, mock_scheduler):
    mock_scheduler.get_session_results.return_value = []
    response = await authenticated_client.get("/api/research/sessions/test-id/results")
    assert response.status_code == 200
    data = response.json()
    assert data["results"] == []
    assert data["total"] == 0
