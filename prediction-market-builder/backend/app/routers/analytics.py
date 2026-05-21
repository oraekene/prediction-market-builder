from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.trade import Trade, TradeStatus

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/summary")
async def analytics_summary(session: AsyncSession = Depends(get_session)):
    executed_count = await session.scalar(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.EXECUTED)
    )
    winning_trades = await session.scalar(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.EXECUTED, Trade.pnl > 0)
    )
    total_pnl = await session.scalar(
        select(func.coalesce(func.sum(Trade.pnl), 0)).where(Trade.status == TradeStatus.EXECUTED)
    )
    return {
        "total_trades": executed_count or 0,
        "winning_trades": winning_trades or 0,
        "total_pnl": float(total_pnl),
        "win_rate": round((winning_trades / executed_count * 100) if executed_count and executed_count > 0 else 0, 2),
    }


@router.get("/backtests")
async def analytics_backtests(session: AsyncSession = Depends(get_session)):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED).order_by(Trade.created_at.desc()).limit(20)
    )
    trades = [
        {
            "market_id": t.market_id,
            "side": t.side,
            "amount": t.amount,
            "price": t.price,
            "pnl": t.pnl,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
        }
        for t in rows.scalars().all()
    ]
    return {"backtests": [] if not trades else [{"name": "All Trades", "trades": trades}]}
