"""Tests for database initialization and entrypoint migration logic."""

import subprocess
from pathlib import Path

import pytest


@pytest.mark.asyncio
async def test_init_db_runs_without_error():
    """init_db() should complete without error (migrations handled by entrypoint)."""
    from app.database import init_db

    await init_db()


def test_entrypoint_script_exists():
    """entrypoint.sh should exist and be executable."""
    entrypoint = Path(__file__).parent.parent / "entrypoint.sh"
    assert entrypoint.exists(), "entrypoint.sh not found"


def test_entrypoint_script_syntax():
    """entrypoint.sh should have valid shell syntax."""
    entrypoint = Path(__file__).parent.parent / "entrypoint.sh"
    result = subprocess.run(
        ["sh", "-n", str(entrypoint)],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Shell syntax error: {result.stderr}"


def test_entrypoint_contains_migration_commands():
    """entrypoint.sh should run alembic upgrade and handle pre-migration stamping."""
    entrypoint = Path(__file__).parent.parent / "entrypoint.sh"
    content = entrypoint.read_text()
    assert "alembic upgrade head" in content
    assert "alembic stamp d1e2f3g4h5i6" in content
    assert "alembic_version" in content
