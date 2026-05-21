import asyncio
from app.main import app
from app.database import Base
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def check():
    print("Tables in metadata:", sorted(Base.metadata.tables.keys()))
    e = create_async_engine("sqlite+aiosqlite://")
    async with e.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with e.connect() as conn:
        r = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
        print("Created tables:", sorted([row[0] for row in r]))

asyncio.run(check())
