#!/usr/bin/env python3
"""One-time fix for MQTT message timestamps that were stored 5 hours ahead.

Root cause: datetime.utcnow() returns a naive datetime. asyncpg treats naive
datetimes as local time (e.g. EST/UTC-5), then converts to UTC for TIMESTAMPTZ
columns -- adding 5 hours.

This script subtracts 5 hours from all messages that came from MQTT sources.

Usage:
    docker exec meshmanager-backend-dev python scripts/fix_mqtt_timestamps.py
"""

import asyncio
import sys

sys.path.insert(0, "/app")

from sqlalchemy import text

from app.database import async_session_maker


async def fix_mqtt_timestamps() -> None:
    """Subtract 5 hours from MQTT-sourced message timestamps."""
    async with async_session_maker() as session:
        result = await session.execute(
            text("""
                UPDATE messages
                SET received_at = received_at - INTERVAL '5 hours'
                WHERE source_id IN (
                    SELECT id FROM sources WHERE type = 'MQTT'::sourcetype
                )
            """)
        )
        await session.commit()
        print(f"Updated {result.rowcount} MQTT message timestamps.")


if __name__ == "__main__":
    asyncio.run(fix_mqtt_timestamps())
