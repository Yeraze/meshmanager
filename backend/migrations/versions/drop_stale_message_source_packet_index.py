"""Drop stale ix_messages_source_packet unique index.

The gateway_node_num migration intended to drop this 2-column index and
replace it with the 3-column idx_messages_source_packet_gateway index,
but it referenced the wrong name (idx_ instead of ix_).  The stale
index causes ON CONFLICT mismatches and noisy duplicate-key errors.

Revision ID: r5s6t7u8v9w0
Revises: q4r5s6t7u8v9
Create Date: 2026-02-12
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "r5s6t7u8v9w0"
down_revision: str = "q4r5s6t7u8v9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop the stale 2-column unique index that was missed by the
    # gateway_node_num migration (which tried to drop idx_ not ix_)
    op.execute(
        sa.text("DROP INDEX IF EXISTS ix_messages_source_packet")
    )
    # Also drop the wrong-name variant in case it exists on some databases
    op.execute(
        sa.text("DROP INDEX IF EXISTS idx_messages_source_packet")
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_messages_source_packet
            ON messages (source_id, packet_id)
        """)
    )
