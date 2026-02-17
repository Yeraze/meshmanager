#!/bin/sh
set -e

# Detect database state:
#   "bootstrap" = fresh empty DB (no alembic_version, no app tables)
#   "stamp"     = pre-Alembic DB (no alembic_version, but has app tables)
#   ""          = normal (has alembic_version, just run migrations)
DB_STATE=$(python -c "
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
        print('stamp')
    elif not has_alembic and not has_app_tables:
        print('bootstrap')

asyncio.run(check())
")

if [ "$DB_STATE" = "bootstrap" ]; then
    echo "Fresh database detected, creating schema..."
    python -c "
import asyncio
from app.database import Base
from app.config import get_settings
from sqlalchemy.ext.asyncio import create_async_engine
import app.models  # noqa: F401 - register all models with Base.metadata

async def create():
    engine = create_async_engine(get_settings().database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()

asyncio.run(create())
"
    echo "Stamping Alembic at head..."
    python -m alembic stamp head
elif [ "$DB_STATE" = "stamp" ]; then
    echo "Detected pre-migration database, stamping at v0.5.2 baseline..."
    python -m alembic stamp d1e2f3g4h5i6
fi

echo "Running database migrations..."
python -m alembic upgrade head
echo "Database migrations completed."

exec "$@"
