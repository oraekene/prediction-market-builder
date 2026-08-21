from __future__ import annotations

import logging
from typing import Any

from app.services.node_executor import ExecutionContext

logger = logging.getLogger(__name__)


async def handle_shap_explainability(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
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

    explainer = ctx.explainability_service
    if not explainer or not explainer.available:
        return {"explanation": None, "error": "SHAP explainer not available in context"}

    try:
        explanation = await explainer.explain_tabpfn_features(features)
        return {"explanation": explanation}
    except Exception as exc:
        logger.warning("SHAP node handler failed: %s", exc)
        return {"explanation": None, "error": str(exc)}


async def handle_shap_feature_importance(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
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
