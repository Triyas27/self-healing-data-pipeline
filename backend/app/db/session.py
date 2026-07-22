import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.db.base import Base

if settings.database_url.startswith("sqlite+aiosqlite:///") and ":memory:" not in settings.database_url:
    db_dir = os.path.dirname(settings.database_url.removeprefix("sqlite+aiosqlite:///"))
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_async_engine(settings.database_url, connect_args=connect_args)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, autocommit=False, autoflush=False, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as db:
        yield db


async def init_db() -> None:
    from app import models  # noqa: F401 registers model metadata

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
