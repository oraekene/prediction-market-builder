import enum
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import String, DateTime, Float, Enum as SAEnum, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketPlatform(str, enum.Enum):
    POLYMARKET = "polymarket"
    KALSHI = "kalshi"
    DRIFT = "drift"


class MarketStatus(str, enum.Enum):
    OPEN = "open"
    CLOSED = "closed"
    RESOLVED = "resolved"


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    platform: Mapped[MarketPlatform] = mapped_column(SAEnum(MarketPlatform))
    platform_market_id: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String, nullable=True)
    current_odds: Mapped[float] = mapped_column(Float)
    bid: Mapped[float] = mapped_column(Float, nullable=True)
    ask: Mapped[float] = mapped_column(Float, nullable=True)
    volume: Mapped[float] = mapped_column(Float, default=0)
    liquidity: Mapped[float] = mapped_column(Float, default=0)
    participants: Mapped[int] = mapped_column(Float, default=0)
    close_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    resolution_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    status: Mapped[MarketStatus] = mapped_column(SAEnum(MarketStatus), default=MarketStatus.OPEN)
    outcomes: Mapped[dict] = mapped_column(JSON, default=list)
    raw_data: Mapped[dict] = mapped_column(JSON, default=dict)
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        sa.UniqueConstraint("platform", "platform_market_id", name="uq_platform_market"),
    )
