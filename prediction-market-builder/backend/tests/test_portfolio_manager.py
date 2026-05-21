import pytest
import numpy as np
from app.services.portfolio_manager import PortfolioManager


@pytest.fixture
def pm():
    return PortfolioManager(initial_capital=10000)


def test_initial_state(pm):
    assert pm.peak_capital == 10000
    assert pm.current_capital == 10000


def test_update_tracks_capital(pm):
    pm.update({"current_capital": 11000, "positions": []})
    assert pm.current_capital == 11000
    assert pm.peak_capital == 11000


def test_update_does_not_reduce_peak(pm):
    pm.update({"current_capital": 11000, "positions": []})
    pm.update({"current_capital": 10500, "positions": []})
    assert pm.peak_capital == 11000


def test_dynamic_position_size_kelly(pm):
    signal = {"probability": 0.7, "market_odds": 0.55}
    size = pm.dynamic_position_size({"current_capital": 10000}, signal, 0.02, method="kelly")
    assert 0 < size < 1


def test_dynamic_position_size_volatility(pm):
    signal = {"probability": 0.7, "market_odds": 0.55}
    size_high_vol = pm.dynamic_position_size({}, signal, 0.05, method="volatility")
    size_low_vol = pm.dynamic_position_size({}, signal, 0.01, method="volatility")
    assert size_low_vol > size_high_vol


def test_dynamic_position_size_fixed(pm):
    size = pm.dynamic_position_size({}, {}, 0.02, method="fixed")
    assert size == 0.02


def test_volatility_regime_low(pm):
    assert pm.volatility_regime([0.001] * 30) == "low"


def test_volatility_regime_high(pm):
    assert pm.volatility_regime([0.05, -0.04, 0.06, -0.05, 0.04] * 6) == "high"


def test_volatility_regime_normal(pm):
    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.015, 30))
    assert pm.volatility_regime(returns) == "normal"


def test_track_drawdown(pm):
    pm.update({"current_capital": 11000, "positions": []})
    result = pm.track_drawdown(10500)
    assert "current_drawdown" in result
    assert "peak_capital" in result
    assert "current_capital" in result


def test_suggest_rebalance_returns_trades(pm):
    positions = [
        {"market_id": "a", "size": 6000},
        {"market_id": "b", "size": 4000},
    ]
    targets = {"a": 0.5, "b": 0.5}
    trades = pm.suggest_rebalance(positions, targets, threshold=0.05)
    assert isinstance(trades, list)


def test_suggest_hedge(pm):
    positions = [
        {"market_id": "a", "size": 5000, "platform": "polymarket"},
        {"market_id": "b", "size": 3000, "platform": "polymarket"},
    ]
    hedge = pm.suggest_hedge(positions)
    assert isinstance(hedge, dict)
    assert "hedges" in hedge


def test_empty_hedge(pm):
    hedge = pm.suggest_hedge([])
    assert hedge == {"hedges": []}
