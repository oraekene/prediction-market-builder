import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class MonitoredPosition(Base):
    __tablename__ = "monitored_positions"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    platform: Mapped[str] = mapped_column(String, nullable=False)
    market_id: Mapped[str] = mapped_column(String, nullable=False)
    market_title: Mapped[str] = mapped_column(String, nullable=True)
    side: Mapped[str] = mapped_column(String, nullable=False)
    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    size: Mapped[float] = mapped_column(Float, nullable=False)
    high_water_mark: Mapped[float] = mapped_column(Float, nullable=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String, default="active")
    risk_config: Mapped[dict] = mapped_column(JSON, default=dict)
    trail_states: Mapped[dict] = mapped_column(JSON, default=dict)
    exit_price: Mapped[float] = mapped_column(Float, nullable=True)
    exit_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, nullable=True)
    withdrawal_strategy_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
