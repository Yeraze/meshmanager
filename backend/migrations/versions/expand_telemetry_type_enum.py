"""Add LOCAL_STATS, HEALTH, HOST to telemetrytype enum.

Revision ID: l9m0n1o2p3q4
Revises: k8l9m0n1o2p3
Create Date: 2026-02-10
"""

from alembic import op

revision = "l9m0n1o2p3q4"
down_revision = "k8l9m0n1o2p3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLAlchemy Enum() uses Python member NAMES (uppercase) as DB values
    for value in ("LOCAL_STATS", "HEALTH", "HOST"):
        op.execute(f"""
            DO $$ BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_enum
                    WHERE enumlabel = '{value}'
                      AND enumtypid = (SELECT oid FROM pg_type WHERE typname = 'telemetrytype')
                ) THEN
                    ALTER TYPE telemetrytype ADD VALUE '{value}';
                END IF;
            END $$;
        """)


def downgrade() -> None:
    # PostgreSQL does not support removing enum values.
    # A full migration would recreate the type, but that is rarely needed.
    pass
