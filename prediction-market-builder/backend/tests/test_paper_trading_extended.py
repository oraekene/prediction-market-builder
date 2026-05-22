import pytest
from datetime import datetime, timezone
from app.models.paper_wallet import PaperWallet, PaperOrder, OrderStatus
from app.services.paper_trading import PaperTradingService


@pytest.fixture
async def wallet(session):
    w = PaperWallet(user_id="test-user")
    session.add(w)
    await session.commit()
    return w


@pytest.fixture
def service():
    return PaperTradingService()


@pytest.fixture
async def filled_orders(session, wallet):
    orders = [
        PaperOrder(wallet_id=wallet.id, platform="polymarket", market_id="mkt-a", side="buy", price=0.65, amount=100.0, filled_amount=100.0, fill_price=0.65, status=OrderStatus.FILLED, pnl=35.0),
        PaperOrder(wallet_id=wallet.id, platform="polymarket", market_id="mkt-b", side="buy", price=0.30, amount=100.0, filled_amount=100.0, fill_price=0.30, status=OrderStatus.FILLED, pnl=70.0),
        PaperOrder(wallet_id=wallet.id, platform="polymarket", market_id="mkt-c", side="buy", price=0.50, amount=100.0, filled_amount=100.0, fill_price=0.50, status=OrderStatus.FILLED, pnl=-20.0),
        PaperOrder(wallet_id=wallet.id, platform="kalshi", market_id="mkt-d", side="sell", price=0.45, amount=100.0, filled_amount=100.0, fill_price=0.45, status=OrderStatus.FILLED, pnl=-10.0),
    ]
    for o in orders:
        session.add(o)
    await session.commit()
    return orders


# --- sync_resolutions ---

@pytest.mark.asyncio
async def test_sync_resolutions_updates_orders(session, wallet, service):
    order = PaperOrder(
        wallet_id=wallet.id, platform="polymarket", market_id="mkt-1",
        side="buy", price=0.65, amount=100.0, filled_amount=100.0,
        fill_price=0.65, status=OrderStatus.FILLED, pnl=0.0,
    )
    session.add(order)
    await session.commit()

    result = await service.sync_resolutions(
        [{"market_id": "mkt-1", "platform": "polymarket", "outcome": "yes"}],
        session,
    )

    assert result["updated"] == 1
    assert result["resolutions"] == 1
    await session.refresh(order)
    assert order.resolved_outcome == "yes"
    assert order.calibration_error is not None
    assert order.calibration_error == round((0.65 - 1.0) ** 2, 4)


@pytest.mark.asyncio
async def test_sync_resolutions_no_outcome(session, wallet, service):
    order = PaperOrder(
        wallet_id=wallet.id, platform="polymarket", market_id="mkt-2",
        side="buy", price=0.50, amount=100.0, filled_amount=100.0,
        fill_price=0.50, status=OrderStatus.FILLED, pnl=0.0,
    )
    session.add(order)
    await session.commit()

    result = await service.sync_resolutions(
        [{"market_id": "mkt-2", "platform": "polymarket", "outcome": "no"}],
        session,
    )
    await session.refresh(order)
    assert order.resolved_outcome == "no"
    assert order.calibration_error == round((0.5 - 0.0) ** 2, 4)


@pytest.mark.asyncio
async def test_sync_resolutions_skips_already_resolved(session, wallet, service):
    order = PaperOrder(
        wallet_id=wallet.id, platform="kalshi", market_id="mkt-3",
        side="sell", price=0.40, amount=100.0, filled_amount=100.0,
        fill_price=0.40, status=OrderStatus.FILLED, pnl=0.0,
        resolved_outcome="yes", calibration_error=0.36,
    )
    session.add(order)
    await session.commit()

    result = await service.sync_resolutions(
        [{"market_id": "mkt-3", "platform": "kalshi", "outcome": "no"}],
        session,
    )
    assert result["updated"] == 0
    await session.refresh(order)
    assert order.resolved_outcome == "yes"


# --- _compute_brier_score ---

@pytest.mark.asyncio
async def test_brier_score_null_when_no_resolutions(session, wallet, service):
    order = PaperOrder(
        wallet_id=wallet.id, platform="polymarket", market_id="mkt-4",
        side="buy", price=0.65, amount=100.0, filled_amount=100.0,
        fill_price=0.65, status=OrderStatus.FILLED, pnl=0.0,
    )
    session.add(order)
    await session.commit()

    perf = await service.get_performance(session=session, wallet_id=wallet.id)
    assert perf["calibration"] is None


@pytest.mark.asyncio
async def test_brier_score_computed_from_resolved(session, wallet, service):
    for i, (price, outcome) in enumerate([(0.65, "yes"), (0.30, "no"), (0.50, "yes")]):
        actual = 1.0 if outcome == "yes" else 0.0
        order = PaperOrder(
            wallet_id=wallet.id, platform="polymarket", market_id=f"mkt-b{i}",
            side="buy", price=price, amount=100.0, filled_amount=100.0,
            fill_price=price, status=OrderStatus.FILLED, pnl=0.0,
            resolved_outcome=outcome,
            calibration_error=round((price - actual) ** 2, 4),
        )
        session.add(order)
    await session.commit()

    perf = await service.get_performance(session=session, wallet_id=wallet.id)
    expected = ((0.65 - 1.0) ** 2 + (0.30 - 0.0) ** 2 + (0.50 - 1.0) ** 2) / 3
    assert perf["calibration"] == round(expected, 4)


# --- get_metric ---

@pytest.mark.asyncio
async def test_get_metric_current_balance(session, wallet, service):
    result = await service.get_metric("current_balance", session=session, wallet_id=wallet.id)
    assert result["metric"] == "current_balance"
    assert result["value"] is not None
    assert result["value"] > 0


@pytest.mark.asyncio
async def test_get_metric_total_pnl(session, wallet, service, filled_orders):
    result = await service.get_metric("total_pnl", session=session, wallet_id=wallet.id)
    assert result["value"] == round(35 + 70 - 20 - 10, 2)


@pytest.mark.asyncio
async def test_get_metric_win_rate(session, wallet, service, filled_orders):
    result = await service.get_metric("win_rate", session=session, wallet_id=wallet.id)
    assert result["value"] == 0.5


@pytest.mark.asyncio
async def test_get_metric_avg_rr(session, wallet, service, filled_orders):
    result = await service.get_metric("avg_rr", session=session, wallet_id=wallet.id)
    avg_win = (35 + 70) / 2
    avg_loss = (20 + 10) / 2
    assert result["value"] == round(avg_win / avg_loss, 4)


@pytest.mark.asyncio
async def test_get_metric_sharpe(session, wallet, service, filled_orders):
    result = await service.get_metric("sharpe", session=session, wallet_id=wallet.id)
    assert result["value"] is not None
    assert isinstance(result["value"], float)


@pytest.mark.asyncio
async def test_get_metric_sortino(session, wallet, service, filled_orders):
    result = await service.get_metric("sortino", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_calmar(session, wallet, service, filled_orders):
    result = await service.get_metric("calmar", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_max_drawdown(session, wallet, service, filled_orders):
    result = await service.get_metric("max_drawdown", session=session, wallet_id=wallet.id)
    assert result["value"] >= 0


@pytest.mark.asyncio
async def test_get_metric_profit_factor(session, wallet, service, filled_orders):
    result = await service.get_metric("profit_factor", session=session, wallet_id=wallet.id)
    assert result["value"] > 1


@pytest.mark.asyncio
async def test_get_metric_kelly_optimal(session, wallet, service, filled_orders):
    result = await service.get_metric("kelly_optimal", session=session, wallet_id=wallet.id)
    assert 0.0 <= result["value"] <= 1.0


@pytest.mark.asyncio
async def test_get_metric_edge(session, wallet, service, filled_orders):
    result = await service.get_metric("edge", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_brier_score_none(session, wallet, service, filled_orders):
    result = await service.get_metric("brier_score", session=session, wallet_id=wallet.id)
    assert result["value"] is None


@pytest.mark.asyncio
async def test_get_metric_brier_score_with_resolutions(session, wallet, service, filled_orders):
    for i, o in enumerate(filled_orders[:2]):
        o.resolved_outcome = "yes" if i == 0 else "no"
        o.calibration_error = round((o.price - (1.0 if i == 0 else 0.0)) ** 2, 4)
    await session.commit()

    result = await service.get_metric("brier_score", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_trade_count(session, wallet, service, filled_orders):
    result = await service.get_metric("trade_count", session=session, wallet_id=wallet.id)
    assert result["value"] == 4


@pytest.mark.asyncio
async def test_get_metric_sqn(session, wallet, service, filled_orders):
    result = await service.get_metric("sqn", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_recovery_factor(session, wallet, service, filled_orders):
    result = await service.get_metric("recovery_factor", session=session, wallet_id=wallet.id)
    assert result["value"] is not None


@pytest.mark.asyncio
async def test_get_metric_largest_win(session, wallet, service, filled_orders):
    result = await service.get_metric("largest_win", session=session, wallet_id=wallet.id)
    assert result["value"] == 70.0


@pytest.mark.asyncio
async def test_get_metric_largest_loss(session, wallet, service, filled_orders):
    result = await service.get_metric("largest_loss", session=session, wallet_id=wallet.id)
    assert result["value"] == -20.0


@pytest.mark.asyncio
async def test_get_metric_consecutive_streak(session, wallet, service, filled_orders):
    result = await service.get_metric("consecutive_streak", session=session, wallet_id=wallet.id)
    assert isinstance(result["value"], int)


@pytest.mark.asyncio
async def test_get_metric_empty_no_orders(session, wallet, service):
    result = await service.get_metric("sharpe", session=session, wallet_id=wallet.id)
    assert result["value"] is None


@pytest.mark.asyncio
async def test_get_metric_unknown_returns_none(session, wallet, service, filled_orders):
    result = await service.get_metric("nonexistent", session=session, wallet_id=wallet.id)
    assert result["value"] is None


@pytest.mark.asyncio
async def test_get_metric_window_limits_orders(session, wallet, service, filled_orders):
    result = await service.get_metric("trade_count", session=session, wallet_id=wallet.id, window=2)
    assert result["window"] == 2
    assert result["total_available"] == 4


# --- compare_strategies ---

@pytest.mark.asyncio
async def test_compare_strategies_empty_list(session, service):
    result = await service.compare_strategies([], session)
    assert result == []


# --- get_performance ---

@pytest.mark.asyncio
async def test_get_performance_empty(session, wallet, service):
    perf = await service.get_performance(session=session, wallet_id=wallet.id)
    assert perf["total_trades"] == 0
    assert perf["calibration"] is None
    assert perf["current_balance"] is not None


@pytest.mark.asyncio
async def test_get_performance_with_trades(session, wallet, service, filled_orders):
    perf = await service.get_performance(session=session, wallet_id=wallet.id)
    assert perf["total_trades"] == 4
    assert perf["winning_trades"] == 2
    assert perf["losing_trades"] == 2
    assert perf["win_rate"] == 0.5
    assert perf["total_pnl"] == round(35 + 70 - 20 - 10, 2)


# --- Endpoint tests ---

@pytest.mark.asyncio
async def test_get_wallet_endpoint(client):
    resp = await client.get("/api/paper/wallet?user_id=ep-user")
    assert resp.status_code == 200
    data = resp.json()
    assert data["initial_balance"] == 10000.0
    assert data["current_balance"] == 10000.0


@pytest.mark.asyncio
async def test_place_and_list_order_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user2")
    wallet_id = wallet_resp.json()["id"]

    order_resp = await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id,
        "platform": "polymarket",
        "market_id": "ep-mkt-1",
        "side": "buy",
        "amount": 100.0,
        "price": 0.55,
    })
    assert order_resp.status_code == 200

    list_resp = await client.get(f"/api/paper/orders?wallet_id={wallet_id}")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_sync_resolutions_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user3")
    wallet_id = wallet_resp.json()["id"]
    await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id, "platform": "polymarket",
        "market_id": "ep-mkt-sync", "side": "buy",
        "amount": 100.0, "price": 0.65,
    })

    sync_resp = await client.post("/api/paper/sync-resolutions", json={
        "resolutions": [{"market_id": "ep-mkt-sync", "platform": "polymarket", "outcome": "yes"}],
    })
    assert sync_resp.status_code == 200
    data = sync_resp.json()
    assert data["resolutions"] == 1


@pytest.mark.asyncio
async def test_metrics_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user4")
    wallet_id = wallet_resp.json()["id"]
    await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id, "platform": "polymarket",
        "market_id": "ep-mkt-m1", "side": "buy",
        "amount": 100.0, "price": 0.55,
    })

    metric_resp = await client.get("/api/paper/metrics/current_balance")
    assert metric_resp.status_code == 200
    data = metric_resp.json()
    assert data["metric"] == "current_balance"


@pytest.mark.asyncio
async def test_performance_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user5")
    wallet_id = wallet_resp.json()["id"]
    await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id, "platform": "polymarket",
        "market_id": "ep-mkt-p1", "side": "buy",
        "amount": 100.0, "price": 0.55,
    })

    perf_resp = await client.get("/api/paper/performance?user_id=ep-user5")
    assert perf_resp.status_code == 200
    data = perf_resp.json()
    assert "total_trades" in data


@pytest.mark.asyncio
async def test_compare_endpoint(client):
    resp = await client.get("/api/paper/compare?strategy_ids=strat-1,strat-2")
    assert resp.status_code == 200
    data = resp.json()
    assert "comparisons" in data


@pytest.mark.asyncio
async def test_compare_empty_strategy_ids_returns_400(client):
    resp = await client.get("/api/paper/compare?strategy_ids=")
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_order_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user6")
    wallet_id = wallet_resp.json()["id"]
    order_resp = await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id, "platform": "polymarket",
        "market_id": "ep-mkt-del", "side": "buy",
        "amount": 100.0, "price": 0.55,
    })
    order_id = order_resp.json()["order"]["id"]

    del_resp = await client.delete(f"/api/paper/orders/{order_id}")
    assert del_resp.status_code in (200, 400)


@pytest.mark.asyncio
async def test_reset_wallet_endpoint(client):
    wallet_resp = await client.get("/api/paper/wallet?user_id=ep-user7")
    wallet_id = wallet_resp.json()["id"]
    await client.post("/api/paper/orders", json={
        "wallet_id": wallet_id, "platform": "polymarket",
        "market_id": "ep-mkt-r1", "side": "buy",
        "amount": 100.0, "price": 0.55,
    })

    reset_resp = await client.post("/api/paper/wallet/reset?user_id=ep-user7")
    assert reset_resp.status_code == 200
    data = reset_resp.json()
    assert data["success"] is True
    assert data["current_balance"] == data["initial_balance"]
