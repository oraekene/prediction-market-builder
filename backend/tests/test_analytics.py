"""Tests for analytics API."""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_analytics_summary(authenticated_client):
    resp = await authenticated_client.get("/api/analytics/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert "total_trades" in body
    assert "winning_trades" in body
    assert "win_rate" in body


@pytest.mark.asyncio
async def test_analytics_backtests(authenticated_client):
    resp = await authenticated_client.get("/api/analytics/backtests")
    assert resp.status_code == 200
    body = resp.json()
    assert "backtests" in body
