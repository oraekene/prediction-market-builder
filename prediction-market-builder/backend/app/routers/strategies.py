from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_session
from app.models.strategy import Strategy
from app.models.template import StrategyTemplate

router = APIRouter(prefix="/api/strategies", tags=["strategies"])


class CreateStrategyRequest(BaseModel):
    user_id: str = "default"
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
async def list_strategies(user_id: str = "default", session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Strategy).where(Strategy.user_id == user_id))
    return result.scalars().all()


@router.post("")
async def create_strategy(data: CreateStrategyRequest, session: AsyncSession = Depends(get_session)):
    strategy = Strategy(
        user_id=data.user_id,
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
    return strategy


@router.get("/templates")
async def list_templates(session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(StrategyTemplate).order_by(StrategyTemplate.updated_at.desc()))
    return result.scalars().all()


@router.post("/templates")
async def create_template(data: CreateTemplateRequest, session: AsyncSession = Depends(get_session)):
    template = StrategyTemplate(
        name=data.name,
        description=data.description,
        config=data.config,
        tags=data.tags,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return template


@router.get("/templates/{template_id}")
async def get_template(template_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.put("/templates/{template_id}")
async def update_template(template_id: str, data: UpdateTemplateRequest, session: AsyncSession = Depends(get_session)):
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
    return template


@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    await session.delete(template)
    await session.commit()
    return {"status": "deleted"}


@router.post("/templates/{template_id}/apply")
async def apply_template(template_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(StrategyTemplate).where(StrategyTemplate.id == template_id))
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    config = template.config
    strategy = Strategy(
        user_id="default",
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
    return strategy


@router.get("/{strategy_id}")
async def get_strategy(strategy_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return strategy


@router.put("/{strategy_id}")
async def update_strategy(strategy_id: str, data: UpdateStrategyRequest, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
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
    return strategy


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str, session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Strategy).where(Strategy.id == strategy_id))
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await session.delete(strategy)
    await session.commit()
    return {"status": "deleted"}
