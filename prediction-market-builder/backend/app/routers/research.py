from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session, async_session
from app.models.research_session import ResearchSession, SessionStatus, SessionMode
from app.models.experiment_result import ExperimentResult
from app.models.rlm_alpha_vector import RLMAlphaVector
from app.models.research_config import ResearchSessionConfig
from app.services.research_scheduler import ResearchScheduler
from app.ai.market_regime_service import MarketRegimeService
from app.ai.tabpfn_service import TabPFNService
from app.ai.rlm_service import RLMService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/research", tags=["research"])

scheduler: ResearchScheduler | None = None
market_regime_service = MarketRegimeService()
tabpfn_service = TabPFNService()
rlm_service = RLMService()

_ws_connections: dict[str, set[WebSocket]] = {}
_ws_lock: Any = None


def init_scheduler(research_scheduler: ResearchScheduler) -> None:
    global scheduler
    scheduler = research_scheduler


async def _get_ws_lock():
    global _ws_lock
    if _ws_lock is None:
        from asyncio import Lock
        _ws_lock = Lock()
    return _ws_lock


async def broadcast_to_session(session_id: str, event: dict[str, Any]) -> None:
    lock = await _get_ws_lock()
    async with lock:
        connections = _ws_connections.get(session_id, set()).copy()
    dead = set()
    for ws in connections:
        try:
            await ws.send_json(event)
        except Exception:
            dead.add(ws)
    if dead:
        async with lock:
            if session_id in _ws_connections:
                _ws_connections[session_id] -= dead


def _get_user_id_from_context() -> str:
    return "default"


@router.post("/run")
async def trigger_run(
    strategy_id: str | None = Query(None),
    preset: str = Query("sharpe_max"),
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    user_id = _get_user_id_from_context()
    result = await scheduler.start_session(
        user_id=user_id,
        strategy_id=strategy_id,
        mode=SessionMode.MANUAL,
        trigger_type="manual",
        preset=preset,
    )
    if not result:
        raise HTTPException(status_code=429, detail="Concurrency limit reached")
    return {"session_id": result.id, "status": "started"}


@router.post("/run-continuous")
async def trigger_continuous(
    strategy_id: str | None = Query(None),
    preset: str = Query("sharpe_max"),
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    user_id = _get_user_id_from_context()
    result = await scheduler.start_session(
        user_id=user_id,
        strategy_id=strategy_id,
        mode=SessionMode.CONTINUOUS,
        trigger_type="continuous",
        preset=preset,
    )
    if not result:
        raise HTTPException(status_code=429, detail="Concurrency limit reached")
    return {"session_id": result.id, "status": "started"}


@router.post("/stop")
async def stop_research(
    session_id: str = Query(...),
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    success = await scheduler.stop_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "stopped"}


@router.post("/sessions")
async def create_session(
    strategy_id: str | None = None,
    mode: str = "manual",
    trigger_type: str | None = None,
    preset: str = "sharpe_max",
    db_session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    mode_enum = SessionMode(mode) if mode in ("manual", "cron", "continuous") else SessionMode.MANUAL
    user_id = _get_user_id_from_context()
    result = await scheduler.start_session(
        user_id=user_id,
        strategy_id=strategy_id,
        mode=mode_enum,
        trigger_type=trigger_type,
        preset=preset,
    )
    if not result:
        raise HTTPException(status_code=429, detail="Concurrency limit reached or scheduler not running")
    return {"session_id": result.id, "status": "created"}


@router.get("/sessions")
async def list_sessions(
    limit: int = Query(20, le=100),
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    sessions = await scheduler.get_user_sessions(_get_user_id_from_context())
    return {
        "sessions": [
            {
                "id": s.id,
                "user_id": s.user_id,
                "strategy_id": s.strategy_id,
                "status": s.status.value,
                "mode": s.mode.value,
                "current_iteration": s.current_iteration,
                "total_kept": s.total_kept,
                "avg_sharpe": s.avg_sharpe,
                "best_sharpe": s.best_sharpe,
                "composite_preset": s.composite_preset.value,
                "toto2_regime": s.toto2_regime,
                "pareto_front": s.pareto_front,
                "created_at": s.created_at.isoformat() if s.created_at else None,
            }
            for s in sessions
        ],
        "total": len(sessions),
    }


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: str,
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    s = await scheduler.get_session(session_id)
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": s.id,
        "user_id": s.user_id,
        "strategy_id": s.strategy_id,
        "status": s.status.value,
        "mode": s.mode.value,
        "trigger_type": s.trigger_type,
        "composite_preset": s.composite_preset.value,
        "current_iteration": s.current_iteration,
        "total_kept": s.total_kept,
        "total_reverted": s.total_reverted,
        "avg_sharpe": s.avg_sharpe,
        "avg_win_rate": s.avg_win_rate,
        "best_sharpe": s.best_sharpe,
        "best_win_rate": s.best_win_rate,
        "rlm_alpha_vector_id": s.rlm_alpha_vector_id,
        "toto2_regime": s.toto2_regime,
        "toto2_volatility": s.toto2_volatility,
        "tabpfn_top_features": s.tabpfn_top_features,
        "hypothesis_count": s.hypothesis_count,
        "pareto_front": s.pareto_front,
        "error_message": s.error_message,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


@router.get("/sessions/{session_id}/results")
async def get_session_results(
    session_id: str,
    limit: int = Query(50, le=200),
    session: AsyncSession = Depends(get_session),
):
    if not scheduler:
        raise HTTPException(status_code=503, detail="Research scheduler not initialized")
    results = await scheduler.get_session_results(session_id)
    return {
        "results": [
            {
                "id": r.id,
                "iteration": r.iteration,
                "hypothesis": r.hypothesis,
                "regime_at_time": r.regime_at_time,
                "backtest_trades": r.backtest_trades,
                "backtest_win_rate": r.backtest_win_rate,
                "backtest_sharpe": r.backtest_sharpe,
                "backtest_max_drawdown": r.backtest_max_drawdown,
                "backtest_total_pnl": r.backtest_total_pnl,
                "tabpfn_probability": r.tabpfn_probability,
                "tabpfn_confidence": r.tabpfn_confidence,
                "composite_score": r.composite_score,
                "verdict": r.verdict,
                "git_commit_hash": r.git_commit_hash,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in results[-limit:]
        ],
        "total": len(results),
    }


@router.get("/stats")
async def get_stats(
    db: AsyncSession = Depends(get_session),
):
    total_sessions = await db.scalar(select(func.count(ResearchSession.id)))
    total_kept = await db.scalar(select(func.coalesce(func.sum(ResearchSession.total_kept), 0)))
    total_reverted = await db.scalar(select(func.coalesce(func.sum(ResearchSession.total_reverted), 0)))
    avg_sharpe = await db.scalar(select(func.avg(ResearchSession.avg_sharpe)))
    avg_win = await db.scalar(select(func.avg(ResearchSession.avg_win_rate)))
    best_sharpe = await db.scalar(select(func.max(ResearchSession.best_sharpe)))
    return {
        "total_sessions": total_sessions or 0,
        "total_kept": total_kept or 0,
        "total_reverted": total_reverted or 0,
        "avg_sharpe": round(float(avg_sharpe or 0.0), 4),
        "avg_win_rate": round(float(avg_win or 0.0), 4),
        "best_sharpe": round(float(best_sharpe or 0.0), 4),
        "keep_rate": round((total_kept or 0) / max((total_kept or 0) + (total_reverted or 0), 1), 4),
    }


@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_session),
):
    user_id = _get_user_id_from_context()
    result = await db.execute(
        select(ResearchSessionConfig).where(ResearchSessionConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        return {"preset": "sharpe_max", "max_concurrent": 2, "cron_enabled": False, "enable_genetic_optimization": False}
    return {
        "preset": config.composite_preset,
        "max_concurrent": config.max_concurrent,
        "cron_enabled": config.cron_enabled,
        "cron_interval_minutes": config.cron_interval_minutes,
        "continuous_enabled": config.continuous_enabled,
        "rlm_cron_enabled": config.rlm_cron_enabled,
        "rlm_cron_interval_minutes": config.rlm_cron_interval_minutes,
        "max_hypotheses_per_session": config.max_hypotheses_per_session,
        "enable_genetic_optimization": config.enable_genetic_optimization,
    }


@router.put("/config")
async def update_config(
    preset: str | None = Query(None),
    max_concurrent: int | None = Query(None),
    cron_enabled: bool | None = Query(None),
    cron_interval: int | None = Query(None),
    continuous_enabled: bool | None = Query(None),
    max_hypotheses: int | None = Query(None),
    enable_genetic_optimization: bool | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    user_id = _get_user_id_from_context()
    result = await db.execute(
        select(ResearchSessionConfig).where(ResearchSessionConfig.user_id == user_id)
    )
    config = result.scalar_one_or_none()
    if not config:
        config = ResearchSessionConfig(user_id=user_id)
        db.add(config)
    if preset is not None:
        config.composite_preset = preset
    if max_concurrent is not None:
        config.max_concurrent = max(min(max_concurrent, 5), 1)
    if cron_enabled is not None:
        config.cron_enabled = cron_enabled
    if cron_interval is not None:
        config.cron_interval_minutes = max(cron_interval, 30)
    if continuous_enabled is not None:
        config.continuous_enabled = continuous_enabled
    if max_hypotheses is not None:
        config.max_hypotheses_per_session = max(min(max_hypotheses, 200), 5)
    if enable_genetic_optimization is not None:
        config.enable_genetic_optimization = enable_genetic_optimization
    await db.commit()
    return {"status": "updated"}


@router.get("/climate")
async def get_climate(
    session: AsyncSession = Depends(get_session),
):
    climate = await market_regime_service.assess_climate([])
    return climate


@router.get("/features")
async def get_features(
    session: AsyncSession = Depends(get_session),
):
    df = _empty_feature_df()
    features = await tabpfn_service.get_feature_importance(df)
    return {"features": features}


@router.get("/alpha-vectors")
async def list_alpha_vectors(
    limit: int = Query(10, le=50),
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(
        select(RLMAlphaVector)
        .order_by(RLMAlphaVector.created_at.desc())
        .limit(limit)
    )
    vectors = list(result.scalars().all())
    return {
        "vectors": [
            {
                "id": v.id,
                "source_type": v.source_type,
                "source_path": v.source_path,
                "token_count": v.token_count,
                "used_in_sessions": v.used_in_sessions,
                "created_at": v.created_at.isoformat() if v.created_at else None,
            }
            for v in vectors
        ]
    }


@router.post("/rlm-scan")
async def trigger_rlm_scan(
    source_type: str = Query("forum"),
    source_path: str | None = Query(None),
    keywords: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    keywords_list = keywords.split(",") if keywords else None
    result = await rlm_service.scan_directory(
        directory=source_path or "./data/archives",
        keywords=keywords_list,
    )
    alpha_vector = RLMAlphaVector(
        source_type=source_type,
        source_path=source_path or "./data/archives",
        source_hash=rlm_service.compute_source_hash(source_path or "./data/archives"),
        token_count=result.get("token_estimate", 0),
        alpha_vector=result.get("alpha_vector", {}),
        sub_agent_traces=rlm_service.get_accumulated_state(),
        traces=rlm_service.get_accumulated_state(),
        dspy_trajectory=rlm_service.inspect_last_trajectory(),
    )
    db.add(alpha_vector)
    await db.commit()
    await db.refresh(alpha_vector)
    return {"alpha_vector_id": alpha_vector.id, "status": "completed", "alpha_vector": alpha_vector.alpha_vector}


@router.post("/rlm-drift")
async def trigger_rlm_drift(
    historical_texts: list[str] = Query(...),
    recent_texts: list[str] = Query(...),
    entities: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    entities_list = [e.strip() for e in entities.split(",") if e.strip()]
    result = await rlm_service.detect_linguistic_drift(
        texts_historical=historical_texts,
        texts_recent=recent_texts,
        target_entities=entities_list,
    )
    return result


@router.post("/rlm-text-batch")
async def trigger_rlm_text_batch(
    texts: list[str] = Query(...),
    query: str = Query(...),
    db: AsyncSession = Depends(get_session),
):
    result = await rlm_service.scan_text_batch(
        texts=texts,
        query=query,
    )
    return result


@router.post("/rlm-pipeline")
async def trigger_rlm_pipeline(
    directory: str = Query("./data/archives"),
    keywords: str | None = Query(None),
    historical_texts: list[str] | None = Query(None),
    recent_texts: list[str] | None = Query(None),
    entities: str | None = Query(None),
    db: AsyncSession = Depends(get_session),
):
    keywords_list = keywords.split(",") if keywords else None
    entities_list = [e.strip() for e in entities.split(",") if e.strip()] if entities else None
    result = await rlm_service.run_pipeline(
        directory=directory,
        keywords=keywords_list,
        historical_texts=historical_texts,
        recent_texts=recent_texts,
        entities=entities_list,
    )
    alpha_vector = RLMAlphaVector(
        source_type="pipeline",
        source_path=directory,
        source_hash=rlm_service.compute_source_hash(directory),
        token_count=result.get("scan", {}).get("token_estimate", 0),
        alpha_vector=result.get("alpha_vector", {}),
        linguistic_signals=result.get("drift"),
        sub_agent_traces=rlm_service.get_accumulated_state(),
        traces=rlm_service.get_accumulated_state(),
        dspy_trajectory=rlm_service.inspect_last_trajectory(),
    )
    db.add(alpha_vector)
    await db.commit()
    await db.refresh(alpha_vector)
    return {
        "alpha_vector_id": alpha_vector.id,
        "alpha_vector": alpha_vector.alpha_vector,
        "linguistic_signals": alpha_vector.linguistic_signals,
        "scan": result.get("scan"),
        "pipeline_complete": True,
    }


@router.get("/rlm-trajectory")
async def get_rlm_trajectory():
    trajectory = rlm_service.inspect_last_trajectory()
    return {"trajectory": trajectory, "available": trajectory is not None}


@router.get("/rlm-state")
async def get_rlm_accumulated_state():
    state = rlm_service.get_accumulated_state()
    return {"state": state, "count": len(state)}


@router.get("/rlm/trace/{vector_id}")
async def get_rlm_trace(vector_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(RLMAlphaVector).where(RLMAlphaVector.id == vector_id)
    )
    vector = result.scalar_one_or_none()
    if not vector:
        raise HTTPException(status_code=404, detail="RLM alpha vector not found")
    return {
        "id": vector.id,
        "source_type": vector.source_type,
        "source_path": vector.source_path,
        "alpha_vector": vector.alpha_vector,
        "linguistic_signals": vector.linguistic_signals,
        "sub_agent_traces": vector.sub_agent_traces,
        "traces": vector.traces,
        "dspy_trajectory": vector.dspy_trajectory,
    }


@router.websocket("/ws/research/{session_id}")
async def research_websocket(websocket: WebSocket, session_id: str):
    await websocket.accept()
    lock = await _get_ws_lock()
    async with lock:
        if session_id not in _ws_connections:
            _ws_connections[session_id] = set()
        _ws_connections[session_id].add(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "pause":
                    if scheduler:
                        await scheduler.stop_session(session_id)
                    await websocket.send_json({"type": "paused"})
                elif msg_type == "resume":
                    if scheduler:
                        async with async_session() as db:
                            result = await db.execute(
                                select(ResearchSession).where(ResearchSession.id == session_id)
                            )
                            s = result.scalar_one_or_none()
                            if s:
                                await scheduler.start_session(
                                    user_id=s.user_id,
                                    strategy_id=s.strategy_id,
                                    mode=SessionMode.MANUAL,
                                )
                    await websocket.send_json({"type": "resumed"})
                elif msg_type == "stop":
                    if scheduler:
                        await scheduler.stop_session(session_id)
                    await websocket.send_json({"type": "stopped"})
                    break
            except json.JSONDecodeError:
                await websocket.send_json({"type": "error", "message": "Invalid JSON"})
    except WebSocketDisconnect:
        pass
    finally:
        async with lock:
            if session_id in _ws_connections:
                _ws_connections[session_id].discard(websocket)


def _empty_feature_df():
    import pandas as pd
    return pd.DataFrame()
