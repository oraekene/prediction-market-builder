import pytest
import numpy as np
from app.services.risk_calculator import RiskCalculator


@pytest.fixture
def calc():
    return RiskCalculator()


@pytest.fixture
def normal_returns():
    np.random.seed(42)
    return list(np.random.normal(0.001, 0.02, 1000))


def test_historical_var(normal_returns, calc):
    var = calc.historical_var(normal_returns, 0.95)
    assert isinstance(var, float)
    assert var > 0


def test_parametric_var(normal_returns, calc):
    var = calc.parametric_var(normal_returns, 0.95)
    assert isinstance(var, float)
    assert var > 0


def test_expected_shortfall(normal_returns, calc):
    es = calc.expected_shortfall(normal_returns, 0.95)
    assert isinstance(es, float)
    assert es > 0


def test_es_greater_than_var(normal_returns, calc):
    var = calc.historical_var(normal_returns, 0.95)
    es = calc.expected_shortfall(normal_returns, 0.95)
    assert es >= var


def test_max_drawdown(calc):
    capital = [100, 110, 105, 95, 98, 80, 90]
    dd = calc.max_drawdown(capital)
    assert dd == pytest.approx(0.2727, 0.01)


def test_current_drawdown(calc):
    dd = calc.current_drawdown(peak=100, current=80)
    assert dd == 0.20


def test_portfolio_volatility(normal_returns, calc):
    vol = calc.portfolio_volatility(normal_returns)
    assert isinstance(vol, float)
    assert vol > 0


def test_concentration_hhi(calc):
    positions = [
        {"market_id": "a", "size": 50},
        {"market_id": "b", "size": 30},
        {"market_id": "c", "size": 20},
    ]
    hhi = calc.concentration(positions)
    expected = (50/100)**2 + (30/100)**2 + (20/100)**2
    assert hhi == pytest.approx(expected, 0.01)


def test_correlation_matrix(calc):
    rets = {
        "a": [0.01, -0.02, 0.03, -0.01, 0.02],
        "b": [-0.01, 0.02, -0.03, 0.01, -0.02],
    }
    matrix = calc.correlation_matrix(rets)
    assert "a" in matrix
    assert "b" in matrix
    assert "a" in matrix["a"]


def test_empty_returns_historical_var(calc):
    var = calc.historical_var([], 0.95)
    assert var == 0.0


def test_single_return_parametric_var(calc):
    var = calc.parametric_var([0.01], 0.95)
    assert var == 0.0


def test_value_at_risk_by_position(calc):
    positions = [
        {"market_id": "a", "size": 1000, "weight": 0.5},
        {"market_id": "b", "size": 1000, "weight": 0.5},
    ]
    np.random.seed(42)
    returns = list(np.random.normal(0.001, 0.02, 1000))
    result = calc.value_at_risk_by_position(positions, returns, 0.95)
    assert len(result) == 2
    for r in result:
        assert "market_id" in r
        assert "var_contribution" in r
        assert "concentration_pct" in r
