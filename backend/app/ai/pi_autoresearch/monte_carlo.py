from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from app.services.backtester import Backtester, BacktestResult

logger = logging.getLogger(__name__)


@dataclass
class MonteCarloResult:
    n_simulations: int
    mean_sharpe: float = 0.0
    std_sharpe: float = 0.0
    mean_win_rate: float = 0.0
    std_win_rate: float = 0.0
    mean_total_pnl: float = 0.0
    std_total_pnl: float = 0.0
    var_95: float = 0.0
    cvar_95: float = 0.0
    simulations: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "n_simulations": self.n_simulations,
            "mean_sharpe": round(self.mean_sharpe, 4),
            "std_sharpe": round(self.std_sharpe, 4),
            "mean_win_rate": round(self.mean_win_rate, 4),
            "std_win_rate": round(self.std_win_rate, 4),
            "mean_total_pnl": round(self.mean_total_pnl, 2),
            "std_total_pnl": round(self.std_total_pnl, 2),
            "var_95": round(self.var_95, 4),
            "cvar_95": round(self.cvar_95, 4),
            "simulations": self.simulations,
        }


def _bootstrap_market_history(history: list[dict], noise_std: float = 0.01) -> list[dict]:
    if not history:
        return []
    n = len(history)
    indices = np.random.choice(n, n)
    sampled = [dict(history[i]) for i in indices]
    if noise_std > 0:
        for s in sampled:
            if "current_odds" in s:
                noise = np.random.normal(0, noise_std)
                s["current_odds"] = max(0.01, min(0.99, s["current_odds"] + noise))
    return sampled


def _bootstrap_trades(trades: list[dict]) -> list[dict]:
    if not trades:
        return []
    n = len(trades)
    indices = np.random.choice(n, n)
    return [dict(trades[i]) for i in indices]


def _sharpe_from_backtest(result: BacktestResult) -> float:
    if result.total_trades < 2:
        return 0.0
    returns = []
    for t in result.trades:
        if t.get("type") == "exit":
            pnl = t.get("pnl", 0)
            entry_price = t.get("entry_price", 0.5)
            if entry_price > 0:
                returns.append(pnl / (entry_price * 1000))
    if not returns:
        return 0.0
    mean_r = np.mean(returns)
    std_r = np.std(returns) + 1e-8
    return float(mean_r / std_r * np.sqrt(252))


async def monte_carlo_backtest(
    backtest_config: dict[str, Any],
    market_history: list[dict[str, Any]],
    n: int = 50,
    backtester: Backtester | None = None,
) -> MonteCarloResult:
    if not market_history:
        return MonteCarloResult(n_simulations=n)

    sharpes: list[float] = []
    win_rates: list[float] = []
    pnls: list[float] = []
    sim_records: list[dict] = []

    if backtester is None:
        backtester = Backtester()

    for i in range(n):
        try:
            boot_history = _bootstrap_market_history(market_history)
            result = await backtester.run(backtest_config, boot_history)
            sharpe = _sharpe_from_backtest(result)
            sharpes.append(sharpe)
            win_rates.append(result.win_rate)
            pnls.append(result.total_pnl)
            sim_records.append({
                "simulation": i,
                "sharpe": round(sharpe, 4),
                "win_rate": round(result.win_rate, 4),
                "total_pnl": round(result.total_pnl, 4),
                "total_trades": result.total_trades,
            })
        except Exception:
            logger.exception(f"Monte Carlo simulation {i} failed")
            continue

    n_completed = len(sharpes)
    if n_completed == 0:
        return MonteCarloResult(n_simulations=0)

    arr_sharpes = np.array(sharpes)
    arr_win_rates = np.array(win_rates)
    arr_pnls = np.array(pnls)

    var_95 = float(np.percentile(arr_pnls, 5))
    cvar_95 = float(arr_pnls[arr_pnls <= var_95].mean()) if np.any(arr_pnls <= var_95) else var_95

    return MonteCarloResult(
        n_simulations=n_completed,
        mean_sharpe=float(np.mean(arr_sharpes)),
        std_sharpe=float(np.std(arr_sharpes)),
        mean_win_rate=float(np.mean(arr_win_rates)),
        std_win_rate=float(np.std(arr_win_rates)),
        mean_total_pnl=float(np.mean(arr_pnls)),
        std_total_pnl=float(np.std(arr_pnls)),
        var_95=var_95,
        cvar_95=cvar_95,
        simulations=sim_records[:10],
    )
