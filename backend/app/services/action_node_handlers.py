from typing import Any


def handle_close_position(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    close_pct = data.get("close_pct", 100)
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    target_market = data.get("market_id")
    orders = []
    for pos in positions:
        if target_market and pos.get("market_id") != target_market:
            continue
        size = pos.get("size", 0)
        close_size = size * (close_pct / 100)
        side = "sell" if pos.get("side", "buy") == "buy" else "buy"
        orders.append({
            "market_id": pos.get("market_id"),
            "platform": pos.get("platform", "polymarket"),
            "side": side,
            "amount": round(close_size, 2),
            "price": pos.get("price", 0.5),
        })
    return {"action": "close_position", "orders_placed": orders,
            "close_pct": close_pct, "approved": True}


def handle_close_position_on_take_profit(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    auto_execute = data.get("auto_execute", False)
    upstream_triggered = False
    for key, val in inputs.items():
        if isinstance(val, dict) and val.get("triggered"):
            upstream_triggered = True
            break
    if not upstream_triggered:
        return {"action": "auto_close", "executed": False, "reason": "no_trigger"}
    if not auto_execute:
        return {"action": "auto_close", "executed": False, "reason": "auto_execute_disabled"}
    portfolio = ctx.portfolio or {}
    positions = portfolio.get("positions", [])
    orders = []
    for pos in positions:
        side = "sell" if pos.get("side", "buy") == "buy" else "buy"
        orders.append({
            "market_id": pos.get("market_id"),
            "platform": pos.get("platform", "polymarket"),
            "side": side,
            "amount": pos.get("size", 0),
            "price": pos.get("price", 0.5),
        })
    return {"action": "auto_close", "executed": True, "orders_placed": orders,
            "approved": True}


def handle_withdraw_to_safe_wallet(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    withdraw_pct = data.get("withdraw_pct", 50)
    source = data.get("source", "profits")
    target_currency = data.get("target_currency", "USDC")
    portfolio = ctx.portfolio or {}
    current_capital = portfolio.get("current_capital", 10000)
    initial_capital = portfolio.get("initial_capital", 10000)
    if source == "profits":
        amount = max(0, current_capital - initial_capital)
    elif source == "capital":
        amount = current_capital
    else:
        amount = current_capital
    withdraw_amount = amount * (withdraw_pct / 100)
    safe_wallet_id = data.get("safe_wallet_id", "default")
    return {"action": "withdraw", "amount": round(withdraw_amount, 2),
            "currency": target_currency, "safe_wallet_id": safe_wallet_id,
            "source": source, "approved": True}


def handle_convert_to_stablecoin(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    target_stablecoin = data.get("target_stablecoin", "USDC")
    convert_pct = data.get("convert_pct", 100)
    portfolio = ctx.portfolio or {}
    current_capital = portfolio.get("current_capital", 10000)
    initial_capital = portfolio.get("initial_capital", 10000)
    profits = max(0, current_capital - initial_capital)
    convert_amount = profits * (convert_pct / 100)
    return {"action": "convert", "amount": round(convert_amount, 2),
            "stablecoin": target_stablecoin, "approved": True}


def handle_withdrawal_strategy(node: dict, inputs, ctx) -> dict[str, Any]:
    data = node.get("data", {})
    steps = data.get("steps", [])
    withdrawal_state = getattr(ctx, "withdrawal_state", {})
    portfolio = ctx.portfolio or {}
    current_capital = portfolio.get("current_capital", 10000)
    initial_capital = portfolio.get("initial_capital", 10000)
    profit = current_capital - initial_capital
    actions = []
    for i, step in enumerate(steps):
        step_id = step.get("id", str(i))
        state = withdrawal_state.get(step_id, {"status": "pending"})
        if step.get("once", True) and state.get("status") == "executed":
            continue
        condition = step.get("condition", {})
        cond_type = condition.get("type", "")
        triggered = False
        if cond_type == "profit_threshold":
            triggered = profit >= condition.get("amount", 0)
        elif cond_type == "profit_pct":
            profit_pct = profit / initial_capital if initial_capital > 0 else 0
            triggered = profit_pct >= condition.get("pct", 0)
        elif cond_type == "drawdown_from_peak":
            peak = portfolio.get("peak_capital", current_capital)
            dd = (peak - current_capital) / peak if peak > 0 else 0
            triggered = dd >= condition.get("pct", 0) / 100
        if triggered:
            action = step.get("action", {})
            act_type = action.get("type", "")
            if act_type == "withdraw_pct":
                amount = profit * (action.get("pct", 0) / 100)
                actions.append({"step_id": step_id, "action": "withdraw",
                                "amount": round(amount, 2),
                                "currency": action.get("currency", "USDC")})
            elif act_type == "withdraw_fixed":
                actions.append({"step_id": step_id, "action": "withdraw",
                                "amount": action.get("amount", 0),
                                "currency": action.get("currency", "USDC")})
            withdrawal_state[step_id] = {"status": "executed"}
    return {"action": "withdrawal_strategy", "actions": actions,
            "steps_evaluated": len(steps), "approved": True}


def register_action_handlers(registry):
    registry.register("close_position", handle_close_position)
    registry.register("close_position_on_take_profit", handle_close_position_on_take_profit)
    registry.register("withdraw_to_safe_wallet", handle_withdraw_to_safe_wallet)
    registry.register("convert_to_stablecoin", handle_convert_to_stablecoin)
    registry.register("withdrawal_strategy", handle_withdrawal_strategy)
