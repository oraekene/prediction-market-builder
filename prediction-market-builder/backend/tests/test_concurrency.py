import asyncio
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_concurrent_chat_messages(authenticated_client):
    from unittest.mock import AsyncMock, patch
    with patch("app.routers.chat.hermes.process_message", new=AsyncMock(return_value={"response": "mock"})):
        async def send_message(i):
            return await authenticated_client.post("/api/chat/message", json={
                "message": f"Concurrent message {i}",
            })

        results = await asyncio.gather(*[send_message(i) for i in range(10)])
        for resp in results:
            assert resp.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_strategy_creations(authenticated_client):
    async def create_strategy(i):
        return await authenticated_client.post("/api/strategies", json={"name": f"Concurrent {i}"})

    results = await asyncio.gather(*[create_strategy(i) for i in range(5)])
    for resp in results:
        assert resp.status_code == 201
        assert "id" in resp.json()


@pytest.mark.asyncio
async def test_concurrent_repl_sessions(authenticated_client):
    from app.routers import repl as repl_router
    from app.ai.repl_service import REPLService
    repl_router.init_repl(REPLService())

    async def create_session():
        return await authenticated_client.post("/ai/repl/create")

    results = await asyncio.gather(*[create_session() for _ in range(5)])
    for resp in results:
        assert resp.status_code == 201


@pytest.mark.asyncio
async def test_rapid_market_requests(authenticated_client):
    async def fetch_markets():
        return await authenticated_client.get("/api/markets")

    results = await asyncio.gather(*[fetch_markets() for _ in range(5)])
    for resp in results:
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_rapid_state_transitions(authenticated_client):
    import httpx
    create_resp = await authenticated_client.post("/api/strategies", json={"name": "StateTest"})
    sid = create_resp.json()["id"]

    async def deploy():
        return await authenticated_client.post(f"/api/strategies/{sid}/deploy")

    results = await asyncio.gather(deploy(), deploy(), deploy())
    assert results[0].status_code == 200
    assert results[0].json()["status"] == "active"


@pytest.mark.asyncio
async def test_concurrent_search_requests(authenticated_client):
    async def search():
        return await authenticated_client.post("/api/v1/search", json={"query": "test"})

    results = await asyncio.gather(*[search() for _ in range(3)])
    for resp in results:
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_market_and_search(authenticated_client):
    async def get_markets():
        return await authenticated_client.get("/api/markets")

    async def search():
        return await authenticated_client.post("/api/v1/search", json={"query": "test"})

    results = await asyncio.gather(get_markets(), search(), get_markets(), search())
    for resp in results:
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_concurrent_auth_and_strategy(authenticated_client):
    async def list_strategies():
        return await authenticated_client.get("/api/strategies")

    async def create_strategy():
        return await authenticated_client.post("/api/strategies", json={"name": "Mixed"})

    results = await asyncio.gather(list_strategies(), create_strategy(), list_strategies(), create_strategy())
    for resp in results:
        assert resp.status_code in (200, 201)
