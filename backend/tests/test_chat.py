import pytest
from unittest.mock import AsyncMock, patch

from app.main import app


@pytest.fixture(autouse=True)
def _patch_hermes():
    with patch("app.routers.chat.hermes.process_message", new=AsyncMock(return_value={
        "response": "Mock response",
        "type": "mock",
    })):
        yield


@pytest.mark.asyncio
async def test_chat_message(authenticated_client):
    resp = await authenticated_client.post("/api/chat/message", json={
        "message": "What is the current market sentiment?",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data


@pytest.mark.asyncio
async def test_chat_message_empty(authenticated_client):
    resp = await authenticated_client.post("/api/chat/message", json={
        "message": "",
    })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_chat_message_no_body(authenticated_client):
    resp = await authenticated_client.post("/api/chat/message", json={})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_chat_history(authenticated_client):
    with patch("app.routers.chat.hermes.get_history", new=AsyncMock(return_value=[])):
        resp = await authenticated_client.get("/api/chat/history?user_id=test-user")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data


@pytest.mark.asyncio
async def test_chat_history_default_user(authenticated_client):
    with patch("app.routers.chat.hermes.get_history", new=AsyncMock(return_value=[])):
        resp = await authenticated_client.get("/api/chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert "history" in data


@pytest.mark.asyncio
async def test_clear_chat_history(authenticated_client):
    with patch("app.routers.chat.hermes.clear_history", new=AsyncMock(return_value=None)):
        resp = await authenticated_client.delete("/api/chat/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "cleared"
