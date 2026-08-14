from typing import Any
import numpy as np


def handle_var_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    confidence = data.get("confidence", 0.95)
    limit = data.get("limit", 0.05)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    rc = ctx.risk_calculator
    if not rc or not returns:
        return {"triggered": False, "var": 0.0, "es": 0.0, "confidence": confidence}
    var = rc.historical_var(returns, confidence)
    es = rc.expected_shortfall(returns, confidence)
    triggered = var > limit
    return {"triggered": bool(triggered), "var": round(var, 4), "es": round(es, 4),
            "confidence": confidence, "limit": limit}


def handle_drawdown_monitor(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_dd = data.get("max_drawdown", 0.15)
    portfolio = ctx.portfolio or {}
    peak = portfolio.get("peak_capital", portfolio.get("current_capital", 10000))
    current = portfolio.get("current_capital", 10000)
    rc = ctx.risk_calculator
    drawdown = rc.current_drawdown(peak, current) if rc else 0.0
    triggered = drawdown >= max_dd
    return {"triggered": bool(triggered), "drawdown": drawdown, "max_drawdown": max_dd}


def handle_correlation_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_corr = data.get("max_correlation", 0.7)
    portfolio = ctx.portfolio or {}
    rc = ctx.risk_calculator
    returns = portfolio.get("returns", {})
    correlation = 0.0
    if rc and isinstance(returns, dict) and len(returns) > 1:
        try:
            corr_matrix = rc.correlation_matrix(returns)
            pairs = [(a, b, c) for a in corr_matrix for b in corr_matrix[a] if a < b]
            correlation = max((c for _, _, c in pairs), default=0.0)
        except Exception:
            correlation = 0.0
    triggered = correlation > max_corr
    return {"triggered": bool(triggered), "correlation": round(correlation, 4), "max_correlation": max_corr}


def handle_concentration_check(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_conc = data.get("max_concentration", 0.3)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    rc = ctx.risk_calculator
    concentration = rc.concentration(positions) if rc and positions else 0.0
    triggered = concentration > max_conc
    return {"triggered": bool(triggered), "concentration": round(concentration, 4), "max_concentration": max_conc}


def handle_position_sizer(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    method = data.get("method", "kelly")
    pm = ctx.portfolio_manager
    signal = ctx.signal or {}
    portfolio = ctx.portfolio or {}
    volatility = data.get("volatility", 0.02)
    if method == "fixed":
        size = data.get("fraction", 0.02)
    elif pm:
        size = pm.dynamic_position_size(portfolio, signal, volatility, method)
    else:
        size = 0.02
    return {"suggested_size": round(size, 4), "method": method, "approved": True}


def handle_hedge_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    hedge_ratio = data.get("hedge_ratio", 0.5)
    pm = ctx.portfolio_manager
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    if pm:
        hedge = pm.suggest_hedge(positions)
    else:
        hedge = {"hedges": []}
    hedge["hedge_ratio"] = hedge_ratio
    return hedge


def handle_rebalance_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    threshold = data.get("threshold", 0.05)
    targets = data.get("target_allocations", {})
    pm = ctx.portfolio_manager
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    if pm and targets:
        trades = pm.suggest_rebalance(positions, targets, threshold)
    else:
        trades = []
    return {"trades": trades}


def handle_alert_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    message = data.get("message", "Risk threshold breached")
    severity = data.get("severity", "warning")
    return {"action": "alert", "message": message, "severity": severity, "approved": True}


def handle_min_confidence(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    min_conf = data.get("min_confidence", 0.5)
    signal = ctx.signal or {}
    confidence = signal.get("confidence", 0)
    triggered = confidence < min_conf
    return {"triggered": bool(triggered), "confidence": confidence, "min_confidence": min_conf}


def handle_max_position_size(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_size = data.get("max_size", 0.2)
    suggested_size = inputs.get("suggested_size", 0.0)
    triggered = suggested_size > max_size
    return {"triggered": bool(triggered), "max_size": max_size, "suggested_size": suggested_size}


def handle_always(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    return {"triggered": True}


def handle_reject_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    return {"approved": False, "suggested_size": 0.0, "violations": ["rule_rejected"]}


def handle_approve_action(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    return {"approved": True, "suggested_size": 0.0, "violations": []}


def handle_stop_loss(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    stop_loss_pct = data.get("stop_loss", 0.1)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    triggered_positions = []
    for pos in positions:
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        if side == "buy":
            loss_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
        else:
            loss_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        if loss_pct >= stop_loss_pct:
            triggered_positions.append({
                "market_id": pos.get("market_id"),
                "entry_price": entry_price,
                "current_price": current_price,
                "loss_pct": round(loss_pct, 4),
            })
    return {
        "triggered": len(triggered_positions) > 0,
        "stop_loss": stop_loss_pct,
        "positions": triggered_positions,
    }


def handle_take_profit(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    take_profit_pct = data.get("take_profit", 0.2)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    triggered_positions = []
    for pos in positions:
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        if side == "buy":
            gain_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        else:
            gain_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
        if gain_pct >= take_profit_pct:
            triggered_positions.append({
                "market_id": pos.get("market_id"),
                "entry_price": entry_price,
                "current_price": current_price,
                "gain_pct": round(gain_pct, 4),
            })
    return {
        "triggered": len(triggered_positions) > 0,
        "take_profit": take_profit_pct,
        "positions": triggered_positions,
    }


def register_risk_handlers(registry):
    registry.register("var_check", handle_var_check)
    registry.register("drawdown_monitor", handle_drawdown_monitor)
    registry.register("correlation_check", handle_correlation_check)
    registry.register("concentration_check", handle_concentration_check)
    registry.register("position_sizer", handle_position_sizer)
    registry.register("hedge_action", handle_hedge_action)
    registry.register("rebalance_action", handle_rebalance_action)
    registry.register("alert_action", handle_alert_action)
    registry.register("min_confidence", handle_min_confidence)
    registry.register("always", handle_always)
    registry.register("position_size_check", handle_max_position_size)
    registry.register("reject_action", handle_reject_action)
    registry.register("approve_action", handle_approve_action)
    registry.register("stop_loss", handle_stop_loss)
    registry.register("take_profit", handle_take_profit)
