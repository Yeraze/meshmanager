"""Database connection and session management."""

import logging
from collections.abc import AsyncGenerator
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    """Return the current UTC time as a timezone-aware datetime."""
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    pass


settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with async_session_maker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Initialize database — run Alembic migrations to head."""
    import asyncio
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy import inspect

    alembic_ini = Path(__file__).parent.parent / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"Alembic config not found: {alembic_ini}")
    alembic_cfg = Config(str(alembic_ini))

    # Check if this is a pre-Alembic database (app tables exist but no alembic_version)
    async with engine.connect() as conn:

        def check_tables(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return "alembic_version" in tables, "nodes" in tables

        has_alembic, has_app_tables = await conn.run_sync(check_tables)

    try:
        if not has_alembic and has_app_tables:
            # v0.5.2 or earlier: tables created by create_all, no migration tracking.
            # Stamp at the last revision that was part of v0.5.2, then upgrade.
            logger.info("Detected pre-migration database, stamping at v0.5.2 baseline...")
            await asyncio.to_thread(command.stamp, alembic_cfg, "d1e2f3g4h5i6")

        logger.info("Running database migrations...")
        await asyncio.to_thread(command.upgrade, alembic_cfg, "head")
        logger.info("Database migrations completed successfully.")
    except Exception:
        logger.exception("Failed to run database migrations")
        raise


async def close_db() -> None:
    """Close database connections."""
    await engine.dispose()
