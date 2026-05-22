from __future__ import annotations

import asyncio
import logging
import math
import random
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.node_executor import ExecutionContext

logger = logging.getLogger(__name__)


async def handle_polymarket_source(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    aggregator = ctx.market_aggregator
    if not aggregator:
        return {"markets": [], "error": "Market aggregator not available"}
    try:
        markets = await aggregator.fetch_all(["polymarket"])
        return {"markets": markets, "count": len(markets), "platform": "polymarket"}
    except Exception as exc:
        return {"markets": [], "error": str(exc)}


async def handle_kalshi_source(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    aggregator = ctx.market_aggregator
    if not aggregator:
        return {"markets": [], "error": "Market aggregator not available"}
    try:
        markets = await aggregator.fetch_all(["kalshi"])
        return {"markets": markets, "count": len(markets), "platform": "kalshi"}
    except Exception as exc:
        return {"markets": [], "error": str(exc)}


async def handle_drift_source(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    aggregator = ctx.market_aggregator
    if not aggregator:
        return {"markets": [], "error": "Market aggregator not available"}
    try:
        markets = await aggregator.fetch_all(["drift"])
        return {"markets": markets, "count": len(markets), "platform": "drift"}
    except Exception as exc:
        return {"markets": [], "error": str(exc)}


async def handle_web_search(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    query = data.get("query", "")
    if not query:
        return {"results": [], "error": "No search query specified"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://api.duckduckgo.com",
                params={"q": query, "format": "json"},
                timeout=10,
            )
            if resp.status_code == 200:
                results = resp.json().get("Results", [])
                return {"results": results, "count": len(results)}
            return {"results": [], "error": f"Search failed: {resp.status_code}"}
    except Exception as exc:
        return {"results": [], "error": str(exc)}


async def handle_news_source(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    query = data.get("query", "prediction market")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://newsapi.org/v2/everything",
                params={"q": query, "pageSize": 10},
                timeout=10,
            )
            if resp.status_code == 200:
                articles = resp.json().get("articles", [])
                return {"articles": articles, "count": len(articles)}
            return {"articles": [], "error": f"News fetch failed: {resp.status_code}"}
    except Exception as exc:
        return {"articles": [], "error": str(exc)}


def handle_time_condition(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    operator = data.get("operator", "before")
    target_time_str = data.get("target_time", "")
    if not target_time_str:
        return {"triggered": False, "error": "No target_time specified"}
    try:
        target = datetime.fromisoformat(target_time_str)
        now = datetime.now(timezone.utc)
        if operator == "before":
            triggered = now < target
        elif operator == "after":
            triggered = now > target
        elif operator == "between":
            end_str = data.get("target_time_end", "")
            target_end = datetime.fromisoformat(end_str) if end_str else target
            triggered = target <= now <= target_end
        else:
            triggered = False
        return {"triggered": triggered, "now": now.isoformat(), "target": target_time_str}
    except Exception as exc:
        return {"triggered": False, "error": str(exc)}


def handle_and_or_gate(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    gate_type = data.get("gate_type", "and")
    upstream_triggers = [
        v.get("triggered", False) for v in inputs.values()
        if isinstance(v, dict)
    ]
    if gate_type == "and":
        triggered = all(upstream_triggers) if upstream_triggers else False
    elif gate_type == "or":
        triggered = any(upstream_triggers) if upstream_triggers else False
    elif gate_type == "xor":
        triggered = upstream_triggers.count(True) == 1 if upstream_triggers else False
    elif gate_type == "nand":
        triggered = not all(upstream_triggers) if upstream_triggers else True
    else:
        triggered = False
    return {"triggered": triggered, "gate_type": gate_type, "upstream_count": len(upstream_triggers)}


def handle_branch(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    condition_input = inputs.get("condition", {})
    triggered = condition_input.get("triggered", False) if isinstance(condition_input, dict) else False
    branch_if = data.get("branch_if", True)
    activated = triggered == branch_if
    return {
        "activated": activated,
        "condition_triggered": triggered,
        "branch_if": branch_if,
        "output": data.get("true_output" if activated else "false_output"),
    }


async def handle_place_bet(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    market = ctx.market or {}
    return {
        "action": "place_bet",
        "approved": True,
        "platform": data.get("platform", market.get("platform", "unknown")),
        "market_id": data.get("market_id", market.get("platform_market_id")),
        "side": data.get("side", inputs.get("side", "yes")),
        "size": data.get("size", inputs.get("suggested_size", 0.01)),
        "type": data.get("order_type", "market"),
        "note": "Placeholder — real execution requires Phase 4 Rust engine",
    }


def handle_forward(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    upstream_key = data.get("upstream_key", "")
    if upstream_key and upstream_key in inputs:
        return inputs[upstream_key]
    last_value = None
    for v in inputs.values():
        last_value = v
    return last_value if last_value is not None else {"forwarded": True}


async def handle_webhook(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    url = data.get("url", "")
    payload = {
        "node_id": node.get("id"),
        "inputs": {k: str(v)[:1000] for k, v in inputs.items()},
        "market": {k: str(v)[:500] for k, v in ctx.market.items() if isinstance(v, (str, int, float))},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if not url:
        return {"sent": False, "error": "No webhook URL configured"}
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=10)
            return {"sent": True, "status_code": resp.status_code, "response": resp.text[:500]}
    except Exception as exc:
        return {"sent": False, "error": str(exc)}


def handle_bayesian_inference(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    prior = data.get("prior", 0.5)
    likelihood_true = data.get("likelihood_true", 0.8)
    likelihood_false = data.get("likelihood_false", 0.4)
    evidence = data.get("evidence", True)

    if evidence:
        posterior = (likelihood_true * prior) / (
            likelihood_true * prior + likelihood_false * (1 - prior)
        )
    else:
        posterior = ((1 - likelihood_true) * prior) / (
            (1 - likelihood_true) * prior + (1 - likelihood_false) * (1 - prior)
        )

    posterior = max(0.0, min(1.0, posterior))
    return {
        "posterior": round(posterior, 4),
        "prior": prior,
        "likelihood_true": likelihood_true,
        "likelihood_false": likelihood_false,
        "evidence": evidence,
    }


async def handle_monte_carlo(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    n_simulations = data.get("n_simulations", 10000)
    base_odds = data.get("base_odds", 0.5)
    volatility = data.get("volatility", 0.05)
    market = ctx.market or {}
    odds = market.get("current_odds", base_odds)

    rng = random.Random()
    results = []
    for _ in range(n_simulations):
        simulated = odds + rng.gauss(0, volatility)
        simulated = max(0.01, min(0.99, simulated))
        results.append(simulated)

    mean = sum(results) / len(results)
    wins = sum(1 for r in results if r > 0.5)
    win_prob = wins / n_simulations

    sorted_r = sorted(results)
    p5 = sorted_r[int(n_simulations * 0.05)]
    p25 = sorted_r[int(n_simulations * 0.25)]
    p75 = sorted_r[int(n_simulations * 0.75)]
    p95 = sorted_r[int(n_simulations * 0.95)]

    return {
        "mean": round(mean, 4),
        "win_probability": round(win_prob, 4),
        "percentiles": {
            "p5": round(p5, 4),
            "p25": round(p25, 4),
            "p75": round(p75, 4),
            "p95": round(p95, 4),
        },
        "n_simulations": n_simulations,
        "base_odds": odds,
        "volatility": volatility,
    }


async def handle_backtest(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    from app.services.backtester import Backtester, SimulatedMarketHistory

    bt = Backtester(initial_capital=data.get("initial_capital", 10000.0))
    history = SimulatedMarketHistory.generate(
        start_odds=data.get("start_odds", 0.5),
        steps=data.get("steps", 100),
        volatility=data.get("volatility", 0.02),
    )
    strategy_config = {
        "threshold": data.get("threshold", data.get("threshold", 0.5)),
        "operator": data.get("operator", "lt"),
        "side": data.get("side", "yes"),
    }
    try:
        result = await bt.run(strategy_config, history)
        return {
            "total_trades": result.total_trades,
            "win_rate": round(result.win_rate, 4),
            "total_pnl": round(result.total_pnl, 4),
            "return_pct": round(result.return_pct, 4),
            "final_capital": round(result.current_capital, 2),
        }
    except Exception as exc:
        return {"error": str(exc), "total_trades": 0}


async def handle_sentiment_filter(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    data = node.get("data", {})
    text = data.get("text", "")
    if not text:
        upstream_text = ""
        for v in inputs.values():
            if isinstance(v, dict):
                upstream_text = str(v.get("text", v.get("content", v.get("response", ""))))
                if upstream_text:
                    break
        text = upstream_text

    if not text:
        return {"triggered": False, "sentiment": 0.0, "label": "neutral", "error": "No text to analyze"}

    try:
        from app.ai.embeddings import EmbeddingService
        embedder = EmbeddingService()
        vec = embedder.encode(text)
        positivity = sum(vec[:10]) / max(len(vec[:10]), 1)
        positivity = max(-1.0, min(1.0, positivity))
        threshold = data.get("threshold", 0.0)

        if positivity > threshold:
            label = "positive"
            triggered = True
        elif positivity < -threshold:
            label = "negative"
            triggered = True
        else:
            label = "neutral"
            triggered = False

        return {
            "triggered": triggered,
            "sentiment": round(positivity, 4),
            "label": label,
            "text_preview": text[:200],
        }
    except Exception as exc:
        return {"triggered": False, "sentiment": 0.0, "label": "neutral", "error": str(exc)}


async def handle_tabpfn_signal(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    tabpfn = ctx.tabpfn
    if not tabpfn:
        return {"verdict": "UNAVAILABLE", "error": "TabPFN not available in context"}
    market = ctx.market or {}
    try:
        result = await tabpfn.validate_signal(market_data=market)
        return result
    except Exception as exc:
        return {"verdict": "ERROR", "error": str(exc)}


async def handle_toto2_climate(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    regime = ctx.market_regime
    if not regime:
        return {"regime": "unknown", "error": "Market regime service not available"}
    market = ctx.market or {}
    try:
        result = await regime.assess_climate([market])
        return result
    except Exception as exc:
        return {"regime": "unknown", "error": str(exc)}


def register_palette_handlers(registry) -> None:
    registry.register("polymarket_source", handle_polymarket_source)
    registry.register("kalshi_source", handle_kalshi_source)
    registry.register("drift_source", handle_drift_source)
    registry.register("web_search", handle_web_search)
    registry.register("news_source", handle_news_source)
    registry.register("time_condition", handle_time_condition)
    registry.register("and_or_gate", handle_and_or_gate)
    registry.register("branch", handle_branch)
    registry.register("place_bet", handle_place_bet)
    registry.register("forward", handle_forward)
    registry.register("webhook", handle_webhook)
    registry.register("bayesian_inference", handle_bayesian_inference)
    registry.register("monte_carlo", handle_monte_carlo)
    registry.register("backtest", handle_backtest)
    registry.register("sentiment_filter", handle_sentiment_filter)
    registry.register("tabpfn_signal", handle_tabpfn_signal)
    registry.register("toto2_climate", handle_toto2_climate)
