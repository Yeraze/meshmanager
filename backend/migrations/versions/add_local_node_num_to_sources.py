"""Add local_node_num to sources table.

Stores the authoritative local node number fetched from MeshMonitor's
/api/status endpoint, replacing the unreliable hops_away=0 heuristic.

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2026-03-11

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c3d4e5f6g7h8"
down_revision: str = "b2c3d4e5f6g7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE sources
        ADD COLUMN IF NOT EXISTS local_node_num BIGINT
    """)


def downgrade() -> None:
    op.execute("""
        ALTER TABLE sources
        DROP COLUMN IF EXISTS local_node_num
    """)
