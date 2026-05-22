from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def handle_shap_explainability(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    market = inputs.get("market", ctx.market or {})
    signal = inputs.get("signal", ctx.signal or {})

    features = {
        "odds": market.get("current_odds", data.get("default_odds", 0.5)),
        "volume": market.get("volume", 0) / 1_000_000,
        "liquidity": market.get("liquidity", 0) / 1_000_000,
        "spread": (market.get("ask", 0) or 0) - (market.get("bid", 0) or 0),
        "participants": market.get("participants", 0) / 1000,
        "hypothesis_threshold": data.get("threshold", signal.get("threshold", 0.5)),
        "volatility": data.get("volatility", market.get("volatility", 0.5)),
        "autocorrelation": data.get("autocorrelation", 0.0),
    }

    tabpfn = ctx.tabpfn
    if tabpfn is None:
        return {"explanation": None, "error": "TabPFN not available in context"}

    try:
        import asyncio
        import pandas as pd

        async def _run_shap():
            df = pd.DataFrame([features])
            prob = await tabpfn.predict_probability(df)
            feature_importance = await tabpfn.get_feature_importance(df)

            contributions = []
            abs_importance = {}
            total_abs = sum(abs(v) for v in feature_importance.values())
            for name, val in feature_importance.items():
                normalized = val / total_abs if total_abs > 0 else 0.0
                sign = 1.0 if val > 0 else -1.0
                shap_val = normalized * (prob - 0.5)
                contributions.append({
                    "name": name,
                    "shap_value": round(shap_val, 6),
                    "feature_value": features.get(name, 0.0),
                })
                abs_importance[name] = round(abs(shap_val), 6)

            ranking = sorted(abs_importance, key=abs_importance.get, reverse=True)
            return {
                "base_value": 0.5,
                "output_value": round(prob, 4),
                "contributions": contributions,
                "mean_abs_importance": {n: abs_importance[n] for n in ranking},
                "ranking": ranking,
            }

        loop = asyncio.get_event_loop()
        if loop.is_running():
            import threading
            future = asyncio.run_coroutine_threadsafe(_run_shap(), loop)
            explanation = future.result(timeout=30)
        else:
            explanation = asyncio.run(_run_shap())

        return {"explanation": explanation}

    except Exception as exc:
        logger.warning("SHAP node handler failed: %s", exc)
        return {"explanation": None, "error": str(exc)}


def handle_shap_feature_importance(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    upstream_explanation = inputs.get(
        "explanation",
        inputs.get("shap_explainability", {}).get("explanation"),
    )

    if not upstream_explanation:
        return {
            "triggered": False,
            "top_features": [],
            "importance": {},
        }

    data = node.get("data", {})
    min_importance = data.get("min_importance", 0.0)
    top_k = data.get("top_k", 5)

    contributions = upstream_explanation.get("contributions", [])
    filtered = [
        c for c in contributions
        if abs(c.get("shap_value", 0)) >= min_importance
    ]
    ranked = sorted(filtered, key=lambda c: abs(c["shap_value"]), reverse=True)
    top_features = ranked[:top_k]

    return {
        "triggered": len(top_features) > 0,
        "top_features": top_features,
        "importance": upstream_explanation.get("mean_abs_importance", {}),
        "ranking": upstream_explanation.get("ranking", []),
        "output_value": upstream_explanation.get("output_value"),
    }


def register_shap_handlers(registry) -> None:
    registry.register("shap_explainability", handle_shap_explainability)
    registry.register("shap_feature_importance", handle_shap_feature_importance)
