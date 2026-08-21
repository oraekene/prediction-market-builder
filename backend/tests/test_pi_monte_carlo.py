from __future__ import annotations

import numpy as np
import pytest

from app.ai.pi_autoresearch.monte_carlo import (
    MonteCarloResult,
    _bootstrap_market_history,
    _bootstrap_trades,
    monte_carlo_backtest,
)


class TestBootstrapMarketHistory:
    def test_preserves_length(self):
        history = [{"current_odds": 0.5}, {"current_odds": 0.6}, {"current_odds": 0.4}]
        np.random.seed(42)
        result = _bootstrap_market_history(history)
        assert len(result) == len(history)

    def test_empty(self):
        result = _bootstrap_market_history([])
        assert result == []

    def test_noise_zero_values_unchanged(self):
        history = [{"current_odds": 0.5}, {"current_odds": 0.6}, {"current_odds": 0.4}]
        np.random.seed(42)
        result = _bootstrap_market_history(history, noise_std=0.0)
        original_values = {0.5, 0.6, 0.4}
        for item in result:
            assert item["current_odds"] in original_values
        assert len(result) == 3


class TestBootstrapTrades:
    def test_preserves_structure(self):
        trades = [
            {"type": "entry", "price": 0.5, "pnl": 0},
            {"type": "exit", "price": 0.6, "pnl": 100},
        ]
        np.random.seed(42)
        result = _bootstrap_trades(trades)
        assert len(result) == 2
        for trade in result:
            assert "type" in trade
            assert "price" in trade
            assert "pnl" in trade


class TestMonteCarloBacktest:
    @pytest.mark.asyncio
    async def test_shape(self):
        np.random.seed(42)
        result = await monte_carlo_backtest(
            {"threshold": 0.5, "operator": "lt", "side": "yes"},
            [{"current_odds": 0.45, "timestamp": "t1"}, {"current_odds": 0.55, "timestamp": "t2"}],
            n=3,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 3
        assert not np.isnan(result.mean_sharpe)
        assert 0 <= result.mean_win_rate <= 1

    @pytest.mark.asyncio
    async def test_var_less_than_cvar(self):
        np.random.seed(42)
        result = await monte_carlo_backtest(
            {"threshold": 0.5, "operator": "lt", "side": "yes"},
            [{"current_odds": 0.45, "timestamp": "t1"}, {"current_odds": 0.55, "timestamp": "t2"}],
            n=10,
        )
        if result.n_simulations == 0:
            pytest.skip("no simulations completed")
        assert result.cvar_95 <= result.var_95 + 1e-10

    @pytest.mark.asyncio
    async def test_with_history(self):
        np.random.seed(42)
        history = [
            {"current_odds": 0.45 + 0.02 * (i % 2), "timestamp": f"t{i}"}
            for i in range(50)
        ]
        result = await monte_carlo_backtest(
            {"threshold": 0.5, "operator": "lt", "side": "yes"},
            history,
            n=5,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations > 0
        d = result.to_dict()
        assert isinstance(d, dict)
        assert "mean_sharpe" in d
        assert "cvar_95" in d

    @pytest.mark.asyncio
    async def test_empty_history_returns_zero_result(self):
        result = await monte_carlo_backtest(
            {"threshold": 0.5, "operator": "lt", "side": "yes"},
            [],
            n=5,
        )
        assert isinstance(result, MonteCarloResult)
        assert result.n_simulations == 5

    @pytest.mark.asyncio
    async def test_to_dict_rounds_values(self):
        np.random.seed(42)
        result = await monte_carlo_backtest(
            {"threshold": 0.5, "operator": "lt", "side": "yes"},
            [{"current_odds": 0.45, "timestamp": "t1"}, {"current_odds": 0.55, "timestamp": "t2"}],
            n=3,
        )
        d = result.to_dict()
        for key in ("mean_sharpe", "std_sharpe", "mean_win_rate", "std_win_rate",
                     "mean_total_pnl", "std_total_pnl", "var_95", "cvar_95"):
            val = d[key]
            dp = 2 if key in ("mean_total_pnl", "std_total_pnl") else 4
            rounded = round(val, dp)
            assert abs(val - rounded) < 1e-10, f"{key}={val} not rounded to {dp}dp"
