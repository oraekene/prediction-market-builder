from datetime import datetime, timezone
from typing import Any
import math

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.paper_wallet import PaperWallet, PaperOrder, OrderStatus
from app.models.trade import Trade, TradeStatus
from app.services.execution import SimulatedExecutionEngine
from app.services.portfolio_manager import PortfolioManager
from app.services.risk_manager import RiskManager, RiskProfile
from app.data.duckdb_manager import DuckDBManager


class PaperTradingService:
    def __init__(self):
        self.execution_engine = SimulatedExecutionEngine()
        self.portfolio_manager = PortfolioManager()

    async def get_or_create_wallet(self, user_id: str, session: AsyncSession) -> PaperWallet:
        result = await session.execute(
            select(PaperWallet).where(PaperWallet.user_id == user_id, PaperWallet.is_active)
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            wallet = PaperWallet(user_id=user_id)
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet

    async def reset_wallet(self, wallet_id: str, session: AsyncSession) -> PaperWallet:
        result = await session.execute(select(PaperWallet).where(PaperWallet.id == wallet_id))
        wallet = result.scalar_one_or_none()
        if wallet:
            wallet.current_balance = wallet.initial_balance
            await session.execute(
                select(PaperOrder).where(
                    PaperOrder.wallet_id == wallet_id,
                    PaperOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]),
                )
            )
            rows = (await session.execute(
                select(PaperOrder).where(
                    PaperOrder.wallet_id == wallet_id,
                    PaperOrder.status.in_([OrderStatus.PENDING, OrderStatus.PARTIAL]),
                )
            )).scalars().all()
            for order in rows:
                order.status = OrderStatus.CANCELLED
            await session.commit()
            await session.refresh(wallet)
        return wallet

    async def place_paper_order(
        self,
        wallet_id: str,
        platform: str,
        market_id: str,
        market_title: str | None,
        side: str,
        amount: float,
        price: float,
        session: AsyncSession,
        strategy_id: str | None = None,
        risk_profile: dict | None = None,
    ) -> dict[str, Any]:
        wallet_result = await session.execute(select(PaperWallet).where(PaperWallet.id == wallet_id))
        wallet = wallet_result.scalar_one_or_none()
        if not wallet:
            return {"success": False, "error": "Wallet not found"}
        if wallet.current_balance < amount:
            return {"success": False, "error": "Insufficient balance"}

        if risk_profile:
            profile = RiskProfile(
                max_position_size=risk_profile.get("max_position_size", 0.2),
                max_drawdown=risk_profile.get("max_drawdown", 0.15),
                stop_loss=risk_profile.get("stop_loss", 0.1),
                kelly_fraction=risk_profile.get("kelly_fraction", 0.25),
                max_correlation=risk_profile.get("max_correlation", 0.7),
                min_confidence=risk_profile.get("min_confidence", 0.6),
                rules=risk_profile.get("rules", []),
            )
            risk_mgr = RiskManager(profile)
            risk_result = risk_mgr.evaluate_trade(
                {"current_odds": price, "platform": platform, "platform_market_id": market_id},
                {"probability": price, "market_odds": price, "confidence": 0.7},
                {"current_capital": wallet.current_balance, "positions": []},
            )
            if not risk_result["approved"]:
                return {"success": False, "error": "Risk check failed", "violations": risk_result["violations"]}

        order_book = self.execution_engine.get_order_book(platform, price, 1_000_000)
        fill_result = self.execution_engine.simulate_fill(platform, side, amount, price, order_book)

        order = PaperOrder(
            wallet_id=wallet_id,
            strategy_id=strategy_id,
            platform=platform,
            market_id=market_id,
            market_title=market_title,
            side=side,
            order_type="market",
            price=price,
            amount=amount,
            filled_amount=fill_result["filled_amount"],
            fill_price=fill_result["fill_price"],
            status=OrderStatus(fill_result["status"]),
            slippage=fill_result["slippage"],
        )

        if fill_result["filled"]:
            cost = fill_result["filled_amount"] * fill_result["fill_price"]
            wallet.current_balance = round(wallet.current_balance - cost, 2)

            if side in ("sell", "no"):
                pnl = fill_result["filled_amount"] * (1 - fill_result["fill_price"])
                order.pnl = round(pnl, 2)

        session.add(order)
        await session.commit()
        await session.refresh(order)

        return {
            "success": fill_result["filled"],
            "order": {
                "id": order.id,
                "platform": order.platform,
                "market_id": order.market_id,
                "side": order.side,
                "amount": order.amount,
                "filled_amount": order.filled_amount,
                "fill_price": order.fill_price,
                "price": order.price,
                "status": order.status.value,
                "pnl": order.pnl,
                "slippage": order.slippage,
                "created_at": order.created_at.isoformat() if order.created_at else None,
            },
            "wallet_balance": wallet.current_balance,
            "slippage": fill_result["slippage"],
            "fill_probability": fill_result["fill_probability"],
        }

    async def cancel_order(self, order_id: str, session: AsyncSession) -> bool:
        result = await session.execute(select(PaperOrder).where(PaperOrder.id == order_id))
        order = result.scalar_one_or_none()
        if not order or order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False

        if order.status == OrderStatus.PARTIAL and order.filled_amount > 0 and order.fill_price:
            wallet_result = await session.execute(select(PaperWallet).where(PaperWallet.id == order.wallet_id))
            wallet = wallet_result.scalar_one_or_none()
            if wallet:
                refund = (order.amount - order.filled_amount) * order.fill_price
                wallet.current_balance = round(wallet.current_balance + refund, 2)

        order.status = OrderStatus.CANCELLED
        await session.commit()
        return True

    async def get_performance(
        self, session: AsyncSession, wallet_id: str | None = None, strategy_id: str | None = None
    ) -> dict[str, Any]:
        query = select(PaperOrder).where(PaperOrder.status == OrderStatus.FILLED)
        if strategy_id:
            query = query.where(PaperOrder.strategy_id == strategy_id)
        if wallet_id:
            query = query.where(PaperOrder.wallet_id == wallet_id)

        rows = await session.execute(query.order_by(PaperOrder.created_at))
        orders = rows.scalars().all()

        total_trades = len(orders)
        if total_trades == 0:
            return {
                "total_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "avg_return": 0.0,
                "profit_factor": 0.0,
            }

        winning_trades = sum(1 for o in orders if o.pnl and o.pnl > 0)
        losing_trades = sum(1 for o in orders if o.pnl and o.pnl < 0)
        total_pnl = sum(o.pnl or 0 for o in orders)
        win_rate = winning_trades / total_trades if total_trades > 0 else 0

        gains = [o.pnl for o in orders if o.pnl and o.pnl > 0]
        losses = [o.pnl for o in orders if o.pnl and o.pnl < 0]
        gross_gain = sum(gains) if gains else 0
        gross_loss = abs(sum(losses)) if losses else 0
        profit_factor = round(gross_gain / gross_loss, 4) if gross_loss > 0 else float("inf") if gross_gain > 0 else 0

        returns = [o.pnl or 0 for o in orders]
        avg_return = sum(returns) / len(returns) if returns else 0
        if len(returns) > 1:
            variance = sum((r - avg_return) ** 2 for r in returns) / (len(returns) - 1)
            std_dev = math.sqrt(variance)
            sharpe_ratio = round((avg_return / std_dev) * math.sqrt(252), 4) if std_dev > 0 else 0
        else:
            sharpe_ratio = 0.0

        peak = 0
        max_dd = 0.0
        cumulative = 0
        for r in returns:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / peak if peak > 0 else 0
            max_dd = max(max_dd, dd)

        wallet = None
        if wallet_id:
            w_result = await session.execute(select(PaperWallet).where(PaperWallet.id == wallet_id))
            wallet = w_result.scalar_one_or_none()

        result = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 4),
            "total_pnl": round(total_pnl, 2),
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": round(max_dd, 4),
            "avg_return": round(avg_return, 4),
            "profit_factor": profit_factor if profit_factor != float("inf") else 999.99,
            "current_balance": round(wallet.current_balance, 2) if wallet else None,
            "initial_balance": round(wallet.initial_balance, 2) if wallet else None,
        }

        try:
            duck = DuckDBManager()
            duck.record_strategy_performance({
                "id": f"paper_{strategy_id or 'all'}_{datetime.now(timezone.utc).isoformat()}",
                "strategy_id": strategy_id or "all",
                "total_trades": total_trades,
                "win_rate": round(win_rate, 4),
                "profit_loss": round(total_pnl, 2),
                "sharpe_ratio": sharpe_ratio,
                "max_drawdown": round(max_dd, 4),
                "period_start": datetime.now(timezone.utc).date(),
                "period_end": datetime.now(timezone.utc).date(),
            })
        except Exception:
            pass

        return result

    async def compare_strategies(
        self, strategy_ids: list[str], session: AsyncSession
    ) -> list[dict[str, Any]]:
        comparisons = []
        for sid in strategy_ids:
            perf = await self.get_performance(session=session, strategy_id=sid)
            result = await session.execute(select(select(func.count()).where(
                PaperOrder.strategy_id == sid, PaperOrder.status == OrderStatus.FILLED
            ).scalar()))
            comparisons.append({
                "strategy_id": sid,
                **perf,
            })
        return comparisons
