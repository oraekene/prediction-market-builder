from datetime import datetime, timedelta, timezone
from typing import Any
import random


class BacktestResult:
    def __init__(self):
        self.trades: list[dict[str, Any]] = []
        self.initial_capital: float = 10000.0
        self.current_capital: float = 10000.0

    @property
    def total_trades(self) -> int:
        return len(self.trades)

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.get("pnl", 0) > 0)
        return wins / len(self.trades)

    @property
    def total_pnl(self) -> float:
        return self.current_capital - self.initial_capital

    @property
    def return_pct(self) -> float:
        return (self.total_pnl / self.initial_capital) * 100


class Backtester:
    """
    Simple backtester for threshold-based strategies.
    Evaluates strategy against historical (or simulated) market data.
    """

    def __init__(self, initial_capital: float = 10000.0):
        self.result = BacktestResult()
        self.result.initial_capital = initial_capital
        self.result.current_capital = initial_capital

    async def run(self, strategy_config: dict[str, Any], market_history: list[dict[str, Any]]) -> BacktestResult:
        position = None
        entry_price = 0.0
        entry_time = None

        for snapshot in market_history:
            odds = snapshot.get("current_odds", 0.5)
            threshold = strategy_config.get("threshold", 0.5)
            operator = strategy_config.get("operator", "lt")
            side = strategy_config.get("side", "yes")

            should_buy = False
            should_sell = False

            if operator == "lt":
                should_buy = odds < threshold
                should_sell = odds >= threshold
            elif operator == "gt":
                should_buy = odds > threshold
                should_sell = odds <= threshold

            if should_buy and position is None:
                position = side
                entry_price = odds
                entry_time = snapshot.get("timestamp")
                self.result.trades.append({
                    "type": "entry",
                    "side": side,
                    "price": odds,
                    "timestamp": entry_time,
                    "position_size": self.result.current_capital * 0.1,
                })

            elif should_sell and position is not None:
                exit_price = odds
                pnl = (exit_price - entry_price) * 1000 if position == "yes" else (entry_price - exit_price) * 1000
                self.result.current_capital += pnl
                self.result.trades.append({
                    "type": "exit",
                    "side": position,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "timestamp": snapshot.get("timestamp"),
                })
                position = None

        return self.result


class SimulatedMarketHistory:
    """Generate simulated market history for testing backtester."""

    @staticmethod
    def generate(start_odds: float = 0.5, steps: int = 100, volatility: float = 0.02) -> list[dict[str, Any]]:
        history = []
        odds = start_odds
        now = datetime.now(timezone.utc)
        for i in range(steps):
            odds += random.uniform(-volatility, volatility)
            odds = max(0.01, min(0.99, odds))
            history.append({
                "current_odds": round(odds, 4),
                "timestamp": (now - timedelta(hours=steps - i)).isoformat(),
            })
        return history
