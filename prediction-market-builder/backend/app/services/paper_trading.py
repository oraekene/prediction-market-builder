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
        wallet = None
        if wallet_id:
            w_result = await session.execute(select(PaperWallet).where(PaperWallet.id == wallet_id))
            wallet = w_result.scalar_one_or_none()

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
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "total_pnl": 0.0,
                "sharpe_ratio": 0.0,
                "max_drawdown": 0.0,
                "avg_return": 0.0,
                "avg_rr": 0.0,
                "kelly_optimal": 0.0,
                "edge": 0.0,
                "profit_factor": 0.0,
                "calibration": None,
                "regime_buckets": {},
                "current_balance": round(wallet.current_balance, 2) if wallet else None,
                "initial_balance": round(wallet.initial_balance, 2) if wallet else None,
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

        avg_win = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(abs(l) for l in losses) / len(losses) if losses else 0
        avg_rr = round(avg_win / avg_loss, 4) if avg_loss > 0 else 0.0

        edge = round(win_rate * avg_win - (1 - win_rate) * avg_loss, 4) if avg_win > 0 and avg_loss > 0 else 0.0
        odds_ratio = avg_win / avg_loss if avg_loss > 0 else 1
        kelly_optimal = round((win_rate * odds_ratio - (1 - win_rate)) / odds_ratio, 4) if odds_ratio > 0 else 0.0
        kelly_optimal = max(0.0, min(1.0, kelly_optimal))

        result = {
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": round(win_rate, 4),
            "total_pnl": round(total_pnl, 2),
            "sharpe_ratio": sharpe_ratio,
            "max_drawdown": round(max_dd, 4),
            "avg_return": round(avg_return, 4),
            "avg_rr": avg_rr,
            "kelly_optimal": kelly_optimal,
            "edge": edge,
            "profit_factor": profit_factor if profit_factor != float("inf") else 999.99,
            "calibration": self._compute_brier_score(orders),
            "regime_buckets": {},
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
                "avg_rr": avg_rr,
                "kelly_optimal": kelly_optimal,
                "period_start": datetime.now(timezone.utc).date(),
                "period_end": datetime.now(timezone.utc).date(),
            })
        except Exception:
            pass

        return result

    def _compute_brier_score(self, orders: list) -> float | None:
        errors = [o.calibration_error for o in orders if o.calibration_error is not None]
        if not errors:
            return None
        return round(sum(errors) / len(errors), 4)

    async def sync_resolutions(
        self, resolutions: list[dict], session: AsyncSession
    ) -> dict[str, Any]:
        updated = 0
        for r in resolutions:
            market_id = r.get("market_id")
            platform = r.get("platform")
            outcome = r.get("outcome")
            if not all([market_id, platform, outcome]):
                continue

            rows = await session.execute(
                select(PaperOrder).where(
                    PaperOrder.market_id == market_id,
                    PaperOrder.platform == platform,
                    PaperOrder.resolved_outcome.is_(None),
                )
            )
            for order in rows.scalars().all():
                order.resolved_outcome = outcome
                actual = 1.0 if outcome == "yes" else 0.0
                order.calibration_error = round((order.price - actual) ** 2, 4)
                updated += 1

        await session.commit()
        return {"updated": updated, "resolutions": len(resolutions)}

    async def get_metric(
        self, metric: str, session: AsyncSession, wallet_id: str | None = None, window: int = 0
    ) -> dict[str, Any]:
        if metric == "current_balance":
            value = None
            if wallet_id:
                wr = await session.execute(select(PaperWallet).where(PaperWallet.id == wallet_id))
                w = wr.scalar_one_or_none()
                value = round(w.current_balance, 2) if w else None
            return {"metric": metric, "value": value, "window": window, "total_available": 0}

        query = select(PaperOrder).where(PaperOrder.status == OrderStatus.FILLED).order_by(PaperOrder.created_at.desc())
        if wallet_id:
            query = query.where(PaperOrder.wallet_id == wallet_id)
        rows = await session.execute(query)
        orders = rows.scalars().all()

        total_available = len(orders)

        if window > 0:
            orders = orders[:window]

        total = len(orders)
        if total == 0:
            return {"metric": metric, "value": None, "window": window, "total_available": total_available}

        winning = [o for o in orders if o.pnl and o.pnl > 0]
        losing = [o for o in orders if o.pnl and o.pnl < 0]
        gains = [o.pnl for o in winning]
        losses = [abs(o.pnl) for o in losing]
        pnls = [o.pnl or 0 for o in orders]

        total_pnl = sum(pnls)
        win_rate = len(winning) / total if total > 0 else 0
        avg_win = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        gross_gain = sum(gains) if gains else 0
        gross_loss = sum(abs(l) for l in losses) if losses else 0

        value = None
        if metric == "total_pnl":
            value = round(total_pnl, 2)
        if metric == "win_rate":
            value = round(win_rate, 4)
        if metric == "avg_rr":
            value = round(avg_win / avg_loss, 4) if avg_loss > 0 else 0.0
        if metric == "sharpe":
            if total > 1:
                avg_r = sum(pnls) / total
                var = sum((p - avg_r) ** 2 for p in pnls) / (total - 1)
                std = math.sqrt(var)
                value = round((avg_r / std) * math.sqrt(252), 4) if std > 0 else 0.0
            else:
                value = 0.0
        if metric == "sortino":
            if total > 1:
                avg_r = sum(pnls) / total
                neg_returns = [p for p in pnls if p < 0]
                if neg_returns:
                    d_var = sum(p ** 2 for p in neg_returns) / (total - 1)
                    d_std = math.sqrt(d_var)
                    value = round((avg_r / d_std) * math.sqrt(252), 4) if d_std > 0 else 0.0
                else:
                    value = 999.99
            else:
                value = 0.0
        if metric == "calmar":
            peak = 0
            max_dd = 0.0
            cumulative = 0
            for p in pnls:
                cumulative += p
                if cumulative > peak:
                    peak = cumulative
                dd = (peak - cumulative) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            value = round(total_pnl / max_dd, 4) if max_dd > 0 else (999.99 if total_pnl > 0 else 0.0)
        if metric == "max_drawdown":
            peak = 0
            max_dd = 0.0
            cumulative = 0
            for p in pnls:
                cumulative += p
                if cumulative > peak:
                    peak = cumulative
                dd = (peak - cumulative) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            value = round(max_dd, 4)
        if metric == "profit_factor":
            value = round(gross_gain / gross_loss, 4) if gross_loss > 0 else (999.99 if gross_gain > 0 else 0.0)
        if metric == "kelly_optimal":
            odds_ratio = avg_win / avg_loss if avg_loss > 0 else 1
            kelly = (win_rate * odds_ratio - (1 - win_rate)) / odds_ratio if odds_ratio > 0 else 0.0
            value = round(max(0.0, min(1.0, kelly)), 4)
        if metric == "edge":
            value = round(win_rate * avg_win - (1 - win_rate) * avg_loss, 4) if avg_win > 0 and avg_loss > 0 else 0.0
        if metric == "brier_score":
            errors = [o.calibration_error for o in orders if o.calibration_error is not None]
            value = round(sum(errors) / len(errors), 4) if errors else None
        if metric == "trade_count":
            value = total
        if metric == "sqn":
            if total > 1:
                avg_r = sum(pnls) / total
                var = sum((p - avg_r) ** 2 for p in pnls) / (total - 1)
                std = math.sqrt(var)
                value = round((avg_r / std) * math.sqrt(total), 4) if std > 0 else 0.0
            else:
                value = 0.0
        if metric == "recovery_factor":
            peak = 0
            max_dd = 0.0
            cumulative = 0
            for p in pnls:
                cumulative += p
                if cumulative > peak:
                    peak = cumulative
                dd = (peak - cumulative) / peak if peak > 0 else 0
                max_dd = max(max_dd, dd)
            value = round(total_pnl / max_dd, 4) if max_dd > 0 else (999.99 if total_pnl > 0 else 0.0)
        if metric == "largest_win":
            value = round(max(gains), 2) if gains else None
        if metric == "largest_loss":
            value = round(min(-l for l in losses), 2) if losses else None
        if metric == "consecutive_streak":
            streak = 0
            for o in sorted(
                [o for o in orders if o.pnl is not None],
                key=lambda x: x.created_at or datetime.min,
            ):
                if o.pnl > 0:
                    streak = streak + 1 if streak >= 0 else 1
                elif o.pnl < 0:
                    streak = streak - 1 if streak <= 0 else -1
            value = streak

        return {"metric": metric, "value": value, "window": window, "total_available": total_available}

    async def compare_strategies(
        self, strategy_ids: list[str], session: AsyncSession
    ) -> list[dict[str, Any]]:
        comparisons = []
        for sid in strategy_ids:
            perf = await self.get_performance(session=session, strategy_id=sid)
            comparisons.append({
                "strategy_id": sid,
                **perf,
            })
        return comparisons
