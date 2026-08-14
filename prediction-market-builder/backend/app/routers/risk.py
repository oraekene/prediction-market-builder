from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_session
from app.models.trade import Trade, TradeStatus
from app.models.user import User
from app.routers.auth import get_current_user
from app.services.risk_calculator import RiskCalculator
from app.services.portfolio_manager import PortfolioManager
from app.services.tabpfn_integration import TabPFNQuantileEstimator

router = APIRouter(prefix="/api/risk", tags=["risk"])
calc = RiskCalculator()
pm = PortfolioManager()
tabpfn_est = TabPFNQuantileEstimator()


@router.get("/summary")
async def risk_summary(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.EXECUTED, Trade.user_id == current_user.id)
        .order_by(Trade.created_at.asc())
        .limit(100)
    )
    trades = rows.scalars().all()
    pnls = [float(t.pnl or 0) for t in trades]
    capital_series = _build_capital_series(trades)
    positions = _build_positions(trades)
    var_95 = calc.historical_var(pnls, 0.95)
    es_95 = calc.expected_shortfall(pnls, 0.95)
    max_dd = calc.max_drawdown(capital_series) if capital_series else 0.0
    current_dd = calc.current_drawdown(max(capital_series) if capital_series else 10000,
                                        capital_series[-1] if capital_series else 10000)
    conc = calc.concentration(positions)
    vol = calc.portfolio_volatility(pnls)
    return {
        "var_95": round(var_95, 4),
        "es_95": round(es_95, 4),
        "max_drawdown": round(max_dd, 4),
        "current_drawdown": round(current_dd, 4),
        "concentration": round(conc, 4),
        "portfolio_volatility": round(vol, 4),
    }


@router.get("/var")
async def risk_var(
    confidence: float = Query(0.95, ge=0.5, le=0.999),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED, Trade.user_id == current_user.id)
    )
    pnls = [float(t.pnl or 0) for t in rows.scalars().all()]
    hist = calc.historical_var(pnls, confidence)
    para = calc.parametric_var(pnls, confidence)
    tabpfn_val = None
    if len(pnls) > 20:
        tabpfn_val = round(await tabpfn_est.estimate_var(returns=pnls, confidence=confidence), 4)
    return {
        "historical": round(hist, 4),
        "parametric": round(para, 4),
        "tabpfn": tabpfn_val,
        "confidence": confidence,
    }


@router.get("/correlation")
async def risk_correlation(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED, Trade.user_id == current_user.id)
    )
    trades = rows.scalars().all()
    by_market: dict[str, list[float]] = {}
    for t in trades:
        mid = t.market_id
        if mid not in by_market:
            by_market[mid] = []
        by_market[mid].append(float(t.pnl or 0))
    filtered = {k: v for k, v in by_market.items() if len(v) >= 3}
    pairs = []
    assets = list(filtered.keys())
    for i in range(len(assets)):
        for j in range(i + 1, len(assets)):
            min_len = min(len(filtered[assets[i]]), len(filtered[assets[j]]))
            a_ret = filtered[assets[i]][:min_len]
            b_ret = filtered[assets[j]][:min_len]
            try:
                corr_matrix = calc.correlation_matrix({assets[i]: a_ret, assets[j]: b_ret})
                val = corr_matrix[assets[i]][assets[j]]
                pairs.append({"asset_a": assets[i], "asset_b": assets[j], "correlation": val})
            except ZeroDivisionError:
                continue
    return {"pairs": pairs, "total_assets": len(assets)}


@router.get("/drawdown")
async def risk_drawdown(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(Trade)
        .where(Trade.status == TradeStatus.EXECUTED, Trade.user_id == current_user.id)
        .order_by(Trade.created_at.asc())
    )
    trades = rows.scalars().all()
    capital_series = _build_capital_series(trades)
    if not capital_series:
        return {"current_drawdown": 0.0, "peak_capital": 10000, "current_capital": 10000, "max_drawdown": 0.0}
    peak = max(capital_series)
    current = capital_series[-1]
    max_dd = calc.max_drawdown(capital_series)
    current_dd = calc.current_drawdown(peak, current)
    return {
        "current_drawdown": round(current_dd, 4),
        "peak_capital": round(peak, 2),
        "current_capital": round(current, 2),
        "max_drawdown": round(max_dd, 4),
    }


@router.get("/portfolio")
async def risk_portfolio(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    rows = await session.execute(
        select(Trade).where(Trade.status == TradeStatus.EXECUTED, Trade.user_id == current_user.id)
    )
    trades = rows.scalars().all()
    positions = _build_positions(trades)
    by_market: dict[str, list[float]] = {}
    for t in trades:
        by_market.setdefault(t.market_id, []).append(float(t.pnl or 0))
    total = sum(p["size"] for p in positions)
    enriched = []
    for p in positions:
        market_pnls = by_market.get(p["market_id"], [])
        market_var = calc.historical_var(market_pnls, 0.95) if market_pnls else 0.0
        weight = p["size"] / total if total > 0 else 0
        enriched.append({
            "market_id": p["market_id"],
            "size": round(p["size"], 2),
            "var_contribution": round(market_var, 4),
            "concentration_pct": round(weight * 100, 2),
        })
    return {"positions": enriched}


def _build_capital_series(trades: list) -> list[float]:
    capital = 10000.0
    series = [capital]
    for t in trades:
        capital += float(t.pnl or 0)
        series.append(round(capital, 2))
    return series


def _build_positions(trades: list) -> list[dict]:
    agg: dict[str, float] = {}
    for t in trades:
        mid = t.market_id
        agg[mid] = agg.get(mid, 0) + float(t.amount or 0)
    return [{"market_id": mid, "size": size} for mid, size in agg.items()]
