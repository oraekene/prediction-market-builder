from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeStatus

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(session: AsyncSession = Depends(get_session)):
    strategy_count = await session.scalar(select(func.count(Strategy.id)))
    total_trades = await session.scalar(select(func.count(Trade.id)))
    executed_count = await session.scalar(
        select(func.count(Trade.id)).where(Trade.status == TradeStatus.EXECUTED)
    )
    total_pnl = await session.scalar(
        select(func.coalesce(func.sum(Trade.pnl), 0)).where(Trade.status == TradeStatus.EXECUTED)
    )
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED).order_by(Trade.created_at.desc()).limit(50)
    )
    positions = [
        {
            "market_id": t.market_id,
            "platform": t.platform,
            "side": t.side,
            "amount": t.amount,
            "price": t.price,
            "pnl": t.pnl,
            "executed_at": t.executed_at.isoformat() if t.executed_at else None,
        }
        for t in rows.scalars().all()
    ]
    return {
        "summary": {
            "total_value": 10000.0,
            "total_pnl": float(total_pnl),
            "active_strategies": strategy_count or 0,
            "total_trades": total_trades or 0,
            "win_rate": 0.0,
        },
        "positions": positions,
    }
