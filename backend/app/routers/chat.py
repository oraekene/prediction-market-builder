from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
import json

from app.ai.hermes_sidecar import HermesSidecar
from app.models.user import User
from app.routers.auth import get_current_user, get_user_from_token

router = APIRouter(prefix="/api/chat", tags=["chat"], dependencies=[Depends(get_current_user)])
ws_router = APIRouter()
hermes = HermesSidecar()


class ChatManager:
    def __init__(self):
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, websocket: WebSocket, user_id: str):
        conns = self.active_connections.get(user_id)
        if conns and websocket in conns:
            conns.remove(websocket)

    async def handle_message(self, websocket: WebSocket, data: dict, user_id: str):
        content = data.get("payload", {}).get("content", "")
        result = await hermes.process_message(content, {"user_id": user_id})
        await websocket.send_json({
            "type": "chat_response",
            "content": result.get("response", ""),
        })


chat_manager = ChatManager()


@ws_router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    try:
        user = await get_user_from_token(token)
    except HTTPException:
        await websocket.close(code=4401)
        return

    await chat_manager.connect(websocket, user.id)
    try:
        while True:
            data = await websocket.receive_json()
            await chat_manager.handle_message(websocket, data, user.id)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, user.id)


@router.post("/message")
async def chat_message(
    body: dict,
    current_user: User = Depends(get_current_user),
):
    content = body.get("message", "")
    if not content.strip():
        raise HTTPException(status_code=400, detail="message is required")
    result = await hermes.process_message(content, {"user_id": current_user.id})
    return result


@router.get("/history")
async def chat_history(current_user: User = Depends(get_current_user)):
    return {"history": await hermes.get_history(current_user.id)}


@router.delete("/history")
async def clear_chat_history(current_user: User = Depends(get_current_user)):
    await hermes.clear_history(current_user.id)
    return {"status": "cleared"}
