"""Add packet_records table for encrypted, unknown, and nodeinfo packets.

Revision ID: x7y8z9a0b1c2
Revises: r5s6t7u8v9w0
Create Date: 2026-02-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "x7y8z9a0b1c2"
down_revision: str = "r5s6t7u8v9w0"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Create the enum type (idempotent)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'packetrecordtype') THEN
                CREATE TYPE packetrecordtype AS ENUM ('ENCRYPTED', 'UNKNOWN', 'NODEINFO');
            END IF;
        END $$;
    """)

    # Create the table (idempotent)
    op.execute("""
        CREATE TABLE IF NOT EXISTS packet_records (
            id UUID NOT NULL PRIMARY KEY,
            source_id UUID NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
            from_node_num BIGINT NOT NULL,
            to_node_num BIGINT,
            packet_type packetrecordtype NOT NULL,
            portnum VARCHAR(100),
            received_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)

    # Create indexes (idempotent)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_packet_records_source_id
            ON packet_records (source_id);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_packet_records_from_node_num
            ON packet_records (from_node_num);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_packet_records_packet_type
            ON packet_records (packet_type);
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_packet_records_received_at
            ON packet_records (received_at);
    """)
    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_packet_records_unique
            ON packet_records (source_id, from_node_num, packet_type, received_at);
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS packet_records;")
    op.execute("DROP TYPE IF EXISTS packetrecordtype;")
