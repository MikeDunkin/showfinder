import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://carshow:Ch@ngeMe2026!@postgres:5432/carshowdb")

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    import asyncio
    for attempt in range(10):
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("[db] connected and tables ready", flush=True)
            return
        except Exception as e:
            wait = 2 ** attempt
            print(f"[db] connection failed (attempt {attempt + 1}/10): {e} — retrying in {wait}s", flush=True)
            await asyncio.sleep(wait)
    raise RuntimeError("Could not connect to database after 10 attempts")
