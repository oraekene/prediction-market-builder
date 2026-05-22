import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Integer, Float, JSON, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class ExperimentResult(Base):
    __tablename__ = "experiment_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    iteration: Mapped[int] = mapped_column(Integer, nullable=False)
    hypothesis: Mapped[str] = mapped_column(Text, nullable=False)
    hypothesis_prompt: Mapped[str] = mapped_column(Text, nullable=True)
    regime_at_time: Mapped[str] = mapped_column(String, nullable=True)
    volatility_at_time: Mapped[float] = mapped_column(Float, nullable=True)
    feature_importance_at_time: Mapped[dict] = mapped_column(JSON, nullable=True)
    rlm_alpha_vector_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True)
    backtest_config: Mapped[dict] = mapped_column(JSON, nullable=True)
    backtest_trades: Mapped[int] = mapped_column(Integer, default=0)
    backtest_win_rate: Mapped[float] = mapped_column(Float, default=0.0)
    backtest_sharpe: Mapped[float] = mapped_column(Float, default=0.0)
    backtest_max_drawdown: Mapped[float] = mapped_column(Float, default=0.0)
    backtest_total_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    tabpfn_probability: Mapped[float] = mapped_column(Float, default=0.0)
    tabpfn_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    composite_score: Mapped[float] = mapped_column(Float, default=0.0)
    shap_explanation: Mapped[dict] = mapped_column(JSON, nullable=True)
    verdict: Mapped[str] = mapped_column(String, default="REVERTED")
    git_commit_hash: Mapped[str] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
