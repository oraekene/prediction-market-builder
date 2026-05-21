"""Tests for analytics API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_analytics_summary(client):
    resp = await client.get("/api/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_trades" in body
    assert "winning_trades" in body
    assert "win_rate" in body


@pytest.mark.asyncio
async def test_analytics_backtests(client):
    resp = await client.get("/api/analytics/backtests")
    assert resp.status_code == 200
    body = resp.json()
    assert "backtests" in body
