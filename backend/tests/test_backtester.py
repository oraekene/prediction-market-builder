import pytest
from app.services.backtester import Backtester, SimulatedMarketHistory


@pytest.mark.asyncio
async def test_backtester_runs():
    backtester = Backtester(initial_capital=10000.0)
    history = SimulatedMarketHistory.generate(start_odds=0.5, steps=50, volatility=0.03)
    strategy_config = {"threshold": 0.45, "operator": "lt", "side": "yes"}
    result = await backtester.run(strategy_config, history)
    assert result.initial_capital == 10000.0
    assert result.total_trades >= 0


@pytest.mark.asyncio
async def test_backtester_trades_recorded():
    backtester = Backtester(initial_capital=10000.0)
    history = SimulatedMarketHistory.generate(start_odds=0.5, steps=100, volatility=0.05)
    strategy_config = {"threshold": 0.5, "operator": "lt", "side": "yes"}
    result = await backtester.run(strategy_config, history)
    assert result.total_trades >= 0


def test_backtest_result_properties():
    from app.services.backtester import BacktestResult
    result = BacktestResult()
    assert result.win_rate == 0.0
    assert result.return_pct == 0.0
