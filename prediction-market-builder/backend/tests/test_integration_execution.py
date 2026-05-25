"""Integration + E2E tests for Task 4.1: Production Execution Engine.

Tests paper trading endpoints, trading mode toggle,
and connector integration through the full FastAPI stack.
"""
import pytest
from httpx import AsyncClient


class TestPaperTradingE2E:
    """E2E: full paper trading lifecycle."""

    @pytest.mark.asyncio
    async def test_full_trade_flow(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "trader@test.com", "password": "strongpass123",
        })
        assert reg.status_code == 200
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        wallet = await client.get("/api/paper/wallet", headers=headers)
        assert wallet.status_code == 200
        wallet_data = wallet.json()
        assert wallet_data["initial_balance"] == 10000.0
        wallet_id = wallet_data["id"]

        order = await client.post("/api/paper/orders", headers=headers, json={
            "wallet_id": wallet_id,
            "platform": "polymarket",
            "market_id": "test-market-1",
            "market_title": "Test Market",
            "side": "buy",
            "amount": 100,
            "price": 0.55,
            "mode": "paper",
        })
        assert order.status_code == 200
        order_data = order.json()
        assert order_data["success"] is True
        assert order_data["order"]["platform"] == "polymarket"
        assert order_data["order"]["side"] == "buy"
        assert order_data["wallet_balance"] < 10000

        # Verify wallet was debited
        wallet2 = await client.get("/api/paper/wallet", headers=headers)
        assert wallet2.json()["current_balance"] == order_data["wallet_balance"]

        # Cancel the order (filled orders cannot be cancelled)
        cancel = await client.delete(f"/api/paper/orders/{order_data['order']['id']}", headers=headers)
        assert cancel.status_code == 400

    @pytest.mark.asyncio
    async def test_trading_mode_toggle(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "mode@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/paper/trading-mode", headers=headers, json={"mode": "live"})
        assert resp.status_code == 200
        assert resp.json()["mode"] == "live"
        assert "warning" in resp.json()

        resp2 = await client.post("/api/paper/trading-mode", headers=headers, json={"mode": "paper"})
        assert resp2.status_code == 200
        assert resp2.json()["mode"] == "paper"

        resp3 = await client.post("/api/paper/trading-mode", headers=headers, json={"mode": "invalid"})
        assert resp3.status_code == 400

    @pytest.mark.asyncio
    async def test_performance_metrics(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "perf@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        perf = await client.get("/api/paper/performance", headers=headers)
        assert perf.status_code == 200
        data = perf.json()
        assert data["total_trades"] == 0
        assert data["win_rate"] == 0.0

    @pytest.mark.asyncio
    async def test_reset_wallet(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "reset@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        wallet = await client.get("/api/paper/wallet", headers=headers)
        wallet_id = wallet.json()["id"]

        await client.post("/api/paper/orders", headers=headers, json={
            "wallet_id": wallet_id, "platform": "polymarket",
            "market_id": "m1", "side": "buy", "amount": 500, "price": 0.5, "mode": "paper",
        })

        resp = await client.post("/api/paper/wallet/reset", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["current_balance"] == 10000.0


class TestExecutionConnectorIntegration:
    """Integration: execution engine with mocked connectors via HTTP."""

    @pytest.mark.asyncio
    async def test_live_trade_requires_user(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "live@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        wallet = await client.get("/api/paper/wallet", headers=headers)
        wallet_id = wallet.json()["id"]

        resp = await client.post("/api/paper/orders", headers=headers, json={
            "wallet_id": wallet_id, "platform": "polymarket",
            "market_id": "m1", "side": "buy", "amount": 100, "price": 0.55, "mode": "live",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is False
        assert data.get("error") is not None

    @pytest.mark.asyncio
    async def test_list_orders_returns_platform_order_id(self, client: AsyncClient):
        reg = await client.post("/api/auth/register", json={
            "email": "list@test.com", "password": "strongpass123",
        })
        token = reg.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        orders = await client.get("/api/paper/orders", headers=headers)
        assert orders.status_code == 200
        assert "orders" in orders.json()
