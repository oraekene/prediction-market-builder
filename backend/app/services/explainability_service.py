from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from app.ai.shap_explainer import ShapExplainer
from app.ai.tabpfn_service import TabPFNService

logger = logging.getLogger(__name__)


class ExplainabilityService:
    def __init__(
        self,
        shap_explainer: ShapExplainer,
        tabpfn_service: TabPFNService,
    ):
        self.shap = shap_explainer
        self.tabpfn = tabpfn_service

    async def initialize(self) -> None:
        feature_names = [
            "odds", "volume", "liquidity", "spread",
            "participants", "hypothesis_threshold",
            "volatility", "autocorrelation",
        ]

        async def model_fn(df: pd.DataFrame) -> Any:
            return await self.tabpfn.predict_probability(df)

        await self.shap.initialize(
            model_fn=model_fn,
            feature_names=feature_names,
        )

    async def explain_tabpfn_features(
        self, features: dict[str, float]
    ) -> dict[str, Any]:
        return await self.shap.explain(features)

    async def explain_validate_signal_features(
        self, market_data: dict, regime_vector: list[float] | None = None
    ) -> dict[str, Any]:
        features = {
            "odds": market_data.get("current_odds", 0.5),
            "volume": market_data.get("volume", 0) / 1_000_000,
            "liquidity": market_data.get("liquidity", 0) / 1_000_000,
            "spread": (market_data.get("ask", 0) or 0) - (market_data.get("bid", 0) or 0),
            "participants": market_data.get("participants", 0) / 1000,
        }
        if regime_vector:
            for i, v in enumerate(regime_vector):
                features[f"regime_{i}"] = v

        feature_names = list(features.keys())

        async def model_fn(df: pd.DataFrame) -> Any:
            return await self.tabpfn.predict_probability(df)

        if not self.shap._feature_names or set(feature_names) != set(self.shap._feature_names):
            await self.shap.initialize(
                model_fn=model_fn,
                feature_names=feature_names,
            )

        return await self.shap.explain(features)

    @property
    def available(self) -> bool:
        return self.shap.available
