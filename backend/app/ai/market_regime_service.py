import numpy as np
import pandas as pd


class MarketRegimeService:
    async def assess_climate(self, market_data: list[dict]) -> dict:
        if not market_data:
            return {"regime": "calm", "confidence": 0.0, "metrics": {}}

        df = pd.DataFrame(market_data)
        odds = df["current_odds"].values

        mean_odds = np.mean(odds)
        std_odds = np.std(odds) + 1e-8
        cv = std_odds / mean_odds

        diffs = np.diff(odds)
        direction = np.mean(np.sign(diffs))
        autocorr = np.corrcoef(odds[:-1], odds[1:])[0, 1] if len(odds) > 2 else 0

        if cv > 0.08:
            regime = "volatile"
            confidence = min(cv * 3, 1.0)
        elif abs(direction) > 0.4 and autocorr > 0.3:
            regime = "trending"
            confidence = min(abs(direction), 1.0)
        elif cv > 0.03:
            regime = "ranging"
            confidence = 0.5 + cv * 2
        else:
            regime = "calm"
            confidence = max(0.3, 1.0 - cv * 10)

        return {
            "regime": regime,
            "confidence": round(min(confidence, 1.0), 3),
            "metrics": {
                "volatility": round(cv, 4),
                "autocorrelation": round(autocorr, 4),
                "direction_strength": round(float(direction), 4),
                "sample_count": len(market_data),
            },
        }

    async def detect_anomalies(self, market_data: list[dict], threshold: float = 2.0) -> list[dict]:
        if not market_data:
            return []

        df = pd.DataFrame(market_data)
        odds = df["current_odds"].values
        volumes = df.get("volume", pd.Series([0] * len(df))).values

        odds_z = np.abs((odds - np.nanmean(odds)) / (np.nanstd(odds) + 1e-8))
        volume_z = np.abs((volumes - np.nanmean(volumes)) / (np.nanstd(volumes) + 1e-8)) if len(volumes) > 1 else np.zeros_like(volumes)
        combined_z = odds_z * 0.6 + volume_z * 0.4

        results = []
        for i in range(len(market_data)):
            results.append({
                "index": i,
                "odds": float(odds[i]),
                "odds_z_score": round(float(odds_z[i]), 3),
                "volume_z_score": round(float(volume_z[i]), 3),
                "z_score": round(float(combined_z[i]), 3),
                "is_anomaly": bool(combined_z[i] > threshold),
            })
        return results

    async def compute_volatility_surface(self, market_data: list[dict]) -> dict:
        if len(market_data) < 3:
            return {"short_term": 0.0, "medium_term": 0.0, "long_term": 0.0}

        odds = pd.Series([m["current_odds"] for m in market_data])
        log_returns = np.diff(np.log(np.clip(odds, 1e-6, None)))

        windows = {"short_term": 5, "medium_term": 20, "long_term": 50}
        result = {}
        for label, window in windows.items():
            if len(log_returns) < max(2, window):
                vol = float(np.std(log_returns)) if len(log_returns) > 1 else 0.0
            else:
                recent = log_returns[-min(window, len(log_returns)):]
                vol = float(np.std(recent))
            result[label] = round(vol, 6)

        return result
