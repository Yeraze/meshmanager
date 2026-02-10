"""Add psk column to channels table.

Revision ID: i6j7k8l9m0n1
Revises: h5i6j7k8l9m0
Create Date: 2026-02-08
"""

import sqlalchemy as sa
from alembic import op

revision = "i6j7k8l9m0n1"
down_revision = "h5i6j7k8l9m0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS for crash-recovery idempotency
    op.execute("ALTER TABLE channels ADD COLUMN IF NOT EXISTS psk VARCHAR(48)")


def downgrade() -> None:
    op.drop_column("channels", "psk")
