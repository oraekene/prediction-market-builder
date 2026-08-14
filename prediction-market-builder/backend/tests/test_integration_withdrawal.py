"""Integration + E2E tests for Task 5: Withdrawal & Safe Wallet System.

Tests safe wallet CRUD, transfer flow, withdrawal strategies,
balance calculations, and authorization through the full FastAPI stack.
"""
import pytest
from httpx import AsyncClient


async def _register_user(client: AsyncClient, email: str) -> str:
    """Register a user and return the auth token."""
    reg = await client.post("/api/auth/register", json={
        "email": email, "password": "strongpass123",
    })
    assert reg.status_code == 200
    return reg.json()["access_token"]


class TestWithdrawalWalletCRUD:
    """Tests for safe wallet create / read / list endpoints."""

    @pytest.mark.asyncio
    async def test_create_wallet(self, client: AsyncClient):
        token = await _register_user(client, "wallet-create@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/wallets", headers=headers, json={
            "name": "Main USDC Vault",
            "currency": "USDC",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Main USDC Vault"
        assert data["currency"] == "USDC"
        assert data["balance"] == 0.0
        assert data["is_disconnected"] is True
        assert data["created_at"] is not None

    @pytest.mark.asyncio
    async def test_list_wallets_empty(self, client: AsyncClient):
        token = await _register_user(client, "wallet-list-empty@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/wallets", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_wallets_after_creation(self, client: AsyncClient):
        token = await _register_user(client, "wallet-list-after@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/withdrawal/wallets", headers=headers, json={
            "name": "Wallet A", "currency": "USDC",
        })
        await client.post("/api/withdrawal/wallets", headers=headers, json={
            "name": "Wallet B", "currency": "USDT",
        })

        resp = await client.get("/api/withdrawal/wallets", headers=headers)
        assert resp.status_code == 200
        wallets = resp.json()
        assert len(wallets) == 2
        names = {w["name"] for w in wallets}
        assert names == {"Wallet A", "Wallet B"}

    @pytest.mark.asyncio
    async def test_get_wallet_by_id(self, client: AsyncClient):
        token = await _register_user(client, "wallet-get@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/wallets", headers=headers, json={
            "name": "Get Me", "currency": "USDC",
        })
        wallet_id = create.json()["id"]

        resp = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == wallet_id
        assert resp.json()["name"] == "Get Me"

    @pytest.mark.asyncio
    async def test_get_wallet_not_found(self, client: AsyncClient):
        token = await _register_user(client, "wallet-404@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/wallets/nonexistent-id", headers=headers)
        assert resp.status_code == 404


class TestWithdrawalBalance:
    """Tests for the balance aggregation endpoint."""

    @pytest.mark.asyncio
    async def test_balance_empty(self, client: AsyncClient):
        token = await _register_user(client, "balance-empty@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/balance", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_wallets"] == 0
        assert data["total_usd_equivalent"] == 0.0
        assert data["wallets"] == []

    @pytest.mark.asyncio
    async def test_balance_after_transfer(self, client: AsyncClient):
        token = await _register_user(client, "balance-after@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 150.0, "currency": "USDC",
        })
        await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 50.0, "currency": "USDT",
        })

        resp = await client.get("/api/withdrawal/balance", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_wallets"] == 2
        assert data["balances_by_currency"]["USDC"] == 150.0
        assert data["balances_by_currency"]["USDT"] == 50.0
        assert data["total_usd_equivalent"] == 200.0


class TestWithdrawalTransfer:
    """Tests for the manual transfer endpoint."""

    @pytest.mark.asyncio
    async def test_transfer_funds(self, client: AsyncClient):
        token = await _register_user(client, "transfer-basic@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 250.0,
            "currency": "USDC",
            "source": "profits",
            "trigger_type": "manual",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["amount"] == 250.0
        assert data["currency"] == "USDC"
        assert data["new_balance"] == 250.0
        assert "record_id" in data
        assert "wallet_id" in data

    @pytest.mark.asyncio
    async def test_transfer_cumulative_balance(self, client: AsyncClient):
        token = await _register_user(client, "transfer-cumulative@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp1 = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 100.0, "currency": "USDC",
        })
        assert resp1.json()["new_balance"] == 100.0

        resp2 = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 75.50, "currency": "USDC",
        })
        assert resp2.json()["new_balance"] == 175.5

    @pytest.mark.asyncio
    async def test_transfer_zero_amount_fails(self, client: AsyncClient):
        token = await _register_user(client, "transfer-zero@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 0, "currency": "USDC",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_negative_amount_fails(self, client: AsyncClient):
        token = await _register_user(client, "transfer-negative@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": -50.0, "currency": "USDC",
        })
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_transfer_different_currencies(self, client: AsyncClient):
        token = await _register_user(client, "transfer-multi@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        usdc = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 100.0, "currency": "USDC",
        })
        usdt = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 200.0, "currency": "USDT",
        })

        assert usdc.json()["currency"] == "USDC"
        assert usdt.json()["currency"] == "USDT"

        balance = await client.get("/api/withdrawal/balance", headers=headers)
        assert balance.json()["total_wallets"] == 2


class TestWithdrawalHistory:
    """Tests for the withdrawal history endpoint."""

    @pytest.mark.asyncio
    async def test_history_empty(self, client: AsyncClient):
        token = await _register_user(client, "history-empty@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/history", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_history_after_transfers(self, client: AsyncClient):
        token = await _register_user(client, "history-after@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 100.0, "currency": "USDC",
        })
        await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 50.0, "currency": "USDT",
        })

        resp = await client.get("/api/withdrawal/history", headers=headers)
        assert resp.status_code == 200
        records = resp.json()
        assert len(records) == 2
        for record in records:
            assert "id" in record
            assert "wallet_id" in record
            assert "amount" in record
            assert "currency" in record
            assert "source" in record
            assert "trigger_type" in record
            assert record["status"] == "completed"


class TestWithdrawalStrategiesCRUD:
    """Tests for withdrawal strategy CRUD endpoints."""

    @pytest.mark.asyncio
    async def test_create_strategy(self, client: AsyncClient):
        token = await _register_user(client, "strategy-create@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Profit-Take 50%",
            "description": "Withdraw 50% when profit hits threshold",
            "steps": [
                {
                    "id": "step-1",
                    "condition": {"type": "profit_threshold", "threshold": 500},
                    "action": {"type": "withdraw_pct", "pct": 50},
                    "once": True,
                }
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["name"] == "Profit-Take 50%"
        assert data["is_active"] is True
        assert len(data["steps"]) == 1
        assert data["steps"][0]["id"] == "step-1"

    @pytest.mark.asyncio
    async def test_list_strategies_empty(self, client: AsyncClient):
        token = await _register_user(client, "strategy-list-empty@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/strategies", headers=headers)
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_strategies_after_creation(self, client: AsyncClient):
        token = await _register_user(client, "strategy-list-after@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Strategy A", "steps": [],
        })
        await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Strategy B", "steps": [],
        })

        resp = await client.get("/api/withdrawal/strategies", headers=headers)
        assert resp.status_code == 201
        strategies = resp.json()
        assert len(strategies) == 2
        names = {s["name"] for s in strategies}
        assert names == {"Strategy A", "Strategy B"}

    @pytest.mark.asyncio
    async def test_get_strategy_by_id(self, client: AsyncClient):
        token = await _register_user(client, "strategy-get@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Get Me",
            "steps": [{"id": "s1", "condition": {"type": "profit_pct", "target_pct": 10}, "action": {"type": "withdraw_fixed", "amount": 200}}],
        })
        strategy_id = create.json()["id"]

        resp = await client.get(f"/api/withdrawal/strategies/{strategy_id}", headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["id"] == strategy_id
        assert data["name"] == "Get Me"
        assert data["step_states"] == {}

    @pytest.mark.asyncio
    async def test_get_strategy_not_found(self, client: AsyncClient):
        token = await _register_user(client, "strategy-404@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.get("/api/withdrawal/strategies/nonexistent-id", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_update_strategy(self, client: AsyncClient):
        token = await _register_user(client, "strategy-update@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Original Name",
            "description": "Original desc",
            "steps": [],
        })
        strategy_id = create.json()["id"]

        resp = await client.put(f"/api/withdrawal/strategies/{strategy_id}", headers=headers, json={
            "name": "Updated Name",
            "description": "Updated desc",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Updated Name"
        assert data["description"] == "Updated desc"

    @pytest.mark.asyncio
    async def test_update_strategy_steps(self, client: AsyncClient):
        token = await _register_user(client, "strategy-update-steps@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Steps Test", "steps": [],
        })
        strategy_id = create.json()["id"]

        new_steps = [
            {"id": "step-1", "condition": {"type": "profit_threshold", "threshold": 100}, "action": {"type": "withdraw_fixed", "amount": 50}},
        ]
        resp = await client.put(f"/api/withdrawal/strategies/{strategy_id}", headers=headers, json={
            "steps": new_steps,
        })
        assert resp.status_code == 201
        assert resp.json()["steps"] == new_steps

    @pytest.mark.asyncio
    async def test_delete_strategy(self, client: AsyncClient):
        token = await _register_user(client, "strategy-delete@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Delete Me", "steps": [],
        })
        strategy_id = create.json()["id"]

        resp = await client.delete(f"/api/withdrawal/strategies/{strategy_id}", headers=headers)
        assert resp.status_code == 201
        assert resp.json()["status"] == "deleted"

        # Verify it's gone
        get_resp = await client.get(f"/api/withdrawal/strategies/{strategy_id}", headers=headers)
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_strategy_not_found(self, client: AsyncClient):
        token = await _register_user(client, "strategy-delete-404@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.delete("/api/withdrawal/strategies/nonexistent-id", headers=headers)
        assert resp.status_code == 404


class TestWithdrawalStrategyEvaluation:
    """Tests for strategy evaluation and toggling."""

    @pytest.mark.asyncio
    async def test_evaluate_strategy(self, client: AsyncClient):
        token = await _register_user(client, "strategy-eval@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Eval Strategy",
            "steps": [
                {"id": "step-1", "condition": {"type": "profit_threshold", "threshold": 500}, "action": {"type": "withdraw_pct", "pct": 25}, "once": True},
                {"id": "step-2", "condition": {"type": "profit_pct", "target_pct": 10}, "action": {"type": "withdraw_fixed", "amount": 100}},
            ],
        })
        strategy_id = create.json()["id"]

        resp = await client.post(f"/api/withdrawal/strategies/{strategy_id}/evaluate", headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["strategy_id"] == strategy_id
        assert data["name"] == "Eval Strategy"
        assert data["is_active"] is True
        assert data["total_steps"] == 2
        assert len(data["triggered_steps"]) == 2
        assert data["triggered_steps"][0]["status"] == "pending"
        assert data["triggered_steps"][1]["status"] == "pending"

    @pytest.mark.asyncio
    async def test_evaluate_strategy_not_found(self, client: AsyncClient):
        token = await _register_user(client, "strategy-eval-404@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/strategies/nonexistent-id/evaluate", headers=headers)
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_toggle_strategy(self, client: AsyncClient):
        token = await _register_user(client, "strategy-toggle@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Toggle Strategy", "steps": [],
        })
        strategy_id = create.json()["id"]
        assert create.json()["is_active"] is True

        resp = await client.post(f"/api/withdrawal/strategies/{strategy_id}/toggle", headers=headers)
        assert resp.status_code == 201
        data = resp.json()
        assert data["is_active"] is False

        resp2 = await client.post(f"/api/withdrawal/strategies/{strategy_id}/toggle", headers=headers)
        assert resp2.status_code == 200
        assert resp2.json()["is_active"] is True

    @pytest.mark.asyncio
    async def test_toggle_strategy_not_found(self, client: AsyncClient):
        token = await _register_user(client, "strategy-toggle-404@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        resp = await client.post("/api/withdrawal/strategies/nonexistent-id/toggle", headers=headers)
        assert resp.status_code == 404


class TestWithdrawalUnauthorizedAccess:
    """Tests that endpoints reject unauthenticated requests."""

    @pytest.mark.asyncio
    async def test_unauthorized_wallets(self, client: AsyncClient):
        resp = await client.get("/api/withdrawal/wallets")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_create_wallet(self, client: AsyncClient):
        resp = await client.post("/api/withdrawal/wallets", json={
            "name": "No Auth", "currency": "USDC",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_balance(self, client: AsyncClient):
        resp = await client.get("/api/withdrawal/balance")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_transfer(self, client: AsyncClient):
        resp = await client.post("/api/withdrawal/transfer", json={
            "amount": 100.0, "currency": "USDC",
        })
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_history(self, client: AsyncClient):
        resp = await client.get("/api/withdrawal/history")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_strategies(self, client: AsyncClient):
        resp = await client.get("/api/withdrawal/strategies")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_unauthorized_create_strategy(self, client: AsyncClient):
        resp = await client.post("/api/withdrawal/strategies", json={
            "name": "No Auth", "steps": [],
        })
        assert resp.status_code == 401


class TestWithdrawalCrossUserIsolation:
    """Tests that users cannot access each other's wallets or strategies."""

    @pytest.mark.asyncio
    async def test_user_b_cannot_see_user_a_wallets(self, client: AsyncClient):
        token_a = await _register_user(client, "iso-a-wallet@test.com")
        token_b = await _register_user(client, "iso-b-wallet@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create = await client.post("/api/withdrawal/wallets", headers=headers_a, json={
            "name": "A's Wallet", "currency": "USDC",
        })
        wallet_id = create.json()["id"]

        # User A can see it
        get_a = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=headers_a)
        assert get_a.status_code == 200

        # User B cannot see it
        get_b = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=headers_b)
        assert get_b.status_code == 404

        # User B's list is empty
        list_b = await client.get("/api/withdrawal/wallets", headers=headers_b)
        assert list_b.json() == []

    @pytest.mark.asyncio
    async def test_user_b_cannot_see_user_a_strategies(self, client: AsyncClient):
        token_a = await _register_user(client, "iso-a-strat@test.com")
        token_b = await _register_user(client, "iso-b-strat@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers_a, json={
            "name": "A's Strategy", "steps": [],
        })
        strategy_id = create.json()["id"]

        # User A can see it
        get_a = await client.get(f"/api/withdrawal/strategies/{strategy_id}", headers=headers_a)
        assert get_a.status_code == 201

        # User B cannot see it
        get_b = await client.get(f"/api/withdrawal/strategies/{strategy_id}", headers=headers_b)
        assert get_b.status_code == 404

        # User B's list is empty
        list_b = await client.get("/api/withdrawal/strategies", headers=headers_b)
        assert list_b.json() == []

    @pytest.mark.asyncio
    async def test_user_b_cannot_update_user_a_strategy(self, client: AsyncClient):
        token_a = await _register_user(client, "iso-a-upd@test.com")
        token_b = await _register_user(client, "iso-b-upd@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers_a, json={
            "name": "A's Strategy", "steps": [],
        })
        strategy_id = create.json()["id"]

        resp = await client.put(f"/api/withdrawal/strategies/{strategy_id}", headers=headers_b, json={
            "name": "Hacked",
        })
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_user_b_cannot_delete_user_a_strategy(self, client: AsyncClient):
        token_a = await _register_user(client, "iso-a-del@test.com")
        token_b = await _register_user(client, "iso-b-del@test.com")
        headers_a = {"Authorization": f"Bearer {token_a}"}
        headers_b = {"Authorization": f"Bearer {token_b}"}

        create = await client.post("/api/withdrawal/strategies", headers=headers_a, json={
            "name": "A's Strategy", "steps": [],
        })
        strategy_id = create.json()["id"]

        resp = await client.delete(f"/api/withdrawal/strategies/{strategy_id}", headers=headers_b)
        assert resp.status_code == 404

        # Verify still exists for A
        get_a = await client.get(f"/api/withdrawal/strategies/{strategy_id}", headers=headers_a)
        assert get_a.status_code == 201


class TestWithdrawalFullWorkflow:
    """End-to-end: create wallet -> transfer -> verify balance -> verify history."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, client: AsyncClient):
        token = await _register_user(client, "workflow@test.com")
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a wallet
        wallet = await client.post("/api/withdrawal/wallets", headers=headers, json={
            "name": "Trading Vault", "currency": "USDC",
        })
        assert wallet.status_code == 200
        wallet_id = wallet.json()["id"]

        # 2. Verify wallet appears in list
        wallets = await client.get("/api/withdrawal/wallets", headers=headers)
        assert len(wallets.json()) == 1
        assert wallets.json()[0]["id"] == wallet_id

        # 3. Transfer funds
        t1 = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 500.0, "currency": "USDC",
        })
        assert t1.json()["success"] is True
        assert t1.json()["new_balance"] == 500.0

        t2 = await client.post("/api/withdrawal/transfer", headers=headers, json={
            "amount": 250.0, "currency": "USDC",
        })
        assert t2.json()["new_balance"] == 750.0

        # 4. Verify balance
        balance = await client.get("/api/withdrawal/balance", headers=headers)
        assert balance.json()["total_usd_equivalent"] == 750.0

        # 5. Verify history has 2 records
        history = await client.get("/api/withdrawal/history", headers=headers)
        records = history.json()
        assert len(records) == 2
        amounts = {r["amount"] for r in records}
        assert amounts == {500.0, 250.0}
        for r in records:
            assert r["status"] == "completed"

        # 6. Create a strategy
        strat = await client.post("/api/withdrawal/strategies", headers=headers, json={
            "name": "Auto-Transfer",
            "steps": [
                {"id": "s1", "condition": {"type": "profit_threshold", "threshold": 1000}, "action": {"type": "withdraw_pct", "pct": 10}},
            ],
        })
        assert strat.status_code == 201
        strat_id = strat.json()["id"]

        # 7. Evaluate strategy
        eval_resp = await client.post(f"/api/withdrawal/strategies/{strat_id}/evaluate", headers=headers)
        assert eval_resp.json()["total_steps"] == 1

        # 8. Toggle strategy off
        toggle = await client.post(f"/api/withdrawal/strategies/{strat_id}/toggle", headers=headers)
        assert toggle.json()["is_active"] is False

        # 9. Delete strategy
        delete = await client.delete(f"/api/withdrawal/strategies/{strat_id}", headers=headers)
        assert delete.json()["status"] == "deleted"

        # 10. Verify strategy list is empty
        list_strats = await client.get("/api/withdrawal/strategies", headers=headers)
        assert list_strats.json() == []
