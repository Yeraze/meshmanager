"""Add meshtastic_id column to messages for cross-source deduplication.

The raw Meshtastic packet ID is stored as an integer, enabling deduplication
across sources that use different packet_id formats (MeshMonitor composite
'{from_node}_{id}' vs MQTT raw '{id}').

Revision ID: g4h5i6j7k8l9
Revises: f3g4h5i6j7k8
Create Date: 2026-02-06
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "g4h5i6j7k8l9"
down_revision = "f3g4h5i6j7k8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add the column
    op.add_column("messages", sa.Column("meshtastic_id", sa.BigInteger(), nullable=True))
    op.create_index("ix_messages_meshtastic_id", "messages", ["meshtastic_id"])

    # Backfill from existing packet_id data:
    # - MeshMonitor format: '{from_node}_{raw_id}' -> extract part after last '_'
    # - MQTT format: '{raw_id}' -> use as-is
    # - traceroute format: 'traceroute_{from_node}_{raw_id}' -> extract part after last '_'
    # Only update rows where the extracted value is a valid integer
    op.execute("""
        UPDATE messages
        SET meshtastic_id = (regexp_replace(packet_id, '^.*_', ''))::bigint
        WHERE packet_id IS NOT NULL
          AND regexp_replace(packet_id, '^.*_', '') ~ '^[0-9]+$'
    """)


def downgrade() -> None:
    op.drop_index("ix_messages_meshtastic_id", table_name="messages")
    op.drop_column("messages", "meshtastic_id")
