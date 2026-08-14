from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.risk_template import RiskTemplate
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.risk_manager import RiskManager, RiskProfile

router = APIRouter(prefix="/api/risk-templates", tags=["risk-templates"])


async def _get_owned_template(template_id: str, user: User, session: AsyncSession) -> RiskTemplate:
    result = await session.execute(
        select(RiskTemplate).where(
            RiskTemplate.id == template_id,
            RiskTemplate.user_id == user.id,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    return template


@router.post("", status_code=201)
async def create_risk_template(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    name = body.get("name")
    if not name:
        raise HTTPException(400, detail="name is required")
    template = RiskTemplate(
        name=name,
        description=body.get("description", ""),
        rules=body.get("rules", []),
        user_id=current_user.id,
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return _template_response(template)


@router.get("")
async def list_risk_templates(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(RiskTemplate)
        .where(RiskTemplate.user_id == current_user.id)
        .order_by(RiskTemplate.created_at.desc())
    )
    templates = [t for t in rows.scalars().all()]
    return {"templates": [_template_response(t) for t in templates]}


@router.get("/{template_id}")
async def get_risk_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    template = await _get_owned_template(template_id, current_user, session)
    return _template_response(template)


@router.put("/{template_id}")
async def update_risk_template(
    template_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    template = await _get_owned_template(template_id, current_user, session)
    if "name" in body:
        template.name = body["name"]
    if "description" in body:
        template.description = body.get("description", "")
    if "rules" in body:
        template.rules = body["rules"]
    await session.commit()
    await session.refresh(template)
    return _template_response(template)


@router.delete("/{template_id}")
async def delete_risk_template(
    template_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    template = await _get_owned_template(template_id, current_user, session)
    await session.delete(template)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{template_id}/evaluate")
async def evaluate_risk_template_endpoint(
    template_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    template = await _get_owned_template(template_id, current_user, session)
    signal = body.get("signal", {})
    portfolio = body.get("portfolio", {})
    profile = RiskProfile(rules=template.rules)
    mgr = RiskManager(profile)
    result = await mgr.evaluate_trade(market={}, signal=signal, portfolio=portfolio)
    return result


def _template_response(t: RiskTemplate) -> dict:
    return {
        "id": t.id,
        "name": t.name,
        "description": t.description,
        "rules": t.rules,
        "created_at": t.created_at.isoformat() if t.created_at else None,
        "updated_at": t.updated_at.isoformat() if t.updated_at else None,
    }
