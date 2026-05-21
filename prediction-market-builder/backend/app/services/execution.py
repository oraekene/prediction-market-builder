import random
from typing import Any


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
