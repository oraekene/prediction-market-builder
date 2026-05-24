import logging
import random
from typing import Any, Literal

from app.services.exchange_base import ExchangeOrder, OrderBook, OrderBookLevel, FillResult
from app.services.polymarket_connector import PolymarketConnector
from app.services.kalshi_connector import KalshiConnector
from app.services.drift_connector import DriftConnector
from app.services.execution_config import POLYMARKET_SETTINGS, KALSHI_SETTINGS, DRIFT_SETTINGS

logger = logging.getLogger(__name__)


class SimulatedOrderBook:
    def __init__(self, platform: str, base_spread: float = 0.02, depth: int = 10):
        self.platform = platform
        self.base_spread = base_spread
        self.depth = depth

    def generate(self, mid_price: float, volume: float, volatility: float = 0.02) -> dict[str, Any]:
        spread = self.base_spread * (1 + volatility * 5)
        bid = round(mid_price * (1 - spread / 2), 4)
        ask = round(mid_price * (1 + spread / 2), 4)

        bids = []
        asks = []
        for i in range(self.depth):
            decay = 1 - (i / self.depth) * 0.5
            size = round((volume / 1_000_000) * decay * random.uniform(0.5, 1.5), 2)
            bids.append({"price": round(bid * (1 - i * 0.002), 4), "size": max(size, 0.01)})
            asks.append({"price": round(ask * (1 + i * 0.002), 4), "size": max(size, 0.01)})

        return {
            "platform": self.platform,
            "mid_price": mid_price,
            "spread": spread,
            "bids": bids,
            "asks": asks,
            "last_price": mid_price * (1 + random.uniform(-0.005, 0.005)),
        }


class SimulatedExecutionEngine:
    def __init__(self):
        self.order_books: dict[str, SimulatedOrderBook] = {
            "polymarket": SimulatedOrderBook("polymarket", base_spread=0.015),
            "kalshi": SimulatedOrderBook("kalshi", base_spread=0.02),
            "drift": SimulatedOrderBook("drift", base_spread=0.025),
        }

    def get_order_book(self, platform: str, mid_price: float, volume: float, volatility: float = 0.02) -> dict:
        book = self.order_books.get(platform, self.order_books["polymarket"])
        return book.generate(mid_price, volume, volatility)

    def simulate_fill(self, platform: str, side: str, amount: float, price: float,
                      order_book: dict, volatility: float = 0.02) -> dict[str, Any]:
        fill_probability = 1.0
        slippage = 0.0

        if side == "buy":
            best_ask = order_book["asks"][0]["price"] if order_book["asks"] else price
            slippage = max(0, (price - best_ask) / best_ask) if best_ask > 0 else 0
            if price < best_ask * 0.98:
                fill_probability = max(0.1, 1 - (best_ask - price) / best_ask * 10)
        else:
            best_bid = order_book["bids"][0]["price"] if order_book["bids"] else price
            slippage = max(0, (best_bid - price) / best_bid) if best_bid > 0 else 0
            if price > best_bid * 1.02:
                fill_probability = max(0.1, 1 - (price - best_bid) / best_bid * 10)

        fill_probability = min(1.0, fill_probability * (1 - volatility * 2))
        slippage = round(slippage + random.uniform(0, volatility * 0.5), 6)

        amount_multiplier = random.uniform(0.8, 1.0) if volatility > 0.03 else random.uniform(0.95, 1.0)
        filled_amount = round(amount * amount_multiplier * fill_probability, 2)

        fill_price = price * (1 + slippage) if side == "buy" else price * (1 - slippage)
        fill_price = round(fill_price, 4)

        fill_status = "filled"
        if fill_probability < 0.3:
            fill_status = "cancelled"
            filled_amount = 0.0
        elif fill_probability < 0.7 and filled_amount < amount:
            fill_status = "partial"

        return {
            "filled": fill_status != "cancelled",
            "status": fill_status,
            "filled_amount": filled_amount,
            "fill_price": fill_price,
            "slippage": slippage,
            "fill_probability": round(fill_probability, 3),
        }


class ExecutionEngine:
    def __init__(self):
        self._connectors: dict[str, Any] = {
            "polymarket": PolymarketConnector(),
            "kalshi": KalshiConnector(),
            "drift": DriftConnector(),
        }

    def _get_credentials(self, user) -> dict:
        from app.services.encryption import encryption_service
        creds: dict[str, str] = {}
        if user.polymarket_key:
            try:
                raw = encryption_service.decrypt(user.polymarket_key)
                parts = raw.split(":", 1)
                creds["api_key"] = parts[0]
                if len(parts) > 1:
                    creds["secret"] = parts[1]
            except Exception:
                creds["api_key"] = user.polymarket_key
        if user.kalshi_key:
            creds["private_key"] = user.kalshi_key
        if user.drift_key:
            creds["api_key"] = user.drift_key
        return creds

    def _get_connector(self, platform: str):
        connector = self._connectors.get(platform)
        if not connector:
            raise ValueError(f"Unsupported platform: {platform}")
        return connector

    async def get_order_book(self, platform: str, market_id: str) -> OrderBook:
        return await self._get_connector(platform).get_order_book(market_id)

    async def place_order(self, platform: str, market_id: str, side: str,
                          amount: float, price: float, user, *,
                          order_type: str = "market",
                          strategy_id: str | None = None) -> FillResult:
        connector = self._get_connector(platform)
        credentials = self._get_credentials(user)
        order = ExchangeOrder(
            platform=platform,
            market_id=market_id,
            side=side,
            order_type=order_type,
            price=price,
            amount=amount,
            user_id=user.id,
            strategy_id=strategy_id,
        )
        return await connector.place_order(order, credentials)

    async def cancel_order(self, platform: str, platform_order_id: str) -> bool:
        return await self._get_connector(platform).cancel_order(platform_order_id)

    async def get_order_status(self, platform: str, platform_order_id: str) -> FillResult:
        return await self._get_connector(platform).get_order_status(platform_order_id)

    async def get_balance(self, platform: str, user) -> list:
        credentials = self._get_credentials(user)
        return await self._get_connector(platform).get_balance(credentials)

    async def calculate_slippage(self, platform: str, market_id: str,
                                  amount: float, side: str) -> dict:
        book = await self.get_order_book(platform, market_id)
        levels = book.asks if side == "buy" else book.bids
        remaining = amount
        total_cost = 0.0
        fill_curve = []
        for level in levels:
            if remaining <= 0:
                break
            take = min(remaining, level.size)
            total_cost += take * level.price
            remaining -= take
            fill_curve.append({"price": level.price, "cumulative_amount": amount - remaining})
        filled = amount - remaining
        avg_price = total_cost / filled if filled > 0 else book.mid_price
        slippage = abs(avg_price - book.mid_price) / book.mid_price if book.mid_price > 0 else 0
        return {
            "estimated_slippage": round(slippage, 6),
            "price_impact": round((avg_price - book.mid_price) / book.mid_price * 100, 4) if book.mid_price > 0 else 0,
            "avg_fill_price": round(avg_price, 4),
            "filled_amount": round(filled, 4),
            "fill_curve": fill_curve,
        }

    async def monitor_order(self, platform: str, platform_order_id: str,
                            max_wait: int = 60, poll_interval: int = 2) -> FillResult:
        import asyncio
        elapsed = 0
        while elapsed < max_wait:
            result = await self.get_order_status(platform, platform_order_id)
            if result.status in ("filled", "cancelled", "failed"):
                return result
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        result = await self.get_order_status(platform, platform_order_id)
        if result.status == "pending":
            result.status = "pending_review"
        return result

    async def available(self, platform: str) -> bool:
        try:
            return await self._get_connector(platform).available()
        except Exception:
            return False

    async def close(self):
        for connector in self._connectors.values():
            try:
                await connector.close()
            except Exception:
                pass
