import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ResearchSessionConfig(Base):
    __tablename__ = "research_session_configs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    max_concurrent: Mapped[int] = mapped_column(Integer, default=2)
    composite_preset: Mapped[str] = mapped_column(String, default="sharpe_max")
    cron_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    cron_interval_minutes: Mapped[int] = mapped_column(Integer, default=360)
    continuous_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rlm_sources: Mapped[dict] = mapped_column(JSON, default=list)
    rlm_cron_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    rlm_cron_interval_minutes: Mapped[int] = mapped_column(Integer, default=1440)
    max_hypotheses_per_session: Mapped[int] = mapped_column(Integer, default=50)
    enable_genetic_optimization: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
