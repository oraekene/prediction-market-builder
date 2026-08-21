import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class WithdrawalStrategyModel(Base):
    __tablename__ = "withdrawal_strategies"
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    steps: Mapped[list] = mapped_column(JSON, default=list)
    current_step_index: Mapped[int] = mapped_column(Integer, default=0)
    step_states: Mapped[dict] = mapped_column(JSON, default=dict)
    safe_wallet_id: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
