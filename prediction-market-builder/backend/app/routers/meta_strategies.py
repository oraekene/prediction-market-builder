import math
from datetime import datetime, timezone, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from app.database import get_session
from app.models.meta_strategy import MetaStrategy, MetaStrategyMode
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeStatus


router = APIRouter(prefix="/api/meta-strategies", tags=["meta-strategies"])


class CreateMetaStrategyRequest(BaseModel):
    user_id: str = "default"
    name: str = "New Meta-Strategy"
    description: str | None = None
    mode: MetaStrategyMode = MetaStrategyMode.COMPETITION
    strategy_ids: list[str] = []
    scoring_config: dict | None = None
    promotion_config: dict | None = None
    confluence_config: dict | None = None
    consumer: str | None = None


class UpdateMetaStrategyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    mode: MetaStrategyMode | None = None
    status: str | None = None
    strategy_ids: list[str] | None = None
    scoring_config: dict | None = None
    promotion_config: dict | None = None
    confluence_config: dict | None = None
    consumer: str | None = None
    current_winner_id: str | None = None


def _compute_default_score(trades: list[dict[str, Any]], weights: dict[str, float] | None = None) -> dict[str, Any]:
    w = weights or {"sharpe": 0.20, "win_rate": 0.15, "profit_factor": 0.15, "max_drawdown": 0.10, "confidence": 0.10, "expected_value": 0.10, "signal_strength": 0.10, "consistency": 0.10}

    pnl_list = [t["pnl"] for t in trades if t.get("pnl") is not None]
    total = len(pnl_list)
    total_pnl = sum(pnl_list) if pnl_list else 0.0

    if total < 2:
        return {"score": round(max(0, total_pnl) / 1000, 4), "total_trades": total, "total_pnl": round(total_pnl, 2), "win_rate": 0.0,
                "confidence": 0.0, "expected_value": 0.0, "signal_strength": 0.0, "consistency": 0.0}

    winning = [p for p in pnl_list if p > 0]
    win_rate = len(winning) / total
    mean_pnl = total_pnl / total
    variance = sum((p - mean_pnl) ** 2 for p in pnl_list) / (total - 1)
    sharpe = (mean_pnl / math.sqrt(variance)) if variance > 0 else 0.0

    cumulative = 0.0
    peak = 0.0
    max_dd = 0.0
    for p in pnl_list:
        cumulative += p
        if cumulative > peak:
            peak = cumulative
        dd = (peak - cumulative) / (peak if peak != 0 else 1)
        if dd > max_dd:
            max_dd = dd

    norm_sharpe = max(0.0, min(sharpe / 3.0, 1.0))
    norm_win = win_rate
    norm_dd = max(0.0, 1.0 - max_dd)
    norm_pnl = max(0.0, min(total_pnl / 10000, 1.0))

    score = (
        norm_sharpe * w.get("sharpe", 0.20)
        + norm_win * w.get("win_rate", 0.15)
        + norm_dd * w.get("max_drawdown", 0.10)
        + norm_pnl * w.get("profit_factor", 0.15)
    )

    return {
        "score": round(score, 4),
        "total_trades": total,
        "total_pnl": round(total_pnl, 2),
        "win_rate": round(win_rate, 4),
        "confidence": 0.0,
        "expected_value": 0.0,
        "signal_strength": 0.0,
        "consistency": 0.0,
    }


def _get_promotion_interval_seconds(promotion_config: dict) -> int:
    interval = promotion_config.get("interval", "daily")
    if interval == "custom" and promotion_config.get("interval_days"):
        return int(promotion_config["interval_days"]) * 86400
    return {"daily": 86400, "weekly": 604800, "monthly": 2592000}.get(interval, 86400)


def _should_promote(ms: MetaStrategy) -> bool:
    if ms.last_promotion_at is None:
        return True
    now = datetime.now(timezone.utc)
    interval_seconds = _get_promotion_interval_seconds(ms.promotion_config or {})
    elapsed = (now - ms.last_promotion_at).total_seconds()
    return elapsed >= interval_seconds


async def _fetch_trades(session: AsyncSession, strategy_id: str) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Trade).where(
            Trade.strategy_id == strategy_id,
            Trade.status == TradeStatus.EXECUTED,
        ).order_by(Trade.executed_at.desc()).limit(200)
    )
    return [
        {"pnl": t.pnl or 0.0, "amount": t.amount, "side": t.side, "market_id": t.market_id}
        for t in result.scalars().all()
    ]


@router.get("")
async def list_meta_strategies(user_id: str = "default", session: AsyncSession = Depends(get_session)):
    result = await session.execute(
        select(MetaStrategy).where(MetaStrategy.user_id == user_id).order_by(MetaStrategy.created_at.desc())
    )
    return result.scalars().all()


@router.post("")
async def create_meta_strategy(data: CreateMetaStrategyRequest, session: AsyncSession = Depends(get_session)):
    ms = MetaStrategy(
        user_id=data.user_id,
        name=data.name,
        description=data.description,
        mode=data.mode,
        strategy_ids=data.strategy_ids,
        consumer=data.consumer,
    )
    if data.scoring_config:
        ms.scoring_config = data.scoring_config
    if data.promotion_config:
        ms.promotion_config = data.promotion_config
    if data.confluence_config:
        ms.confluence_config = data.confluence_config
    session.add(ms)
    await session.commit()
    await session.refresh(ms)
    return ms


@router.get("/{ms_id}")
async def get_meta_strategy(ms_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")
    return ms


@router.put("/{ms_id}")
async def update_meta_strategy(ms_id: str, data: UpdateMetaStrategyRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")
    if data.name is not None:
        ms.name = data.name
    if data.description is not None:
        ms.description = data.description
    if data.mode is not None:
        ms.mode = data.mode
    if data.status is not None:
        ms.status = data.status
    if data.strategy_ids is not None:
        ms.strategy_ids = data.strategy_ids
    if data.scoring_config is not None:
        ms.scoring_config = data.scoring_config
    if data.promotion_config is not None:
        ms.promotion_config = data.promotion_config
    if data.confluence_config is not None:
        ms.confluence_config = data.confluence_config
    if data.consumer is not None:
        ms.consumer = data.consumer
    if data.current_winner_id is not None:
        ms.current_winner_id = data.current_winner_id
    await session.commit()
    await session.refresh(ms)
    return ms


@router.delete("/{ms_id}")
async def delete_meta_strategy(ms_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")
    await session.delete(ms)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{ms_id}/strategies")
async def add_strategy_to_pool(ms_id: str, strategy_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")

    strat_result = await session.execute(select(Strategy).where(Strategy.id == strategy_id))
    if not strat_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Strategy not found")

    if strategy_id not in ms.strategy_ids:
        ids = list(ms.strategy_ids)
        ids.append(strategy_id)
        ms.strategy_ids = ids
        await session.commit()
        await session.refresh(ms)
    return ms


@router.delete("/{ms_id}/strategies/{strategy_id}")
async def remove_strategy_from_pool(ms_id: str, strategy_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")

    ids = [s for s in ms.strategy_ids if s != strategy_id]
    ms.strategy_ids = ids
    if ms.current_winner_id == strategy_id:
        ms.current_winner_id = None
    await session.commit()
    await session.refresh(ms)
    return ms


@router.get("/{ms_id}/rankings")
async def get_rankings(ms_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")

    weights = (ms.scoring_config or {}).get("metrics", None)
    strategy_scores = []
    for sid in ms.strategy_ids:
        strat_result = await session.execute(select(Strategy).where(Strategy.id == sid))
        strat = strat_result.scalar_one_or_none()
        strat_name = strat.name if strat else sid
        trades = await _fetch_trades(session, sid)
        score_result = _compute_default_score(trades, weights)
        strategy_scores.append({"id": sid, "name": strat_name, **score_result})

    strategy_scores.sort(key=lambda x: x["score"], reverse=True)
    for rank, entry in enumerate(strategy_scores, 1):
        entry["rank"] = rank
        entry["is_winner"] = entry["id"] == ms.current_winner_id

    return {
        "meta_strategy_id": ms_id,
        "name": ms.name,
        "mode": ms.mode,
        "current_winner_id": ms.current_winner_id,
        "last_promotion_at": ms.last_promotion_at.isoformat() if ms.last_promotion_at else None,
        "rankings": strategy_scores,
    }


@router.post("/{ms_id}/evaluate")
async def evaluate_promotion(ms_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")

    weights = (ms.scoring_config or {}).get("metrics", None)
    probation_hours = (ms.promotion_config or {}).get("probation_hours", 0)

    strategy_scores = []
    for sid in ms.strategy_ids:
        trades = await _fetch_trades(session, sid)
        score_result = _compute_default_score(trades, weights)
        strategy_scores.append({"id": sid, **score_result})

    strategy_scores.sort(key=lambda x: x["score"], reverse=True)
    best_sid = strategy_scores[0]["id"] if strategy_scores else None

    promoted = False
    if best_sid and _should_promote(ms):
        if ms.mode in (MetaStrategyMode.CONFLUENCE, MetaStrategyMode.BOTH):
            cc = ms.confluence_config or {}
            threshold = cc.get("threshold", 3)
            from_top = cc.get("from_top", 5)
            top_n = strategy_scores[:from_top]
            trade_signals = {}
            for sid_candidate in [s["id"] for s in top_n]:
                sc_trades = await _fetch_trades(session, sid_candidate)
                latest_pnl = sc_trades[0]["pnl"] if sc_trades else 0
                trade_signals[sid_candidate] = "buy" if latest_pnl > 0 else "sell"

            signal_counts: dict[str, int] = {}
            for ts in trade_signals.values():
                signal_counts[ts] = signal_counts.get(ts, 0) + 1
            max_consensus = max(signal_counts.values()) if signal_counts else 0

            if max_consensus < threshold:
                return {
                    "meta_strategy_id": ms_id,
                    "current_winner_id": ms.current_winner_id,
                    "last_promotion_at": ms.last_promotion_at.isoformat() if ms.last_promotion_at else None,
                    "promoted": False,
                    "reason": f"Confluence not met: {max_consensus}/{threshold} agreement needed",
                }

        if probation_hours > 0 and ms.current_winner_id and best_sid != ms.current_winner_id:
            probation_seconds = probation_hours * 3600
            now = datetime.now(timezone.utc)
            promoted_at = ms.last_promotion_at or now
            if (now - promoted_at).total_seconds() < probation_seconds:
                return {
                    "meta_strategy_id": ms_id,
                    "current_winner_id": ms.current_winner_id,
                    "last_promotion_at": ms.last_promotion_at.isoformat() if ms.last_promotion_at else None,
                    "promoted": False,
                    "reason": f"Probation: {best_sid} must hold rank for {probation_hours}h before promotion",
                }

        ms.current_winner_id = best_sid
        ms.last_promotion_at = datetime.now(timezone.utc)
        promoted = True
        await session.commit()
        await session.refresh(ms)

    return {
        "meta_strategy_id": ms_id,
        "current_winner_id": ms.current_winner_id,
        "last_promotion_at": ms.last_promotion_at.isoformat() if ms.last_promotion_at else None,
        "promoted": promoted,
    }


@router.post("/{ms_id}/force-promote")
async def force_promote(ms_id: str, strategy_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")
    if strategy_id not in ms.strategy_ids:
        raise HTTPException(status_code=400, detail="Strategy not in meta-strategy pool")
    ms.current_winner_id = strategy_id
    ms.last_promotion_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(ms)
    return ms


@router.get("/{ms_id}/performance")
async def get_meta_strategy_performance(ms_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(MetaStrategy).where(MetaStrategy.id == ms_id))
    ms = result.scalar_one_or_none()
    if not ms:
        raise HTTPException(status_code=404, detail="Meta-strategy not found")

    total_pnl = 0.0
    total_trades = 0
    winning_trades = 0
    strategy_performances = []

    for sid in ms.strategy_ids:
        strat_result = await session.execute(select(Strategy).where(Strategy.id == sid))
        strat = strat_result.scalar_one_or_none()
        strat_name = strat.name if strat else sid

        trades = await _fetch_trades(session, sid)
        strat_pnl = sum(t["pnl"] for t in trades)
        strat_count = len(trades)
        strat_winning = sum(1 for t in trades if t["pnl"] > 0)

        total_pnl += strat_pnl
        total_trades += strat_count
        winning_trades += strat_winning

        strategy_performances.append({
            "id": sid,
            "name": strat_name,
            "pnl": round(strat_pnl, 2),
            "trades": strat_count,
            "win_rate": round(strat_winning / strat_count, 4) if strat_count > 0 else 0,
        })

    overall_win_rate = round(winning_trades / total_trades, 4) if total_trades > 0 else 0

    return {
        "meta_strategy_id": ms_id,
        "name": ms.name,
        "mode": ms.mode,
        "current_winner_id": ms.current_winner_id,
        "total_pnl": round(total_pnl, 2),
        "total_trades": total_trades,
        "overall_win_rate": overall_win_rate,
        "strategy_performances": strategy_performances,
    }
