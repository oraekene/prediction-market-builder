from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.ai.alchemy_service import AlchemyService, AlchemyRequest
from app.models.user import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/alchemy", tags=["alchemy"])

_alchemy_service: AlchemyService | None = None


def init_alchemy(service: AlchemyService) -> None:
    global _alchemy_service
    _alchemy_service = service


def _require_service() -> AlchemyService:
    if not _alchemy_service:
        raise HTTPException(status_code=503, detail="Alchemy service not initialized")
    return _alchemy_service


@router.post("/analyze")
async def analyze(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    svc = _require_service()
    request = AlchemyRequest(
        query=body.get("query", ""),
        market_id=body.get("market_id"),
        force_refresh=body.get("force_refresh", False),
    )
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="query is required")
    report = await svc.analyze(request)
    return report.model_dump()


@router.get("/history")
async def get_history(current_user: User = Depends(get_current_user)):
    svc = _require_service()
    reports = svc.get_history()
    return [r.model_dump() for r in reports]


@router.get("/history/{report_id}")
async def get_report(
    report_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = _require_service()
    report = svc.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return report.model_dump()
