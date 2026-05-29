from typing import Any
import numpy as np
from datetime import datetime, timezone


# ─── Position-Level Exit Nodes ────────────────────────────────────────────────

def handle_trailing_stop(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    trail_pct = data.get("trail_pct", 0.05)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    trail_states = getattr(ctx, "trail_states", {})
    triggered_positions = []
    for pos in positions:
        pid = pos.get("market_id", "unknown")
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        state = trail_states.get(pid, {})
        hwm = state.get("high_water_mark", entry_price)
        if side == "buy":
            if current_price > hwm:
                hwm = current_price
            loss_from_hwm = (hwm - current_price) / hwm if hwm > 0 else 0
            triggered = loss_from_hwm >= trail_pct
        else:
            if current_price < hwm or hwm == entry_price:
                hwm = current_price
            loss_from_hwm = (current_price - hwm) / hwm if hwm > 0 else 0
            triggered = loss_from_hwm >= trail_pct
        trail_states[pid] = {"high_water_mark": hwm}
        if triggered:
            triggered_positions.append({
                "market_id": pid, "entry_price": entry_price,
                "current_price": current_price, "hwm": hwm,
                "loss_from_hwm": round(loss_from_hwm, 4),
            })
    return {"triggered": len(triggered_positions) > 0, "trail_pct": trail_pct,
            "positions": triggered_positions}


def handle_tightening_trailing_stop(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    thresholds = data.get("thresholds", [[0.05, 0.03], [0.10, 0.02], [0.20, 0.01]])
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    trail_states = getattr(ctx, "trail_states", {})
    triggered_positions = []
    for pos in positions:
        pid = pos.get("market_id", "unknown")
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        state = trail_states.get(pid, {})
        hwm = state.get("high_water_mark", entry_price)
        if side == "buy":
            if current_price > hwm:
                hwm = current_price
            profit_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        else:
            if current_price < hwm or hwm == entry_price:
                hwm = current_price
            profit_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
        active_trail_pct = thresholds[0][1] if thresholds else 0.05
        current_tier = 0
        for i, (tp, trp) in enumerate(thresholds):
            if profit_pct >= tp:
                active_trail_pct = trp
                current_tier = i
        trail_states[pid] = {"high_water_mark": hwm}
        if side == "buy":
            loss_from_hwm = (hwm - current_price) / hwm if hwm > 0 else 0
        else:
            loss_from_hwm = (current_price - hwm) / hwm if hwm > 0 else 0
        if loss_from_hwm >= active_trail_pct:
            triggered_positions.append({
                "market_id": pid, "entry_price": entry_price,
                "current_price": current_price, "hwm": hwm,
                "current_tier": current_tier, "trail_pct": active_trail_pct,
            })
    return {"triggered": len(triggered_positions) > 0, "positions": triggered_positions}


def handle_atr_stop(node: dict, inputs: dict, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    atr_multiplier = data.get("atr_multiplier", 2.0)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    atr_values = portfolio.get("atr_values", [])
    current_atr = atr_values[-1] if atr_values else 0.02
    stop_distance = atr_multiplier * current_atr
    triggered_positions = []
    for pos in positions:
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        if side == "buy":
            stop_price = entry_price - stop_distance
            triggered = current_price <= stop_price
        else:
            stop_price = entry_price + stop_distance
            triggered = current_price >= stop_price
        if triggered:
            triggered_positions.append({
                "market_id": pos.get("market_id"), "entry_price": entry_price,
                "current_price": current_price, "stop_price": round(stop_price, 4),
            })
    return {"triggered": len(triggered_positions) > 0, "stop_distance": round(stop_distance, 4),
            "atr": round(current_atr, 4), "positions": triggered_positions}


def handle_volatility_stop(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    vol_threshold = data.get("vol_threshold", 0.03)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    if len(returns) < 2:
        return {"triggered": False, "current_vol": 0.0, "threshold": vol_threshold}
    arr = np.array(returns, dtype=np.float64)
    current_vol = float(np.std(arr, ddof=1))
    return {"triggered": current_vol >= vol_threshold, "current_vol": round(current_vol, 4),
            "threshold": vol_threshold}


def handle_time_exit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_hold_days = data.get("max_hold_days", 30)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    now = datetime.now(timezone.utc)
    triggered_positions = []
    for pos in positions:
        entry_time_str = pos.get("entry_time")
        if not entry_time_str:
            continue
        try:
            entry_time = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        hold_days = (now - entry_time).total_seconds() / 86400
        if hold_days >= max_hold_days:
            triggered_positions.append({
                "market_id": pos.get("market_id"), "hold_days": round(hold_days, 1),
                "max_hold_days": max_hold_days,
            })
    return {"triggered": len(triggered_positions) > 0, "max_hold_days": max_hold_days,
            "positions": triggered_positions}


def handle_break_even_stop(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    trigger_pct = data.get("trigger_pct", 0.02)
    buffer_pct = data.get("buffer_pct", 0.005)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    triggered_positions = []
    for pos in positions:
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        if side == "buy":
            profit_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
            stop_price = entry_price * (1 + buffer_pct)
            triggered = profit_pct >= trigger_pct and current_price <= stop_price
        else:
            profit_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
            stop_price = entry_price * (1 - buffer_pct)
            triggered = profit_pct >= trigger_pct and current_price >= stop_price
        if triggered:
            triggered_positions.append({
                "market_id": pos.get("market_id"), "entry_price": entry_price,
                "current_price": current_price, "stop_price": round(stop_price, 4),
            })
    return {"triggered": len(triggered_positions) > 0, "positions": triggered_positions}


def handle_scaling_exit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    tiers = data.get("tiers", [{"profit_pct": 0.10, "exit_pct": 33}, {"profit_pct": 0.25, "exit_pct": 50}])
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    market = ctx.market or {}
    current_price = market.get("current_odds", 0.5)
    triggered_positions = []
    for pos in positions:
        entry_price = pos.get("price", current_price)
        side = pos.get("side", "buy")
        if side == "buy":
            profit_pct = (current_price - entry_price) / entry_price if entry_price > 0 else 0
        else:
            profit_pct = (entry_price - current_price) / entry_price if entry_price > 0 else 0
        for i, tier in enumerate(tiers):
            if profit_pct >= tier["profit_pct"]:
                triggered_positions.append({
                    "market_id": pos.get("market_id"), "exit_tier": i,
                    "exit_pct": tier["exit_pct"], "profit_pct": round(profit_pct, 4),
                })
    return {"triggered": len(triggered_positions) > 0, "positions": triggered_positions}


def handle_moving_average_exit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    period = data.get("period", 20)
    ma_type = data.get("ma_type", "sma")
    portfolio = ctx.portfolio or {}
    price_history = portfolio.get("price_history", [])
    if len(price_history) < period:
        return {"triggered": False, "ma_value": 0.0, "crossover": "none"}
    arr = np.array(price_history[-period:], dtype=np.float64)
    if ma_type == "ema":
        weights = np.exp(np.linspace(-1., 0., len(arr)))
        weights /= weights.sum()
        ma_value = float(np.dot(arr, weights))
    else:
        ma_value = float(np.mean(arr))
    current_price = price_history[-1] if price_history else 0
    prev_price = price_history[-2] if len(price_history) >= 2 else current_price
    crossover = "none"
    if prev_price <= ma_value and current_price > ma_value:
        crossover = "bullish"
    elif prev_price >= ma_value and current_price < ma_value:
        crossover = "bearish"
    return {"triggered": crossover == "bearish", "ma_value": round(ma_value, 4),
            "crossover": crossover, "period": period}


# ─── Portfolio-Level Risk Nodes ───────────────────────────────────────────────

def handle_daily_loss_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_daily_loss = data.get("max_daily_loss", 0.03)
    portfolio = ctx.portfolio or {}
    daily_pnl = getattr(ctx, "daily_pnl", 0.0)
    initial_capital = portfolio.get("initial_capital", portfolio.get("current_capital", 10000))
    loss_pct = abs(daily_pnl) / initial_capital if initial_capital > 0 and daily_pnl < 0 else 0
    return {"triggered": daily_pnl < 0 and loss_pct >= max_daily_loss,
            "daily_pnl": round(daily_pnl, 2), "loss_pct": round(loss_pct, 4),
            "limit": max_daily_loss}


def handle_weekly_loss_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_weekly_loss = data.get("max_weekly_loss", 0.05)
    portfolio = ctx.portfolio or {}
    weekly_pnl = getattr(ctx, "weekly_pnl", 0.0)
    initial_capital = portfolio.get("initial_capital", portfolio.get("current_capital", 10000))
    loss_pct = abs(weekly_pnl) / initial_capital if initial_capital > 0 and weekly_pnl < 0 else 0
    return {"triggered": weekly_pnl < 0 and loss_pct >= max_weekly_loss,
            "weekly_pnl": round(weekly_pnl, 2), "loss_pct": round(loss_pct, 4),
            "limit": max_weekly_loss}


def handle_monthly_loss_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_monthly_loss = data.get("max_monthly_loss", 0.10)
    portfolio = ctx.portfolio or {}
    monthly_pnl = getattr(ctx, "monthly_pnl", 0.0)
    initial_capital = portfolio.get("initial_capital", portfolio.get("current_capital", 10000))
    loss_pct = abs(monthly_pnl) / initial_capital if initial_capital > 0 and monthly_pnl < 0 else 0
    return {"triggered": monthly_pnl < 0 and loss_pct >= max_monthly_loss,
            "monthly_pnl": round(monthly_pnl, 2), "loss_pct": round(loss_pct, 4),
            "limit": max_monthly_loss}


def handle_max_position_count(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_count = data.get("max_count", 10)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    count = len(positions)
    return {"triggered": count > max_count, "count": count, "max_count": max_count}


def handle_max_gross_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_exposure = data.get("max_exposure", 1.0)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    total_capital = portfolio.get("current_capital", 10000)
    gross = sum(abs(p.get("size", 0)) for p in positions)
    exposure = gross / total_capital if total_capital > 0 else 0
    return {"triggered": exposure > max_exposure, "exposure": round(exposure, 4),
            "max_exposure": max_exposure}


def handle_max_net_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_net = data.get("max_net_exposure", 0.5)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    total_capital = portfolio.get("current_capital", 10000)
    net = sum(p.get("size", 0) * (1 if p.get("side", "buy") == "buy" else -1) for p in positions)
    net_exposure = abs(net) / total_capital if total_capital > 0 else 0
    return {"triggered": net_exposure > max_net, "net_exposure": round(net_exposure, 4),
            "max_net_exposure": max_net}


def handle_leverage_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_leverage = data.get("max_leverage", 2.0)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    total_capital = portfolio.get("current_capital", 10000)
    total_notional = sum(abs(p.get("size", 0) * p.get("price", 0.5)) for p in positions)
    leverage = total_notional / total_capital if total_capital > 0 else 0
    return {"triggered": leverage > max_leverage, "leverage": round(leverage, 4),
            "max_leverage": max_leverage}


def handle_sector_exposure_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    sector_limits = data.get("sector_limits", {})
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    total_capital = portfolio.get("current_capital", 10000)
    sector_exposure: dict[str, float] = {}
    for p in positions:
        sector = p.get("sector", "default")
        sector_exposure[sector] = sector_exposure.get(sector, 0) + abs(p.get("size", 0))
    breached = []
    for sector, limit in sector_limits.items():
        exposure = sector_exposure.get(sector, 0) / total_capital if total_capital > 0 else 0
        if exposure > limit:
            breached.append({"sector": sector, "exposure": round(exposure, 4), "limit": limit})
    return {"triggered": len(breached) > 0, "breached_sectors": breached}


def handle_beta_exposure_limit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_beta = data.get("max_beta", 1.0)
    portfolio = ctx.portfolio or {}
    beta = portfolio.get("beta", 0)
    return {"triggered": abs(beta) > max_beta, "beta": round(beta, 4), "max_beta": max_beta}


def handle_volatility_targeting(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    target_vol = data.get("target_vol", 0.10)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    if len(returns) < 2:
        return {"scaling_factor": 1.0, "current_vol": 0.0, "target_vol": target_vol}
    arr = np.array(returns, dtype=np.float64)
    current_vol = float(np.std(arr, ddof=1))
    scaling = target_vol / current_vol if current_vol > 0 else 1.0
    scaling = max(0.1, min(scaling, 3.0))
    return {"scaling_factor": round(scaling, 4), "current_vol": round(current_vol, 4),
            "target_vol": target_vol}


def handle_stress_test(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    scenarios = data.get("scenarios", [])
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    total_capital = portfolio.get("current_capital", 10000)
    worst_case_loss = 0.0
    scenario_results = []
    for scenario in scenarios:
        shocks = scenario.get("shocks", {})
        portfolio_loss = 0.0
        for pos in positions:
            market_id = pos.get("market_id", "")
            shock = shocks.get(market_id, 0.0)
            portfolio_loss += pos.get("size", 0) * shock
        loss_pct = abs(portfolio_loss) / total_capital if total_capital > 0 else 0
        scenario_results.append({
            "name": scenario.get("name", "unnamed"),
            "loss_pct": round(loss_pct, 4),
        })
        worst_case_loss = max(worst_case_loss, loss_pct)
    max_loss_limit = data.get("max_worst_case_loss", 0.20)
    return {"triggered": worst_case_loss >= max_loss_limit,
            "worst_case_loss": round(worst_case_loss, 4),
            "scenarios": scenario_results}


def handle_monte_carlo_risk(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    num_simulations = data.get("num_simulations", 1000)
    confidence = data.get("confidence", 0.95)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    if len(returns) < 2:
        return {"var_mc": 0.0, "worst_case": 0.0, "percentile_5": 0.0}
    arr = np.array(returns, dtype=np.float64)
    mu = float(np.mean(arr))
    sigma = float(np.std(arr, ddof=1))
    simulated = np.random.normal(mu, sigma, (num_simulations, 30))
    cumulative = np.cumsum(simulated, axis=1)[:, -1]
    var_mc = float(np.percentile(cumulative, (1 - confidence) * 100))
    worst_case = float(np.min(cumulative))
    percentile_5 = float(np.percentile(cumulative, 5))
    return {"var_mc": round(abs(var_mc), 4), "worst_case": round(worst_case, 4),
            "percentile_5": round(percentile_5, 4), "simulations": num_simulations}


def handle_tail_risk_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_kurtosis = data.get("max_kurtosis", 5.0)
    max_skewness = data.get("max_skewness", -0.5)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    if len(returns) < 4:
        return {"triggered": False, "kurtosis": 0.0, "skewness": 0.0}
    arr = np.array(returns, dtype=np.float64)
    mean = np.mean(arr)
    std = np.std(arr, ddof=1)
    if std == 0:
        return {"triggered": False, "kurtosis": 0.0, "skewness": 0.0}
    skewness = float(np.mean(((arr - mean) / std) ** 3))
    kurtosis = float(np.mean(((arr - mean) / std) ** 4))
    triggered = kurtosis > max_kurtosis or skewness < max_skewness
    return {"triggered": triggered, "kurtosis": round(kurtosis, 4),
            "skewness": round(skewness, 4)}


def handle_liquidity_risk_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    min_liquidity = data.get("min_liquidity", 10000)
    max_spread_pct = data.get("max_spread_pct", 0.05)
    market = ctx.market or {}
    liquidity = market.get("liquidity", 0)
    spread = market.get("spread", 0)
    mid_price = market.get("current_odds", 0.5)
    spread_pct = spread / mid_price if mid_price > 0 else 0
    triggered = liquidity < min_liquidity or spread_pct > max_spread_pct
    return {"triggered": triggered, "liquidity": liquidity, "spread_pct": round(spread_pct, 4)}


def handle_factor_exposure_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_exposures = data.get("max_factor_exposures", {})
    portfolio = ctx.portfolio or {}
    factor_exposures = portfolio.get("factor_exposures", {})
    breached = []
    for factor, limit in max_exposures.items():
        exposure = abs(factor_exposures.get(factor, 0))
        if exposure > limit:
            breached.append({"factor": factor, "exposure": round(exposure, 4), "limit": limit})
    return {"triggered": len(breached) > 0, "breached_factors": breached}


def handle_mcr_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_mcr = data.get("max_mcr", 0.1)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    rc = ctx.risk_calculator
    returns = portfolio.get("returns", [])
    if not rc or not returns or not positions:
        return {"triggered": False, "mcr_values": []}
    total_var = rc.historical_var(returns, 0.95)
    total_size = sum(abs(p.get("size", 0)) for p in positions)
    mcr_values = []
    for p in positions:
        weight = abs(p.get("size", 0)) / total_size if total_size > 0 else 0
        mcr = total_var * weight
        mcr_values.append({"market_id": p.get("market_id"), "mcr": round(mcr, 4)})
    max_mcr_val = max((m["mcr"] for m in mcr_values), default=0)
    return {"triggered": max_mcr_val > max_mcr, "mcr_values": mcr_values}


def handle_worst_case_portfolio(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_wcl = data.get("max_worst_case_loss", 0.20)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    if len(returns) < 2:
        return {"triggered": False, "worst_case_loss": 0.0}
    arr = np.array(returns, dtype=np.float64)
    worst = float(np.min(arr))
    cumulative_worst = float(np.sum(arr[arr < 0])) if np.any(arr < 0) else 0
    total_capital = portfolio.get("current_capital", 10000)
    loss_pct = abs(cumulative_worst) / total_capital if total_capital > 0 else 0
    return {"triggered": loss_pct >= max_wcl, "worst_case_loss": round(loss_pct, 4)}


def handle_expected_shortfall_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    confidence = data.get("confidence", 0.95)
    limit = data.get("limit", 0.08)
    portfolio = ctx.portfolio or {}
    returns = portfolio.get("returns", [])
    rc = ctx.risk_calculator
    if not rc or not returns:
        return {"triggered": False, "es": 0.0, "confidence": confidence}
    es = rc.expected_shortfall(returns, confidence)
    return {"triggered": es > limit, "es": round(es, 4), "confidence": confidence,
            "limit": limit}


# ─── Greeks/Options Risk Nodes ────────────────────────────────────────────────

def handle_delta_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_delta = data.get("max_delta", 1.0)
    portfolio = ctx.portfolio or {}
    delta = portfolio.get("greeks", {}).get("delta", 0)
    return {"triggered": abs(delta) > max_delta, "delta": round(delta, 4),
            "max_delta": max_delta}


def handle_gamma_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_gamma = data.get("max_gamma", 0.5)
    portfolio = ctx.portfolio or {}
    gamma = portfolio.get("greeks", {}).get("gamma", 0)
    return {"triggered": abs(gamma) > max_gamma, "gamma": round(gamma, 4),
            "max_gamma": max_gamma}


def handle_vega_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_vega = data.get("max_vega", 0.5)
    portfolio = ctx.portfolio or {}
    vega = portfolio.get("greeks", {}).get("vega", 0)
    return {"triggered": abs(vega) > max_vega, "vega": round(vega, 4),
            "max_vega": max_vega}


def handle_theta_decay(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_theta_loss = data.get("max_theta_loss", 100)
    portfolio = ctx.portfolio or {}
    theta = portfolio.get("greeks", {}).get("theta", 0)
    return {"triggered": abs(theta) > max_theta_loss and theta < 0,
            "theta": round(theta, 4), "max_theta_loss": max_theta_loss}


def handle_vanna_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_vanna = data.get("max_vanna", 0.3)
    portfolio = ctx.portfolio or {}
    vanna = portfolio.get("greeks", {}).get("vanna", 0)
    return {"triggered": abs(vanna) > max_vanna, "vanna": round(vanna, 4),
            "max_vanna": max_vanna}


def handle_volga_exposure(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_volga = data.get("max_volga", 0.3)
    portfolio = ctx.portfolio or {}
    volga = portfolio.get("greeks", {}).get("volga", 0)
    return {"triggered": abs(volga) > max_volga, "volga": round(volga, 4),
            "max_volga": max_volga}


# ─── Execution/Operational Risk Nodes ─────────────────────────────────────────

def handle_circuit_breaker(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_daily_loss = data.get("max_daily_loss", 0.05)
    max_consecutive = data.get("max_consecutive_losses", 5)
    cooldown_sec = data.get("cooldown_seconds", 300)
    portfolio = ctx.portfolio or {}
    cb_state = getattr(ctx, "circuit_breaker_state", {})
    daily_pnl = getattr(ctx, "daily_pnl", 0.0)
    consecutive_losses = getattr(ctx, "consecutive_losses", 0)
    initial_capital = portfolio.get("initial_capital", portfolio.get("current_capital", 10000))
    loss_pct = abs(daily_pnl) / initial_capital if initial_capital > 0 and daily_pnl < 0 else 0
    state = cb_state.get("state", "closed")
    reason = ""
    if state == "cooldown":
        import time
        cooldown_start = cb_state.get("cooldown_start", 0)
        if time.time() - cooldown_start >= cooldown_sec:
            state = "closed"
            cb_state["state"] = "closed"
        else:
            reason = "cooldown_active"
    elif loss_pct >= max_daily_loss:
        state = "open"
        reason = f"daily_loss_{loss_pct:.1%}_exceeds_{max_daily_loss:.1%}"
    elif consecutive_losses >= max_consecutive:
        state = "open"
        reason = f"consecutive_losses_{consecutive_losses}_exceeds_{max_consecutive}"
    if state == "open" and reason:
        import time
        cb_state["state"] = "cooldown"
        cb_state["cooldown_start"] = time.time()
        state = "cooldown"
    return {"triggered": state != "closed", "state": state, "reason": reason}


def handle_slippage_guard(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_slippage = data.get("max_slippage_pct", 0.02)
    portfolio = ctx.portfolio or {}
    last_slippage = portfolio.get("last_trade_slippage", 0)
    return {"triggered": last_slippage > max_slippage,
            "last_slippage": round(last_slippage, 4), "max_slippage": max_slippage}


def handle_max_consecutive_losses(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_streak = data.get("max_streak", 5)
    consecutive_losses = getattr(ctx, "consecutive_losses", 0)
    return {"triggered": consecutive_losses >= max_streak,
            "consecutive_losses": consecutive_losses, "max_streak": max_streak}


def handle_cooldown_period(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    cooldown_trades = data.get("cooldown_trades", 3)
    consecutive_losses = getattr(ctx, "consecutive_losses", 0)
    return {"triggered": consecutive_losses >= cooldown_trades,
            "consecutive_losses": consecutive_losses, "cooldown_trades": cooldown_trades}


def handle_position_timeout(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    max_hold_sec = data.get("max_hold_seconds", 86400)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    now = datetime.now(timezone.utc)
    triggered = []
    for pos in positions:
        entry_time_str = pos.get("entry_time")
        if not entry_time_str:
            continue
        try:
            entry_time = datetime.fromisoformat(entry_time_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            continue
        hold_sec = (now - entry_time).total_seconds()
        if hold_sec >= max_hold_sec:
            triggered.append({"market_id": pos.get("market_id"),
                              "hold_seconds": round(hold_sec)})
    return {"triggered": len(triggered) > 0, "positions": triggered}


# ─── Regime/Market Structure Nodes ────────────────────────────────────────────

def handle_volatility_regime_check(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    target_regime = data.get("target_regime", "normal")
    portfolio = ctx.portfolio or {}
    vol_regime = portfolio.get("volatility_regime", "normal")
    return {"triggered": vol_regime != target_regime,
            "current_regime": vol_regime, "target_regime": target_regime}


def handle_correlation_regime_shift(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    spike_threshold = data.get("correlation_spike_threshold", 0.3)
    portfolio = ctx.portfolio or {}
    current_corr = portfolio.get("current_avg_correlation", 0)
    historical_corr = portfolio.get("historical_avg_correlation", 0)
    shift = abs(current_corr - historical_corr)
    return {"triggered": shift > spike_threshold,
            "correlation_shift": round(shift, 4), "threshold": spike_threshold}


def handle_toxicity_detection(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    vpin_threshold = data.get("vpin_threshold", 0.7)
    vpin = getattr(ctx, "vpin", 0)
    return {"triggered": vpin > vpin_threshold, "vpin": round(vpin, 4),
            "threshold": vpin_threshold}


def handle_order_flow_imbalance(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    imbalance_threshold = data.get("imbalance_threshold", 0.3)
    ofi = getattr(ctx, "ofi", 0)
    return {"triggered": abs(ofi) > imbalance_threshold,
            "ofi": round(ofi, 4), "threshold": imbalance_threshold}


# ─── Portfolio Construction Nodes ─────────────────────────────────────────────

def handle_risk_parity_allocation(node: dict, inputs, ctx) -> dict[str, Any]:
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    if not positions:
        return {"suggested_weights": {}}
    returns_dict = portfolio.get("position_returns", {})
    weights = {}
    inv_vol_sum = 0
    for p in positions:
        mid = p.get("market_id", "")
        rets = returns_dict.get(mid, [])
        if len(rets) < 2:
            vol = 1.0
        else:
            vol = float(np.std(np.array(rets, dtype=np.float64), ddof=1))
        inv_vol = 1.0 / max(vol, 0.001)
        weights[mid] = inv_vol
        inv_vol_sum += inv_vol
    for mid in weights:
        weights[mid] = round(weights[mid] / inv_vol_sum, 4) if inv_vol_sum > 0 else 0
    return {"suggested_weights": weights}


def handle_mean_variance_optimization(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    risk_aversion = data.get("risk_aversion", 1.0)
    portfolio = ctx.portfolio or {}
    returns_dict = portfolio.get("position_returns", {})
    if not returns_dict:
        return {"suggested_weights": {}, "expected_return": 0, "expected_risk": 0}
    assets = list(returns_dict.keys())
    min_len = min((len(v) for v in returns_dict.values()), default=0)
    if min_len < 2 or not assets:
        return {"suggested_weights": {}, "expected_return": 0, "expected_risk": 0}
    returns_matrix = np.array([returns_dict[a][:min_len] for a in assets], dtype=np.float64)
    mu = np.mean(returns_matrix, axis=1)
    cov = np.cov(returns_matrix)
    try:
        inv_cov = np.linalg.inv(cov)
        ones = np.ones(len(assets))
        A = ones @ inv_cov @ mu
        B = mu @ inv_cov @ mu
        C = ones @ inv_cov @ ones
        w = (inv_cov @ mu) / risk_aversion
        w = np.maximum(w, 0)
        w_sum = np.sum(w)
        if w_sum > 0:
            w = w / w_sum
        weights = {assets[i]: round(float(w[i]), 4) for i in range(len(assets))}
    except np.linalg.LinAlgError:
        weights = {a: round(1.0 / len(assets), 4) for a in assets}
    return {"suggested_weights": weights}


def handle_black_litterman(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    views = data.get("views", {})
    tau = data.get("tau", 0.05)
    portfolio = ctx.portfolio or {}
    returns_dict = portfolio.get("position_returns", {})
    if not returns_dict or not views:
        equal_w = 1.0 / max(len(returns_dict), 1)
        return {"suggested_weights": {a: round(equal_w, 4) for a in returns_dict}}
    assets = list(returns_dict.keys())
    min_len = min((len(v) for v in returns_dict.values()), default=0)
    if min_len < 2:
        equal_w = 1.0 / max(len(assets), 1)
        return {"suggested_weights": {a: round(equal_w, 4) for a in assets}}
    returns_matrix = np.array([returns_dict[a][:min_len] for a in assets], dtype=np.float64)
    cov = np.cov(returns_matrix)
    try:
        inv_cov = np.linalg.inv(cov)
        ones = np.ones(len(assets))
        pi = tau * cov @ inv_cov @ (ones @ inv_cov @ ones)
        view_assets = [a for a in views if a in assets]
        if not view_assets:
            w = inv_cov @ pi
            w = np.maximum(w, 0)
            w_sum = np.sum(w)
            if w_sum > 0:
                w = w / w_sum
            weights = {assets[i]: round(float(w[i]), 4) for i in range(len(assets))}
        else:
            equal_w = 1.0 / len(assets)
            weights = {a: round(equal_w, 4) for a in assets}
    except np.linalg.LinAlgError:
        equal_w = 1.0 / len(assets)
        weights = {a: round(equal_w, 4) for a in assets}
    return {"suggested_weights": weights}


def handle_hierarchical_risk_parity(node: dict, inputs, ctx) -> dict[str, Any]:
    portfolio = ctx.portfolio or {}
    returns_dict = portfolio.get("position_returns", {})
    if not returns_dict:
        return {"suggested_weights": {}}
    assets = list(returns_dict.keys())
    min_len = min((len(v) for v in returns_dict.values()), default=0)
    if min_len < 2 or len(assets) < 2:
        equal_w = 1.0 / max(len(assets), 1)
        return {"suggested_weights": {a: round(equal_w, 4) for a in assets}}
    returns_matrix = np.array([returns_dict[a][:min_len] for a in assets], dtype=np.float64)
    cov = np.cov(returns_matrix)
    vols = np.sqrt(np.diag(cov))
    vols = np.maximum(vols, 1e-8)
    inv_vol_weights = (1.0 / vols)
    inv_vol_weights = inv_vol_weights / np.sum(inv_vol_weights)
    weights = {assets[i]: round(float(inv_vol_weights[i]), 4) for i in range(len(assets))}
    return {"suggested_weights": weights}


# ─── Registration ─────────────────────────────────────────────────────────────

def register_advanced_risk_handlers(registry):
    # Position exits
    registry.register("trailing_stop", handle_trailing_stop)
    registry.register("tightening_trailing_stop", handle_tightening_trailing_stop)
    registry.register("atr_stop", handle_atr_stop)
    registry.register("volatility_stop", handle_volatility_stop)
    registry.register("time_exit", handle_time_exit)
    registry.register("break_even_stop", handle_break_even_stop)
    registry.register("scaling_exit", handle_scaling_exit)
    registry.register("moving_average_exit", handle_moving_average_exit)
    # Portfolio limits
    registry.register("daily_loss_limit", handle_daily_loss_limit)
    registry.register("weekly_loss_limit", handle_weekly_loss_limit)
    registry.register("monthly_loss_limit", handle_monthly_loss_limit)
    registry.register("max_position_count", handle_max_position_count)
    registry.register("max_gross_exposure", handle_max_gross_exposure)
    registry.register("max_net_exposure", handle_max_net_exposure)
    registry.register("leverage_limit", handle_leverage_limit)
    registry.register("sector_exposure_limit", handle_sector_exposure_limit)
    registry.register("beta_exposure_limit", handle_beta_exposure_limit)
    registry.register("volatility_targeting", handle_volatility_targeting)
    registry.register("stress_test", handle_stress_test)
    registry.register("monte_carlo_risk", handle_monte_carlo_risk)
    registry.register("tail_risk_check", handle_tail_risk_check)
    registry.register("liquidity_risk_check", handle_liquidity_risk_check)
    registry.register("expected_shortfall_check", handle_expected_shortfall_check)
    # Diversification
    registry.register("factor_exposure_check", handle_factor_exposure_check)
    registry.register("mcr_check", handle_mcr_check)
    registry.register("worst_case_portfolio", handle_worst_case_portfolio)
    # Greeks
    registry.register("delta_exposure", handle_delta_exposure)
    registry.register("gamma_exposure", handle_gamma_exposure)
    registry.register("vega_exposure", handle_vega_exposure)
    registry.register("theta_decay", handle_theta_decay)
    registry.register("vanna_exposure", handle_vanna_exposure)
    registry.register("volga_exposure", handle_volga_exposure)
    # Execution
    registry.register("circuit_breaker", handle_circuit_breaker)
    registry.register("slippage_guard", handle_slippage_guard)
    registry.register("max_consecutive_losses", handle_max_consecutive_losses)
    registry.register("cooldown_period", handle_cooldown_period)
    registry.register("position_timeout", handle_position_timeout)
    # Regime
    registry.register("volatility_regime_check", handle_volatility_regime_check)
    registry.register("correlation_regime_shift", handle_correlation_regime_shift)
    registry.register("toxicity_detection", handle_toxicity_detection)
    registry.register("order_flow_imbalance", handle_order_flow_imbalance)
    # Portfolio construction
    registry.register("risk_parity_allocation", handle_risk_parity_allocation)
    registry.register("mean_variance_optimization", handle_mean_variance_optimization)
    registry.register("black_litterman", handle_black_litterman)
    registry.register("hierarchical_risk_parity", handle_hierarchical_risk_parity)
