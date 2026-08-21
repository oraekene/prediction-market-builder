from typing import Any
import numpy as np


class PortfolioManager:
    def __init__(self, initial_capital: float = 10000):
        self.peak_capital = initial_capital
        self.current_capital = initial_capital
        self.positions: list[dict] = []

    def update(self, portfolio_state: dict) -> None:
        capital = portfolio_state.get("current_capital", self.current_capital)
        self.current_capital = capital
        if capital > self.peak_capital:
            self.peak_capital = capital
        self.positions = portfolio_state.get("positions", self.positions)

    def dynamic_position_size(self, portfolio: dict, signal: dict,
                               volatility: float, method: str = "kelly") -> float:
        if method == "fixed":
            return signal.get("fixed_fraction", 0.02)

        if method == "volatility":
            base = 0.05
            if volatility <= 0:
                return base
            return round(min(base / volatility * 0.01, 0.5), 4)

        probability = signal.get("probability", 0.5)
        odds = signal.get("market_odds", 0.5)
        if odds <= 0:
            return 0.0
        b = (1 - odds) / odds
        p = probability
        q = 1 - p
        if b <= 0:
            return 0.0
        kelly = (p * b - q) / b
        cap = portfolio.get("current_capital", 10000)
        if volatility > 0:
            kelly = kelly * (0.02 / max(volatility, 0.005))
        return round(max(0, kelly * 0.25), 4)

    def volatility_regime(self, returns: list[float]) -> str:
        if len(returns) < 5:
            return "normal"
        std = float(np.std(returns, ddof=1))
        if std < 0.005:
            return "low"
        if std > 0.03:
            return "high"
        return "normal"

    def track_drawdown(self, current_capital: float) -> dict[str, Any]:
        if current_capital > self.peak_capital:
            self.peak_capital = current_capital
        dd = 0.0
        if self.peak_capital > 0:
            dd = round((self.peak_capital - current_capital) / self.peak_capital, 4)
        return {
            "current_drawdown": dd,
            "peak_capital": self.peak_capital,
            "current_capital": current_capital,
            "max_drawdown": dd,
        }

    def suggest_rebalance(self, positions: list[dict], target_allocations: dict[str, float],
                           threshold: float = 0.05) -> list[dict]:
        total = sum(p.get("size", 0) for p in positions)
        if total <= 0:
            return []
        trades = []
        for p in positions:
            mid = p["market_id"]
            current_pct = p.get("size", 0) / total
            target_pct = target_allocations.get(mid, 0)
            if abs(current_pct - target_pct) > threshold:
                diff = target_pct - current_pct
                trades.append({
                    "market_id": mid,
                    "action": "buy" if diff > 0 else "sell",
                    "amount": round(abs(diff) * total, 2),
                    "reason": f"rebalance: {current_pct:.1%} -> {target_pct:.1%}",
                })
        return trades

    def suggest_hedge(self, positions: list[dict]) -> dict[str, Any]:
        if not positions:
            return {"hedges": []}
        total = sum(p.get("size", 0) for p in positions)
        hedges = []
        for p in positions:
            pct = p.get("size", 0) / total if total > 0 else 0
            if pct > 0.3:
                hedges.append({
                    "market_id": p["market_id"],
                    "hedge_amount": round(p.get("size", 0) * 0.3, 2),
                    "instrument": f"inverse-{p['market_id']}",
                    "reason": f"position {pct:.1%} exceeds 30% concentration threshold",
                })
        return {"hedges": hedges}
