from __future__ import annotations

import logging
import hashlib
import json
from typing import Any, Callable
from functools import lru_cache

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


class ShapExplainer:
    def __init__(self, n_samples: int = 128, cache_size: int = 256):
        self._explainer = None
        self._background: pd.DataFrame | None = None
        self._feature_names: list[str] | None = None
        self.n_samples = n_samples
        self._cache_size = cache_size

    async def initialize(
        self,
        model_fn: Callable[[pd.DataFrame], np.ndarray],
        feature_names: list[str],
        background_data: pd.DataFrame | None = None,
    ) -> None:
        try:
            import shap
        except ImportError:
            logger.warning("shap not installed, explainability disabled")
            self._explainer = None
            return

        self._feature_names = feature_names
        if background_data is not None:
            self._background = background_data
        else:
            default_values = {
                "odds": 0.5,
                "volume": 0.5,
                "liquidity": 0.5,
                "spread": 0.05,
                "participants": 0.5,
                "hypothesis_threshold": 0.5,
                "volatility": 0.5,
                "autocorrelation": 0.0,
            }
            rows = []
            rng = np.random.default_rng(42)
            for _ in range(50):
                row = {}
                for fn in feature_names:
                    base = default_values.get(fn, 0.5)
                    noise = rng.normal(0, max(base * 0.2, 0.02))
                    row[fn] = max(0.0, base + noise)
                rows.append(row)
            self._background = pd.DataFrame(rows)

        def predict_fn(X: np.ndarray) -> np.ndarray:
            df = pd.DataFrame(X, columns=feature_names)
            return model_fn(df)

        import shap.maskers
        masker = shap.maskers.Independent(self._background.values, max_samples=100)
        self._explainer = shap.PermutationExplainer(
            predict_fn,
            masker,
            feature_names=feature_names,
        )

    @property
    def available(self) -> bool:
        return self._explainer is not None

    async def explain(self, features: dict[str, float]) -> dict[str, Any]:
        if not self.available:
            return self._empty_explanation(features)

        feature_hash = self._hash_features(features)
        return await self._compute_explanation(features, feature_hash)

    @lru_cache(maxsize=256)
    def _cached_explain(self, feature_json: str) -> dict[str, Any]:
        features = json.loads(feature_json)
        return self._run_shap(features)

    async def _compute_explanation(
        self, features: dict[str, float], feature_hash: str
    ) -> dict[str, Any]:
        feature_json = json.dumps(features, sort_keys=True)
        return self._cached_explain(feature_json)

    def _run_shap(self, features: dict[str, float]) -> dict[str, Any]:
        if not self.available or not self._feature_names:
            return self._empty_explanation(features)

        df = pd.DataFrame([features])

        for fn in self._feature_names:
            if fn not in df.columns:
                df[fn] = 0.0
        df = df[self._feature_names]

        try:
            shap_values = self._explainer(df.values)
        except Exception as exc:
            logger.warning("SHAP explain failed: %s", exc)
            return self._empty_explanation(features)

        if isinstance(shap_values, list):
            shap_values = shap_values[0]

        shap_values = np.asarray(shap_values)
        if shap_values.ndim > 1:
            shap_values = shap_values[0]

        base_value = float(self._explainer.expected_value)
        if isinstance(base_value, (list, np.ndarray)):
            base_value = float(base_value[0] if len(base_value) > 0 else 0.5)

        output_value = float(base_value + shap_values.sum())

        contributions = []
        abs_importances = {}
        for i, name in enumerate(self._feature_names):
            sv = float(shap_values[i]) if i < len(shap_values) else 0.0
            fv = features.get(name, 0.0)
            contributions.append({
                "name": name,
                "shap_value": round(sv, 6),
                "feature_value": round(fv, 6),
            })
            abs_importances[name] = round(abs(sv), 6)

        ranking = sorted(abs_importances, key=abs_importances.get, reverse=True)
        mean_abs_importance = {
            name: round(abs_importances[name], 6)
            for name in ranking
        }

        return {
            "base_value": round(base_value, 6),
            "output_value": round(output_value, 6),
            "contributions": contributions,
            "mean_abs_importance": mean_abs_importance,
            "ranking": ranking,
        }

    def _empty_explanation(self, features: dict[str, float]) -> dict[str, Any]:
        return {
            "base_value": 0.5,
            "output_value": 0.5,
            "contributions": [
                {"name": k, "shap_value": 0.0, "feature_value": v}
                for k, v in features.items()
            ],
            "mean_abs_importance": {k: 0.0 for k in features},
            "ranking": list(features.keys()),
        }

    def _hash_features(self, features: dict[str, float]) -> str:
        raw = json.dumps(features, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]
