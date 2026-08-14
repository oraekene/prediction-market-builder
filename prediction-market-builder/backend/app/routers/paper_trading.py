from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models.paper_wallet import PaperWallet, PaperOrder, OrderStatus
from app.models.user import User
from app.services.paper_trading import PaperTradingService
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/paper", tags=["paper-trading"])
service = PaperTradingService()


async def _get_owned_wallet(user: User, session: AsyncSession) -> PaperWallet:
    wallet = await service.get_or_create_wallet(user.id, session)
    return wallet


@router.get("/wallet")
async def get_wallet(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await _get_owned_wallet(current_user, session)

    open_orders = await session.execute(
        select(PaperOrder).where(
            PaperOrder.wallet_id == wallet.id,
            PaperOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]),
        ).order_by(PaperOrder.created_at.desc())
    )

    filled_orders = await session.execute(
        select(PaperOrder).where(
            PaperOrder.wallet_id == wallet.id,
            PaperOrder.status == OrderStatus.FILLED,
        ).order_by(PaperOrder.created_at.desc()).limit(50)
    )

    pnl = wallet.current_balance - wallet.initial_balance
    pnl_pct = round((pnl / wallet.initial_balance) * 100, 2) if wallet.initial_balance > 0 else 0

    return {
        "id": wallet.id,
        "initial_balance": wallet.initial_balance,
        "current_balance": wallet.current_balance,
        "pnl": round(pnl, 2),
        "pnl_pct": pnl_pct,
        "currency": wallet.currency,
        "is_active": wallet.is_active,
        "open_positions": [
            {
                "id": o.id,
                "market_id": o.market_id,
                "market_title": o.market_title,
                "platform": o.platform,
                "side": o.side,
                "amount": o.amount,
                "filled_amount": o.filled_amount,
                "price": o.price,
                "fill_price": o.fill_price,
                "status": o.status.value,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in open_orders.scalars().all()
        ],
        "recent_trades": [
            {
                "id": o.id,
                "market_id": o.market_id,
                "market_title": o.market_title or o.market_id,
                "platform": o.platform,
                "side": o.side,
                "amount": o.amount,
                "filled_amount": o.filled_amount,
                "price": o.price,
                "fill_price": o.fill_price,
                "pnl": o.pnl,
                "slippage": o.slippage,
                "status": o.status.value,
                "created_at": o.created_at.isoformat() if o.created_at else None,
            }
            for o in filled_orders.scalars().all()
        ],
    }


@router.post("/wallet/reset")
async def reset_wallet(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await _get_owned_wallet(current_user, session)
    wallet = await service.reset_wallet(wallet.id, session)
    return {
        "success": True,
        "initial_balance": wallet.initial_balance,
        "current_balance": wallet.current_balance,
    }


@router.post("/orders")
async def place_order(
    body: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    wallet_id = body.get("wallet_id")
    if not wallet_id:
        raise HTTPException(status_code=400, detail="wallet_id required")

    wallet_result = await session.execute(
        select(PaperWallet).where(PaperWallet.id == wallet_id, PaperWallet.user_id == current_user.id)
    )
    if not wallet_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Wallet not found")

    mode = body.get("mode", "paper")
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'paper' or 'live'")
    user = current_user if mode == "live" else None

    result = await service.place_paper_order(
        wallet_id=wallet_id,
        platform=body.get("platform", "polymarket"),
        market_id=body.get("market_id", ""),
        market_title=body.get("market_title"),
        side=body.get("side", "buy"),
        amount=body.get("amount", 0),
        price=body.get("price", 0.5),
        session=session,
        strategy_id=body.get("strategy_id"),
        risk_profile=body.get("risk_profile"),
        mode=mode,
        user=user,
    )

    if not result["success"]:
        resp = {
            "success": False,
            "error": result.get("error", "Order failed"),
            "violations": result.get("violations"),
        }
        if result.get("need_confirmation"):
            resp["need_confirmation"] = True
        return resp

    return result


@router.post("/trading-mode")
async def set_trading_mode(
    body: dict,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user),
):
    mode = body.get("mode", "paper")
    if mode not in ("paper", "live"):
        raise HTTPException(status_code=400, detail="mode must be 'paper' or 'live'")

    prefs = dict(current_user.preferences or {})
    prefs["trading_mode"] = mode
    current_user.preferences = prefs
    await session.commit()

    if mode == "live":
        has_key = bool(current_user.polymarket_key or current_user.kalshi_key or current_user.drift_key)
        if not has_key:
            return {"mode": mode, "warning": "No exchange API keys configured. Live trading will fail."}

    return {"mode": mode}


@router.get("/orders")
async def list_orders(
    status: str | None = Query(None),
    limit: int = Query(50, le=200),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await _get_owned_wallet(current_user, session)
    query = select(PaperOrder).where(PaperOrder.wallet_id == wallet.id).order_by(PaperOrder.created_at.desc()).limit(limit)
    if status:
        try:
            query = query.where(PaperOrder.status == OrderStatus(status))
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")

    rows = await session.execute(query)
    orders = []
    for o in rows.scalars().all():
        orders.append({
            "id": o.id,
            "wallet_id": o.wallet_id,
            "strategy_id": o.strategy_id,
            "platform": o.platform,
            "market_id": o.market_id,
            "market_title": o.market_title,
            "side": o.side,
            "order_type": o.order_type,
            "price": o.price,
            "amount": o.amount,
            "filled_amount": o.filled_amount,
            "fill_price": o.fill_price,
            "status": o.status.value,
            "pnl": o.pnl,
            "slippage": o.slippage,
            "platform_order_id": o.platform_order_id,
            "created_at": o.created_at.isoformat() if o.created_at else None,
            "updated_at": o.updated_at.isoformat() if o.updated_at else None,
        })
    return {"orders": orders, "total": len(orders)}


@router.delete("/orders/{order_id}")
async def cancel_order(
    order_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(PaperOrder).join(PaperWallet, PaperOrder.wallet_id == PaperWallet.id).where(
            PaperOrder.id == order_id,
            PaperWallet.user_id == current_user.id,
        )
    )
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    cancelled = await service.cancel_order(order_id, session)
    if not cancelled:
        raise HTTPException(status_code=400, detail="Order cannot be cancelled or not found")
    return {"success": True, "order_id": order_id}


@router.get("/performance")
async def get_performance(
    strategy_id: str | None = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await _get_owned_wallet(current_user, session)
    perf = await service.get_performance(session=session, wallet_id=wallet.id, strategy_id=strategy_id)
    return perf


@router.post("/sync-resolutions")
async def sync_resolutions(
    body: dict,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    resolutions = body.get("resolutions", [])
    if not isinstance(resolutions, list):
        raise HTTPException(status_code=400, detail="resolutions must be a list")
    wallet = await _get_owned_wallet(current_user, session)
    owned = await session.execute(
        select(PaperOrder.market_id, PaperOrder.platform).where(PaperOrder.wallet_id == wallet.id)
    )
    owned_pairs = {(r.market_id, r.platform) for r in owned.all()}
    filtered = [
        r for r in resolutions
        if isinstance(r, dict) and (r.get("market_id"), r.get("platform")) in owned_pairs
    ]
    result = await service.sync_resolutions(filtered, session)
    return result


@router.get("/metrics/{metric}")
async def get_metric(
    metric: str,
    window: int = Query(0, ge=0, le=5000),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await _get_owned_wallet(current_user, session)
    result = await service.get_metric(metric, session=session, wallet_id=wallet.id, window=window)
    return result


@router.get("/compare")
async def compare_strategies(
    strategy_ids: str = Query(..., description="Comma-separated strategy IDs"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    from app.models.strategy import Strategy
    ids = [s.strip() for s in strategy_ids.split(",") if s.strip()]
    if not ids:
        raise HTTPException(status_code=400, detail="At least one strategy_id required")
    result = await session.execute(
        select(Strategy.id).where(Strategy.id.in_(ids), Strategy.user_id == current_user.id)
    )
    owned_ids = [r for r in result.scalars().all()]
    comparisons = await service.compare_strategies(owned_ids, session)
    return {"comparisons": comparisons}


@router.post("/confirm-live")
async def confirm_live(
    current_user: User = Depends(get_current_user),
):
    result = await service.confirm_live(current_user.id)
    return result


@router.post("/kill-switch")
async def kill_switch(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await service.kill_switch(session, current_user.id)
    return result


@router.get("/connection-test")
async def connection_test(
    platform: str = "polymarket",
    current_user: User = Depends(get_current_user),
):
    ok = await service.live_connection_ok(platform)
    return {"platform": platform, "available": ok}
