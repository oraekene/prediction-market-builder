from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.research_session import ResearchSession, SessionStatus, SessionMode
from app.models.experiment_result import ExperimentResult
from app.models.research_config import ResearchSessionConfig
from app.ai.autoresearch import AutoresearchService
from app.ai.tabpfn_service import TabPFNService
from app.ai.market_regime_service import MarketRegimeService
from app.ai.rlm_service import RLMService
from app.services.explainability_service import ExplainabilityService
from app.services.backtester import SimulatedMarketHistory

logger = logging.getLogger(__name__)


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class ResearchScheduler:
    """Manages the lifecycle of research sessions.

    - Spawns/resumes sessions as asyncio background tasks
    - Enforces per-user and global concurrency limits
    - Handles cron triggers, manual triggers, continuous mode
    - Auto-resumes interrupted sessions on server start
    """

    def __init__(
        self,
        autoresearch: AutoresearchService | None = None,
        tabpfn: TabPFNService | None = None,
        market_regime: MarketRegimeService | None = None,
        rlm: RLMService | None = None,
        explainability: ExplainabilityService | None = None,
    ):
        self.autoresearch = autoresearch or AutoresearchService(tabpfn_service=tabpfn)
        self.tabpfn = tabpfn or TabPFNService()
        self.market_regime = market_regime or MarketRegimeService()
        self.rlm = rlm or RLMService()
        self.explainability = explainability

        self._sessions: dict[str, asyncio.Task] = {}
        self._session_owners: dict[str, str] = {}
        self._global_lock = asyncio.Semaphore(5)
        self._stop_events: dict[str, asyncio.Event] = {}
        self._broadcast: Callable | None = None
        self._cron_task: asyncio.Task | None = None
        self._running = False

    def set_broadcast(self, broadcast_fn: Callable) -> None:
        self._broadcast = broadcast_fn

    async def _broadcast_event(self, session_id: str, event: dict[str, Any]) -> None:
        if self._broadcast:
            try:
                await self._broadcast(session_id, event)
            except Exception as exc:
                logger.debug("Broadcast failed: %s", exc)

    async def start(self) -> None:
        self._running = True
        logger.info("ResearchScheduler started")
        await self.resume_interrupted_sessions()
        self._cron_task = asyncio.create_task(self._cron_worker())

    async def stop(self) -> None:
        self._running = False
        if self._cron_task:
            self._cron_task.cancel()
            self._cron_task = None
        for session_id, task in list(self._sessions.items()):
            task.cancel()
            self._stop_events.pop(session_id, None)
        self._sessions.clear()
        self._session_owners.clear()
        logger.info("ResearchScheduler stopped")

    def _user_active_count(self, user_id: str) -> int:
        return sum(
            1 for sid, t in self._sessions.items()
            if not t.done() and self._session_owners.get(sid) == user_id
        )

    async def start_session(
        self,
        user_id: str,
        strategy_id: str | None = None,
        mode: SessionMode = SessionMode.MANUAL,
        trigger_type: str | None = None,
        preset: str = "sharpe_max",
    ) -> ResearchSession | None:
        if not self._running:
            logger.warning("Scheduler not running")
            return None

        user_config = await self._get_user_config(user_id)
        max_concurrent = user_config.max_concurrent if user_config else 2
        if self._user_active_count(user_id) >= max_concurrent:
            logger.warning("User %s at max concurrency (%d)", user_id, max_concurrent)
            return None

        session = ResearchSession(
            user_id=user_id,
            strategy_id=strategy_id,
            status=SessionStatus.RUNNING,
            mode=mode,
            trigger_type=trigger_type,
            composite_preset=preset,
        )
        async with async_session() as db:
            db.add(session)
            await db.commit()
            await db.refresh(session)

        stop_event = asyncio.Event()
        self._stop_events[session.id] = stop_event
        task = asyncio.create_task(self._run_session_loop(session.id, stop_event))
        self._sessions[session.id] = task
        self._session_owners[session.id] = user_id
        logger.info("Session %s started for user %s", session.id, user_id)
        return session

    async def stop_session(self, session_id: str) -> bool:
        stop_event = self._stop_events.get(session_id)
        if stop_event:
            stop_event.set()
        task = self._sessions.pop(session_id, None)
        self._session_owners.pop(session_id, None)
        if task and not task.done():
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        async with async_session() as db:
            result = await db.execute(
                select(ResearchSession).where(ResearchSession.id == session_id)
            )
            session = result.scalar_one_or_none()
            if session:
                session.status = SessionStatus.PAUSED
                await db.commit()
            else:
                return False
        return True

    async def get_session(self, session_id: str) -> ResearchSession | None:
        async with async_session() as db:
            result = await db.execute(
                select(ResearchSession).where(ResearchSession.id == session_id)
            )
            return result.scalar_one_or_none()

    async def get_user_sessions(self, user_id: str, limit: int = 20) -> list[ResearchSession]:
        async with async_session() as db:
            result = await db.execute(
                select(ResearchSession)
                .where(ResearchSession.user_id == user_id)
                .order_by(ResearchSession.created_at.desc())
                .limit(limit)
            )
            return list(result.scalars().all())

    async def get_session_results(self, session_id: str) -> list[ExperimentResult]:
        async with async_session() as db:
            result = await db.execute(
                select(ExperimentResult)
                .where(ExperimentResult.session_id == session_id)
                .order_by(ExperimentResult.iteration.asc())
            )
            return list(result.scalars().all())

    async def _run_session_loop(self, session_id: str, stop_event: asyncio.Event) -> None:
        try:
            async with async_session() as db:
                result = await db.execute(
                    select(ResearchSession).where(ResearchSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if not session:
                    return

                config = await self._get_user_config(session.user_id)
                max_hypotheses = config.max_hypotheses_per_session if config else 50

                while not stop_event.is_set() and session.current_iteration < max_hypotheses:
                    try:
                        async with self._global_lock:
                            await self._run_single_iteration(session, db)
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        logger.exception("Iteration failed for session %s: %s", session_id, exc)
                        session.error_message = str(exc)[:500]
                        await db.commit()
                        if stop_event.is_set():
                            break
                        await asyncio.sleep(5)

                    if mode_is_manual(session.mode):
                        break

                    if stop_event.is_set():
                        break
                    cooldown = 30 if session.mode == SessionMode.CONTINUOUS else 3600
                    await self._wait_until(stop_event, cooldown)

                if session.current_iteration >= max_hypotheses:
                    session.status = SessionStatus.COMPLETED
                elif stop_event.is_set():
                    session.status = SessionStatus.PAUSED
                await db.commit()

        except asyncio.CancelledError:
            async with async_session() as db:
                result = await db.execute(
                    select(ResearchSession).where(ResearchSession.id == session_id)
                )
                session = result.scalar_one_or_none()
                if session:
                    session.status = SessionStatus.PAUSED
                    await db.commit()
            raise
        finally:
            self._sessions.pop(session_id, None)
            self._session_owners.pop(session_id, None)
            self._stop_events.pop(session_id, None)

    async def _run_single_iteration(self, session: ResearchSession, db: AsyncSession) -> None:
        climate = await self.market_regime.assess_climate([])

        import pandas as pd
        tabpfn_feature_columns = [
            "odds", "volume", "liquidity", "spread",
            "participants", "hypothesis_threshold",
            "volatility", "autocorrelation",
        ]
        dummy_features = pd.DataFrame(
            [[0.5, 0.5, 0.5, 0.05, 0.5, 0.5, 0.5, 0.0]],
            columns=tabpfn_feature_columns,
        )
        feature_importance = await self.tabpfn.get_feature_importance(dummy_features)

        alpha_vector = await self._get_alpha_vector(session.rlm_alpha_vector_id)

        past_results = await self._get_past_results(session.id)

        market_history = SimulatedMarketHistory.generate(
            start_odds=0.5, steps=100, volatility=0.02
        )

        config = await self._get_user_config(session.user_id)
        enable_ga = config.enable_genetic_optimization if config else False

        result_dict = await self.autoresearch.run_iteration(
            strategy_id=session.strategy_id or "",
            market_history=market_history,
            climate=climate,
            feature_importance=feature_importance,
            alpha_vector=alpha_vector,
            past_results=past_results,
            preset=session.composite_preset.value,
            session_id=session.id,
            enable_genetic=enable_ga,
        )

        if result_dict.get("verdict") == "SKIPPED":
            session.current_iteration += 1
            await db.commit()
            return

        if result_dict.get("verdict") == "COMPLETED":
            session.current_iteration += 1
            session.status = SessionStatus.COMPLETED
            await db.commit()
            return

        shap_explanation = None
        tabpfn_features = result_dict.get("tabpfn_features")
        if tabpfn_features and self.explainability and self.explainability.available:
            try:
                shap_explanation = await self.explainability.explain_tabpfn_features(
                    tabpfn_features
                )
            except Exception as exc:
                logger.warning("SHAP explain failed for iteration %d: %s",
                               session.current_iteration + 1, exc)

        experiment = ExperimentResult(
            session_id=session.id,
            iteration=session.current_iteration + 1,
            hypothesis=result_dict.get("hypothesis", ""),
            hypothesis_prompt=result_dict.get("hypothesis_prompt", ""),
            regime_at_time=climate.get("regime", ""),
            volatility_at_time=climate.get("metrics", {}).get("volatility", 0.0),
            feature_importance_at_time=feature_importance,
            rlm_alpha_vector_snapshot=alpha_vector,
            backtest_config=result_dict.get("backtest_config"),
            backtest_trades=result_dict.get("backtest_trades", 0),
            backtest_win_rate=result_dict.get("backtest_win_rate", 0.0),
            backtest_sharpe=result_dict.get("backtest_sharpe", 0.0),
            backtest_max_drawdown=result_dict.get("backtest_max_drawdown", 0.0),
            backtest_total_pnl=result_dict.get("backtest_total_pnl", 0.0),
            tabpfn_probability=result_dict.get("tabpfn_probability", 0.0),
            tabpfn_confidence=result_dict.get("tabpfn_confidence", 0.0),
            composite_score=result_dict.get("composite_score", 0.0),
            shap_explanation=shap_explanation,
            verdict=result_dict.get("verdict", "REVERTED"),
        )
        db.add(experiment)

        session.current_iteration += 1
        score = result_dict.get("composite_score", 0.0)
        win_rate = result_dict.get("backtest_win_rate", 0.0)
        if result_dict.get("verdict") == "KEPT":
            session.total_kept += 1
        elif result_dict.get("verdict") == "REVERTED":
            session.total_reverted += 1
        session.avg_sharpe = ((session.avg_sharpe * (session.current_iteration - 1)) + score) / session.current_iteration
        session.avg_win_rate = ((session.avg_win_rate * (session.current_iteration - 1)) + win_rate) / session.current_iteration
        session.best_sharpe = max(session.best_sharpe, score)
        session.best_win_rate = max(session.best_win_rate, win_rate)
        session.toto2_regime = climate.get("regime")
        session.toto2_volatility = climate.get("metrics", {}).get("volatility")
        session.tabpfn_top_features = feature_importance
        await db.commit()

        shap_summary = None
        if shap_explanation:
            contributions = shap_explanation.get("contributions", [])
            top_3 = sorted(
                contributions,
                key=lambda c: abs(c.get("shap_value", 0)),
                reverse=True,
            )[:3]
            shap_summary = {
                "base_value": shap_explanation.get("base_value"),
                "output_value": shap_explanation.get("output_value"),
                "top_features": top_3,
            }

        await self._broadcast_event(session.id, {
            "type": "iteration_complete",
            "session_id": session.id,
            "iteration": experiment.iteration,
            "hypothesis": experiment.hypothesis,
            "score": experiment.composite_score,
            "sharpe": experiment.backtest_sharpe,
            "win_rate": experiment.backtest_win_rate,
            "verdict": experiment.verdict,
            "shap_summary": shap_summary,
        })

    async def _get_user_config(self, user_id: str) -> ResearchSessionConfig | None:
        async with async_session() as db:
            result = await db.execute(
                select(ResearchSessionConfig).where(ResearchSessionConfig.user_id == user_id)
            )
            return result.scalar_one_or_none()

    async def _get_alpha_vector(self, alpha_vector_id: str | None) -> dict[str, Any] | None:
        if not alpha_vector_id:
            return None
        async with async_session() as db:
            from app.models.rlm_alpha_vector import RLMAlphaVector
            result = await db.execute(
                select(RLMAlphaVector).where(RLMAlphaVector.id == alpha_vector_id)
            )
            vec = result.scalar_one_or_none()
            return vec.alpha_vector if vec else None

    async def _get_past_results(self, session_id: str) -> list[dict[str, Any]]:
        results = await self.get_session_results(session_id)
        return [
            {
                "verdict": r.verdict,
                "composite_score": r.composite_score,
                "backtest_config": r.backtest_config or {},
            }
            for r in results
        ]

    async def resume_interrupted_sessions(self) -> None:
        async with async_session() as db:
            result = await db.execute(
                select(ResearchSession).where(ResearchSession.status == SessionStatus.RUNNING)
            )
            sessions = list(result.scalars().all())
        for session in sessions:
            logger.info("Resuming session %s for user %s", session.id, session.user_id)
            stop_event = asyncio.Event()
            self._stop_events[session.id] = stop_event
            task = asyncio.create_task(self._run_session_loop(session.id, stop_event))
            self._sessions[session.id] = task
            self._session_owners[session.id] = session.user_id

    async def _cron_worker(self) -> None:
        while self._running:
            try:
                await asyncio.sleep(60)
                if not self._running:
                    break
                async with async_session() as db:
                    result = await db.execute(
                        select(ResearchSessionConfig).where(ResearchSessionConfig.cron_enabled == True)  # noqa: E712
                    )
                    configs = list(result.scalars().all())
                for cfg in configs:
                    if len(self._sessions) >= 5:
                        break
                    if self._user_active_count(cfg.user_id) >= cfg.max_concurrent:
                        continue
                    async with async_session() as db:
                        last_result = await db.execute(
                            select(ExperimentResult)
                            .where(ExperimentResult.session_id.in_(
                                select(ResearchSession.id).where(
                                    ResearchSession.user_id == cfg.user_id
                                )
                            ))
                            .order_by(ExperimentResult.created_at.desc())
                            .limit(1)
                        )
                        last = last_result.scalar_one_or_none()
                        if last and last.created_at is not None:
                            elapsed = (
                                datetime.now(timezone.utc) - _as_utc(last.created_at)
                            ).total_seconds() / 60
                            if elapsed < (cfg.cron_interval_minutes or 3600):
                                continue
                    await self.start_session(
                        user_id=cfg.user_id,
                        mode=SessionMode.CRON,
                        trigger_type="cron",
                    )
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.exception("Cron worker error: %s", exc)

    async def _wait_until(self, stop_event: asyncio.Event, timeout: int) -> None:
        try:
            await asyncio.wait_for(stop_event.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            pass


def mode_is_manual(mode: SessionMode) -> bool:
    return mode == SessionMode.MANUAL
