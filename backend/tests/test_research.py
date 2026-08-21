import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.backtester import BacktestResult

# Ensure models are registered with Base.metadata before API tests
from app.models import (ResearchSession, ExperimentResult, ResearchSessionConfig)  # noqa: F401


@pytest.mark.asyncio
async def test_autoresearch_run_iteration():
    from app.ai.autoresearch import AutoresearchService
    mock_tabpfn = AsyncMock()
    mock_tabpfn.predict_probability.return_value = 0.65
    mock_tabpfn.validate_signal.return_value = {
        "probability": 0.68,
        "confidence": 0.55,
        "edge": 0.03,
        "verdict": "APPROVED",
    }
    mock_tabpfn.get_feature_importance.return_value = {"odds": 0.4, "volume": 0.3}

    service = AutoresearchService(tabpfn_service=mock_tabpfn)
    result = await service.run_iteration(
        strategy_id="test-strat",
        market_history=[{"current_odds": 0.5, "volume": 1000000, "liquidity": 500000}],
        climate={"regime": "trending", "metrics": {"volatility": 0.05}},
    )
    assert "verdict" in result
    assert result["verdict"] in ("KEPT", "WARN", "REVERTED", "SKIPPED")
    assert "composite_score" in result
    assert "hypothesis" in result


@pytest.mark.asyncio
async def test_autoresearch_composite_scores():
    from app.ai.autoresearch import AutoresearchService, _dict_to_df
    service = AutoresearchService(tabpfn_service=MagicMock())

    result = BacktestResult()
    result.trades = [
        {"type": "exit", "pnl": 100, "entry_price": 0.5},
        {"type": "exit", "pnl": 200, "entry_price": 0.5},
        {"type": "exit", "pnl": -50, "entry_price": 0.5},
    ]
    result.current_capital = 10250.0

    tabpfn_result = {"probability": 0.7, "confidence": 0.6}

    sharpe_score = service._compute_composite_score(result, 1.0, tabpfn_result, "sharpe_max")
    assert sharpe_score > 0

    win_rate_score = service._compute_composite_score(result, 1.0, tabpfn_result, "win_rate_max")
    assert 0 <= win_rate_score <= 3

    risk_adj_score = service._compute_composite_score(result, 1.0, tabpfn_result, "risk_adjusted")
    assert risk_adj_score > 0


@pytest.mark.asyncio
async def test_autoresearch_quick_rejection():
    from app.ai.autoresearch import AutoresearchService
    mock_tabpfn = AsyncMock()
    mock_tabpfn.predict_probability.return_value = 0.75
    service = AutoresearchService(tabpfn_service=mock_tabpfn)

    hypotheses = [
        {"description": "test1", "operator": "gt", "threshold": 0.6, "regime_affinity": ["trending"]},
        {"description": "test2", "operator": "lt", "threshold": 0.4, "regime_affinity": ["calm"]},
    ]
    surviving = await service._quick_rejection(hypotheses, {"current_odds": 0.5})
    assert len(surviving) == 2


@pytest.mark.asyncio
async def test_autoresearch_hypothesis_generation():
    from app.ai.autoresearch import AutoresearchService
    service = AutoresearchService(tabpfn_service=MagicMock())

    hypotheses = await service._generate_hypotheses(
        climate={"regime": "trending", "metrics": {}},
        feature_importance={"volume_momentum": 0.4, "odds_acceleration": 0.3},
        n=3,
    )
    assert len(hypotheses) <= 3
    for h in hypotheses:
        assert "description" in h
        assert "operator" in h
        assert "threshold" in h


@pytest.mark.asyncio
async def test_autoresearch_determine_verdict():
    from app.ai.autoresearch import AutoresearchService
    service = AutoresearchService(tabpfn_service=MagicMock())

    result = BacktestResult()
    result.trades = [{"type": "exit", "pnl": 100, "entry_price": 0.5}]

    assert service._determine_verdict(1.8) == "KEPT"
    assert service._determine_verdict(0.6) == "KEPT"
    assert service._determine_verdict(0.5) == "WARN"
    assert service._determine_verdict(0.3) == "REVERTED"


@pytest.mark.asyncio
async def test_research_session_model():
    from app.models.research_session import ResearchSession, SessionStatus, SessionMode
    session = ResearchSession(
        user_id="user-1",
        strategy_id="strat-1",
        status=SessionStatus.RUNNING,
        mode=SessionMode.MANUAL,
    )
    assert session.status == SessionStatus.RUNNING
    assert session.current_iteration == 0 or session.current_iteration is None
    assert session.total_kept == 0 or session.total_kept is None


@pytest.mark.asyncio
async def test_experiment_result_model():
    from app.models.experiment_result import ExperimentResult
    result = ExperimentResult(
        session_id="session-1",
        iteration=1,
        hypothesis="volume_momentum_breakout",
        verdict="KEPT",
        composite_score=1.82,
    )
    assert result.hypothesis == "volume_momentum_breakout"
    assert result.verdict == "KEPT"


@pytest.mark.asyncio
async def test_research_config_model():
    from app.models.research_config import ResearchSessionConfig
    config = ResearchSessionConfig(
        user_id="user-1",
        max_concurrent=3,
        composite_preset="risk_adjusted",
    )
    assert config.user_id == "user-1"
    assert config.max_concurrent == 3


@pytest.mark.asyncio
async def test_research_api_stats(authenticated_client):
    response = await authenticated_client.get("/api/research/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "avg_sharpe" in data


@pytest.mark.asyncio
async def test_research_api_config(authenticated_client):
    response = await authenticated_client.put("/api/research/config?preset=risk_adjusted&max_concurrent=3")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"


@pytest.mark.asyncio
async def test_research_api_climate(authenticated_client):
    response = await authenticated_client.get("/api/research/climate")
    assert response.status_code == 200
    data = response.json()
    assert "regime" in data


# ── New tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_research_session_defaults():
    from app.models.research_session import ResearchSession, SessionStatus, SessionMode, CompositePreset
    session = ResearchSession(
        user_id="user-test",
        strategy_id="strat-test",
    )
    assert session.user_id == "user-test"
    assert session.strategy_id == "strat-test"
    assert session.id is None or len(session.id) > 0
    assert session.status == SessionStatus.RUNNING or session.status is None
    assert session.mode == SessionMode.MANUAL or session.mode is None
    assert session.composite_preset == CompositePreset.SHARPE_MAX or session.composite_preset is None
    assert session.current_iteration == 0 or session.current_iteration is None
    assert session.total_kept == 0 or session.total_kept is None


@pytest.mark.asyncio
async def test_experiment_result_defaults():
    from app.models.experiment_result import ExperimentResult
    result = ExperimentResult(
        session_id="session-test",
        iteration=1,
        hypothesis="test_hypothesis",
        verdict="KEPT",
        composite_score=1.5,
    )
    assert result.session_id == "session-test"
    assert result.hypothesis == "test_hypothesis"
    assert result.verdict == "KEPT"
    assert result.composite_score == 1.5
    assert result.id is None or len(result.id) > 0
    assert result.backtest_trades == 0 or result.backtest_trades is None
    assert result.backtest_win_rate == 0.0 or result.backtest_win_rate is None
    assert result.backtest_sharpe == 0.0 or result.backtest_sharpe is None
    assert result.tabpfn_probability == 0.0 or result.tabpfn_probability is None
    assert result.hypothesis_prompt is None


@pytest.mark.asyncio
async def test_autoresearch_composite_scores_edge():
    from app.ai.autoresearch import AutoresearchService
    service = AutoresearchService(tabpfn_service=MagicMock())
    result = BacktestResult()
    tabpfn_result = {"probability": 0.5, "confidence": 0.0}
    score = service._compute_composite_score(result, 0.0, tabpfn_result, "sharpe_max")
    assert score == pytest.approx(0.15)


@pytest.mark.asyncio
async def test_autoresearch_empty_hypotheses():
    from app.ai.autoresearch import AutoresearchService
    service = AutoresearchService(tabpfn_service=MagicMock())
    hypotheses = await service._generate_hypotheses(
        climate={"regime": "trending", "metrics": {}},
        feature_importance={"volume_momentum": 0.4},
        n=0,
    )
    assert hypotheses == []


@pytest.mark.asyncio
async def test_autoresearch_determine_verdict_skip():
    from app.ai.autoresearch import AutoresearchService
    service = AutoresearchService(tabpfn_service=MagicMock())
    result = BacktestResult()
    result.trades = [{"type": "exit", "pnl": 0, "entry_price": 0.5}]
    assert service._determine_verdict(0.2) == "REVERTED"


@pytest.mark.asyncio
async def test_autoresearch_quick_rejection_no_match():
    from app.ai.autoresearch import AutoresearchService
    mock_tabpfn = AsyncMock()
    mock_tabpfn.predict_probability.return_value = 0.3
    service = AutoresearchService(tabpfn_service=mock_tabpfn)
    hypotheses = [
        {"description": "test1", "operator": "gt", "threshold": 100, "regime_affinity": ["trending"]},
        {"description": "test2", "operator": "lt", "threshold": 0.01, "regime_affinity": ["calm"]},
    ]
    surviving = await service._quick_rejection(hypotheses, {"current_odds": 0.5})
    assert len(surviving) == 0


# ── Integration/API tests ──────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_research_api_config_defaults(authenticated_client):
    response = await authenticated_client.get("/api/research/config")
    assert response.status_code == 200
    data = response.json()
    assert data["preset"] == "sharpe_max"
    assert data["max_concurrent"] == 2
    assert data["cron_enabled"] is False


@pytest.mark.asyncio
async def test_research_api_config_roundtrip(authenticated_client):
    put_resp = await authenticated_client.put(
        "/api/research/config",
        params={"preset": "risk_adjusted", "max_concurrent": 3},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["status"] == "updated"

    get_resp = await authenticated_client.get("/api/research/config")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["preset"] == "risk_adjusted"
    assert data["max_concurrent"] == 3
