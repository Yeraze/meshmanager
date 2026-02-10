"""Replace is_admin with role column on users table.

Revision ID: j7k8l9m0n1o2
Revises: i6j7k8l9m0n1
Create Date: 2026-02-08
"""

import sqlalchemy as sa
from alembic import op

revision = "j7k8l9m0n1o2"
down_revision = "i6j7k8l9m0n1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # IF NOT EXISTS for crash-recovery idempotency
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS role VARCHAR(20) NOT NULL DEFAULT 'viewer'"
    )
    # Only migrate data if is_admin still exists (skip on re-run after partial apply)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'users' AND column_name = 'is_admin'
            ) THEN
                UPDATE users SET role = 'admin' WHERE is_admin = true;
                ALTER TABLE users DROP COLUMN is_admin;
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.add_column("users", sa.Column("is_admin", sa.Boolean(), nullable=False, server_default="false"))
    op.execute("UPDATE users SET is_admin = true WHERE role = 'admin'")
    op.drop_column("users", "role")
