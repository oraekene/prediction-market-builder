from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.risk_template import RiskTemplate
from app.services.risk_engine import evaluate_risk_template

router = APIRouter(prefix="/api/risk-templates", tags=["risk-templates"])


@router.post("")
async def create_risk_template(body: dict, session: AsyncSession = Depends(get_session)):
    template = RiskTemplate(
        name=body["name"],
        description=body.get("description", ""),
        rules=body.get("rules", []),
        user_id=body.get("user_id", "default"),
    )
    session.add(template)
    await session.commit()
    await session.refresh(template)
    return _template_response(template)


@router.get("")
async def list_risk_templates(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(select(RiskTemplate).order_by(RiskTemplate.created_at.desc()))
    templates = [t for t in rows.scalars().all()]
    return {"templates": [_template_response(t) for t in templates]}


@router.get("/{template_id}")
async def get_risk_template(template_id: str, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    return _template_response(template)


@router.put("/{template_id}")
async def update_risk_template(template_id: str, body: dict, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
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
async def delete_risk_template(template_id: str, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    await session.delete(template)
    await session.commit()
    return {"status": "deleted"}


@router.post("/{template_id}/evaluate")
async def evaluate_risk_template_endpoint(template_id: str, body: dict, session: AsyncSession = Depends(get_session)):
    template = await session.get(RiskTemplate, template_id)
    if not template:
        raise HTTPException(404, detail="Risk template not found")
    signal = body.get("signal", {})
    portfolio = body.get("portfolio", {})
    result = evaluate_risk_template(template, signal, portfolio)
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
