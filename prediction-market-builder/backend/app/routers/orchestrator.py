from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.ai.hermes_orchestrator import HermesOrchestrator
from app.ai.skill_creator import SkillCreator
from app.ai.watchdog import WatchdogService

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


@router.post("/message")
async def process_message(
    body: dict[str, Any] = Body(...),
):
    if not _orchestrator:
        return {"error": "Orchestrator not initialized"}
    message = body.get("message", "").strip()
    if not message:
        return {"error": "message is required"}
    session_id = body.get("session_id", "default")
    user_id = body.get("user_id", "default")

    result = await _orchestrator.process_message(
        message=message,
        context={"session_id": session_id, "user_id": user_id},
    )
    if _watchdog:
        _watchdog.track_session_activity(session_id)
    return result


@router.get("/session/{session_id}")
async def get_session_state(session_id: str = "default"):
    if not _orchestrator:
        return {"error": "Orchestrator not initialized"}
    summary = await _orchestrator.get_session_summary(session_id)
    return summary


@router.delete("/session/{session_id}")
async def clear_session(session_id: str = "default"):
    if not _orchestrator:
        return {"error": "Orchestrator not initialized"}
    await _orchestrator.clear_session(session_id)
    if _watchdog:
        _watchdog.untrack_session(session_id)
    return {"status": "cleared"}


@router.get("/health")
async def orchestrator_health():
    if not _watchdog:
        return {"status": "unknown", "detail": "Watchdog not initialized"}
    return _watchdog.get_health()


@router.get("/sessions")
async def list_active_sessions():
    if not _watchdog:
        return {"sessions": {}}
    return {"sessions": _watchdog.get_session_states()}


@router.post("/skill/create")
async def create_skill(
    body: dict[str, Any] = Body(...),
):
    if not _skill_creator:
        return {"error": "Skill creator not initialized"}
    description = body.get("description", "").strip()
    if len(description) < 10:
        return {"error": "description must be at least 10 characters"}
    user_id = body.get("user_id", "default")
    result = await _skill_creator.create_skill_from_description(
        description=description,
        user_id=user_id,
    )
    return result


@router.get("/skills")
async def list_skills():
    if not _skill_creator:
        return {"skills": []}
    skills = _skill_creator.list_skills()
    return {"skills": skills, "total": len(skills)}


@router.post("/spawn")
async def spawn_agent(body: dict[str, Any] = Body(...)):
    if not _orchestrator:
        return {"error": "Orchestrator not initialized"}
    goal = body.get("goal", "").strip()
    if not goal:
        return {"error": "goal is required"}
    toolsets = body.get("toolsets", ["file", "web"])
    role = body.get("role", "leaf")
    session_id = body.get("session_id", "default")

    result = await _orchestrator._handle_spawn_agent(
        message=goal,
        context={"session_id": session_id, "toolsets": toolsets, "role": role},
        memory_context=None,
        session=_orchestrator._init_session(session_id),
    )
    return result


@router.get("/agents")
async def list_agents(session_id: str = Query("default")):
    if not _orchestrator:
        return {"agents": []}
    agents = _orchestrator.agent_spawner.list_active_agents(parent_session_id=session_id)
    return {"agents": agents}


@router.get("/goals")
async def list_cognitive_goals(session_id: str = Query("default")):
    if not _orchestrator:
        return {"goals": []}
    goals = _orchestrator.get_cognitive_goals(session_id)
    return {"goals": goals}


@router.post("/pipeline")
async def run_full_pipeline(
    body: dict[str, Any] = Body(...),
):
    if not _orchestrator:
        return {"error": "Orchestrator not initialized"}
    message = body.get("message", "Run full analysis")
    session_id = body.get("session_id", "default")
    result = await _orchestrator.process_message(
        message=message,
        context={"session_id": session_id, "user_id": body.get("user_id", "default")},
    )
    return result
