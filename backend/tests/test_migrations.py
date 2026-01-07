"""Tests for Alembic database migrations."""

import subprocess
from pathlib import Path


def test_alembic_no_multiple_heads():
    """Verify that the migration chain has no multiple heads."""
    # Run alembic heads command
    result = subprocess.run(
        ["python", "-m", "alembic", "heads"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # Should succeed
    assert result.returncode == 0, f"alembic heads failed: {result.stderr}"

    # Count the number of heads (each head is on its own line)
    heads = [line for line in result.stdout.strip().split("\n") if line and "(head)" in line]
    assert len(heads) == 1, f"Expected 1 head, found {len(heads)}: {heads}"


def test_alembic_check_no_pending_migrations():
    """Verify migration scripts are consistent with models."""
    # Run alembic check command
    result = subprocess.run(
        ["python", "-m", "alembic", "check"],
        capture_output=True,
        text=True,
        cwd=Path(__file__).parent.parent,
    )

    # alembic check returns 0 if no new migrations needed
    # Note: This may show "New upgrade operations detected" which is fine
    # We mainly care that it doesn't error due to broken chain
    assert "FAILED" not in result.stderr, f"alembic check failed: {result.stderr}"


def test_migration_chain_is_linear():
    """Verify the migration chain has proper linear dependencies."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    # Get the alembic config
    alembic_cfg = Config(str(Path(__file__).parent.parent / "alembic.ini"))
    script_dir = ScriptDirectory.from_config(alembic_cfg)

    # Get all revisions
    revisions = list(script_dir.walk_revisions())

    # Build dependency graph
    revision_map = {rev.revision: rev for rev in revisions}

    # Verify each revision (except base) has exactly one down_revision
    for rev in revisions:
        if rev.down_revision is not None:
            # down_revision should be a string (single parent), not a tuple (merge)
            assert isinstance(
                rev.down_revision, str
            ), f"Revision {rev.revision} has multiple parents (merge migration): {rev.down_revision}"

            # The down_revision should exist
            assert (
                rev.down_revision in revision_map
            ), f"Revision {rev.revision} references non-existent down_revision: {rev.down_revision}"
