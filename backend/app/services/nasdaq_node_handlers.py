"""
NASDAQ Trading Strategy Node Handlers

A mean-reversion + momentum strategy for NASDAQ-100 / QQQ prediction markets.

Strategy overview:
  1. Signal Generator  -- z-score of returns; triggers on extreme moves (|z| > threshold)
  2. Confirmation      -- volume filter + VIX regime check
  3. Risk Management   -- ATR-based position sizing, max portfolio %
  4. Entry/Exit Logic  -- long on oversold + volume, short on overbought + volume
  5. Execution         -- limit order placement with fill timeout

Indicators used:
  - Z-score of N-period returns
  - Average True Range (ATR)
  - Volume moving average
  - VIX regime (via market_regime)
"""

from __future__ import annotations

import logging
import math
from typing import Any

import numpy as np

from app.services.node_executor import ExecutionContext

logger = logging.getLogger(__name__)


# --- Helpers ------------------------------------------------------------------

def _sma(values: list[float], period: int) -> float:
    """Simple moving average of the last `period` values."""
    if not values:
        return 0.0
    window = values[-period:]
    return sum(window) / len(window)


def _std(values: list[float], period: int) -> float:
    """Sample standard deviation of the last `period` values."""
    if len(values) < 2:
        return 0.0
    window = values[-period:]
    mean = sum(window) / len(window)
    variance = sum((x - mean) ** 2 for x in window) / (len(window) - 1)
    return math.sqrt(variance)


def _compute_atr(highs: list[float], lows: list[float], closes: list[float], period: int = 14) -> float:
    """Average True Range from OHLC-style price lists."""
    if len(closes) < 2:
        return 0.0
    trs = []
    for i in range(1, len(closes)):
        h = highs[i] if i < len(highs) else closes[i]
        l = lows[i] if i < len(lows) else closes[i]
        prev_c = closes[i - 1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr)
    if not trs:
        return 0.0
    window = trs[-period:]
    return sum(window) / len(window)


def _compute_zscore(returns: list[float], lookback: int = 30) -> float:
    """Z-score of the most recent return over a lookback window."""
    if len(returns) < 2:
        return 0.0
    window = returns[-lookback:]
    mean = sum(window) / len(window)
    std = _std(window, len(window))
    if std == 0:
        return 0.0
    return (returns[-1] - mean) / std


# --- 1. Signal Generator Node ------------------------------------------------

def handle_nasdaq_signal_generator(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Generates buy/sell signals based on z-score mean reversion.

    Node data parameters:
      - lookback (int): Period for z-score calculation (default 30)
      - z_threshold (float): Absolute z-score required to trigger (default 2.0)
      - price_field (str): Field in market data to use (default "nasdaq_price")

    Returns signal dict with direction, z-score, and trigger state.
    """
    data = node.get("data", {})
    lookback = data.get("lookback", 30)
    z_threshold = data.get("z_threshold", 2.0)
    price_field = data.get("price_field", "nasdaq_price")

    market = ctx.market or {}
    price_history = ctx.price_history or []

    # Use provided price field or fall back to current_odds
    current_price = market.get(price_field, market.get("current_odds", 0.5))

    # Compute returns from price history
    close_prices = list(price_history) if price_history else [current_price]
    if len(close_prices) > 1:
        returns = [
            (close_prices[i] - close_prices[i - 1]) / close_prices[i - 1]
            for i in range(1, len(close_prices))
            if close_prices[i - 1] != 0
        ]
    else:
        returns = []

    z_score = _compute_zscore(returns, lookback) if returns else 0.0

    if z_score <= -z_threshold:
        direction = "long"
        triggered = True
    elif z_score >= z_threshold:
        direction = "short"
        triggered = True
    else:
        direction = "flat"
        triggered = False

    return {
        "triggered": triggered,
        "direction": direction,
        "z_score": round(z_score, 4),
        "z_threshold": z_threshold,
        "current_price": current_price,
        "returns_count": len(returns),
    }


# --- 2. Confirmation Node ----------------------------------------------------

def handle_nasdaq_confirmation(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Confirms a signal with volume filter and VIX regime check.

    Node data parameters:
      - volume_multiplier (float): Required volume above average (default 1.5)
      - volume_period (int): Lookback for volume moving average (default 20)
      - check_vix (bool): Whether to also check VIX regime (default True)
      - max_vix_regime (str): Max allowed VIX regime (default "high")

    Upstream inputs expected:
      - signal output from handle_nasdaq_signal_generator
    """
    data = node.get("data", {})
    volume_multiplier = data.get("volume_multiplier", 1.5)
    volume_period = data.get("volume_period", 20)
    check_vix = data.get("check_vix", True)
    max_vix = data.get("max_vix_regime", "high")

    regime_rank = {"low": 0, "normal": 1, "high": 2, "extreme": 3}

    market = ctx.market or {}

    # Find upstream signal
    upstream = {}
    for v in inputs.values():
        if isinstance(v, dict) and "triggered" in v:
            upstream = v
            break

    if not upstream.get("triggered", False):
        return {
            "triggered": False,
            "reason": "no_upstream_signal",
            "volume_passed": False,
            "vix_passed": True,
        }

    # Volume filter
    volume_history = market.get("volume_history", [])
    current_volume = market.get("volume", 0)
    vol_avg = _sma(volume_history, volume_period) if volume_history else current_volume
    volume_passed = current_volume >= vol_avg * volume_multiplier if vol_avg > 0 else True

    # VIX regime check
    vix_passed = True
    vix_info = None
    if check_vix and ctx.market_regime:
        try:
            regime = ctx.market_regime.current_regime if hasattr(ctx.market_regime, "current_regime") else "normal"
            current_rank = regime_rank.get(regime, 1)
            max_rank = regime_rank.get(max_vix, 2)
            vix_passed = current_rank <= max_rank
            vix_info = regime
        except Exception as exc:
            logger.debug("VIX regime check failed: %s", exc)
            vix_passed = True  # fail open

    confirmed = volume_passed and vix_passed
    reasons = []
    if not volume_passed:
        reasons.append("insufficient_volume")
    if not vix_passed:
        reasons.append("vix_regime_too_high")

    return {
        "triggered": confirmed,
        "direction": upstream.get("direction", "flat"),
        "volume_passed": volume_passed,
        "vix_passed": vix_passed,
        "vix_regime": vix_info,
        "current_volume": current_volume,
        "volume_avg": round(vol_avg, 2),
        "reasons": reasons,
    }


# --- 3. Risk Management Node ------------------------------------------------

def handle_nasdaq_risk_management(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Computes position size using ATR-based risk model.

    Node data parameters:
      - max_portfolio_pct (float): Max portfolio % per trade (default 0.05)
      - atr_period (int): ATR lookback (default 14)
      - atr_multiplier (float): Stop-loss distance in ATR multiples (default 2.0)
      - risk_per_trade (float): Fraction of portfolio to risk (default 0.01)
    """
    data = node.get("data", {})
    max_portfolio_pct = data.get("max_portfolio_pct", 0.05)
    atr_period = data.get("atr_period", 14)
    atr_multiplier = data.get("atr_multiplier", 2.0)
    risk_per_trade = data.get("risk_per_trade", 0.01)

    portfolio = ctx.portfolio or {}
    market = ctx.market or {}
    price_history = ctx.price_history or []

    # Find upstream confirmation
    upstream = {}
    for v in inputs.values():
        if isinstance(v, dict) and "triggered" in v:
            upstream = v
            break

    if not upstream.get("triggered", False):
        return {
            "triggered": False,
            "approved": False,
            "suggested_size": 0.0,
            "reason": "no_confirmed_signal",
        }

    current_price = market.get("nasdaq_price", market.get("current_odds", 0.5))
    current_capital = portfolio.get("current_capital", 10000.0)

    # Compute ATR from price history
    if len(price_history) >= 2:
        highs = [p * 1.001 for p in price_history]
        lows = [p * 0.999 for p in price_history]
        atr = _compute_atr(highs, lows, price_history, atr_period)
    else:
        atr = current_price * 0.02  # fallback: 2% of price

    # Position sizing: risk_per_trade * capital / (atr * multiplier)
    stop_distance = atr * atr_multiplier
    if stop_distance > 0:
        risk_amount = risk_per_trade * current_capital
        atr_size = risk_amount / stop_distance
    else:
        atr_size = 0.0

    # Cap at max_portfolio_pct
    max_size = max_portfolio_pct * current_capital / current_price if current_price > 0 else 0.0
    suggested_size = min(atr_size, max_size)
    suggested_size = max(0.0, suggested_size)

    # Stop-loss price
    direction = upstream.get("direction", "long")
    if direction == "long":
        stop_loss_price = current_price - stop_distance
    else:
        stop_loss_price = current_price + stop_distance

    approved = suggested_size > 0

    return {
        "triggered": approved,
        "approved": approved,
        "suggested_size": round(suggested_size, 4),
        "direction": direction,
        "atr": round(atr, 6),
        "stop_distance": round(stop_distance, 6),
        "stop_loss_price": round(stop_loss_price, 4),
        "current_price": current_price,
        "current_capital": current_capital,
        "risk_per_trade": risk_per_trade,
        "max_portfolio_pct": max_portfolio_pct,
    }


# --- 4. Entry/Exit Logic Node ------------------------------------------------

def handle_nasdaq_entry_exit(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Determines entry or exit actions based on confirmed signal + risk params.

    Node data parameters:
      - exit_z_threshold (float): z-score at which to exit (default 0.5)
      - max_hold_bars (int): Maximum holding period in bars (default 390)
      - order_type (str): "limit" or "market" (default "limit")
      - limit_offset (float): Offset from midpoint for limit orders (default 0.005)
    """
    data = node.get("data", {})
    exit_z_threshold = data.get("exit_z_threshold", 0.5)
    max_hold_bars = data.get("max_hold_bars", 390)
    order_type = data.get("order_type", "limit")
    limit_offset = data.get("limit_offset", 0.005)

    market = ctx.market or {}
    portfolio = ctx.portfolio or {}

    # Collect upstream outputs
    risk_output = {}
    signal_output = {}
    for v in inputs.values():
        if isinstance(v, dict):
            if "suggested_size" in v:
                risk_output = v
            if "z_score" in v:
                signal_output = v

    current_z = signal_output.get("z_score", 0.0)
    direction = risk_output.get("direction", "flat")
    suggested_size = risk_output.get("suggested_size", 0.0)
    stop_loss_price = risk_output.get("stop_loss_price", 0.0)
    current_price = market.get("nasdaq_price", market.get("current_odds", 0.5))

    # Check if we should exit existing positions
    positions = portfolio.get("positions", [])
    exit_actions = []
    for pos in positions:
        if abs(current_z) <= exit_z_threshold:
            exit_actions.append({
                "action": "exit",
                "reason": "z_reversion",
                "market_id": pos.get("market_id"),
                "size": pos.get("size", 0),
            })
        bars_held = pos.get("bars_held", 0)
        if bars_held >= max_hold_bars:
            exit_actions.append({
                "action": "exit",
                "reason": "max_hold_time",
                "market_id": pos.get("market_id"),
                "size": pos.get("size", 0),
            })

    # Determine entry
    entry_action = None
    if risk_output.get("approved") and suggested_size > 0 and direction != "flat":
        if order_type == "limit":
            if direction == "long":
                limit_price = current_price - limit_offset
            else:
                limit_price = current_price + limit_offset
        else:
            limit_price = current_price

        entry_action = {
            "action": "enter",
            "side": "yes" if direction == "long" else "no",
            "size": suggested_size,
            "order_type": order_type,
            "limit_price": round(limit_price, 4),
            "stop_loss": round(stop_loss_price, 4),
        }

    has_action = entry_action is not None or len(exit_actions) > 0

    return {
        "triggered": has_action,
        "entry": entry_action,
        "exits": exit_actions,
        "current_z": round(current_z, 4),
        "direction": direction,
        "exit_z_threshold": exit_z_threshold,
    }


# --- 5. Execution Node -------------------------------------------------------

def handle_nasdaq_execution(node: dict, inputs: dict, ctx: ExecutionContext) -> dict[str, Any]:
    """
    Formats and submits orders to the execution engine.

    Node data parameters:
      - fill_timeout_sec (int): Seconds to wait for fill before cancel (default 300)
      - platform (str): Target platform -- "kalshi" or "polymarket" (default "kalshi")
      - market_prefix (str): Market ID prefix (default "NASDAQ-")
    """
    data = node.get("data", {})
    fill_timeout = data.get("fill_timeout_sec", 300)
    platform = data.get("platform", "kalshi")
    market_prefix = data.get("market_prefix", "NASDAQ-")

    market = ctx.market or {}

    # Find upstream entry/exit output
    upstream = {}
    for v in inputs.values():
        if isinstance(v, dict) and ("entry" in v or "exits" in v):
            upstream = v
            break

    if not upstream.get("triggered", False):
        return {
            "action": "no_action",
            "orders": [],
            "approved": True,
            "reason": "no_entry_or_exit",
        }

    orders = []

    # Entry order
    entry = upstream.get("entry")
    if entry and entry.get("action") == "enter":
        market_id = market.get("market_id", f"{market_prefix}UNKNOWN")
        orders.append({
            "type": "entry",
            "platform": platform,
            "market_id": market_id,
            "side": entry.get("side", "yes"),
            "size": entry.get("size", 0),
            "order_type": entry.get("order_type", "limit"),
            "limit_price": entry.get("limit_price", 0),
            "stop_loss": entry.get("stop_loss", 0),
            "fill_timeout_sec": fill_timeout,
            "status": "pending",
        })

    # Exit orders
    for exit_action in upstream.get("exits", []):
        if exit_action.get("action") == "exit":
            market_id = exit_action.get("market_id", f"{market_prefix}UNKNOWN")
            orders.append({
                "type": "exit",
                "platform": platform,
                "market_id": market_id,
                "size": exit_action.get("size", 0),
                "reason": exit_action.get("reason", "signal"),
                "order_type": "market",
                "status": "pending",
            })

    # Submit to execution engine if available
    submitted = []
    if ctx.execution_engine and orders:
        try:
            for order in orders:
                ctx.execution_engine.submit(order)
                submitted.append(order)
        except Exception as exc:
            logger.error("NASDAQ execution submission failed: %s", exc)
            return {
                "action": "execution_error",
                "orders": orders,
                "submitted": submitted,
                "error": str(exc),
                "approved": False,
            }

    return {
        "action": "execute",
        "orders": orders,
        "submitted_count": len(submitted),
        "approved": True,
        "platform": platform,
        "fill_timeout_sec": fill_timeout,
    }


# --- Registration -----------------------------------------------------------

def register_nasdaq_handlers(registry) -> None:
    """Register all NASDAQ strategy node handlers."""
    registry.register("nasdaq_signal_generator", handle_nasdaq_signal_generator)
    registry.register("nasdaq_confirmation", handle_nasdaq_confirmation)
    registry.register("nasdaq_risk_management", handle_nasdaq_risk_management)
    registry.register("nasdaq_entry_exit", handle_nasdaq_entry_exit)
    registry.register("nasdaq_execution", handle_nasdaq_execution)
