import asyncio
import os
import uuid
from datetime import datetime, timezone
from passlib.context import CryptContext
from sqlalchemy import select

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def seed():
    from app.database import async_session
    from app.models import User, Strategy, RiskTemplate

    async with async_session() as session:
        result = await session.execute(select(User).limit(1))
        if result.scalar_one_or_none() is not None:
            print("Database already has users — skipping seed")
            return

        admin_password = os.environ.get("ADMIN_PASSWORD", "admin123")
        admin = User(
            id=str(uuid.uuid4()),
            email="admin@pmbuilder.io",
            hashed_password=pwd_context.hash(admin_password),
            display_name="Admin",
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            preferences={},
        )
        session.add(admin)
        await session.flush()

        strategies = [
            Strategy(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Momentum Strategy",
                description="Captures trending markets by entering positions with strong recent price momentum and trailing stop-losses.",
                status="active",
                mode="automated",
                nodes=[
                    {"id": "1", "type": "signal", "params": {"indicator": "rsi", "period": 14}},
                    {"id": "2", "type": "filter", "params": {"min_volume": 100000}},
                    {"id": "3", "type": "execution", "params": {"slippage": 0.001}},
                ],
                edges=[{"from": "1", "to": "2"}, {"from": "2", "to": "3"}],
                risk_profile={
                    "max_position_size": 0.1,
                    "stop_loss": 0.05,
                    "take_profit": 0.15,
                    "max_drawdown": 0.25,
                },
                version=1,
                version_history=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Strategy(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Mean Reversion Strategy",
                description="Profits from temporary price deviations by entering contrarian positions when assets are statistically overbought or oversold.",
                status="draft",
                mode="chat",
                nodes=[
                    {"id": "1", "type": "signal", "params": {"indicator": "bollinger", "period": 20, "std": 2}},
                    {"id": "2", "type": "filter", "params": {"z_score_threshold": 1.5}},
                    {"id": "3", "type": "execution", "params": {"hedge_ratio": 0.5}},
                ],
                edges=[{"from": "1", "to": "2"}, {"from": "2", "to": "3"}],
                risk_profile={
                    "max_position_size": 0.08,
                    "stop_loss": 0.03,
                    "take_profit": 0.08,
                    "max_drawdown": 0.15,
                },
                version=1,
                version_history=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            Strategy(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Hedging Strategy",
                description="Pairs correlated assets to neutralize directional risk while capturing relative value inefficiencies between prediction markets.",
                status="active",
                mode="automated",
                nodes=[
                    {"id": "1", "type": "signal", "params": {"indicator": "correlation", "window": 30}},
                    {"id": "2", "type": "filter", "params": {"min_spread": 0.02}},
                    {"id": "3", "type": "execution", "params": {"pair_trade": True}},
                ],
                edges=[{"from": "1", "to": "2"}, {"from": "2", "to": "3"}],
                risk_profile={
                    "max_position_size": 0.15,
                    "stop_loss": 0.04,
                    "take_profit": 0.12,
                    "max_drawdown": 0.20,
                },
                version=1,
                version_history=[],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        session.add_all(strategies)

        risk_templates = [
            RiskTemplate(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Conservative",
                description="Low-risk profile focused on capital preservation. Suitable for cautious traders.",
                rules=[
                    {"key": "max_position_size", "value": 0.05, "operator": "lte"},
                    {"key": "max_drawdown", "value": 0.10, "operator": "lte"},
                    {"key": "stop_loss", "value": 0.02, "operator": "lte"},
                    {"key": "leverage", "value": 1.0, "operator": "eq"},
                ],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            RiskTemplate(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Moderate",
                description="Balanced risk profile targeting steady growth with controlled drawdowns.",
                rules=[
                    {"key": "max_position_size", "value": 0.10, "operator": "lte"},
                    {"key": "max_drawdown", "value": 0.20, "operator": "lte"},
                    {"key": "stop_loss", "value": 0.05, "operator": "lte"},
                    {"key": "leverage", "value": 2.0, "operator": "lte"},
                ],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
            RiskTemplate(
                id=str(uuid.uuid4()),
                user_id=admin.id,
                name="Aggressive",
                description="High-risk profile for experienced traders seeking maximum returns.",
                rules=[
                    {"key": "max_position_size", "value": 0.25, "operator": "lte"},
                    {"key": "max_drawdown", "value": 0.40, "operator": "lte"},
                    {"key": "stop_loss", "value": 0.10, "operator": "lte"},
                    {"key": "leverage", "value": 3.0, "operator": "lte"},
                ],
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ),
        ]
        session.add_all(risk_templates)

        await session.commit()
        print(f"Seeded: admin user ({admin.email}), {len(strategies)} strategies, {len(risk_templates)} risk templates")


if __name__ == "__main__":
    asyncio.run(seed())
