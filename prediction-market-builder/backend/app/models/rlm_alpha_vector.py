import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class RLMAlphaVector(Base):
    __tablename__ = "rlm_alpha_vectors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    source_type: Mapped[str] = mapped_column(String, nullable=False)
    source_path: Mapped[str] = mapped_column(Text, nullable=True)
    source_hash: Mapped[str] = mapped_column(String, nullable=True, index=True)
    token_count: Mapped[int] = mapped_column(Integer, default=0)
    alpha_vector: Mapped[dict] = mapped_column(JSON, nullable=True)
    linguistic_signals: Mapped[dict] = mapped_column(JSON, nullable=True)
    sub_agent_traces: Mapped[dict] = mapped_column(JSON, nullable=True)
    dspy_trajectory: Mapped[str] = mapped_column(Text, nullable=True)
    used_in_sessions: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
