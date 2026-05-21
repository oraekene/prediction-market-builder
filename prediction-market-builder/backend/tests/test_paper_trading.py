import pytest
from datetime import datetime, timezone
from app.models.paper_wallet import PaperWallet, PaperOrder, OrderStatus


@pytest.mark.asyncio
async def test_create_wallet(session):
    wallet = PaperWallet(user_id="test-user")
    session.add(wallet)
    await session.commit()
    assert wallet.id is not None
    assert wallet.initial_balance == 10000.0
    assert wallet.current_balance == 10000.0
    assert wallet.is_active is True


@pytest.mark.asyncio
async def test_create_order(session):
    wallet = PaperWallet(user_id="test-user")
    session.add(wallet)
    await session.commit()

    order = PaperOrder(
        wallet_id=wallet.id,
        platform="polymarket",
        market_id="test-123",
        market_title="Will it rain?",
        side="buy",
        price=0.65,
        amount=100.0,
    )
    session.add(order)
    await session.commit()

    assert order.id is not None
    assert order.status == OrderStatus.PENDING
    assert order.filled_amount == 0.0


@pytest.mark.asyncio
async def test_order_status_enum():
    assert OrderStatus.PENDING.value == "pending"
    assert OrderStatus.PARTIAL.value == "partial"
    assert OrderStatus.FILLED.value == "filled"
    assert OrderStatus.CANCELLED.value == "cancelled"


@pytest.mark.asyncio
async def test_wallet_balance_update(session):
    wallet = PaperWallet(user_id="test-user")
    session.add(wallet)
    await session.commit()

    wallet.current_balance = 9000.0
    await session.commit()

    result = await session.get(PaperWallet, wallet.id)
    assert result.current_balance == 9000.0


@pytest.mark.asyncio
async def test_order_pnl_tracking(session):
    wallet = PaperWallet(user_id="test-user")
    session.add(wallet)
    await session.commit()

    order = PaperOrder(
        wallet_id=wallet.id,
        platform="kalshi",
        market_id="test-456",
        side="sell",
        price=0.5,
        amount=200.0,
        filled_amount=200.0,
        fill_price=0.55,
        status=OrderStatus.FILLED,
        pnl=10.0,
    )
    session.add(order)
    await session.commit()

    assert order.pnl == 10.0
    assert order.status == OrderStatus.FILLED
