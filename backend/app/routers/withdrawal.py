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


def _validate_steps(steps: list) -> None:
    if not isinstance(steps, list):
        raise HTTPException(status_code=400, detail="steps must be a list")
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            raise HTTPException(status_code=400, detail=f"step {i} must be an object")
        action = step.get("action", {})
        atype = action.get("type", "")
        if atype in ("withdraw_pct", "convert_to_stablecoin") and "pct" in action:
            pct = action["pct"]
            if not isinstance(pct, (int, float)) or pct < 0 or pct > 100:
                raise HTTPException(status_code=400, detail=f"step {i}: pct must be between 0 and 100")
        if atype in ("withdraw_fixed", "convert_to_stablecoin") and "amount" in action:
            amount = action["amount"]
            if not isinstance(amount, (int, float)) or amount < 0:
                raise HTTPException(status_code=400, detail=f"step {i}: amount must be non-negative")


class CreateWalletRequest(BaseModel):
    name: str
    currency: str = "USDC"


class TransferRequest(BaseModel):
    amount: float
    currency: str = "USDC"
    source: str = "profits"
    trigger_type: str = "manual"
    strategy_id: str | None = None


class CreateStrategyRequest(BaseModel):
    name: str
    description: str | None = None
    steps: list = []
    safe_wallet_id: str | None = None


class UpdateStrategyRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    steps: list | None = None
    is_active: bool | None = None
    safe_wallet_id: str | None = None


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
        "is_disconnected": wallet.is_disconnected,
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
            "is_disconnected": w.is_disconnected,
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
        "is_disconnected": wallet.is_disconnected,
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
    # Internal ledger entry. There is no payout path consuming this balance
    # today; if one is added, transfers must be derived from verified
    # exchange/on-chain balances instead of client-asserted amounts.
    if data.amount > 1_000_000:
        raise HTTPException(status_code=400, detail="Transfer amount exceeds cap")
    result = await safe_wallet_service.transfer_to_safe_wallet(
        user_id=current_user.id,
        amount=data.amount,
        currency=data.currency,
        source=data.source,
        trigger_type=data.trigger_type,
        strategy_id=data.strategy_id,
        session=session,
    )
    if not result.get("success", True):
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


@router.post("/strategies", status_code=201)
async def create_withdrawal_strategy(
    data: CreateStrategyRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    _validate_steps(data.steps)
    strategy = WithdrawalStrategy(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        steps=data.steps,
        safe_wallet_id=data.safe_wallet_id,
    )
    session.add(strategy)
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "is_active": strategy.is_active,
        "steps": strategy.steps,
        "safe_wallet_id": strategy.safe_wallet_id,
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
            "is_active": s.is_active,
            "steps": s.steps,
            "safe_wallet_id": s.safe_wallet_id,
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
        "is_active": strategy.is_active,
        "steps": strategy.steps,
        "step_states": strategy.step_states,
        "safe_wallet_id": strategy.safe_wallet_id,
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
    if data.steps is not None:
        _validate_steps(data.steps)
        strategy.steps = data.steps
    if data.is_active is not None:
        strategy.is_active = data.is_active
    if data.safe_wallet_id is not None:
        strategy.safe_wallet_id = data.safe_wallet_id
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "description": strategy.description,
        "is_active": strategy.is_active,
        "steps": strategy.steps,
        "safe_wallet_id": strategy.safe_wallet_id,
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
async def evaluate_withdrawal_strategy(
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

    steps = strategy.steps or []
    step_states = strategy.step_states or {}
    triggered_steps = []

    for i, step in enumerate(steps):
        step_id = step.get("id", str(i))
        state = step_states.get(step_id, {"status": "pending"})
        if step.get("once", True) and state.get("status") == "executed":
            continue
        condition = step.get("condition", {})
        triggered_steps.append({
            "step_id": step_id,
            "condition_type": condition.get("type", "unknown"),
            "status": state.get("status", "pending"),
        })

    return {
        "strategy_id": strategy.id,
        "name": strategy.name,
        "is_active": strategy.is_active,
        "total_steps": len(steps),
        "triggered_steps": triggered_steps,
    }


@router.post("/strategies/{strategy_id}/toggle")
async def toggle_withdrawal_strategy(
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
    strategy.is_active = not strategy.is_active
    await session.commit()
    await session.refresh(strategy)
    return {
        "id": strategy.id,
        "name": strategy.name,
        "is_active": strategy.is_active,
    }
