import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class SafeWallet(Base):
    __tablename__ = "safe_wallets"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    currency: Mapped[str] = mapped_column(String, default="USDC")
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    address: Mapped[str] = mapped_column(String, nullable=True)
    is_disconnected: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

class WithdrawalRecord(Base):
    __tablename__ = "withdrawal_records"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    safe_wallet_id: Mapped[str] = mapped_column(String, nullable=False)
    strategy_id: Mapped[str] = mapped_column(String, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, default="profits")
    trigger_type: Mapped[str] = mapped_column(String, default="manual")
    trigger_step_id: Mapped[str] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
