"""Tests for portfolio API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_portfolio(client):
    resp = await client.get("/api/portfolio")
    assert resp.status_code == 200
    body = resp.json()
    assert "summary" in body
    assert "positions" in body
    assert "active_strategies" in body["summary"]
    assert "total_trades" in body["summary"]
