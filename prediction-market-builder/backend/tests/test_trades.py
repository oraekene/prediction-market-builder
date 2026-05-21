import pytest


@pytest.mark.asyncio
async def test_evaluate_trade_approved(client):
    resp = await client.post("/api/trades/evaluate", json={
        "signal": {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        "portfolio": {"current_capital": 10000, "peak_capital": 10000},
        "market": {"current_odds": 0.55},
        "risk_profile": {"min_confidence": 0.5},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is True
    assert body["suggested_size"] > 0


@pytest.mark.asyncio
async def test_evaluate_trade_rejected_low_confidence(client):
    resp = await client.post("/api/trades/evaluate", json={
        "signal": {"probability": 0.7, "confidence": 0.3, "market_odds": 0.55},
        "portfolio": {"current_capital": 10000, "peak_capital": 10000},
        "market": {"current_odds": 0.55},
        "risk_profile": {"min_confidence": 0.6},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is False
    assert "low_confidence" in body["violations"]


@pytest.mark.asyncio
async def test_evaluate_trade_rejected_max_drawdown(client):
    resp = await client.post("/api/trades/evaluate", json={
        "signal": {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        "portfolio": {"current_capital": 7000, "peak_capital": 10000},
        "market": {"current_odds": 0.55},
        "risk_profile": {"max_drawdown": 0.1},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is False
    assert "max_drawdown_reached" in body["violations"]


@pytest.mark.asyncio
async def test_create_trade_approved(client):
    resp = await client.post("/api/trades", json={
        "user_id": "user_1",
        "strategy_id": "strat_1",
        "side": "buy",
        "signal": {"probability": 0.7, "confidence": 0.8, "market_odds": 0.55},
        "portfolio": {"current_capital": 10000, "peak_capital": 10000},
        "market": {"current_odds": 0.55, "platform_market_id": "mkt-1", "platform": "polymarket"},
        "risk_profile": {"min_confidence": 0.5},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is True
    assert body["trade"] is not None
    assert body["trade"]["market_id"] == "mkt-1"
    assert body["trade"]["status"] == "pending"


@pytest.mark.asyncio
async def test_create_trade_rejected(client):
    resp = await client.post("/api/trades", json={
        "side": "buy",
        "signal": {"probability": 0.7, "confidence": 0.3, "market_odds": 0.55},
        "portfolio": {"current_capital": 7000, "peak_capital": 10000},
        "market": {"current_odds": 0.55, "platform_market_id": "mkt-1", "platform": "polymarket"},
        "risk_profile": {"max_drawdown": 0.1},
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["approved"] is False
    assert body["trade"] is None


@pytest.mark.asyncio
async def test_list_trades(client):
    resp = await client.get("/api/trades")
    assert resp.status_code == 200
    body = resp.json()
    assert "trades" in body


@pytest.mark.asyncio
async def test_list_trades_with_status(client):
    resp = await client.get("/api/trades?status=executed")
    assert resp.status_code == 200
    body = resp.json()
    assert "trades" in body
