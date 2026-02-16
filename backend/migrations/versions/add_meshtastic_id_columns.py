"""Add meshtastic_id to telemetry, traceroutes, and packet_records for cross-source dedup.

Revision ID: b2c3d4e5f6g7
Revises: x7y8z9a0b1c2
Create Date: 2026-02-16
"""

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6g7"
down_revision: str = "x7y8z9a0b1c2"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Add meshtastic_id to telemetry (idempotent)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'telemetry' AND column_name = 'meshtastic_id'
            ) THEN
                ALTER TABLE telemetry ADD COLUMN meshtastic_id BIGINT;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_telemetry_meshtastic_id
            ON telemetry (meshtastic_id);
    """)

    # Add meshtastic_id to traceroutes (idempotent)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'traceroutes' AND column_name = 'meshtastic_id'
            ) THEN
                ALTER TABLE traceroutes ADD COLUMN meshtastic_id BIGINT;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_traceroutes_meshtastic_id
            ON traceroutes (meshtastic_id);
    """)

    # Add meshtastic_id to packet_records (idempotent)
    op.execute("""
        DO $$ BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'packet_records' AND column_name = 'meshtastic_id'
            ) THEN
                ALTER TABLE packet_records ADD COLUMN meshtastic_id BIGINT;
            END IF;
        END $$;
    """)
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_packet_records_meshtastic_id
            ON packet_records (meshtastic_id);
    """)


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_packet_records_meshtastic_id;")
    op.execute("ALTER TABLE packet_records DROP COLUMN IF EXISTS meshtastic_id;")
    op.execute("DROP INDEX IF EXISTS ix_traceroutes_meshtastic_id;")
    op.execute("ALTER TABLE traceroutes DROP COLUMN IF EXISTS meshtastic_id;")
    op.execute("DROP INDEX IF EXISTS ix_telemetry_meshtastic_id;")
    op.execute("ALTER TABLE telemetry DROP COLUMN IF EXISTS meshtastic_id;")
