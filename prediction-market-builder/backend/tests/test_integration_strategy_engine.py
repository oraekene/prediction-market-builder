"""Integration tests for the strategy engine with all new handlers.

Tests exercise the full FastAPI stack via POST /api/strategies/evaluate
with various node types (advanced risk, action, portfolio construction, etc.).
"""
import time
import pytest
from httpx import AsyncClient

from app.services.strategy_engine import StrategyEngine
from app.routers import strategies as strategies_router


def _ensure_engine():
    if strategies_router._strategy_engine is None:
        strategies_router._strategy_engine = StrategyEngine()


@pytest.mark.asyncio
async def test_evaluate_trailing_stop(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "trailing@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "ts1", "type": "trailing_stop", "data": {"trail_pct": 0.05}},
    ]
    edges = []

    strat = await client.post("/api/strategies", headers=headers, json={
        "name": "Trailing Stop Test",
        "nodes": nodes,
        "edges": edges,
    })
    assert strat.status_code == 201

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": edges,
        "market": {"current_odds": 0.5},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "triggered" in data
    assert "trail_pct" in data
    assert isinstance(data["triggered"], bool)


@pytest.mark.asyncio
async def test_evaluate_trailing_stop_triggered(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "trailing-trig@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "ts1", "type": "trailing_stop", "data": {"trail_pct": 0.05}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {"current_odds": 0.5},
        "portfolio": {
            "positions": [
                {"market_id": "m1", "price": 0.6, "side": "buy", "size": 100},
            ]
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is True
    assert len(data["positions"]) > 0


@pytest.mark.asyncio
async def test_evaluate_trailing_stop_not_triggered(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "trailing-notrig@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "ts1", "type": "trailing_stop", "data": {"trail_pct": 0.20}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {"current_odds": 0.55},
        "portfolio": {
            "positions": [
                {"market_id": "m1", "price": 0.54, "side": "buy", "size": 100},
            ]
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is False
    assert len(data["positions"]) == 0


@pytest.mark.asyncio
async def test_evaluate_daily_loss_limit(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "dailyloss@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "dll1", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "initial_capital": 10000,
            "current_capital": 9600,
        },
        "daily_pnl": -500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is True
    assert data["daily_pnl"] == -500
    assert data["loss_pct"] >= 0.03


@pytest.mark.asyncio
async def test_evaluate_daily_loss_limit_not_triggered(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "dailyloss-ok@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "dll1", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "initial_capital": 10000,
        },
        "daily_pnl": -100,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is False


@pytest.mark.asyncio
async def test_evaluate_circuit_breaker(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "circuit@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "cb1", "type": "circuit_breaker", "data": {
            "max_daily_loss": 0.05,
            "max_consecutive_losses": 5,
            "cooldown_seconds": 300,
        }},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {"initial_capital": 10000},
        "daily_pnl": -800,
        "consecutive_losses": 0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is True
    assert data["state"] in ("open", "cooldown")
    assert "reason" in data


@pytest.mark.asyncio
async def test_evaluate_circuit_breaker_cooldown(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "cb-cool@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "cb1", "type": "circuit_breaker", "data": {
            "max_daily_loss": 0.05,
            "cooldown_seconds": 300,
        }},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {"initial_capital": 10000},
        "daily_pnl": -600,
        "circuit_breaker_state": {"state": "cooldown", "cooldown_start": time.time() - 10},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is True
    assert data["state"] == "cooldown"


@pytest.mark.asyncio
async def test_evaluate_risk_parity_allocation(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "rparity@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "rp1", "type": "risk_parity_allocation", "data": {}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "positions": [
                {"market_id": "m1"},
                {"market_id": "m2"},
            ],
            "position_returns": {
                "m1": [0.01, -0.005, 0.02, -0.01],
                "m2": [0.005, -0.002, 0.008, -0.003],
            },
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_weights" in data
    weights = data["suggested_weights"]
    assert len(weights) == 2
    assert all(isinstance(v, float) for v in weights.values())
    assert abs(sum(weights.values()) - 1.0) < 0.01


@pytest.mark.asyncio
async def test_evaluate_risk_parity_allocation_empty(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "rparity-empty@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "rp1", "type": "risk_parity_allocation", "data": {}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {"positions": []},
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["suggested_weights"] == {}


@pytest.mark.asyncio
async def test_evaluate_mean_variance_optimization(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "mvo@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "mvo1", "type": "mean_variance_optimization", "data": {"risk_aversion": 1.0}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "positions": [
                {"market_id": "m1"},
                {"market_id": "m2"},
            ],
            "position_returns": {
                "m1": [0.01, -0.005, 0.02, -0.01, 0.015],
                "m2": [0.005, -0.002, 0.008, -0.003, 0.007],
            },
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "suggested_weights" in data
    weights = data["suggested_weights"]
    assert len(weights) == 2
    assert all(isinstance(v, float) for v in weights.values())


@pytest.mark.asyncio
async def test_evaluate_close_position(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "closepos@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "cp1", "type": "close_position", "data": {"close_pct": 50}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "positions": [
                {"market_id": "m1", "price": 0.55, "side": "buy", "size": 200,
                 "platform": "polymarket"},
            ]
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "close_position"
    assert data["approved"] is True
    assert len(data["orders_placed"]) == 1
    order = data["orders_placed"][0]
    assert order["market_id"] == "m1"
    assert order["side"] == "sell"
    assert order["amount"] == 100.0


@pytest.mark.asyncio
async def test_evaluate_close_position_all(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "closeall@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "cp1", "type": "close_position", "data": {"close_pct": 100}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "positions": [
                {"market_id": "m1", "price": 0.5, "side": "buy", "size": 300,
                 "platform": "polymarket"},
                {"market_id": "m2", "price": 0.6, "side": "sell", "size": 150,
                 "platform": "kalshi"},
            ]
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "close_position"
    assert len(data["orders_placed"]) == 2


@pytest.mark.asyncio
async def test_evaluate_withdraw_to_safe_wallet(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "withdraw@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "w1", "type": "withdraw_to_safe_wallet", "data": {
            "withdraw_pct": 50,
            "source": "profits",
            "target_currency": "USDC",
            "safe_wallet_id": "wallet-abc",
        }},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "initial_capital": 10000,
            "current_capital": 12000,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "withdraw"
    assert data["approved"] is True
    assert data["amount"] == 1000.0
    assert data["currency"] == "USDC"
    assert data["safe_wallet_id"] == "wallet-abc"


@pytest.mark.asyncio
async def test_evaluate_withdraw_to_safe_wallet_no_profit(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "withdraw-np@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "w1", "type": "withdraw_to_safe_wallet", "data": {
            "withdraw_pct": 50,
            "source": "profits",
        }},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {},
        "portfolio": {
            "initial_capital": 10000,
            "current_capital": 9500,
        },
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "withdraw"
    assert data["amount"] == 0.0


@pytest.mark.asyncio
async def test_evaluate_multiple_connected_nodes(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "chain@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "a", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}},
        {"id": "b", "type": "circuit_breaker", "data": {"max_daily_loss": 0.05}},
        {"id": "c", "type": "close_position", "data": {"close_pct": 100}},
    ]
    edges = [
        {"source": "a", "target": "b"},
        {"source": "b", "target": "c"},
    ]

    strat = await client.post("/api/strategies", headers=headers, json={
        "name": "Chain Test",
        "nodes": nodes,
        "edges": edges,
    })
    assert strat.status_code == 201

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": edges,
        "market": {},
        "portfolio": {
            "initial_capital": 10000,
            "positions": [
                {"market_id": "m1", "price": 0.5, "side": "buy", "size": 500,
                 "platform": "polymarket"},
            ],
        },
        "daily_pnl": -500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["action"] == "close_position"
    assert data["approved"] is True


@pytest.mark.asyncio
async def test_evaluate_empty_graph(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "empty@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": [],
        "edges": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["approved"] is True
    assert data["suggested_size"] == 0.0
    assert data["violations"] == []


@pytest.mark.asyncio
async def test_evaluate_unknown_node_type(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "unknown@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "unk1", "type": "totally_fake_node_type", "data": {}},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_evaluate_unknown_node_among_known(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "mixed@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "unk1", "type": "totally_fake", "data": {}},
        {"id": "dl1", "type": "daily_loss_limit", "data": {"max_daily_loss": 0.03}},
    ]
    edges = [
        {"source": "unk1", "target": "dl1"},
    ]

    resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": edges,
        "market": {},
        "portfolio": {"initial_capital": 10000},
        "daily_pnl": -500,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["triggered"] is True


@pytest.mark.asyncio
async def test_evaluate_create_and_evaluate_flow(client: AsyncClient):
    _ensure_engine()
    reg = await client.post("/api/auth/register", json={
        "email": "flow@test.com", "password": "strongpass123",
    })
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    nodes = [
        {"id": "ts1", "type": "trailing_stop", "data": {"trail_pct": 0.05}},
    ]

    create_resp = await client.post("/api/strategies", headers=headers, json={
        "name": "Full Flow Strategy",
        "description": "Create then evaluate",
        "nodes": nodes,
        "edges": [],
    })
    assert create_resp.status_code == 201
    strategy_id = create_resp.json()["id"]

    eval_resp = await client.post("/api/strategies/evaluate", headers=headers, json={
        "nodes": nodes,
        "edges": [],
        "market": {"current_odds": 0.5},
    })
    assert eval_resp.status_code == 200
    data = eval_resp.json()
    assert "triggered" in data

    get_resp = await client.get(f"/api/strategies/{strategy_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Full Flow Strategy"
