import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from starlette.testclient import TestClient

from app.main import app, scheduler as main_scheduler
from app.routers import research as research_router
from app.models.research_session import ResearchSession
from app.models.user import User


@pytest.fixture(autouse=True)
def reset_ws_state():
    research_router._ws_connections.clear()
    research_router._ws_lock = None
    research_router.scheduler = None
    yield
    research_router._ws_connections.clear()
    research_router._ws_lock = None
    research_router.scheduler = None


@pytest.fixture(autouse=True)
def _patch_scheduler_init_and_start():
    with (
        patch.object(main_scheduler, "start", AsyncMock(return_value=None)),
        patch("app.routers.research.init_scheduler", return_value=None),
    ):
        yield


@pytest.fixture
def ws_auth():
    user = User(id="user1", email="ws@test.com", hashed_password="x")
    with patch("app.routers.research.get_user_from_token", AsyncMock(return_value=user)):
        yield user


@pytest.fixture
def ws_db(session_record=None):
    with patch("app.routers.research.async_session") as m:
        db = AsyncMock()
        m.return_value.__aenter__.return_value = db
        result = MagicMock()
        result.scalar_one_or_none.return_value = session_record
        db.execute.return_value = result
        yield db


def _owned_session(record_id="test-id", user_id="user1"):
    return ResearchSession(id=record_id, user_id=user_id, strategy_id=None)


class TestWebSocketCommands:
    """WebSocket connection and command tests using Starlette TestClient."""

    def test_connect_and_disconnect(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        with TestClient(app) as client:
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok"):
                pass

    def test_unauthenticated_rejected(self):
        with patch("app.routers.research.get_user_from_token", AsyncMock(
            side_effect=__import__("fastapi").HTTPException(status_code=401, detail="no")
        )):
            with TestClient(app) as client:
                with pytest.raises(Exception):
                    with client.websocket_connect("/api/research/ws/research/test-id?token=bad"):
                        pass

    def test_pause(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        mock_scheduler = AsyncMock()
        with TestClient(app) as client:
            research_router.scheduler = mock_scheduler
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "pause"})
                data = ws.receive_json()
                assert data["type"] == "paused"
        mock_scheduler.stop_session.assert_awaited_once_with("test-id")

    def test_stop(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        mock_scheduler = AsyncMock()
        with TestClient(app) as client:
            research_router.scheduler = mock_scheduler
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "stop"})
                data = ws.receive_json()
                assert data["type"] == "stopped"
        mock_scheduler.stop_session.assert_awaited_once_with("test-id")

    def test_invalid_json(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        with TestClient(app) as client:
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_text("not-json")
                data = ws.receive_json()
                assert data["type"] == "error"
                assert "message" in data

    def test_pause_no_scheduler(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        with TestClient(app) as client:
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "pause"})
                data = ws.receive_json()
                assert data["type"] == "paused"

    def test_stop_no_scheduler(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        with TestClient(app) as client:
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "stop"})
                data = ws.receive_json()
                assert data["type"] == "stopped"

    def test_resume_no_scheduler(self, ws_auth, ws_db):
        ws_db.execute.return_value.scalar_one_or_none.return_value = _owned_session()
        with TestClient(app) as client:
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "resume"})
                data = ws.receive_json()
                assert data["type"] == "resumed"

    def test_resume_with_scheduler_and_db_record(self, ws_auth, ws_db):
        mock_scheduler = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = _owned_session()
        ws_db.execute.return_value = mock_result

        with TestClient(app) as client:
            research_router.scheduler = mock_scheduler
            with client.websocket_connect("/api/research/ws/research/test-id?token=tok") as ws:
                ws.send_json({"type": "resume"})
                data = ws.receive_json()
                assert data["type"] == "resumed"
        mock_scheduler.start_session.assert_awaited_once()


class TestBroadcastToSession:
    """broadcast_to_session unit tests with mocked connections."""

    async def test_single_client(self):
        mock_ws = AsyncMock()
        research_router._ws_connections["sess1"] = {mock_ws}

        await research_router.broadcast_to_session("sess1", {"type": "update", "score": 1.5})

        mock_ws.send_json.assert_awaited_once_with({"type": "update", "score": 1.5})

    async def test_multiple_clients(self):
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        research_router._ws_connections["sess1"] = {mock_ws1, mock_ws2}

        await research_router.broadcast_to_session("sess1", {"type": "update"})

        mock_ws1.send_json.assert_awaited_once_with({"type": "update"})
        mock_ws2.send_json.assert_awaited_once_with({"type": "update"})

    async def test_session_isolation(self):
        mock_a = AsyncMock()
        mock_b = AsyncMock()
        research_router._ws_connections["sess-a"] = {mock_a}
        research_router._ws_connections["sess-b"] = {mock_b}

        await research_router.broadcast_to_session("sess-a", {"type": "event_a"})

        mock_a.send_json.assert_awaited_once()
        mock_b.send_json.assert_not_awaited()

    async def test_no_connections(self):
        await research_router.broadcast_to_session("nonexistent", {"type": "test"})

    async def test_dead_connection_removal(self):
        mock_ok = AsyncMock()
        mock_dead = AsyncMock()
        mock_dead.send_json.side_effect = Exception("Closed")
        research_router._ws_connections["sess1"] = {mock_ok, mock_dead}

        await research_router.broadcast_to_session("sess1", {"type": "update"})

        assert mock_ok in research_router._ws_connections["sess1"]
        assert mock_dead not in research_router._ws_connections["sess1"]
        mock_ok.send_json.assert_awaited_once()
