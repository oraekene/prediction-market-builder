import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone

from app.services.backtester import BacktestResult

# Ensure models are registered with Base.metadata before API tests
from app.models import (ResearchSession, ExperimentResult, RLMAlphaVector, ResearchSessionConfig)  # noqa: F401


@pytest.mark.asyncio
async def test_rlm_service_fallback_scan():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("This file mentions oracle-lag and slippage-limit")
        result = await service.scan_directory(tmpdir, keywords=["oracle-lag", "slippage"])
        assert "alpha_vector" in result
        assert "findings" in result["alpha_vector"]


@pytest.mark.asyncio
async def test_rlm_service_fallback_text_batch():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.scan_text_batch(
        ["forum post about sentiment", "another post about momentum"],
        "Find alpha signals",
    )
    assert "alpha_vector" in result


@pytest.mark.asyncio
async def test_rlm_service_drift_fallback():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.detect_linguistic_drift(
        ["old post"], ["new post"], ["manager"]
    )
    assert "drift_scores" in result
    assert result["drift_scores"]["manager"]["drift_score"] == 0.0


@pytest.mark.asyncio
async def test_rlm_service_source_hash():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("path/to/data")
    h2 = service.compute_source_hash("path/to/data")
    assert h1 == h2
    h3 = service.compute_source_hash("different/path")
    assert h1 != h3


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

    sharpe_score = service._compute_composite_score(result, tabpfn_result, "sharpe_max")
    assert sharpe_score > 0

    win_rate_score = service._compute_composite_score(result, tabpfn_result, "win_rate_max")
    assert 0 <= win_rate_score <= 3

    risk_adj_score = service._compute_composite_score(result, tabpfn_result, "risk_adjusted")
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

    assert service._determine_verdict(1.8, pareto_rank=0) == "KEPT"
    assert service._determine_verdict(1.0, pareto_rank=0) == "KEPT"
    assert service._determine_verdict(0.6, pareto_rank=1) == "WARN"
    assert service._determine_verdict(0.5, pareto_rank=2) == "REVERTED"


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
async def test_rlm_alpha_vector_model():
    from app.models.rlm_alpha_vector import RLMAlphaVector
    vec = RLMAlphaVector(
        source_type="forum",
        source_path="/data/forums",
        token_count=50000,
        alpha_vector={"findings": [{"signal": "sentiment_drop", "strength": 0.7}]},
    )
    assert vec.source_type == "forum"
    assert vec.used_in_sessions == 0 or vec.used_in_sessions is None


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
async def test_research_api_stats(client):
    response = await client.get("/api/research/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_sessions" in data
    assert "avg_sharpe" in data


@pytest.mark.asyncio
async def test_research_api_config(client):
    response = await client.put("/api/research/config?preset=risk_adjusted&max_concurrent=3")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "updated"


@pytest.mark.asyncio
async def test_research_api_climate(client):
    response = await client.get("/api/research/climate")
    assert response.status_code == 200
    data = response.json()
    assert "regime" in data


@pytest.mark.asyncio
async def test_research_api_alpha_vectors(client):
    response = await client.get("/api/research/alpha-vectors")
    assert response.status_code == 200
    data = response.json()
    assert "vectors" in data


# ── New tests ─────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rlm_service_empty_directory():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await service.scan_directory(tmpdir, keywords=["test"])
        assert "alpha_vector" in result
        assert result["alpha_vector"]["findings"] == []
        assert result["files_scanned"] == 0


@pytest.mark.asyncio
async def test_rlm_service_no_keywords():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("some content")
        result = await service.scan_directory(tmpdir, keywords=None)
        assert "alpha_vector" in result


@pytest.mark.asyncio
async def test_rlm_service_linguistic_drift_no_change():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.detect_linguistic_drift(
        ["same post content"], ["same post content"], ["manager", "analyst"]
    )
    assert "drift_scores" in result
    assert result["drift_scores"]["manager"]["drift_score"] == 0.0
    assert result["drift_scores"]["analyst"]["drift_score"] == 0.0


@pytest.mark.asyncio
async def test_rlm_service_source_hash_deterministic():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("forum/data")
    h2 = service.compute_source_hash("forum/data")
    h3 = service.compute_source_hash("forum/data")
    assert h1 == h2 == h3
    h4 = service.compute_source_hash("paper/data")
    assert h1 != h4


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
    score = service._compute_composite_score(result, tabpfn_result, "sharpe_max")
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
    assert service._determine_verdict(0.2, pareto_rank=2) == "REVERTED"


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
async def test_research_api_rlm_scan(client):
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "test.txt")
        with open(fpath, "w") as f:
            f.write("This file mentions oracle-lag and slippage-limit")
        response = await client.post(
            "/api/research/rlm-scan",
            params={"source_path": tmpdir, "keywords": "oracle-lag,slippage"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "alpha_vector_id" in data

        vec_response = await client.get("/api/research/alpha-vectors")
        assert vec_response.status_code == 200
        vec_data = vec_response.json()
        assert len(vec_data["vectors"]) >= 1
        created_ids = [v["id"] for v in vec_data["vectors"]]
        assert data["alpha_vector_id"] in created_ids


@pytest.mark.asyncio
async def test_research_api_rlm_scan_no_keywords(client):
    import tempfile, os

    with tempfile.TemporaryDirectory() as tmpdir:
        fpath = os.path.join(tmpdir, "data.txt")
        with open(fpath, "w") as f:
            f.write("some random content")
        response = await client.post(
            "/api/research/rlm-scan",
            params={"source_path": tmpdir},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert "alpha_vector_id" in data


@pytest.mark.asyncio
async def test_research_api_features(client):
    from app.routers.research import tabpfn_service

    with patch.object(
        tabpfn_service,
        "get_feature_importance",
        new_callable=AsyncMock,
        return_value={"odds": 0.5, "volume": 0.3},
    ):
        response = await client.get("/api/research/features")
        assert response.status_code == 200
        data = response.json()
        assert "features" in data
        assert data["features"] == {"odds": 0.5, "volume": 0.3}


@pytest.mark.asyncio
async def test_research_api_config_defaults(client):
    response = await client.get("/api/research/config")
    assert response.status_code == 200
    data = response.json()
    assert data["preset"] == "sharpe_max"
    assert data["max_concurrent"] == 2
    assert data["cron_enabled"] is False


@pytest.mark.asyncio
async def test_research_api_config_roundtrip(client):
    put_resp = await client.put(
        "/api/research/config",
        params={"preset": "risk_adjusted", "max_concurrent": 3},
    )
    assert put_resp.status_code == 200
    assert put_resp.json()["status"] == "updated"

    get_resp = await client.get("/api/research/config")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["preset"] == "risk_adjusted"
    assert data["max_concurrent"] == 3


# ── Enhanced RLM Tests ─────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rlm_linguistic_drift_detector_keyword():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["old post about manager", "another old one"],
        recent=["new post about manager bad performance", "manager criticism growing"],
        entities=["manager", "analyst"],
    )
    assert "manager" in scores
    assert "analyst" in scores
    assert scores["manager"]["drift_score"] > 0
    assert scores["analyst"]["drift_score"] == 0.0


@pytest.mark.asyncio
async def test_rlm_linguistic_drift_detector_empty():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=[],
        recent=[],
        entities=["test"],
    )
    assert scores["test"]["drift_score"] == 0.0
    assert scores["test"]["direction"] == "neutral"


@pytest.mark.asyncio
async def test_rlm_linguistic_drift_detector_no_entity_mention():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["completely unrelated text"],
        recent=["also unrelated content"],
        entities=["missing_entity"],
    )
    assert scores["missing_entity"]["drift_score"] == 0.0


@pytest.mark.asyncio
async def test_rlm_service_scan_directory_with_keywords():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ["a.txt", "b.txt", "c.log"]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write(f"content about oracle-lag and slippage in {fname}")
        result = await service.scan_directory(tmpdir, keywords=["oracle-lag"])
        assert result["alpha_vector"]["findings"]
        assert result["files_scanned"] == 3
        assert result["files_matched"] == 3


@pytest.mark.asyncio
async def test_rlm_service_scan_directory_file_pattern():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for fname in ["data.txt", "data.csv", "notes.log"]:
            with open(os.path.join(tmpdir, fname), "w") as f:
                f.write("some content")
        result = await service.scan_directory(tmpdir, keywords=["content"], file_pattern="*.txt")
        assert result["files_matched"] == 1
        assert result["files_scanned"] == 1
        alpha = result["alpha_vector"]
        assert alpha["total_files_with_signals"] == 1


@pytest.mark.asyncio
async def test_rlm_service_scan_directory_token_budget():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(10):
            with open(os.path.join(tmpdir, f"file_{i}.txt"), "w") as f:
                f.write("a" * 50000)
        result = await service.scan_directory(
            tmpdir, keywords=None, max_tokens=100_000
        )
        assert result["files_scanned"] == 10
        assert result["files_matched"] > 0


@pytest.mark.asyncio
async def test_rlm_service_scan_directory_no_readable_files():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        result = await service.scan_directory(tmpdir, keywords=["test"])
        assert result["alpha_vector"]["findings"] == []


@pytest.mark.asyncio
async def test_rlm_service_scan_directory_nonexistent():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.scan_directory("/nonexistent/path", keywords=["test"])
    assert "error" in result["alpha_vector"]
    assert result["files_scanned"] == 0


@pytest.mark.asyncio
async def test_rlm_service_text_batch_empty():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.scan_text_batch([], "test query")
    assert result["documents_processed"] == 0
    assert result["token_estimate"] == 0


@pytest.mark.asyncio
async def test_rlm_service_text_batch_filtered():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    texts = ["short text", "another short one", "third document"]
    result = await service.scan_text_batch(texts, "find signals")
    assert result["documents_processed"] == 3
    assert result["documents_filtered"] == 3
    assert result["alpha_vector"]["filtered_count"] == 3


@pytest.mark.asyncio
async def test_rlm_service_drift_with_embedding():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.detect_linguistic_drift(
        texts_historical=["old manager post", "old analyst post"],
        texts_recent=["new manager post criticism", "new analyst post praise"],
        target_entities=["manager", "analyst"],
        use_dspy=False,
    )
    assert "drift_scores" in result
    assert "manager" in result["drift_scores"]
    assert "analyst" in result["drift_scores"]
    assert "top_drift_entities" in result
    assert result["historical_docs"] == 2
    assert result["recent_docs"] == 2


@pytest.mark.asyncio
async def test_rlm_service_drift_no_entities():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    result = await service.detect_linguistic_drift(
        texts_historical=["old content"],
        texts_recent=["new content"],
        target_entities=[],
        use_dspy=False,
    )
    assert result["drift_scores"] == {}
    assert result["total_entities_analyzed"] == 0


@pytest.mark.asyncio
async def test_rlm_service_sub_agent_fallback():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.spawn_sub_agent(
        document="This is a test document about oracle-lag risks in lending protocols",
        instruction="Extract all risk signals",
    )
    assert "keyword_matches" in result or "Fallback" in result


@pytest.mark.asyncio
async def test_rlm_service_sub_agent_depth_limit():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    result = await service.spawn_sub_agent(
        document="test " * 10000,
        instruction="analyze",
        max_depth=1,
        depth=1,
    )
    assert "max depth" in result


@pytest.mark.asyncio
async def test_rlm_service_run_pipeline():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "forum.txt"), "w") as f:
            f.write("Forum post about manager changes and team sentiment")
        with open(os.path.join(tmpdir, "news.txt"), "w") as f:
            f.write("News article about market oracle volatility")
        result = await service.run_pipeline(
            directory=tmpdir,
            keywords=["manager", "oracle"],
            historical_texts=["old manager post", "old analyst post"],
            recent_texts=["new manager post criticism"],
            entities=["manager", "analyst"],
        )
        assert "alpha_vector" in result
        assert result["pipeline_complete"]
        assert result["scan"]["files_scanned"] == 2
        assert result["drift"] is not None
        assert result["drift"]["top_drift_entities"]


@pytest.mark.asyncio
async def test_rlm_service_run_pipeline_no_drift():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "data.txt"), "w") as f:
            f.write("simple data")
        result = await service.run_pipeline(
            directory=tmpdir,
            keywords=["data"],
        )
        assert result["pipeline_complete"]
        assert result["drift"] is None


@pytest.mark.asyncio
async def test_rlm_service_token_budget_tracking():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._reset_budget(500_000)
    assert service._token_budget == 500_000
    assert service._consume_token_budget(100)
    assert service._token_budget == 499_900
    assert not service._consume_token_budget(499_900)
    assert service._token_budget == 0
    assert not service._consume_token_budget(1)


@pytest.mark.asyncio
async def test_rlm_service_accumulated_state():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    state = service.get_accumulated_state()
    assert state == []
    assert isinstance(state, list)


@pytest.mark.asyncio
async def test_rlm_service_estimate_tokens():
    from app.ai.rlm_service import _estimate_tokens
    assert _estimate_tokens("hello world") == 2
    assert _estimate_tokens("a" * 400) == 100
    assert _estimate_tokens("") == 1


@pytest.mark.asyncio
async def test_rlm_service_fallback_scan_directory_method():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "test.txt"), "w") as f:
            f.write("oracle-lag signal found")
        result = await service.fallback_scan_directory(tmpdir, keywords=["oracle-lag"])
        assert result["files_scanned"] == 1
        assert result["files_matched"] == 1


@pytest.mark.asyncio
async def test_rlm_drift_api_endpoint(client):
    response = await client.post(
        "/api/research/rlm-drift",
        params={
            "historical_texts": ["old manager post"],
            "recent_texts": ["new manager criticism"],
            "entities": "manager,analyst",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "drift_scores" in data
    assert "top_drift_entities" in data


@pytest.mark.asyncio
async def test_rlm_text_batch_api_endpoint(client):
    response = await client.post(
        "/api/research/rlm-text-batch",
        params={
            "texts": ["first document", "second document"],
            "query": "find alpha signals",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "alpha_vector" in data
    assert "documents_processed" in data


@pytest.mark.asyncio
async def test_rlm_trajectory_api_endpoint(client):
    response = await client.get("/api/research/rlm-trajectory")
    assert response.status_code == 200
    data = response.json()
    assert "trajectory" in data
    assert "available" in data


@pytest.mark.asyncio
async def test_rlm_state_api_endpoint(client):
    response = await client.get("/api/research/rlm-state")
    assert response.status_code == 200
    data = response.json()
    assert "state" in data
    assert "count" in data


@pytest.mark.asyncio
async def test_rlm_pipeline_api_endpoint(client):
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "data.txt"), "w") as f:
            f.write("test signal data")
        fpath = tmpdir.replace("\\", "/")
        response = await client.post(
            "/api/research/rlm-pipeline",
            params={
                "directory": fpath,
                "keywords": "signal",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "alpha_vector_id" in data
        assert data["pipeline_complete"]


@pytest.mark.asyncio
async def test_rlm_pipeline_api_full(client):
    import tempfile, os
    with tempfile.TemporaryDirectory() as tmpdir:
        with open(os.path.join(tmpdir, "forum.txt"), "w") as f:
            f.write("forum post about manager changes")
        fpath = tmpdir.replace("\\", "/")
        response = await client.post(
            "/api/research/rlm-pipeline",
            params={
                "directory": fpath,
                "keywords": "manager",
                "historical_texts": ["old post about manager"],
                "recent_texts": ["new post criticizing manager"],
                "entities": "manager",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "linguistic_signals" in data
        assert data["pipeline_complete"]


@pytest.mark.asyncio
async def test_rlm_keyword_match_edge_cases():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    service._available = False
    assert service._keyword_match("Hello World", ["hello"]) is True
    assert service._keyword_match("Hello World", ["world"]) is True
    assert service._keyword_match("Hello World", ["xyz"]) is False
    assert service._keyword_match("", ["test"]) is False


@pytest.mark.asyncio
async def test_rlm_extract_keyword_findings():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    findings = service._extract_keyword_findings("The oracle-lag is 2 seconds", ["oracle-lag"])
    assert len(findings) == 1
    assert findings[0]["keyword"] == "oracle-lag"
    assert findings[0]["position"] == 4
    empty = service._extract_keyword_findings("no match", ["keyword"])
    assert empty == []
    all_content = service._extract_keyword_findings("content", None)
    assert len(all_content) == 1
    assert all_content[0]["keyword"] == "any"


@pytest.mark.asyncio
async def test_rlm_linguistic_drift_embedding_fallback():
    from app.ai.rlm_service import LinguisticDriftDetector
    detector = LinguisticDriftDetector()
    detector._embed_available = False
    scores = await detector.compute_drift(
        historical=["a" * 1000, "b" * 1000],
        recent=["c" * 1000, "d" * 1000],
        entities=["entity1", "entity2"],
    )
    assert len(scores) == 2
    for s in scores.values():
        assert "drift_score" in s
        assert "direction" in s
        assert "keyword_score" in s
        assert "global_drift" in s


@pytest.mark.asyncio
async def test_rlm_source_hash_consistency():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    h1 = service.compute_source_hash("/data/archives/forum_2024.json")
    h2 = service.compute_source_hash("/data/archives/forum_2024.json")
    h3 = service.compute_source_hash("/DATA/ARCHIVES/FORUM_2024.JSON")
    assert h1 == h2
    assert h1 != h3


@pytest.mark.asyncio
async def test_rlm_inspect_trajectory_none():
    from app.ai.rlm_service import RLMService
    service = RLMService()
    assert service.inspect_last_trajectory() is None
