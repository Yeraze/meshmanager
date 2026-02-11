"""Add route_positions JSONB column to traceroutes table.

Stores historical node positions at the time a traceroute was completed,
so the map draws routes to the correct (historical) locations even if
nodes have moved since.

Revision ID: q4r5s6t7u8v9
Revises: p3q4r5s6t7u8
Create Date: 2026-02-11
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "q4r5s6t7u8v9"
down_revision: str = "p3q4r5s6t7u8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        sa.text("""
            ALTER TABLE traceroutes
            ADD COLUMN IF NOT EXISTS route_positions JSONB
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            ALTER TABLE traceroutes
            DROP COLUMN IF EXISTS route_positions
        """)
    )
