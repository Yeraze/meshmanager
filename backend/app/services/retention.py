"""Data retention cleanup service."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select

from app.database import async_session_maker
from app.models import Message, SystemSetting, Telemetry, Traceroute

logger = logging.getLogger(__name__)

# Default retention periods (days)
DEFAULT_RETENTION = {
    "messages": 30,
    "telemetry": 7,
    "traceroutes": 30,
}


async def get_retention_settings() -> dict[str, int]:
    """Get retention settings from database or use defaults."""
    async with async_session_maker() as db:
        result = await db.execute(
            select(SystemSetting).where(SystemSetting.key.like("retention.%"))
        )
        settings = result.scalars().all()

        retention = DEFAULT_RETENTION.copy()
        for setting in settings:
            key = setting.key.replace("retention.", "")
            if key in retention and isinstance(setting.value, dict):
                retention[key] = setting.value.get("days", retention[key])

        return retention


async def cleanup_old_data() -> dict[str, int]:
    """Delete data older than retention period. Returns count of deleted rows."""
    retention = await get_retention_settings()
    deleted = {}

    async with async_session_maker() as db:
        # Clean messages
        cutoff = datetime.now(UTC) - timedelta(days=retention["messages"])
        result = await db.execute(
            delete(Message).where(Message.received_at < cutoff)
        )
        deleted["messages"] = result.rowcount
        logger.info(f"Deleted {result.rowcount} messages older than {retention['messages']} days")

        # Clean telemetry
        cutoff = datetime.now(UTC) - timedelta(days=retention["telemetry"])
        result = await db.execute(
            delete(Telemetry).where(Telemetry.received_at < cutoff)
        )
        deleted["telemetry"] = result.rowcount
        logger.info(
            f"Deleted {result.rowcount} telemetry records older than {retention['telemetry']} days"
        )

        # Clean traceroutes
        cutoff = datetime.now(UTC) - timedelta(days=retention["traceroutes"])
        result = await db.execute(
            delete(Traceroute).where(Traceroute.received_at < cutoff)
        )
        deleted["traceroutes"] = result.rowcount
        logger.info(
            f"Deleted {result.rowcount} traceroutes older than {retention['traceroutes']} days"
        )

        await db.commit()

    return deleted


class RetentionService:
    """Background service for data retention cleanup."""

    def __init__(self, interval_hours: int = 24):
        self._interval = interval_hours * 3600
        self._running = False
        self._task: asyncio.Task | None = None

    async def start(self) -> None:
        """Start the retention cleanup service."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._cleanup_loop())
        logger.info("Started retention cleanup service")

    async def _cleanup_loop(self) -> None:
        """Periodic cleanup loop."""
        while self._running:
            try:
                await cleanup_old_data()
            except Exception as e:
                logger.error(f"Retention cleanup error: {e}")

            await asyncio.sleep(self._interval)

    async def stop(self) -> None:
        """Stop the retention cleanup service."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped retention cleanup service")


# Global retention service instance
retention_service = RetentionService()
