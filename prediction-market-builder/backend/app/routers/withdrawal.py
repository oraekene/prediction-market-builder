from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel

from app.database import get_session
from app.models.user import User
from app.models.safe_wallet import SafeWallet
from app.models.withdrawal_strategy import WithdrawalStrategyModel as WithdrawalStrategy
from app.routers.auth import get_current_user
from app.services.safe_wallet_service import SafeWalletService

router = APIRouter(prefix="/api/withdrawal", tags=["withdrawal"])

safe_wallet_service = SafeWalletService()


class CreateWalletRequest(BaseModel):
    name: str
    currency: str = "USD"


class TransferRequest(BaseModel):
    amount: float
    currency: str = "USD"
    source: str = "paper_trading"
    trigger_type: str = "manual"
    strategy_id: str | None = None


class CreateStrategyRequest(BaseModel):
    name: str
    description: str | None = None
    trigger_type: str = "manual"
    percentage: float = 0.1
    min_amount: float = 10.0
    max_amount: float = 1000.0
    currency: str = "USD"
    target_wallet_id: str | None = None
    conditions: dict = {}
    enabled: bool = True


class UpdateStrategyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger_type: str | None = None
    percentage: float | None = None
    min_amount: float | None = None
    max_amount: float | None = None
    currency: str | None = None
    target_wallet_id: str | None = None
    conditions: dict | None = None
    enabled: bool | None = None


@router.post("/wallets")
async def create_safe_wallet(
    data: CreateWalletRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    wallet = await safe_wallet_service.get_or_create_safe_wallet(
        user_id=current_user.id,
        name=data.name,
        currency=data.currency,
        session=session,
    )
    return {
        "id": wallet.id,
        "name": wallet.name,
        "currency": wallet.currency,
        "balance": wallet.balance,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
    }


@router.get("/wallets")
async def list_safe_wallets(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SafeWallet).where(SafeWallet.user_id == current_user.id)
    )
    wallets = result.scalars().all()
    return [
        {
            "id": w.id,
            "name": w.name,
            "currency": w.currency,
            "balance": w.balance,
            "created_at": w.created_at.isoformat() if w.created_at else None,
        }
        for w in wallets
    ]


@router.get("/wallets/{wallet_id}")
async def get_safe_wallet(
    wallet_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(SafeWallet).where(
            SafeWallet.id == wallet_id,
            SafeWallet.user_id == current_user.id,
        )
    )
    wallet = result.scalar_one_or_none()
    if not wallet:
        raise HTTPException(status_code=404, detail="Safe wallet not found")
    return {
        "id": wallet.id,
        "name": wallet.name,
        "currency": wallet.currency,
        "balance": wallet.balance,
        "created_at": wallet.created_at.isoformat() if wallet.created_at else None,
    }


@router.get("/balance")
async def get_total_balance(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await safe_wallet_service.get_safe_wallet_balance(
        user_id=current_user.id, session=session
    )


@router.post("/transfer")
async def manual_transfer(
    data: TransferRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await safe_wallet_service.transfer_to_safe_wallet(
        user_id=current_user.id,
        amount=data.amount,
        currency=data.currency,
        source=data.source,
        trigger_type=data.trigger_type,
        strategy_id=data.strategy_id,
        session=session,
    )
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result.get("error", "Transfer failed"))
    return result


@router.get("/history")
async def get_withdrawal_history(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    return await safe_wallet_service.get_withdrawal_history(
        user_id=current_user.id, session=session
    )


@router.post("/strategies")
async def create_withdrawal_strategy(
    data: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    strategy = WithdrawalStrategy(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        trigger_type=data.trigger_type,
        percentage=data.percentage,
        min_amount=data.min_amount,
        max_amount=data.max_amount,
        currency=data.currency,
        target_wallet_id=data.target_wallet_id,
        conditions=data.conditions,
        enabled=data.enabled,
    )
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "trigger_type": strategy.trigger_type,
        "percentage": strategy.percentage,
        "min_amount": strategy.min_amount,
        "max_amount": strategy.max_amount,
        "currency": strategy.currency,
        "target_wallet_id": strategy.target_wallet_id,
        "conditions": strategy.conditions,
        "enabled": strategy.enabled,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
    }


@router.get("/strategies")
async def list_withdrawal_strategies(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.user_id == current_user.id
        )
    )
    strategies = result.scalars().all()
    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "trigger_type": s.trigger_type,
            "percentage": s.percentage,
            "min_amount": s.min_amount,
            "max_amount": s.max_amount,
            "currency": s.currency,
            "target_wallet_id": s.target_wallet_id,
            "conditions": s.conditions,
            "enabled": s.enabled,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        }
        for s in strategies
    ]


@router.get("/strategies/{strategy_id}")
async def get_withdrawal_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.id == strategy_id,
            WithdrawalStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "trigger_type": strategy.trigger_type,
        "percentage": strategy.percentage,
        "min_amount": strategy.min_amount,
        "max_amount": strategy.max_amount,
        "currency": strategy.currency,
        "target_wallet_id": strategy.target_wallet_id,
        "conditions": strategy.conditions,
        "enabled": strategy.enabled,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
    }


@router.put("/strategies/{strategy_id}")
async def update_withdrawal_strategy(
    strategy_id: str,
    data: UpdateStrategyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.id == strategy_id,
            WithdrawalStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    if data.name is not None:
        strategy.name = data.name
    if data.description is not None:
        strategy.description = data.description
    if data.trigger_type is not None:
        strategy.trigger_type = data.trigger_type
    if data.percentage is not None:
        strategy.percentage = data.percentage
    if data.min_amount is not None:
        strategy.min_amount = data.min_amount
    if data.max_amount is not None:
        strategy.max_amount = data.max_amount
    if data.currency is not None:
        strategy.currency = data.currency
    if data.target_wallet_id is not None:
        strategy.target_wallet_id = data.target_wallet_id
    if data.conditions is not None:
        strategy.conditions = data.conditions
    if data.enabled is not None:
        strategy.enabled = data.enabled
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "trigger_type": strategy.trigger_type,
        "percentage": strategy.percentage,
        "min_amount": strategy.min_amount,
        "max_amount": strategy.max_amount,
        "currency": strategy.currency,
        "target_wallet_id": strategy.target_wallet_id,
        "conditions": strategy.conditions,
        "enabled": strategy.enabled,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None,
    }


@router.delete("/strategies/{strategy_id}")
async def delete_withdrawal_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.id == strategy_id,
            WithdrawalStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await session.delete(strategy)
    await session.commit()
    return {"status": "deleted"}


@router.post("/strategies/{strategy_id}/evaluate")
async def evaluate_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.id == strategy_id,
            WithdrawalStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")

    wallet_result = await session.execute(
        select(SafeWallet).where(
            SafeWallet.user_id == current_user.id,
            SafeWallet.currency == strategy.currency,
        )
    )
    wallet = wallet_result.scalar_one_or_none()

    current_balance = wallet.balance if wallet else 0.0
    potential_withdrawal = round(current_balance * strategy.percentage, 2)
    within_limits = strategy.min_amount <= potential_withdrawal <= strategy.max_amount

    return {
        "strategy_id": strategy.id,
        "name": strategy.name,
        "trigger_type": strategy.trigger_type,
        "percentage": strategy.percentage,
        "current_balance": current_balance,
        "potential_withdrawal": potential_withdrawal,
        "min_amount": strategy.min_amount,
        "max_amount": strategy.max_amount,
        "within_limits": within_limits,
        "enabled": strategy.enabled,
    }


@router.post("/strategies/{strategy_id}/toggle")
async def toggle_strategy(
    strategy_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(WithdrawalStrategy).where(
            WithdrawalStrategy.id == strategy_id,
            WithdrawalStrategy.user_id == current_user.id,
        )
    )
    strategy = result.scalar_one_or_none()
    if not strategy:
        raise HTTPException(status_code=404, detail="Strategy not found")
    strategy.enabled = not strategy.enabled
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "enabled": strategy.enabled,
    }
