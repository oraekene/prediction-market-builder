import numpy as np
import pandas as pd


class TabPFNQuantileEstimator:
    def __init__(self):
        self._regressor = None

    async def _ensure_loaded(self):
        if self._regressor is not None:
            return
        try:
            from tabpfn import TabPFNRegressor
            self._regressor = TabPFNRegressor()
        except (ImportError, Exception):
            self._regressor = False

    async def estimate_var(
        self, features: dict | None = None,
        returns: list[float] | None = None,
        confidence: float = 0.95,
    ) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        await self._ensure_loaded()
        if self._regressor and features and len(returns) > 20:
            try:
                df = pd.DataFrame([features])
                preds = self._regressor.predict(df.values)
                q = float(np.percentile(preds, (1 - confidence) * 100))
                return abs(q) if q < 0 else abs(np.percentile(returns, (1 - confidence) * 100))
            except Exception:
                return self._fallback_var(returns, confidence)
        return self._fallback_var(returns, confidence)

    async def estimate_es(
        self, features: dict | None = None,
        returns: list[float] | None = None,
        confidence: float = 0.95,
    ) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        var = await self.estimate_var(features, returns, confidence)
        arr = np.array(returns, dtype=np.float64)
        tail = arr[arr <= -var]
        if len(tail) == 0:
            return var
        return float(abs(np.mean(tail)))

    def _fallback_var(self, returns: list[float], confidence: float) -> float:
        arr = np.array(returns, dtype=np.float64)
        return float(abs(np.percentile(arr, (1 - confidence) * 100)))
