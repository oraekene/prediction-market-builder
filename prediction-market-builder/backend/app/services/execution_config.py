from pydantic import BaseModel


class ExchangeSettings(BaseModel):
    api_base_url: str
    ws_url: str | None = None
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: float = 1.0
    rate_limit_per_minute: int = 60


POLYMARKET_SETTINGS = ExchangeSettings(
    api_base_url="https://clob.polymarket.com",
    ws_url="wss://ws-subscriptions.clob.polymarket.com/ws",
    rate_limit_per_minute=120,
    timeout_seconds=30,
)

KALSHI_SETTINGS = ExchangeSettings(
    api_base_url="https://trading-api.kalshi.com/trade-api/v2",
    rate_limit_per_minute=60,
)

DRIFT_SETTINGS = ExchangeSettings(
    api_base_url="https://api.drift.trade",
    rate_limit_per_minute=30,
    timeout_seconds=15,
)
