"""Add anonymous user for tab-based permission checks.

Adds an is_anonymous boolean column and inserts a built-in anonymous user
with well-known UUID. When no session exists, the middleware returns this
user so data endpoints can enforce per-tab permissions for unauthenticated
visitors.

Revision ID: o2p3q4r5s6t7
Revises: n1o2p3q4r5s6
Create Date: 2026-02-10
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "o2p3q4r5s6t7"
down_revision: str = "n1o2p3q4r5s6"
branch_labels = None
depends_on = None

ANONYMOUS_USER_ID = "00000000-0000-0000-0000-000000000000"


def upgrade() -> None:
    # Add the is_anonymous column
    op.execute(
        sa.text("""
            ALTER TABLE users
            ADD COLUMN IF NOT EXISTS is_anonymous BOOLEAN NOT NULL DEFAULT FALSE
        """)
    )

    # Index for user count queries that filter by is_anonymous
    op.execute(
        sa.text("""
            CREATE INDEX IF NOT EXISTS ix_users_is_anonymous ON users (is_anonymous)
        """)
    )

    # Insert the anonymous user with default permissions (read all except settings)
    op.execute(
        sa.text("""
            INSERT INTO users (id, username, auth_provider, role, is_active, is_anonymous, permissions, created_at)
            VALUES (
                CAST(:id AS UUID),
                'anonymous',
                'system',
                'user',
                TRUE,
                TRUE,
                CAST(:permissions AS JSONB),
                NOW()
            )
            ON CONFLICT (id) DO NOTHING
        """).bindparams(
            id=ANONYMOUS_USER_ID,
            permissions='{"map": {"read": true, "write": false}, "nodes": {"read": true, "write": false}, "graphs": {"read": true, "write": false}, "analysis": {"read": true, "write": false}, "communication": {"read": true, "write": false}, "settings": {"read": false, "write": false}}',
        )
    )


def downgrade() -> None:
    # Remove the anonymous user
    op.execute(
        sa.text("DELETE FROM users WHERE id = CAST(:id AS UUID)").bindparams(id=ANONYMOUS_USER_ID)
    )

    # Drop the index and column
    op.execute(sa.text("DROP INDEX IF EXISTS ix_users_is_anonymous"))
    op.execute(
        sa.text("ALTER TABLE users DROP COLUMN IF EXISTS is_anonymous")
    )
