"""Add unique constraint to traceroutes table.

Prevents duplicate traceroutes from being inserted on each poll.
Also cleans up existing duplicates by keeping only the first occurrence.

Revision ID: e2f3g4h5i6j7
Revises: d1e2f3g4h5i6
Create Date: 2026-01-28
"""

from alembic import op


# revision identifiers
revision = "e2f3g4h5i6j7"
down_revision = "d1e2f3g4h5i6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # First, remove duplicates keeping only one row per unique key
    # This uses a CTE to identify duplicates and delete them
    # Order by id to keep a deterministic record (first inserted)
    op.execute("""
        DELETE FROM traceroutes
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                    ROW_NUMBER() OVER (
                        PARTITION BY source_id, from_node_num, to_node_num, received_at
                        ORDER BY id
                    ) as row_num
                FROM traceroutes
            ) t
            WHERE t.row_num > 1
        )
    """)

    # Now add the unique constraint (IF NOT EXISTS for crash-recovery idempotency)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_traceroutes_unique
        ON traceroutes (source_id, from_node_num, to_node_num, received_at)
    """)


def downgrade() -> None:
    op.drop_index("idx_traceroutes_unique", table_name="traceroutes")
