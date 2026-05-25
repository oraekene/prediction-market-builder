from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_session
from app.models.trade import Trade, TradeStatus
from app.services.risk_manager import RiskManager, RiskProfile

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.post("/evaluate")
async def evaluate_trade(body: dict):
    profile_dict = body.get("risk_profile", {})
    profile = RiskProfile(
        max_position_size=profile_dict.get("max_position_size", 0.2),
        max_drawdown=profile_dict.get("max_drawdown", 0.15),
        stop_loss=profile_dict.get("stop_loss", 0.1),
        kelly_fraction=profile_dict.get("kelly_fraction", 0.25),
        max_correlation=profile_dict.get("max_correlation", 0.7),
        min_confidence=profile_dict.get("min_confidence", 0.6),
        rules=profile_dict.get("rules", []),
    )
    mgr = RiskManager(profile)

    market = body.get("market", {})
    signal = body.get("signal", {})
    portfolio = body.get("portfolio", {})

    result = await mgr.evaluate_trade(market, signal, portfolio)
    return result


@router.post("")
async def create_trade(body: dict, session: AsyncSession = Depends(get_session)):
    profile_dict = body.get("risk_profile", {})
    profile = RiskProfile(
        max_position_size=profile_dict.get("max_position_size", 0.2),
        max_drawdown=profile_dict.get("max_drawdown", 0.15),
        stop_loss=profile_dict.get("stop_loss", 0.1),
        kelly_fraction=profile_dict.get("kelly_fraction", 0.25),
        max_correlation=profile_dict.get("max_correlation", 0.7),
        min_confidence=profile_dict.get("min_confidence", 0.6),
        rules=profile_dict.get("rules", []),
    )
    mgr = RiskManager(profile)

    market = body.get("market", {})
    signal = body.get("signal", {})
    portfolio = body.get("portfolio", {})
    risk_result = await mgr.evaluate_trade(market, signal, portfolio)

    if not risk_result["approved"]:
        return {
            "approved": False,
            "violations": risk_result["violations"],
            "trade": None,
        }

    trade = Trade(
        user_id=body.get("user_id", "default"),
        strategy_id=body.get("strategy_id"),
        market_id=market.get("platform_market_id", ""),
        platform=market.get("platform", "unknown"),
        side=body.get("side", "buy"),
        amount=risk_result["suggested_size"],
        price=signal.get("market_odds", 0.5),
        status=TradeStatus.PENDING,
    )
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    return {
        "approved": True,
        "violations": [],
        "trade": {
            "id": trade.id,
            "market_id": trade.market_id,
            "platform": trade.platform,
            "side": trade.side,
            "amount": trade.amount,
            "price": trade.price,
            "status": trade.status.value,
        },
    }


@router.get("")
async def list_trades(
    status: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_session),
):
    query = select(Trade).order_by(Trade.created_at.desc()).limit(limit)
    if status:
        query = query.where(Trade.status == TradeStatus(status))
    rows = await session.execute(query)
    trades = []
    for t in rows.scalars().all():
        trades.append({
            "id": t.id,
            "user_id": t.user_id,
            "strategy_id": t.strategy_id,
            "market_id": t.market_id,
            "platform": t.platform,
            "side": t.side,
            "amount": t.amount,
            "price": t.price,
            "status": t.status.value,
            "pnl": t.pnl,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })
    return {"trades": trades}
