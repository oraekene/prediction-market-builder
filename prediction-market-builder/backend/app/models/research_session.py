import uuid
import enum
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Float, JSON, Text, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class SessionStatus(str, enum.Enum):
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionMode(str, enum.Enum):
    MANUAL = "manual"
    CRON = "cron"
    CONTINUOUS = "continuous"


class CompositePreset(str, enum.Enum):
    SHARPE_MAX = "sharpe_max"
    WIN_RATE_MAX = "win_rate_max"
    RISK_ADJUSTED = "risk_adjusted"
    WIN_RATE = "win_rate"
    CALMAR = "calmar"
    PROFIT_FACTOR = "profit_factor"


class ResearchSession(Base):
    __tablename__ = "research_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    status: Mapped[SessionStatus] = mapped_column(SAEnum(SessionStatus), default=SessionStatus.RUNNING)
    mode: Mapped[SessionMode] = mapped_column(SAEnum(SessionMode), default=SessionMode.MANUAL)
    trigger_type: Mapped[str] = mapped_column(String, nullable=True)
    composite_preset: Mapped[CompositePreset] = mapped_column(SAEnum(CompositePreset), default=CompositePreset.SHARPE_MAX)
    current_iteration: Mapped[int] = mapped_column(Integer, default=0)
    total_kept: Mapped[int] = mapped_column(Integer, default=0)
    total_reverted: Mapped[int] = mapped_column(Integer, default=0)
    avg_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    avg_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    best_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    best_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    rlm_alpha_vector_id: Mapped[str] = mapped_column(String, nullable=True)
    toto2_regime: Mapped[str] = mapped_column(String, nullable=True)
    toto2_volatility: Mapped[float] = mapped_column(Float, nullable=True)
    tabpfn_top_features: Mapped[dict] = mapped_column(JSON, nullable=True)
    hypothesis_count: Mapped[int] = mapped_column(Integer, default=0)
    pareto_front: Mapped[dict] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
