import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, Integer, JSON, Text, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class HermesTrace(Base):
    __tablename__ = "hermes_traces"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, index=True)
    intent: Mapped[str] = mapped_column(String)
    prompt: Mapped[str] = mapped_column(Text)
    response: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int] = mapped_column(Integer)
    tool_calls_attempted: Mapped[list] = mapped_column(JSON, default=list)
    tool_results: Mapped[list | None] = mapped_column(JSON, nullable=True)
    classification_chain: Mapped[list | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
