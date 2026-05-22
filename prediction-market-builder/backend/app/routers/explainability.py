from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.models.experiment_result import ExperimentResult
from app.routers.auth import get_current_user
from app.services.explainability_service import ExplainabilityService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/explainability", tags=["explainability"])

_explainability_service: ExplainabilityService | None = None


def init_explainability(service: ExplainabilityService) -> None:
    global _explainability_service
    _explainability_service = service


def get_service() -> ExplainabilityService:
    if _explainability_service is None:
        raise HTTPException(status_code=503, detail="Explainability service not available")
    return _explainability_service


@router.get("/{result_id}")
async def get_explanation(
    result_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    async with async_session() as db:
        result = await db.execute(
            select(ExperimentResult).where(ExperimentResult.id == result_id)
        )
        experiment = result.scalar_one_or_none()

    if not experiment:
        raise HTTPException(status_code=404, detail="Experiment result not found")

    if not experiment.shap_explanation:
        return {"explanation": None, "message": "No SHAP explanation available for this result"}

    return {"explanation": experiment.shap_explanation}


@router.get("/session/{session_id}/aggregate")
async def get_session_aggregate(
    session_id: str,
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    async with async_session() as db:
        result = await db.execute(
            select(ExperimentResult)
            .where(ExperimentResult.session_id == session_id)
            .order_by(ExperimentResult.iteration.asc())
        )
        experiments = list(result.scalars().all())

    if not experiments:
        return {"aggregate": None, "count": 0}

    explanations = [e.shap_explanation for e in experiments if e.shap_explanation]

    if not explanations:
        return {"aggregate": None, "count": len(experiments)}

    agg_importance: dict[str, float] = {}
    for exp in explanations:
        for name, val in exp.get("mean_abs_importance", {}).items():
            agg_importance[name] = agg_importance.get(name, 0.0) + abs(val)

    count = len(explanations)
    for name in agg_importance:
        agg_importance[name] = round(agg_importance[name] / count, 6)

    ranking = sorted(agg_importance, key=agg_importance.get, reverse=True)

    return {
        "aggregate": {
            "mean_abs_importance": agg_importance,
            "ranking": ranking,
        },
        "count": count,
    }


@router.post("/explain")
async def explain_features(
    body: dict[str, Any],
    user: dict = Depends(get_current_user),
) -> dict[str, Any]:
    service = get_service()

    features = body.get("features", {})
    regime_vector = body.get("regime_vector")

    if regime_vector:
        explanation = await service.explain_validate_signal_features(
            features, regime_vector
        )
    else:
        explanation = await service.explain_tabpfn_features(features)

    return {"explanation": explanation}
