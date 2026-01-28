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
    # First, remove duplicates keeping only the row with the earliest id (first inserted)
    # This uses a CTE to identify duplicates and delete them
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

    # Now add the unique constraint
    op.create_index(
        "idx_traceroutes_unique",
        "traceroutes",
        ["source_id", "from_node_num", "to_node_num", "received_at"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_traceroutes_unique", table_name="traceroutes")
