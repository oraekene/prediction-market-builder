import math
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.safe_wallet import SafeWallet, WithdrawalRecord


class SafeWalletService:
    async def get_or_create_safe_wallet(
        self, user_id: str, name: str, currency: str, session: AsyncSession
    ) -> SafeWallet:
        result = await session.execute(
            select(SafeWallet).where(
                SafeWallet.user_id == user_id,
                SafeWallet.name == name,
                SafeWallet.currency == currency,
            )
        )
        wallet = result.scalar_one_or_none()
        if wallet is None:
            wallet = SafeWallet(
                user_id=user_id,
                name=name,
                currency=currency,
                balance=0.0,
            )
            session.add(wallet)
            await session.commit()
            await session.refresh(wallet)
        return wallet

    async def transfer_to_safe_wallet(
        self,
        user_id: str,
        amount: float,
        currency: str,
        source: str,
        trigger_type: str,
        strategy_id: str | None,
        session: AsyncSession,
    ) -> dict:
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return {"success": False, "error": "Amount must be a number"}
        if not math.isfinite(amount) or amount <= 0:
            return {"success": False, "error": "Amount must be a positive finite number"}

        result = await session.execute(
            select(SafeWallet).where(
                SafeWallet.user_id == user_id,
                SafeWallet.currency == currency,
            )
        )
        wallet = result.scalar_one_or_none()
        if not wallet:
            wallet = SafeWallet(
                user_id=user_id,
                name=f"{currency} Safe Wallet",
                currency=currency,
                balance=0.0,
            )
            session.add(wallet)
            await session.flush()

        wallet.balance = round(wallet.balance + amount, 2)

        record = WithdrawalRecord(
            safe_wallet_id=wallet.id,
            user_id=user_id,
            amount=amount,
            currency=currency,
            source=source,
            trigger_type=trigger_type,
            strategy_id=strategy_id,
            status="completed",
        )
        session.add(record)
        await session.commit()
        await session.refresh(wallet)
        await session.refresh(record)

        return {
            "success": True,
            "record_id": record.id,
            "wallet_id": wallet.id,
            "amount": amount,
            "currency": currency,
            "new_balance": wallet.balance,
            "created_at": record.created_at.isoformat() if record.created_at else None,
        }

    async def get_safe_wallet_balance(
        self, user_id: str, session: AsyncSession
    ) -> dict:
        result = await session.execute(
            select(SafeWallet).where(SafeWallet.user_id == user_id)
        )
        wallets = result.scalars().all()

        balances_by_currency: dict[str, float] = {}
        total_usd = 0.0
        wallet_list = []

        for wallet in wallets:
            balances_by_currency[wallet.currency] = balances_by_currency.get(
                wallet.currency, 0.0
            ) + wallet.balance
            wallet_list.append({
                "id": wallet.id,
                "name": wallet.name,
                "currency": wallet.currency,
                "balance": wallet.balance,
                "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
            })

        for currency, balance in balances_by_currency.items():
            if currency in ("USD", "USDC", "USDT", "DAI"):
                total_usd += balance

        return {
            "total_wallets": len(wallets),
            "balances_by_currency": balances_by_currency,
            "total_usd_equivalent": round(total_usd, 2),
            "wallets": wallet_list,
        }

    async def get_withdrawal_history(
        self, user_id: str, session: AsyncSession
    ) -> list[dict]:
        result = await session.execute(
            select(WithdrawalRecord)
            .where(WithdrawalRecord.user_id == user_id)
            .order_by(WithdrawalRecord.created_at.desc())
        )
        records = result.scalars().all()

        return [
            {
                "id": record.id,
                "wallet_id": record.safe_wallet_id,
                "amount": record.amount,
                "currency": record.currency,
                "source": record.source,
                "trigger_type": record.trigger_type,
                "strategy_id": record.strategy_id,
                "status": record.status,
                "created_at": record.created_at.isoformat() if record.created_at else None,
            }
            for record in records
        ]
