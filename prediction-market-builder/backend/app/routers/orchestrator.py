from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query

from app.ai.hermes_orchestrator import HermesOrchestrator
from app.ai.skill_creator import SkillCreator
from app.ai.watchdog import WatchdogService
from app.models.user import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/orchestrator", tags=["orchestrator"])

_orchestrator: HermesOrchestrator | None = None
_watchdog: WatchdogService | None = None
_skill_creator: SkillCreator | None = None


def init_orchestrator(
    orchestrator: HermesOrchestrator,
    watchdog: WatchdogService,
    skill_creator: SkillCreator,
) -> None:
    global _orchestrator, _watchdog, _skill_creator
    _orchestrator = orchestrator
    _watchdog = watchdog
    _skill_creator = skill_creator


def _require_orchestrator() -> HermesOrchestrator:
    if not _orchestrator:
        raise HTTPException(status_code=503, detail="Orchestrator not initialized")
    return _orchestrator


def _session_key(user: User, session_id: str | None) -> str:
    requested = (session_id or "default").strip() or "default"
    return f"{user.id}:{requested}"


@router.post("/message")
async def process_message(
    body: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    message = body.get("message", "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")
    session_key = _session_key(current_user, body.get("session_id"))

    result = await orchestrator.process_message(
        message=message,
        context={"session_id": session_key, "user_id": current_user.id},
    )
    if _watchdog:
        _watchdog.track_session_activity(session_key)
    return result


@router.get("/session/{session_id}")
async def get_session_state(
    session_id: str = "default",
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    summary = await orchestrator.get_session_summary(_session_key(current_user, session_id))
    return summary


@router.delete("/session/{session_id}")
async def clear_session(
    session_id: str = "default",
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    session_key = _session_key(current_user, session_id)
    await orchestrator.clear_session(session_key)
    if _watchdog:
        _watchdog.untrack_session(session_key)
    return {"status": "cleared"}


@router.get("/health")
async def orchestrator_health(current_user: User = Depends(get_current_user)):
    if not _watchdog:
        return {"status": "unknown", "detail": "Watchdog not initialized"}
    return _watchdog.get_health()


@router.get("/sessions")
async def list_active_sessions(current_user: User = Depends(get_current_user)):
    if not _watchdog:
        return {"sessions": {}}
    return {"sessions": _watchdog.get_session_states()}


@router.post("/skill/create", status_code=201)
async def create_skill(
    body: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
):
    if not _skill_creator:
        raise HTTPException(status_code=503, detail="Skill creator not initialized")
    description = body.get("description", "").strip()
    if len(description) < 10:
        raise HTTPException(status_code=400, detail="description must be at least 10 characters")
    result = await _skill_creator.create_skill_from_description(
        description=description,
        user_id=current_user.id,
        build_container=bool(body.get("build_container", False)),
    )
    if result.get("skill") is None:
        raise HTTPException(status_code=422, detail=result.get("response", "Skill creation failed"))
    return result


@router.get("/skills")
async def list_skills(current_user: User = Depends(get_current_user)):
    if not _skill_creator:
        return {"skills": []}
    skills = _skill_creator.list_skills()
    return {"skills": skills, "total": len(skills)}


@router.post("/spawn", status_code=201)
async def spawn_agent(
    body: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    goal = body.get("goal", "").strip()
    if not goal:
        raise HTTPException(status_code=400, detail="goal is required")
    toolsets = body.get("toolsets", ["file", "web"])
    role = body.get("role", "leaf")
    session_key = _session_key(current_user, body.get("session_id"))
    try:
        agent = await orchestrator.spawn_agent(
            goal=goal,
            context=body.get("context"),
            toolsets=toolsets,
            role=role,
            parent_session_id=session_key,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=429, detail=str(exc))
    return {"agent_id": agent.agent_id, "status": agent.status.value}


@router.get("/agents")
async def list_agents(
    session_id: str = Query("default"),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    session_key = _session_key(current_user, session_id)
    agents = orchestrator.agent_spawner.list_active_agents(parent_session_id=session_key)
    return {"agents": agents}


@router.get("/traces/{session_id}")
async def get_traces(
    session_id: str = "default",
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    traces = orchestrator.get_traces(_session_key(current_user, session_id), limit=limit)
    return {"traces": traces}


@router.get("/goals")
async def list_cognitive_goals(
    session_id: str = Query("default"),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    goals = orchestrator.get_cognitive_goals(_session_key(current_user, session_id))
    return {"goals": goals}


@router.post("/pipeline")
async def run_full_pipeline(
    body: dict[str, Any] = Body(...),
    current_user: User = Depends(get_current_user),
):
    orchestrator = _require_orchestrator()
    message = body.get("message", "Run full analysis")
    session_key = _session_key(current_user, body.get("session_id"))
    result = await orchestrator.process_message(
        message=message,
        context={"session_id": session_key, "user_id": current_user.id},
    )
    return result
