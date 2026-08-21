from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.ai.repl_service import REPLService
from app.models.user import User
from app.routers.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/repl", tags=["repl"])

_repl_service: REPLService | None = None
_session_owners: dict[str, str] = {}


def init_repl(service: REPLService) -> None:
    global _repl_service
    _repl_service = service


def _require_service() -> REPLService:
    if not _repl_service:
        raise HTTPException(status_code=503, detail="REPL service not initialized")
    return _repl_service


def _owned(session_id: str, user: User) -> REPLService:
    svc = _require_service()
    if svc.get_session_state(session_id) is None:
        raise HTTPException(status_code=404, detail="Session not found")
    owner = _session_owners.get(session_id)
    if owner is None:
        _session_owners[session_id] = user.id
    elif owner != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return svc


@router.post("/create", status_code=201)
async def create_session(current_user: User = Depends(get_current_user)):
    svc = _require_service()
    result = svc.create_session()
    session_id = result["session_id"]
    _session_owners[session_id] = current_user.id
    return result


@router.post("/{session_id}/execute")
async def execute_code(
    session_id: str,
    body: dict,
    current_user: User = Depends(get_current_user),
):
    svc = _owned(session_id, current_user)
    code = body.get("code", "").strip()
    if not code:
        raise HTTPException(status_code=400, detail="code is required")
    return await svc.execute_code(session_id, code)


@router.get("/{session_id}/state")
async def get_session_state(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = _owned(session_id, current_user)
    return svc.get_session_state(session_id)


@router.delete("/{session_id}")
async def destroy_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    svc = _owned(session_id, current_user)
    deleted = svc.destroy_session(session_id)
    _session_owners.pop(session_id, None)
    return {"deleted": deleted, "session_id": session_id}
