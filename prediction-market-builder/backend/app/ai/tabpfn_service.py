from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class TabPFNService:
    def __init__(self):
        self._model = None
        self._client = None
        self._context_X: pd.DataFrame | None = None
        self._context_y: np.ndarray | None = None

    async def initialize(self):
        if self._model is not None:
            return
        if settings.tabpfn_mode == "client":
            self._init_client()
            return
        try:
            from tabpfn import TabPFNClassifier
            self._model = TabPFNClassifier()
        except Exception as exc:
            logger.warning("TabPFNClassifier not available: %s", exc)
            self._model = False

    def _init_client(self):
        try:
            from tabpfn_client import Client
            self._client = Client()
        except Exception as exc:
            logger.warning("tabpfn-client not available: %s", exc)
            self._model = False

    def set_context(self, X: pd.DataFrame, y: np.ndarray) -> None:
        self._context_X = X
        self._context_y = y

    async def predict_probability(
        self, features: pd.DataFrame, context: pd.DataFrame | None = None
    ) -> float:
        await self.initialize()
        if self._client:
            return self._predict_client(features)
        if not self._model:
            logger.warning("TabPFN not available, returning 0.5")
            return 0.5
        try:
            probabilities = self._model.predict_proba(features)
            if probabilities.ndim == 2 and probabilities.shape[1] > 1:
                return float(probabilities[0][1])
            elif probabilities.ndim == 1:
                return float(probabilities[0])
            return float(probabilities[0][0])
        except Exception as exc:
            logger.warning("TabPFN predict_proba failed: %s", exc)
            return 0.5

    def _predict_client(self, features: pd.DataFrame) -> float:
        try:
            result = self._client.predict(features.values.tolist())
            if isinstance(result, dict):
                return float(result.get("probability", 0.5))
            if isinstance(result, (list, tuple)):
                return float(result[0][1]) if len(result[0]) > 1 else 0.5
            return 0.5
        except Exception as exc:
            logger.warning("tabpfn-client prediction failed: %s", exc)
            return 0.5

    async def validate_signal(
        self,
        market_data: dict,
        regime_vector: list[float] | None = None,
    ) -> dict:
        row = {
            "odds": market_data.get("current_odds", 0.5),
            "volume": market_data.get("volume", 0) / 1_000_000,
            "liquidity": market_data.get("liquidity", 0) / 1_000_000,
            "spread": (market_data.get("ask", 0) or 0) - (market_data.get("bid", 0) or 0),
            "participants": market_data.get("participants", 0) / 1000,
        }
        if regime_vector:
            for i, v in enumerate(regime_vector):
                row[f"regime_{i}"] = v
        df = pd.DataFrame([row])
        probability = await self.predict_probability(df)
        confidence = min(probability, 1 - probability) * 2
        return {
            "probability": probability,
            "confidence": round(confidence, 3),
            "edge": round(probability - (market_data.get("current_odds", 0.5)), 4),
            "verdict": "APPROVED" if probability > 0.6 else "REJECTED",
        }

    async def get_feature_importance(
        self, features: pd.DataFrame
    ) -> dict[str, float]:
        await self.initialize()
        if self._client:
            return {col: 0.0 for col in features.columns}
        if not self._model:
            return {col: 0.0 for col in features.columns}
        try:
            _ = self._model.predict_proba(features)
            if hasattr(self._model, "feature_importances_"):
                fi = self._model.feature_importances_
                return dict(zip(features.columns, fi))
        except Exception:
            pass
        return {col: 0.0 for col in features.columns}
