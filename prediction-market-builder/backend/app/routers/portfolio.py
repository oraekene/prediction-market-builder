from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.strategy import Strategy
from app.models.trade import Trade, TradeStatus
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def get_portfolio(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    user_id = current_user.id
    strategy_count = await session.scalar(
        select(func.count(Strategy.id)).where(Strategy.user_id == user_id)
    )
    total_trades = await session.scalar(
        select(func.count(Trade.id)).where(Trade.user_id == user_id)
    )
    executed_count = await session.scalar(
        select(func.count(Trade.id)).where(Trade.user_id == user_id, Trade.status == TradeStatus.EXECUTED)
    )
    winning_count = await session.scalar(
        select(func.count(Trade.id)).where(
            Trade.user_id == user_id,
            Trade.status == TradeStatus.EXECUTED,
            Trade.pnl > 0,
        )
    )
    total_pnl = await session.scalar(
        select(func.coalesce(func.sum(Trade.pnl), 0)).where(
            Trade.user_id == user_id, Trade.status == TradeStatus.EXECUTED
        )
    )
    rows = await session.execute(
        select(Trade)
        .where(Trade.user_id == user_id, Trade.status == TradeStatus.EXECUTED)
        .order_by(Trade.created_at.desc())
        .limit(50)
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
    win_rate = (winning_count / executed_count) if executed_count else 0.0
    return {
        "summary": {
            "total_value": 10000.0 + float(total_pnl),
            "total_pnl": float(total_pnl),
            "active_strategies": strategy_count or 0,
            "total_trades": total_trades or 0,
            "win_rate": round(win_rate, 4),
        },
        "positions": positions,
    }
