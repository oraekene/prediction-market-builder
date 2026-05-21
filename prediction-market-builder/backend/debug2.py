import asyncio
import os

from app.main import app
from app.database import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text

DB_FILE = os.path.join(os.path.dirname(__file__), ".pytest_test.db")

async def check():
    # Remove old db
    if os.path.exists(DB_FILE):
        os.remove(DB_FILE)
    
    engine = create_async_engine(f"sqlite+aiosqlite:///{DB_FILE}")
    
    print("Tables in metadata:", sorted(Base.metadata.tables.keys()))
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Now simulate what override_get_session does
    session = async_sessionmaker(engine)()
    async with session:
        try:
            result = await session.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]
            print("Tables in DB:", sorted(tables))
        except Exception as e:
            print(f"Error: {e}")

asyncio.run(check())

# Cleanup
if os.path.exists(DB_FILE):
    os.remove(DB_FILE)
