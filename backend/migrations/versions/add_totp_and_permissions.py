"""Add TOTP and granular permissions to users table.

Revision ID: k8l9m0n1o2p3
Revises: j7k8l9m0n1o2
Create Date: 2026-02-08
"""

import sqlalchemy as sa
from alembic import op

revision = "k8l9m0n1o2p3"
down_revision = "j7k8l9m0n1o2"
branch_labels = None
depends_on = None

DEFAULT_PERMISSIONS = (
    '{"map":{"read":true,"write":false},'
    '"nodes":{"read":true,"write":false},'
    '"graphs":{"read":true,"write":false},'
    '"analysis":{"read":true,"write":false},'
    '"communication":{"read":true,"write":false},'
    '"settings":{"read":true,"write":false}}'
)

ALL_WRITE_PERMISSIONS = (
    '{"map":{"read":true,"write":true},'
    '"nodes":{"read":true,"write":true},'
    '"graphs":{"read":true,"write":true},'
    '"analysis":{"read":true,"write":true},'
    '"communication":{"read":true,"write":true},'
    '"settings":{"read":true,"write":true}}'
)


def upgrade() -> None:
    # Add TOTP columns (IF NOT EXISTS for crash-recovery idempotency)
    op.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(255)")
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN NOT NULL DEFAULT false"
    )

    # Add permissions JSON column
    op.execute(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS permissions JSON NOT NULL DEFAULT "
        f"'{DEFAULT_PERMISSIONS}'"
    )

    # Migrate editors: set all write=true, change role to 'user'
    op.execute(
        sa.text(
            "UPDATE users SET role = 'user', permissions = CAST(:perms AS json) "
            "WHERE role = 'editor'"
        ).bindparams(perms=ALL_WRITE_PERMISSIONS)
    )

    # Migrate viewers: change role to 'user' (permissions default is read-only)
    op.execute(sa.text("UPDATE users SET role = 'user' WHERE role = 'viewer'"))

    # Add CHECK constraint to enforce valid role values (skip if already exists)
    op.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'ck_users_role_valid'
            ) THEN
                ALTER TABLE users ADD CONSTRAINT ck_users_role_valid CHECK (role IN ('admin', 'user'));
            END IF;
        END $$;
    """)


def downgrade() -> None:
    op.drop_constraint("ck_users_role_valid", "users", type_="check")

    # Convert back based on settings write permission
    op.execute(
        sa.text(
            "UPDATE users SET role = 'editor' "
            "WHERE role = 'user' AND permissions::text LIKE :pattern"
        ).bindparams(pattern='%"settings":{"read":true,"write":true}%')
    )
    op.execute(sa.text("UPDATE users SET role = 'viewer' WHERE role = 'user'"))

    op.drop_column("users", "permissions")
    op.drop_column("users", "totp_enabled")
    op.drop_column("users", "totp_secret")
