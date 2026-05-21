import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class TradeStatus(str, enum.Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String, nullable=True)
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    side: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float)
    price: Mapped[float] = mapped_column(Float)
    status: Mapped[TradeStatus] = mapped_column(SAEnum(TradeStatus), default=TradeStatus.PENDING)
    platform_trade_id: Mapped[str] = mapped_column(String, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
