"""Change message packet_id to string type.

MeshMonitor returns composite string IDs like "2068784147_2133719606"
which cannot be stored as BigInteger.

Revision ID: d1e2f3g4h5i6
Revises: add_historical_days_back_to_sources
Create Date: 2024-12-18
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = "d1e2f3g4h5i6"
down_revision = "add_historical_days_back"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column(
        "messages",
        "packet_id",
        existing_type=sa.BigInteger(),
        type_=sa.String(64),
        existing_nullable=True,
        postgresql_using="packet_id::VARCHAR(64)",
    )
    # Add unique index for ON CONFLICT clause
    op.create_index(
        "idx_messages_source_packet",
        "messages",
        ["source_id", "packet_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("idx_messages_source_packet", table_name="messages")
    # Note: This may fail if there are non-numeric packet_ids
    op.alter_column(
        "messages",
        "packet_id",
        existing_type=sa.String(64),
        type_=sa.BigInteger(),
        existing_nullable=True,
        postgresql_using="packet_id::BIGINT",
    )
