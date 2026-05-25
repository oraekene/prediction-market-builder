import pytest


@pytest.mark.asyncio
async def test_risk_summary_endpoint(authenticated_client):
    resp = await authenticated_client.get("/api/risk/summary")
    assert resp.status_code == 200
    data = resp.json()
    assert "var_95" in data
    assert "es_95" in data
    assert "max_drawdown" in data
    assert "current_drawdown" in data
    assert "concentration" in data
    assert "portfolio_volatility" in data


@pytest.mark.asyncio
async def test_risk_var_endpoint(authenticated_client):
    resp = await authenticated_client.get("/api/risk/var?confidence=0.95")
    assert resp.status_code == 200
    data = resp.json()
    assert "historical" in data
    assert "parametric" in data
    assert "confidence" in data


@pytest.mark.asyncio
async def test_risk_correlation_endpoint(authenticated_client):
    resp = await authenticated_client.get("/api/risk/correlation")
    assert resp.status_code == 200
    data = resp.json()
    assert "pairs" in data


@pytest.mark.asyncio
async def test_risk_drawdown_endpoint(authenticated_client):
    resp = await authenticated_client.get("/api/risk/drawdown")
    assert resp.status_code == 200
    data = resp.json()
    assert "current_drawdown" in data
    assert "peak_capital" in data
    assert "current_capital" in data


@pytest.mark.asyncio
async def test_risk_portfolio_endpoint(authenticated_client):
    resp = await authenticated_client.get("/api/risk/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "positions" in data
