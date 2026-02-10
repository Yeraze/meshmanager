#!/bin/sh
set -e

# Stamp pre-Alembic databases (v0.5.2 or earlier) at the baseline revision
# so that subsequent `alembic upgrade head` only applies new migrations.
NEEDS_STAMP=$(python -c "
import asyncio
from app.config import get_settings
from sqlalchemy import inspect
from sqlalchemy.ext.asyncio import create_async_engine

async def check():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async with engine.connect() as conn:
        def _check(sync_conn):
            inspector = inspect(sync_conn)
            tables = inspector.get_table_names()
            return 'alembic_version' in tables, 'nodes' in tables
        has_alembic, has_app_tables = await conn.run_sync(_check)
    await engine.dispose()
    if not has_alembic and has_app_tables:
        print('yes')

asyncio.run(check())
")

if [ "$NEEDS_STAMP" = "yes" ]; then
    echo "Detected pre-migration database, stamping at v0.5.2 baseline..."
    python -m alembic stamp d1e2f3g4h5i6
fi

echo "Running database migrations..."
python -m alembic upgrade head
echo "Database migrations completed."

exec "$@"
