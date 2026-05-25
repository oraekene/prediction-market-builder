from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
import json

from app.ai.hermes_sidecar import HermesSidecar
from app.routers.auth import get_current_user

router = APIRouter(dependencies=[Depends(get_current_user)])
ws_router = APIRouter()
hermes = HermesSidecar()


class ChatManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def handle_message(self, websocket: WebSocket, data: dict):
        content = data.get("payload", {}).get("content", "")
        user_id = data.get("payload", {}).get("user_id", "default")
        result = await hermes.process_message(content, {"user_id": user_id})
        await websocket.send_json({
            "type": "chat_response",
            "content": result.get("response", ""),
        })


chat_manager = ChatManager()


@ws_router.websocket("/ws/chat")
async def chat_endpoint(websocket: WebSocket):
    await chat_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await chat_manager.handle_message(websocket, data)
    except WebSocketDisconnect:
        chat_manager.disconnect(websocket)


@router.post("/api/chat/message")
async def chat_message(body: dict):
    content = body.get("message", "")
    user_id = body.get("user_id", "default")
    result = await hermes.process_message(content, {"user_id": user_id})
    return result


@router.get("/api/chat/history")
async def chat_history(user_id: str = "default"):
    return {"history": await hermes.get_history(user_id)}


@router.delete("/api/chat/history")
async def clear_chat_history(user_id: str = "default"):
    await hermes.clear_history(user_id)
    return {"status": "cleared"}
