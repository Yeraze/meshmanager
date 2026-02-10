"""Add gateway_node_num to messages and update unique index.

Stores the MQTT gateway node that uploaded each packet, enabling
per-gateway message retention (no more cross-gateway dedup) and
smarter relay node resolution.

Revision ID: n1o2p3q4r5s6
Revises: m0n1o2p3q4r5
Create Date: 2026-02-10
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "n1o2p3q4r5s6"
down_revision: str = "m0n1o2p3q4r5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the gateway_node_num column
    op.execute(
        sa.text("""
            ALTER TABLE messages
            ADD COLUMN IF NOT EXISTS gateway_node_num BIGINT
        """)
    )

    # Drop the old unique index and create the new one that includes gateway
    op.execute(
        sa.text("""
            DROP INDEX IF EXISTS idx_messages_source_packet
        """)
    )
    op.execute(
        sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_source_packet_gateway
            ON messages (source_id, packet_id, gateway_node_num)
        """)
    )


def downgrade() -> None:
    op.execute(
        sa.text("""
            DROP INDEX IF EXISTS idx_messages_source_packet_gateway
        """)
    )
    op.execute(
        sa.text("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_messages_source_packet
            ON messages (source_id, packet_id)
        """)
    )
    op.execute(
        sa.text("""
            ALTER TABLE messages
            DROP COLUMN IF EXISTS gateway_node_num
        """)
    )
