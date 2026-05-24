import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from app.services.exchange_base import (
    ExchangeConnector,
    ExchangeOrder,
    OrderBook,
    OrderBookLevel,
    FillResult,
    Balance,
)
from app.services.execution_config import POLYMARKET_SETTINGS

logger = logging.getLogger(__name__)


def _sign_request(method: str, path: str, body: dict | None, api_key: str, secret: str) -> dict:
    timestamp = str(int(time.time()))
    msg = f"{timestamp}{method}{path}"
    if body:
        msg += json.dumps(body, sort_keys=True)
    signature = hmac.new(secret.encode(), msg.encode(), hashlib.sha256).hexdigest()
    return {
        "POLY-API-KEY": api_key,
        "POLY-SIGNATURE": signature,
        "POLY-TIMESTAMP": timestamp,
    }


class PolymarketConnector(ExchangeConnector):
    def __init__(self):
        self._client: httpx.AsyncClient | None = None
        self._settings = POLYMARKET_SETTINGS

    def _get_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._settings.api_base_url,
                timeout=self._settings.timeout_seconds,
                limits=httpx.Limits(max_keepalive_connections=10, max_connections=20),
            )
        return self._client

    async def _request(self, method: str, path: str, api_key: str = "", secret: str = "", **kwargs) -> dict:
        client = self._get_client()
        headers = kwargs.pop("headers", {})
        if api_key and secret:
            headers.update(_sign_request(method, path, kwargs.get("json"), api_key, secret))
        for attempt in range(self._settings.max_retries):
            try:
                resp = await client.request(method, path, headers=headers, **kwargs)
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 502, 503, 504) and attempt < self._settings.max_retries - 1:
                    wait = self._settings.retry_delay_seconds * (2 ** attempt)
                    logger.warning("Polymarket retry %d after %s: %s", attempt + 1, wait, e)
                    await asyncio.sleep(wait)
                    continue
                raise
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                if attempt < self._settings.max_retries - 1:
                    wait = self._settings.retry_delay_seconds * (2 ** attempt)
                    await asyncio.sleep(wait)
                    continue
                raise

    async def get_order_book(self, market_id: str) -> OrderBook:
        data = await self._request("GET", f"/books?market={market_id}")
        bids = [OrderBookLevel(price=float(b["price"]), size=float(b["size"])) for b in data.get("bids", [])]
        asks = [OrderBookLevel(price=float(a["price"]), size=float(a["size"])) for a in data.get("asks", [])]
        best_bid = bids[0].price if bids else 0.0
        best_ask = asks[0].price if asks else 0.0
        mid = (best_bid + best_ask) / 2 if best_bid and best_ask else 0.0
        spread = (best_ask - best_bid) / mid if mid > 0 else 0.0
        return OrderBook(
            platform="polymarket",
            market_id=market_id,
            bids=bids,
            asks=asks,
            mid_price=mid,
            spread=spread,
            last_price=data.get("last_price"),
        )

    async def place_order(self, order: ExchangeOrder, credentials: dict) -> FillResult:
        api_key = credentials.get("api_key", "")
        secret = credentials.get("secret", "")
        body = {
            "market": order.market_id,
            "side": order.side.upper(),
            "type": order.order_type.upper(),
            "price": str(order.price),
            "size": str(order.amount),
            "time_in_force": order.time_in_force,
        }
        if order.client_order_id:
            body["client_order_id"] = order.client_order_id
        try:
            data = await self._request("POST", "/order", api_key=api_key, secret=secret, json=body)
            platform_id = data.get("id", "")
            status = "filled" if data.get("status") == "FILLED" else "pending"
            filled = float(data.get("matched_size", 0))
            fill_price = float(data.get("average_filled_price", order.price))
            cost = filled * fill_price
            slippage = abs(fill_price - order.price) / order.price if order.price > 0 else 0
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=platform_id,
                status=status,
                filled_amount=filled,
                fill_price=fill_price,
                total_cost=cost,
                slippage=slippage,
                fee=float(data.get("fee", 0)),
            )
        except httpx.HTTPStatusError as e:
            body = e.response.text
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=None,
                status="failed",
                filled_amount=0,
                fill_price=0,
                total_cost=0,
                slippage=0,
                error=f"HTTP {e.response.status_code}: {body[:200]}",
            )
        except Exception as e:
            return FillResult(
                order_id=order.client_order_id or "",
                platform_order_id=None,
                status="failed",
                filled_amount=0,
                fill_price=0,
                total_cost=0,
                slippage=0,
                error=str(e),
            )

    async def cancel_order(self, platform_order_id: str) -> bool:
        try:
            await self._request("DELETE", f"/order/{platform_order_id}")
            return True
        except Exception:
            return False

    async def get_order_status(self, platform_order_id: str) -> FillResult:
        data = await self._request("GET", f"/order/{platform_order_id}")
        status = data.get("status", "pending")
        filled = float(data.get("matched_size", 0))
        fill_price = float(data.get("average_filled_price", 0))
        return FillResult(
            order_id="",
            platform_order_id=platform_order_id,
            status=status,
            filled_amount=filled,
            fill_price=fill_price,
            total_cost=filled * fill_price,
            slippage=0,
        )

    async def get_balance(self, credentials: dict) -> list[Balance]:
        api_key = credentials.get("api_key", "")
        secret = credentials.get("secret", "")
        data = await self._request("GET", "/balance", api_key=api_key, secret=secret)
        balances = []
        for asset, info in data.items():
            free = float(info.get("balance", 0))
            balances.append(Balance(asset=asset, free=free, locked=0, total=free))
        return balances

    async def available(self) -> bool:
        try:
            await self._request("GET", "/markets?limit=1")
            return True
        except Exception:
            return False

    async def close(self):
        if self._client:
            await self._client.aclose()
            self._client = None


import asyncio
