from __future__ import annotations

import logging

from fastapi import APIRouter

from app.ai.repl_service import REPLService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/repl", tags=["repl"])

_repl_service: REPLService | None = None


def init_repl(service: REPLService) -> None:
    global _repl_service
    _repl_service = service


@router.post("/create")
async def create_session():
    if not _repl_service:
        return {"error": "REPL service not initialized"}
    return _repl_service.create_session()


@router.post("/{session_id}/execute")
async def execute_code(session_id: str, body: dict):
    if not _repl_service:
        return {"error": "REPL service not initialized"}
    code = body.get("code", "").strip()
    if not code:
        return {"error": "code is required"}
    return await _repl_service.execute_code(session_id, code)


@router.get("/{session_id}/state")
async def get_session_state(session_id: str):
    if not _repl_service:
        return {"error": "REPL service not initialized"}
    state = _repl_service.get_session_state(session_id)
    if state is None:
        return {"error": f"Session '{session_id}' not found or expired"}
    return state


@router.delete("/{session_id}")
async def destroy_session(session_id: str):
    if not _repl_service:
        return {"error": "REPL service not initialized"}
    deleted = _repl_service.destroy_session(session_id)
    return {"deleted": deleted, "session_id": session_id}
