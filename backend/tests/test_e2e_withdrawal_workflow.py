"""End-to-end tests for the complete auto-profit protection workflow.

Covers full lifecycle, multi-wallet, strategy steps, cross-user isolation,
and a full auto-profit protection simulation through the HTTP API.
"""
import pytest
from httpx import AsyncClient


async def _register(client: AsyncClient, email: str) -> str:
    resp = await client.post("/api/auth/register", json={
        "email": email, "password": "strongpass123",
    })
    assert resp.status_code == 200
    return resp.json()["access_token"]


async def _headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ── 1. Full withdrawal lifecycle ───────────────────────────────────────


@pytest.mark.asyncio
async def test_full_withdrawal_lifecycle(client: AsyncClient):
    """Register user -> create safe wallet -> transfer funds -> verify balance
    -> verify history -> create strategy -> evaluate -> toggle -> delete strategy
    -> verify wallet still exists."""
    token = await _register(client, "lifecycle@test.com")
    h = await _headers(token)

    # Register and create wallet
    wallet = await client.post("/api/withdrawal/wallets", headers=h, json={
        "name": "Lifecycle Vault", "currency": "USDC",
    })
    assert wallet.status_code == 200
    wallet_id = wallet.json()["id"]
    assert wallet.json()["balance"] == 0.0

    # Transfer funds
    t1 = await client.post("/api/withdrawal/transfer", headers=h, json={
        "amount": 300.0, "currency": "USDC",
    })
    assert t1.status_code == 200
    assert t1.json()["success"] is True
    assert t1.json()["new_balance"] == 300.0

    t2 = await client.post("/api/withdrawal/transfer", headers=h, json={
        "amount": 200.0, "currency": "USDC",
    })
    assert t2.status_code == 200
    assert t2.json()["new_balance"] == 500.0

    # Verify balance
    balance = await client.get("/api/withdrawal/balance", headers=h)
    assert balance.status_code == 200
    assert balance.json()["total_usd_equivalent"] == 500.0
    assert balance.json()["total_wallets"] == 1

    # Verify history
    history = await client.get("/api/withdrawal/history", headers=h)
    assert history.status_code == 200
    records = history.json()
    assert len(records) == 2
    amounts = {r["amount"] for r in records}
    assert amounts == {300.0, 200.0}
    for r in records:
        assert r["status"] == "completed"
        assert r["currency"] == "USDC"

    # Create withdrawal strategy
    strat = await client.post("/api/withdrawal/strategies", headers=h, json={
        "name": "Lifecycle Strategy",
        "description": "Auto-profit protection lifecycle test",
        "steps": [
            {
                "id": "step-1",
                "condition": {"type": "profit_threshold", "threshold": 500},
                "action": {"type": "withdraw_pct", "pct": 25},
                "once": True,
            }
        ],
    })
    assert strat.status_code == 201
    strat_id = strat.json()["id"]
    assert strat.json()["is_active"] is True

    # Evaluate strategy
    eval_resp = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/evaluate", headers=h,
    )
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert data["strategy_id"] == strat_id
    assert data["total_steps"] == 1
    assert len(data["triggered_steps"]) == 1

    # Toggle strategy off
    toggle = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h,
    )
    assert toggle.status_code == 200
    assert toggle.json()["is_active"] is False

    # Delete strategy
    delete = await client.delete(
        f"/api/withdrawal/strategies/{strat_id}", headers=h,
    )
    assert delete.status_code == 200
    assert delete.json()["status"] == "deleted"

    # Verify strategy is gone
    get_strat = await client.get(
        f"/api/withdrawal/strategies/{strat_id}", headers=h,
    )
    assert get_strat.status_code == 404

    # Verify wallet still exists and balance is intact
    get_wallet = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=h)
    assert get_wallet.status_code == 200
    assert get_wallet.json()["balance"] == 500.0

    final_balance = await client.get("/api/withdrawal/balance", headers=h)
    assert final_balance.status_code == 200
    assert final_balance.json()["total_usd_equivalent"] == 500.0


# ── 2. Multi-wallet workflow ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_multi_wallet_workflow(client: AsyncClient):
    """Create 2 wallets (USDC + USDT) -> transfer to both -> verify total
    balance -> verify each wallet balance."""
    token = await _register(client, "multi-wallet@test.com")
    h = await _headers(token)

    # Create USDC wallet
    usdc_wallet = await client.post("/api/withdrawal/wallets", headers=h, json={
        "name": "USDC Vault", "currency": "USDC",
    })
    assert usdc_wallet.status_code == 200
    usdc_id = usdc_wallet.json()["id"]

    # Create USDT wallet
    usdt_wallet = await client.post("/api/withdrawal/wallets", headers=h, json={
        "name": "USDT Vault", "currency": "USDT",
    })
    assert usdt_wallet.status_code == 200
    usdt_id = usdt_wallet.json()["id"]

    # Verify both appear in list
    wallets = await client.get("/api/withdrawal/wallets", headers=h)
    assert wallets.status_code == 200
    wallet_ids = {w["id"] for w in wallets.json()}
    assert usdc_id in wallet_ids
    assert usdt_id in wallet_ids

    # Transfer funds to USDC wallet
    t1 = await client.post("/api/withdrawal/transfer", headers=h, json={
        "amount": 1000.0, "currency": "USDC",
    })
    assert t1.status_code == 200
    assert t1.json()["new_balance"] == 1000.0
    assert t1.json()["currency"] == "USDC"

    # Transfer funds to USDT wallet
    t2 = await client.post("/api/withdrawal/transfer", headers=h, json={
        "amount": 500.0, "currency": "USDT",
    })
    assert t2.status_code == 200
    assert t2.json()["new_balance"] == 500.0
    assert t2.json()["currency"] == "USDT"

    # Verify total balance aggregation
    total = await client.get("/api/withdrawal/balance", headers=h)
    assert total.status_code == 200
    data = total.json()
    assert data["total_wallets"] == 2
    assert data["balances_by_currency"]["USDC"] == 1000.0
    assert data["balances_by_currency"]["USDT"] == 500.0
    assert data["total_usd_equivalent"] == 1500.0

    # Verify individual wallet balances via list
    wallet_list = await client.get("/api/withdrawal/wallets", headers=h)
    balances = {w["currency"]: w["balance"] for w in wallet_list.json()}
    assert balances["USDC"] == 1000.0
    assert balances["USDT"] == 500.0

    # Verify individual wallet via get
    get_usdc = await client.get(f"/api/withdrawal/wallets/{usdc_id}", headers=h)
    assert get_usdc.status_code == 200
    assert get_usdc.json()["balance"] == 1000.0

    get_usdt = await client.get(f"/api/withdrawal/wallets/{usdt_id}", headers=h)
    assert get_usdt.status_code == 200
    assert get_usdt.json()["balance"] == 500.0


# ── 3. Strategy with steps workflow ────────────────────────────────────


@pytest.mark.asyncio
async def test_strategy_with_steps_workflow(client: AsyncClient):
    """Create strategy with 3 steps -> verify steps saved -> update strategy
    -> verify update -> evaluate -> verify evaluation -> toggle -> verify toggle -> delete."""
    token = await _register(client, "steps-workflow@test.com")
    h = await _headers(token)

    steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 100},
            "action": {"type": "withdraw_pct", "pct": 10},
            "once": True,
        },
        {
            "id": "step-2",
            "condition": {"type": "profit_pct", "target_pct": 15},
            "action": {"type": "withdraw_fixed", "amount": 200},
        },
        {
            "id": "step-3",
            "condition": {"type": "drawdown_from_peak", "max_drawdown_pct": 10},
            "action": {"type": "withdraw_pct", "pct": 50},
        },
    ]

    # Create strategy with 3 steps
    create = await client.post("/api/withdrawal/strategies", headers=h, json={
        "name": "Multi-Step Strategy",
        "description": "Strategy with 3 distinct steps",
        "steps": steps,
    })
    assert create.status_code == 201
    strat_id = create.json()["id"]
    assert create.json()["is_active"] is True
    assert len(create.json()["steps"]) == 3

    # Verify steps are saved
    get_strat = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert get_strat.status_code == 200
    saved_steps = get_strat.json()["steps"]
    assert len(saved_steps) == 3
    step_ids = {s["id"] for s in saved_steps}
    assert step_ids == {"step-1", "step-2", "step-3"}

    # Update strategy name and description
    update = await client.put(f"/api/withdrawal/strategies/{strat_id}", headers=h, json={
        "name": "Updated Multi-Step",
        "description": "Updated description",
    })
    assert update.status_code == 200
    assert update.json()["name"] == "Updated Multi-Step"
    assert update.json()["description"] == "Updated description"

    # Verify update persisted
    verify_update = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert verify_update.json()["name"] == "Updated Multi-Step"
    assert verify_update.json()["description"] == "Updated description"

    # Update steps
    new_steps = [
        {
            "id": "step-1",
            "condition": {"type": "profit_threshold", "threshold": 200},
            "action": {"type": "withdraw_pct", "pct": 20},
        },
        {
            "id": "step-2",
            "condition": {"type": "trailing_stop_fall", "fall_pct": 5},
            "action": {"type": "withdraw_pct", "pct": 100},
        },
    ]
    update_steps = await client.put(f"/api/withdrawal/strategies/{strat_id}", headers=h, json={
        "steps": new_steps,
    })
    assert update_steps.status_code == 200
    assert len(update_steps.json()["steps"]) == 2

    # Evaluate strategy
    eval_resp = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/evaluate", headers=h,
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["strategy_id"] == strat_id
    assert eval_data["name"] == "Updated Multi-Step"
    assert eval_data["total_steps"] == 2
    assert len(eval_data["triggered_steps"]) == 2
    triggered_ids = {s["step_id"] for s in eval_data["triggered_steps"]}
    assert triggered_ids == {"step-1", "step-2"}

    # Toggle strategy off
    toggle_off = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h,
    )
    assert toggle_off.status_code == 200
    assert toggle_off.json()["is_active"] is False

    # Verify toggle persisted
    verify_off = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert verify_off.json()["is_active"] is False

    # Toggle strategy back on
    toggle_on = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h,
    )
    assert toggle_on.status_code == 200
    assert toggle_on.json()["is_active"] is True

    # Verify toggle persisted
    verify_on = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert verify_on.json()["is_active"] is True

    # Delete strategy
    delete = await client.delete(
        f"/api/withdrawal/strategies/{strat_id}", headers=h,
    )
    assert delete.status_code == 200
    assert delete.json()["status"] == "deleted"

    # Verify gone
    gone = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert gone.status_code == 404

    # Verify list is empty
    list_strats = await client.get("/api/withdrawal/strategies", headers=h)
    assert list_strats.json() == []


# ── 4. Cross-user isolation E2E ───────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_user_isolation_e2e(client: AsyncClient):
    """User A creates wallet + strategy -> User B tries to access both
    -> verify 404 for both."""
    token_a = await _register(client, "iso-e2e-a@test.com")
    token_b = await _register(client, "iso-e2e-b@test.com")
    h_a = await _headers(token_a)
    h_b = await _headers(token_b)

    # User A creates a wallet
    wallet = await client.post("/api/withdrawal/wallets", headers=h_a, json={
        "name": "A's Vault", "currency": "USDC",
    })
    assert wallet.status_code == 200
    wallet_id = wallet.json()["id"]

    # User A transfers funds
    await client.post("/api/withdrawal/transfer", headers=h_a, json={
        "amount": 500.0, "currency": "USDC",
    })

    # User A creates a strategy
    strat = await client.post("/api/withdrawal/strategies", headers=h_a, json={
        "name": "A's Strategy",
        "steps": [
            {"id": "s1", "condition": {"type": "profit_threshold", "threshold": 1000},
             "action": {"type": "withdraw_pct", "pct": 50}},
        ],
    })
    assert strat.status_code == 201
    strat_id = strat.json()["id"]

    # User A can see wallet
    a_wallet = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=h_a)
    assert a_wallet.status_code == 200

    # User B cannot see User A's wallet
    b_wallet = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=h_b)
    assert b_wallet.status_code == 404

    # User A can see strategy
    a_strat = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h_a)
    assert a_strat.status_code == 200

    # User B cannot see User A's strategy
    b_strat = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h_b)
    assert b_strat.status_code == 404

    # User B cannot evaluate User A's strategy
    b_eval = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/evaluate", headers=h_b,
    )
    assert b_eval.status_code == 404

    # User B cannot toggle User A's strategy
    b_toggle = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h_b,
    )
    assert b_toggle.status_code == 404

    # User B cannot update User A's strategy
    b_update = await client.put(
        f"/api/withdrawal/strategies/{strat_id}", headers=h_b,
        json={"name": "Hacked"},
    )
    assert b_update.status_code == 404

    # User B cannot delete User A's strategy
    b_delete = await client.delete(
        f"/api/withdrawal/strategies/{strat_id}", headers=h_b,
    )
    assert b_delete.status_code == 404

    # User A's wallet and strategy still exist and work
    a_wallet_final = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=h_a)
    assert a_wallet_final.status_code == 200
    assert a_wallet_final.json()["balance"] == 500.0

    a_strat_final = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h_a)
    assert a_strat_final.status_code == 200
    assert a_strat_final.json()["name"] == "A's Strategy"

    # User B's wallet list and strategy list are empty
    b_wallets = await client.get("/api/withdrawal/wallets", headers=h_b)
    assert b_wallets.json() == []

    b_strats = await client.get("/api/withdrawal/strategies", headers=h_b)
    assert b_strats.json() == []


# ── 5. Full auto-profit protection simulation ─────────────────────────


@pytest.mark.asyncio
async def test_full_auto_profit_protection_simulation(client: AsyncClient):
    """Conceptual end-to-end simulation of the auto-profit protection system.

    Covers: register user -> create safe wallet -> create strategy with
    withdrawal steps -> verify strategy evaluation works -> toggle strategy
    off/on -> delete strategy -> verify clean state.
    """
    token = await _register(client, "auto-profit@test.com")
    h = await _headers(token)

    # 1. Register and verify user is authenticated
    me = await client.get("/api/auth/me", headers=h)
    assert me.status_code == 200

    # 2. Create safe wallet
    wallet = await client.post("/api/withdrawal/wallets", headers=h, json={
        "name": "Auto-Profit Vault", "currency": "USDC",
    })
    assert wallet.status_code == 200
    wallet_id = wallet.json()["id"]
    assert wallet.json()["is_disconnected"] is True

    # 3. Create strategy with multi-step withdrawal plan
    steps = [
        {
            "id": "tier-1",
            "condition": {"type": "profit_threshold", "threshold": 500},
            "action": {"type": "withdraw_pct", "pct": 25},
            "once": True,
        },
        {
            "id": "tier-2",
            "condition": {"type": "profit_pct", "target_pct": 20},
            "action": {"type": "withdraw_fixed", "amount": 300},
            "cooldown_seconds": 3600,
        },
        {
            "id": "tier-3",
            "condition": {"type": "trailing_stop_fall", "fall_pct": 10},
            "action": {"type": "withdraw_pct", "pct": 100},
            "once": True,
        },
    ]

    strat = await client.post("/api/withdrawal/strategies", headers=h, json={
        "name": "Auto-Profit Protection",
        "description": "Tiered auto-profit protection with trailing stop",
        "steps": steps,
        "safe_wallet_id": wallet_id,
    })
    assert strat.status_code == 201
    strat_id = strat.json()["id"]
    assert strat.json()["is_active"] is True
    assert strat.json()["safe_wallet_id"] == wallet_id
    assert len(strat.json()["steps"]) == 3

    # 4. Verify strategy evaluation works
    eval_resp = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/evaluate", headers=h,
    )
    assert eval_resp.status_code == 200
    eval_data = eval_resp.json()
    assert eval_data["strategy_id"] == strat_id
    assert eval_data["is_active"] is True
    assert eval_data["total_steps"] == 3
    assert len(eval_data["triggered_steps"]) == 3

    # 5. Toggle strategy off
    toggle_off = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h,
    )
    assert toggle_off.status_code == 200
    assert toggle_off.json()["is_active"] is False

    # Verify toggle persisted
    verify_off = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert verify_off.json()["is_active"] is False

    # 6. Toggle strategy back on
    toggle_on = await client.post(
        f"/api/withdrawal/strategies/{strat_id}/toggle", headers=h,
    )
    assert toggle_on.status_code == 200
    assert toggle_on.json()["is_active"] is True

    # 7. Delete strategy
    delete = await client.delete(
        f"/api/withdrawal/strategies/{strat_id}", headers=h,
    )
    assert delete.status_code == 200
    assert delete.json()["status"] == "deleted"

    # 8. Verify clean state
    # Strategy list should be empty
    list_strats = await client.get("/api/withdrawal/strategies", headers=h)
    assert list_strats.json() == []

    # Deleted strategy returns 404
    get_deleted = await client.get(f"/api/withdrawal/strategies/{strat_id}", headers=h)
    assert get_deleted.status_code == 404

    # Wallet still exists and untouched
    get_wallet = await client.get(f"/api/withdrawal/wallets/{wallet_id}", headers=h)
    assert get_wallet.status_code == 200
    assert get_wallet.json()["name"] == "Auto-Profit Vault"
    assert get_wallet.json()["balance"] == 0.0

    # Balance endpoint shows clean wallet
    balance = await client.get("/api/withdrawal/balance", headers=h)
    assert balance.status_code == 200
    assert balance.json()["total_wallets"] == 1
    assert balance.json()["total_usd_equivalent"] == 0.0

    # History is empty (no transfers were made)
    history = await client.get("/api/withdrawal/history", headers=h)
    assert history.status_code == 200
    assert history.json() == []
