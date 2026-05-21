from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

try:
    import sentence_transformers  # noqa: F401
    _st_available = True
except ImportError:
    _st_available = False


@pytest.mark.skipif(not _st_available, reason="requires sentence-transformers")
async def test_embedding_encode():
    from app.ai.embeddings import EmbeddingService
    service = EmbeddingService()
    vec = service.encode("Will the Fed cut rates in June?")
    assert len(vec) == 384
    assert all(isinstance(v, float) for v in vec)


@pytest.mark.skipif(not _st_available, reason="requires sentence-transformers")
async def test_embedding_batch():
    from app.ai.embeddings import EmbeddingService
    service = EmbeddingService()
    texts = ["Hello world", "Another text"]
    vecs = service.encode(texts)
    assert len(vecs) == 2
    assert all(len(v) == 384 for v in vecs)


def _mock_tabpfn_module():
    import numpy as np
    mock_clf = MagicMock()
    mock_clf.predict_proba.return_value = np.array([[0.3, 0.7]])
    mock_clf.feature_importances_ = np.array([0.4, 0.3, 0.2, 0.1, 0.0])
    mock_mod = MagicMock()
    mock_mod.TabPFNClassifier.return_value = mock_clf
    return mock_mod


@patch.dict("sys.modules", {"tabpfn": _mock_tabpfn_module()})
async def test_tabpfn_validate_signal():
    from app.ai.tabpfn_service import TabPFNService
    service = TabPFNService()
    result = await service.validate_signal({
        "current_odds": 0.5,
        "volume": 1_000_000,
        "liquidity": 500_000,
    })
    assert "probability" in result
    assert "confidence" in result
    assert "edge" in result
    assert result["verdict"] in ("APPROVED", "REJECTED")


@patch.dict("sys.modules", {"tabpfn": _mock_tabpfn_module()})
async def test_tabpfn_predict_probability():
    from app.ai.tabpfn_service import TabPFNService
    service = TabPFNService()
    features = pd.DataFrame({"odds": [0.45], "volume": [1.0], "liquidity": [0.5]})
    prob = await service.predict_probability(features)
    assert 0.0 <= prob <= 1.0


@patch.dict("sys.modules", {"tabpfn": _mock_tabpfn_module()})
async def test_tabpfn_validate_with_regime():
    from app.ai.tabpfn_service import TabPFNService
    service = TabPFNService()
    result = await service.validate_signal(
        {"current_odds": 0.5, "volume": 1_000_000, "liquidity": 500_000},
        regime_vector=[0.8, 0.2],
    )
    assert result["verdict"] in ("APPROVED", "REJECTED")


@patch.dict("sys.modules", {"tabpfn": _mock_tabpfn_module()})
async def test_tabpfn_get_feature_importance():
    from app.ai.tabpfn_service import TabPFNService
    service = TabPFNService()
    features = pd.DataFrame({
        "odds": [0.45], "volume": [1.0], "liquidity": [0.5],
        "spread": [0.02], "participants": [0.5],
    })
    importance = await service.get_feature_importance(features)
    assert isinstance(importance, dict)
    assert len(importance) == 5


mock_market_data = [
    {"current_odds": 0.45, "volume": 100000, "timestamp": "2024-01-01"},
    {"current_odds": 0.48, "volume": 120000, "timestamp": "2024-01-02"},
    {"current_odds": 0.52, "volume": 90000, "timestamp": "2024-01-03"},
    {"current_odds": 0.55, "volume": 150000, "timestamp": "2024-01-04"},
    {"current_odds": 0.53, "volume": 110000, "timestamp": "2024-01-05"},
]


async def test_market_regime_assess_climate():
    from app.ai.market_regime_service import MarketRegimeService
    service = MarketRegimeService()
    result = await service.assess_climate(mock_market_data)
    assert "regime" in result
    assert result["regime"] in ("trending", "ranging", "volatile", "calm")
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1
    assert "metrics" in result


async def test_market_regime_detect_anomalies():
    from app.ai.market_regime_service import MarketRegimeService
    service = MarketRegimeService()
    results = await service.detect_anomalies(mock_market_data)
    assert isinstance(results, list)
    for r in results:
        assert "index" in r
        assert "z_score" in r
        assert "is_anomaly" in r


async def test_market_regime_compute_volatility_surface():
    from app.ai.market_regime_service import MarketRegimeService
    service = MarketRegimeService()
    result = await service.compute_volatility_surface(mock_market_data)
    assert "short_term" in result
    assert "medium_term" in result
    assert "long_term" in result
    for v in result.values():
        assert isinstance(v, float)
        assert v >= 0


async def test_market_regime_no_data():
    from app.ai.market_regime_service import MarketRegimeService
    service = MarketRegimeService()
    result = await service.assess_climate([])
    assert result["regime"] == "calm"
    assert result["confidence"] == 0.0
