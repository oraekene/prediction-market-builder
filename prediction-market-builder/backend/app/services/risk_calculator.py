from typing import Any
import numpy as np


class RiskCalculator:
    def historical_var(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        return float(abs(np.percentile(arr, (1 - confidence) * 100)))

    def parametric_var(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        mean = np.mean(arr)
        std = np.std(arr, ddof=1)
        if std == 0:
            return 0.0
        from scipy import stats as scipy_stats
        z = scipy_stats.norm.ppf(1 - confidence)
        return float(abs(mean + z * std))

    def expected_shortfall(self, returns: list[float], confidence: float) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        var = self.historical_var(returns, confidence)
        tail = arr[arr <= -var]
        if len(tail) == 0:
            return var
        return float(abs(np.mean(tail)))

    def max_drawdown(self, capital_series: list[float]) -> float:
        if len(capital_series) < 2:
            return 0.0
        arr = np.array(capital_series, dtype=np.float64)
        peak = np.maximum.accumulate(arr)
        drawdown = (peak - arr) / peak
        return float(np.max(drawdown))

    def current_drawdown(self, peak: float, current: float) -> float:
        if peak <= 0:
            return 0.0
        return round((peak - current) / peak, 4)

    def portfolio_volatility(self, returns: list[float], periods: int = 252) -> float:
        if len(returns) < 2:
            return 0.0
        arr = np.array(returns, dtype=np.float64)
        daily_std = np.std(arr, ddof=1)
        return float(daily_std * np.sqrt(periods))

    def concentration(self, positions: list[dict]) -> float:
        if not positions:
            return 0.0
        total = sum(p.get("size", 0) for p in positions)
        if total <= 0:
            return 0.0
        weights = np.array([p.get("size", 0) for p in positions], dtype=np.float64) / total
        return float(np.sum(weights ** 2))

    def correlation_matrix(self, portfolio_returns: dict[str, list[float]]) -> dict[str, dict[str, float]]:
        assets = list(portfolio_returns.keys())
        if len(assets) < 2:
            return {a: {a: 1.0} for a in assets}
        arr = np.array([portfolio_returns[a] for a in assets], dtype=np.float64)
        corr = np.corrcoef(arr)
        result = {}
        for i, a in enumerate(assets):
            result[a] = {}
            for j, b in enumerate(assets):
                result[a][b] = round(float(corr[i][j]), 4)
        return result

    def value_at_risk_by_position(self, positions: list[dict], portfolio_returns: list[float],
                                   confidence: float) -> list[dict]:
        total_var = self.historical_var(portfolio_returns, confidence)
        total_size = sum(p.get("size", 0) for p in positions)
        if total_size <= 0:
            return [{"market_id": p["market_id"], "var_contribution": 0.0, "concentration_pct": 0.0} for p in positions]
        result = []
        for p in positions:
            weight = p.get("size", 0) / total_size
            result.append({
                "market_id": p["market_id"],
                "var_contribution": round(total_var * weight, 4),
                "concentration_pct": round(weight * 100, 2),
            })
        return result
