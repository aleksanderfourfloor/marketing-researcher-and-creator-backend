"""Async SQLite database setup with SQLAlchemy and aiosqlite."""
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


# Use same URL but ensure aiosqlite driver for async
DATABASE_URL = (
    settings.DATABASE_URL
    if settings.DATABASE_URL.startswith("sqlite+aiosqlite")
    else settings.DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://", 1)
)

engine = create_async_engine(
    DATABASE_URL,
    echo=settings.DEBUG,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class for all ORM models."""

    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that yields an async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager for async database session (e.g. in background tasks)."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """Create all tables. Call on application startup."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Dispose engine on shutdown."""
    await engine.dispose()


# Sync engine/session for Celery workers (SQLite sync driver)
SYNC_DATABASE_URL = DATABASE_URL.replace("sqlite+aiosqlite", "sqlite")
_sync_engine = None
_SyncSessionLocal = None


def get_sync_session():
    """Return a sync session factory for use in Celery. Lazy init."""
    global _sync_engine, _SyncSessionLocal
    if _sync_engine is None:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        _sync_engine = create_engine(
            SYNC_DATABASE_URL,
            echo=settings.DEBUG,
            connect_args={"check_same_thread": False} if "sqlite" in SYNC_DATABASE_URL else {},
        )
        _SyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_sync_engine)
    return _SyncSessionLocal()
