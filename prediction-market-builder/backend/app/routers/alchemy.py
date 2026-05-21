from __future__ import annotations

import logging

from fastapi import APIRouter

from app.ai.alchemy_service import AlchemyService, AlchemyRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/alchemy", tags=["alchemy"])

_alchemy_service: AlchemyService | None = None


def init_alchemy(service: AlchemyService) -> None:
    global _alchemy_service
    _alchemy_service = service


@router.post("/analyze")
async def analyze(body: dict):
    if not _alchemy_service:
        return {"error": "Alchemy service not initialized"}
    request = AlchemyRequest(
        query=body.get("query", ""),
        market_id=body.get("market_id"),
        force_refresh=body.get("force_refresh", False),
    )
    if not request.query.strip():
        return {"error": "query is required"}
    report = await _alchemy_service.analyze(request)
    return report.model_dump()


@router.get("/history")
async def get_history():
    if not _alchemy_service:
        return {"error": "Alchemy service not initialized"}
    reports = _alchemy_service.get_history()
    return [r.model_dump() for r in reports]


@router.get("/history/{report_id}")
async def get_report(report_id: str):
    if not _alchemy_service:
        return {"error": "Alchemy service not initialized"}
    report = _alchemy_service.get_report(report_id)
    if report is None:
        return {"error": f"Report '{report_id}' not found"}
    return report.model_dump()
