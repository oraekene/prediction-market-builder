from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class ExchangeOrder:
    platform: str
    market_id: str
    side: Literal["buy", "sell"]
    order_type: Literal["limit", "market"]
    price: float
    amount: float
    user_id: str | None = None
    strategy_id: str | None = None
    client_order_id: str | None = None
    time_in_force: str = "GTC"


@dataclass
class OrderBookLevel:
    price: float
    size: float


@dataclass
class OrderBook:
    platform: str
    market_id: str
    bids: list[OrderBookLevel]
    asks: list[OrderBookLevel]
    mid_price: float
    spread: float
    last_price: float | None = None


@dataclass
class FillResult:
    order_id: str
    platform_order_id: str | None
    status: Literal["filled", "partial", "pending", "cancelled", "failed"]
    filled_amount: float
    fill_price: float
    total_cost: float
    slippage: float
    fee: float = 0.0
    error: str | None = None


@dataclass
class Balance:
    asset: str
    free: float
    locked: float
    total: float


class ExchangeConnector(ABC):

    @abstractmethod
    async def get_order_book(self, market_id: str) -> OrderBook:
        ...

    @abstractmethod
    async def place_order(self, order: ExchangeOrder, credentials: dict) -> FillResult:
        ...

    @abstractmethod
    async def cancel_order(self, platform_order_id: str) -> bool:
        ...

    @abstractmethod
    async def get_order_status(self, platform_order_id: str) -> FillResult:
        ...

    @abstractmethod
    async def get_balance(self, credentials: dict) -> list[Balance]:
        ...

    @abstractmethod
    async def available(self) -> bool:
        ...
