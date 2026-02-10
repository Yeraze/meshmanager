"""Tests for init_db() migration logic."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def mock_engine():
    """Mock the database engine for init_db tests."""
    mock_async_conn = AsyncMock()
    mock_async_conn.run_sync = AsyncMock()
    mock_async_conn.__aenter__ = AsyncMock(return_value=mock_async_conn)
    mock_async_conn.__aexit__ = AsyncMock(return_value=False)

    mock_eng = MagicMock()
    mock_eng.connect = MagicMock(return_value=mock_async_conn)

    return mock_eng, mock_async_conn


def _make_check_tables_side_effect(has_alembic: bool, has_app_tables: bool):
    """Create a side effect for run_sync that returns the given table state."""

    async def run_sync_side_effect(fn):
        return has_alembic, has_app_tables

    return run_sync_side_effect


@pytest.mark.asyncio
async def test_init_db_fresh_install(mock_engine):
    """Fresh database (no tables) — should only call upgrade, not stamp."""
    mock_eng, mock_async_conn = mock_engine
    mock_async_conn.run_sync.side_effect = _make_check_tables_side_effect(
        has_alembic=False, has_app_tables=False
    )

    with (
        patch("app.database.engine", mock_eng),
        patch("alembic.command.upgrade") as mock_upgrade,
        patch("alembic.command.stamp") as mock_stamp,
        patch("pathlib.Path.exists", return_value=True),
    ):
        from app.database import init_db

        await init_db()

        mock_stamp.assert_not_called()
        mock_upgrade.assert_called_once()
        assert mock_upgrade.call_args[0][1] == "head"


@pytest.mark.asyncio
async def test_init_db_pre_alembic_database(mock_engine):
    """Pre-Alembic database (app tables but no alembic_version) — should stamp then upgrade."""
    mock_eng, mock_async_conn = mock_engine
    mock_async_conn.run_sync.side_effect = _make_check_tables_side_effect(
        has_alembic=False, has_app_tables=True
    )

    with (
        patch("app.database.engine", mock_eng),
        patch("alembic.command.upgrade") as mock_upgrade,
        patch("alembic.command.stamp") as mock_stamp,
        patch("pathlib.Path.exists", return_value=True),
    ):
        from app.database import init_db

        await init_db()

        mock_stamp.assert_called_once()
        assert mock_stamp.call_args[0][1] == "d1e2f3g4h5i6"
        mock_upgrade.assert_called_once()
        assert mock_upgrade.call_args[0][1] == "head"


@pytest.mark.asyncio
async def test_init_db_normal_upgrade(mock_engine):
    """Normal upgrade (alembic_version exists) — should only call upgrade, not stamp."""
    mock_eng, mock_async_conn = mock_engine
    mock_async_conn.run_sync.side_effect = _make_check_tables_side_effect(
        has_alembic=True, has_app_tables=True
    )

    with (
        patch("app.database.engine", mock_eng),
        patch("alembic.command.upgrade") as mock_upgrade,
        patch("alembic.command.stamp") as mock_stamp,
        patch("pathlib.Path.exists", return_value=True),
    ):
        from app.database import init_db

        await init_db()

        mock_stamp.assert_not_called()
        mock_upgrade.assert_called_once()
        assert mock_upgrade.call_args[0][1] == "head"


@pytest.mark.asyncio
async def test_init_db_migration_failure_raises(mock_engine):
    """Migration failure should log and re-raise the exception."""
    mock_eng, mock_async_conn = mock_engine
    mock_async_conn.run_sync.side_effect = _make_check_tables_side_effect(
        has_alembic=True, has_app_tables=True
    )

    with (
        patch("app.database.engine", mock_eng),
        patch("alembic.command.upgrade", side_effect=RuntimeError("migration failed")),
        patch("alembic.command.stamp"),
        patch("pathlib.Path.exists", return_value=True),
    ):
        from app.database import init_db

        with pytest.raises(RuntimeError, match="migration failed"):
            await init_db()


@pytest.mark.asyncio
async def test_init_db_missing_alembic_ini():
    """Missing alembic.ini should raise FileNotFoundError."""
    with patch("pathlib.Path.exists", return_value=False):
        from app.database import init_db

        with pytest.raises(FileNotFoundError, match="alembic.ini"):
            await init_db()
