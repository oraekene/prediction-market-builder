import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class MetaStrategyMode(str, enum.Enum):
    STANDARD = "standard"
    COMPETITION = "competition"
    CONFLUENCE = "confluence"
    BOTH = "both"


DEFAULT_SCORING_CONFIG = {
    "metrics": {
        "sharpe": 0.20, "win_rate": 0.15, "profit_factor": 0.15, "max_drawdown": 0.10,
        "confidence": 0.10, "expected_value": 0.10, "signal_strength": 0.10, "consistency": 0.10,
    },
}

DEFAULT_PROMOTION_CONFIG = {
    "interval": "daily",
    "interval_days": None,
    "probation_hours": 48,
    "evaluation_window_days": 30,
}

DEFAULT_CONFLUENCE_CONFIG = {
    "threshold": 3,
    "source": "top_n",
    "from_top": 5,
    "manual_strategy_ids": [],
}


class MetaStrategy(Base):
    __tablename__ = "meta_strategies"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    mode: Mapped[MetaStrategyMode] = mapped_column(String, default=MetaStrategyMode.COMPETITION.value)
    status: Mapped[str] = mapped_column(String, default="active")

    strategy_ids: Mapped[list] = mapped_column(JSON, default=list)

    scoring_config: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_SCORING_CONFIG))
    promotion_config: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_PROMOTION_CONFIG))
    confluence_config: Mapped[dict] = mapped_column(JSON, default=lambda: dict(DEFAULT_CONFLUENCE_CONFIG))

    consumer: Mapped[str] = mapped_column(String, nullable=True)
    current_winner_id: Mapped[str] = mapped_column(String, nullable=True)
    last_promotion_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
