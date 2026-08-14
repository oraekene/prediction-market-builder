from datetime import datetime, timezone
from copy import deepcopy

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_session
from app.models.strategy import Strategy, StrategyStatus
from app.models.template import StrategyTemplate
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.node_executor import ExecutionContext

router = APIRouter(prefix="/api/strategies", tags=["strategies"])

_strategy_engine = None
_tabpfn = None
_market_regime = None
_explainability_service = None
_hermes = None
_rlm = None
_market_aggregator = None


def init_strategy_engine(strategy_engine, tabpfn=None, market_regime=None,
                         explainability_service=None, hermes=None, rlm=None,
                         market_aggregator=None):
    global _strategy_engine, _tabpfn, _market_regime, _explainability_service
    global _hermes, _rlm, _market_aggregator
    _strategy_engine = strategy_engine
    _tabpfn = tabpfn
    _market_regime = market_regime
    _explainability_service = explainability_service
    _hermes = hermes
    _rlm = rlm
    _market_aggregator = market_aggregator


def _serialize_strategy(s: Strategy) -> dict:
    return {
        "id": s.id,
        "user_id": s.user_id,
        "name": s.name,
        "description": s.description,
        "mode": s.mode,
        "nodes": s.nodes,
        "edges": s.edges,
        "risk_profile": s.risk_profile,
        "status": s.status.value,
        "version": s.version,
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }


def _serialize_template(t: StrategyTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "config": t.config,
        "tags": t.tags,
        "usage_count": t.usage_count,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }


async def _get_owned_strategy(strategy_id: str, user: User, session: AsyncSession) -> Strategy:
    result = await session.execute(
        select(Strategy).where(Strategy.id == strategy_id, Strategy.user_id == user.id)
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


class CreateStrategyRequest(BaseModel):
    name: str = "New Strategy"
    description: str | None = None
    mode: str = "chat"
    nodes: list = []
    edges: list = []
    risk_profile: dict = {}


class CreateTemplateRequest(BaseModel):
    name: str
    description: str | None = None
    config: dict = {}
    tags: list = []


class UpdateTemplateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    config: dict | None = None
    tags: list | None = None


class UpdateStrategyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    mode: str | None = None
    nodes: list | None = None
    edges: list | None = None
    risk_profile: dict | None = None


@router.get("")
async def list_strategies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(Strategy).where(Strategy.user_id == current_user.id)
    )
    return [_serialize_strategy(s) for s in result.scalars().all()]


@router.post("", status_code=201)
async def create_strategy(
    data: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = Strategy(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        mode=data.mode,
        nodes=data.nodes,
        edges=data.edges,
        risk_profile=data.risk_profile,
    )
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.get("/templates")
async def list_templates(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StrategyTemplate).order_by(StrategyTemplate.updated_at.desc()))
    return [_serialize_template(t) for t in result.scalars().all()]


@router.post("/templates", status_code=201)
async def create_template(
    data: CreateTemplateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    template = StrategyTemplate(
        name=data.name,
        description=data.description,
        config=data.config,
        tags=data.tags,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return _serialize_template(template)


@router.get("/templates/{template_id}")
async def get_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return _serialize_template(template)


@router.put("/templates/{template_id}")
async def update_template(
    template_id: str,
    data: UpdateTemplateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    if data.name is not None:
        template.name = data.name
    if data.description is not None:
        template.description = data.description
    if data.config is not None:
        template.config = data.config
    if data.tags is not None:
        template.tags = data.tags
    await session.commit()
    await session.refresh(template)
    return _serialize_template(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await session.delete(template)
    await session.commit()
    return {"status": "deleted"}


@router.post("/templates/{template_id}/apply", status_code=201)
async def apply_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    config = template.config
    strategy = Strategy(
        user_id=current_user.id,
        name=template.name,
        description=template.description,
        mode=config.get("mode", "chat"),
        nodes=config.get("nodes", []),
        edges=config.get("edges", []),
        risk_profile=config.get("risk_profile", {}),
    )
    session.add(strategy)
    template.usage_count += 1
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.get("/{strategy_id}")
async def get_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    return _serialize_strategy(strategy)


@router.put("/{strategy_id}")
async def update_strategy(
    strategy_id: str,
    data: UpdateStrategyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if data.name is not None:
        strategy.name = data.name
    if data.description is not None:
        strategy.description = data.description
    if data.mode is not None:
        strategy.mode = data.mode
    if data.nodes is not None:
        strategy.nodes = data.nodes
    if data.edges is not None:
        strategy.edges = data.edges
    if data.risk_profile is not None:
        strategy.risk_profile = data.risk_profile
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.delete("/{strategy_id}")
async def delete_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    await session.delete(strategy)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{strategy_id}/deploy")
async def deploy_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if strategy.status == StrategyStatus.ACTIVE:
        return _serialize_strategy(strategy)
    _save_version_snapshot(strategy)
    strategy.status = StrategyStatus.ACTIVE
    strategy.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/pause")
async def pause_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if strategy.status != StrategyStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active strategies can be paused")
    _save_version_snapshot(strategy)
    strategy.status = StrategyStatus.PAUSED
    strategy.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/resume")
async def resume_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if strategy.status != StrategyStatus.PAUSED:
        raise HTTPException(status_code=400, detail="Only paused strategies can be resumed")
    _save_version_snapshot(strategy)
    strategy.status = StrategyStatus.ACTIVE
    strategy.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/archive")
async def archive_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if strategy.status == StrategyStatus.ARCHIVED:
        return _serialize_strategy(strategy)
    _save_version_snapshot(strategy)
    strategy.status = StrategyStatus.ARCHIVED
    strategy.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.post("/{strategy_id}/rollback")
async def rollback_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    if not strategy.version_history:
        raise HTTPException(status_code=400, detail="No previous version to rollback to")
    prev = strategy.version_history[-1]
    strategy.nodes = prev.get("nodes", strategy.nodes)
    strategy.edges = prev.get("edges", strategy.edges)
    strategy.risk_profile = prev.get("risk_profile", strategy.risk_profile)
    strategy.version = max(1, strategy.version - 1)
    strategy.version_history = strategy.version_history[:-1]
    strategy.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(strategy)
    return _serialize_strategy(strategy)


@router.get("/{strategy_id}/history")
async def get_strategy_history(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = await _get_owned_strategy(strategy_id, current_user, session)
    return {
        "current_version": strategy.version,
        "history": strategy.version_history,
    }


def _save_version_snapshot(strategy: Strategy) -> None:
    snapshot = {
        "version": strategy.version,
        "status": strategy.status.value,
        "nodes": deepcopy(strategy.nodes),
        "edges": deepcopy(strategy.edges),
        "risk_profile": deepcopy(strategy.risk_profile),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    history = list(strategy.version_history or [])
    history.append(snapshot)
    strategy.version_history = history
    strategy.version = (strategy.version or 1) + 1


class EvaluateStrategyRequest(BaseModel):
    nodes: list = []
    edges: list = []
    market_id: str | None = None
    market: dict | None = None
    portfolio: dict | None = None
    signal: dict | None = None
    daily_pnl: float = 0.0
    weekly_pnl: float = 0.0
    monthly_pnl: float = 0.0
    consecutive_losses: int = 0
    trail_states: dict | None = None
    circuit_breaker_state: dict | None = None
    withdrawal_state: dict | None = None
    price_history: list | None = None
    factor_exposures: dict | None = None
    greeks: dict | None = None
    vpin: float = 0.0
    ofi: float = 0.0


@router.post("/evaluate")
async def evaluate_strategy(
    data: EvaluateStrategyRequest,
    current_user: User = Depends(get_current_user),
):
    if not _strategy_engine:
        raise HTTPException(status_code=503, detail="Strategy engine not initialized")

    from app.data.chromadb_manager import ChromaDBManager

    market = data.market or {}
    if data.market_id and _market_aggregator:
        markets = await _market_aggregator.fetch_all()
        for m in markets:
            if m.get("platform_market_id") == data.market_id or m.get("id") == data.market_id:
                market = m
                break

    ctx = ExecutionContext(
        market=market,
        portfolio=data.portfolio,
        signal=data.signal,
        tabpfn=_tabpfn,
        market_regime=_market_regime,
        explainability_service=_explainability_service,
        hermes=_hermes,
        rlm=_rlm,
        market_aggregator=_market_aggregator,
        chromadb_manager=ChromaDBManager(),
        trail_states=data.trail_states,
        circuit_breaker_state=data.circuit_breaker_state,
        withdrawal_state=data.withdrawal_state,
        daily_pnl=data.daily_pnl,
        weekly_pnl=data.weekly_pnl,
        monthly_pnl=data.monthly_pnl,
        consecutive_losses=data.consecutive_losses,
        price_history=data.price_history,
        factor_exposures=data.factor_exposures,
        greeks=data.greeks,
        vpin=data.vpin,
        ofi=data.ofi,
    )
    return await _strategy_engine.evaluate(data.nodes, data.edges, ctx)
