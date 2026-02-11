"""Integration tests for Alembic migrations.

Verifies that the full migration chain can run against a fresh database
and that running it twice is idempotent (no errors on re-run).

Tests marked ``integration`` are skipped unless TEST_DATABASE_URL points
at a PostgreSQL instance — the migrations use PostgreSQL-specific SQL.
"""

from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory


def _get_alembic_cfg() -> Config:
    """Return an Alembic Config pointing at the backend directory."""
    backend_dir = Path(__file__).resolve().parent.parent
    cfg = Config(str(backend_dir / "alembic.ini"))
    cfg.set_main_option("script_location", str(backend_dir / "migrations"))
    return cfg


def test_set_missing_server_defaults_revision_exists():
    """The set_missing_server_defaults migration exists and chains correctly."""
    cfg = _get_alembic_cfg()
    script_dir = ScriptDirectory.from_config(cfg)

    rev = script_dir.get_revision("p3q4r5s6t7u8")
    assert rev is not None, "Revision p3q4r5s6t7u8 not found"
    assert rev.down_revision == "o2p3q4r5s6t7", (
        f"Expected down_revision 'o2p3q4r5s6t7', got '{rev.down_revision}'"
    )


def test_add_route_positions_is_head():
    """The add_route_positions_to_traceroutes migration should be the current head."""
    cfg = _get_alembic_cfg()
    script_dir = ScriptDirectory.from_config(cfg)

    heads = script_dir.get_heads()
    assert "q4r5s6t7u8v9" in heads, f"Expected q4r5s6t7u8v9 in heads, got {heads}"


def test_model_server_defaults_present():
    """All NOT NULL columns with Python defaults should declare server_default.

    This duplicates what ``scripts/validate_server_defaults.py`` checks,
    but runs as part of the standard pytest suite.
    """
    from sqlalchemy import DateTime

    from app.database import Base

    # Import all models to register them with Base.metadata
    from app.models import (  # noqa: F401
        Channel,
        Message,
        Node,
        Source,
        User,
    )

    missing: list[str] = []
    for table in Base.metadata.sorted_tables:
        for column in table.columns:
            if column.primary_key or column.foreign_keys or column.nullable:
                continue
            if isinstance(column.type, DateTime):
                continue
            if column.default is None:
                continue
            if column.server_default is None:
                missing.append(f"{table.name}.{column.name}")

    assert not missing, (
        f"Columns with Python default but no server_default: {', '.join(missing)}"
    )


@pytest.mark.integration
def test_alembic_upgrade_head_fresh_db():
    """Run alembic upgrade head on a fresh PostgreSQL database."""
    import os

    from alembic import command
    from sqlalchemy import create_engine, text

    db_url = os.environ.get("TEST_DATABASE_URL", "")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")

    # Convert async URL to sync for alembic
    sync_url = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")

    cfg = _get_alembic_cfg()
    cfg.set_main_option("sqlalchemy.url", sync_url)

    # Run upgrade head
    command.upgrade(cfg, "head")

    # Verify the anonymous user exists with correct defaults
    engine = create_engine(sync_url)
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, is_anonymous, role, is_active FROM users WHERE username = 'anonymous'")
        )
        row = result.fetchone()
        assert row is not None, "Anonymous user not found after upgrade"
        assert row.is_anonymous is True
        assert row.role == "user"
        assert row.is_active is True

    engine.dispose()


@pytest.mark.integration
def test_alembic_upgrade_head_idempotent():
    """Running alembic upgrade head twice should not error (idempotency)."""
    import os

    from alembic import command

    db_url = os.environ.get("TEST_DATABASE_URL", "")
    if not db_url:
        pytest.skip("TEST_DATABASE_URL not set")

    sync_url = db_url.replace("+asyncpg", "").replace("+aiosqlite", "")

    cfg = _get_alembic_cfg()
    cfg.set_main_option("sqlalchemy.url", sync_url)

    # First run
    command.upgrade(cfg, "head")

    # Second run — should be a no-op, not an error
    command.upgrade(cfg, "head")
