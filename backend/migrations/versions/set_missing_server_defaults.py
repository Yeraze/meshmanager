"""Set missing server-side DEFAULT clauses on NOT NULL columns.

Older installs bootstrapped via Base.metadata.create_all have columns with
Python-side defaults but no PostgreSQL DEFAULT clause. Raw SQL INSERTs that
omit these columns then fail with NOT NULL violations.

This migration retroactively sets server defaults for all affected columns.
All statements are idempotent (SET DEFAULT is a no-op if the default matches).

Revision ID: p3q4r5s6t7u8
Revises: o2p3q4r5s6t7
Create Date: 2026-02-11
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "p3q4r5s6t7u8"
down_revision: str = "o2p3q4r5s6t7"
branch_labels = None
depends_on = None

# DEFAULT_PERMISSIONS JSON — colons escaped for SQLAlchemy text()
_DEFAULT_PERMISSIONS_SQL = (
    '\'{"map"\\: {"read"\\: true, "write"\\: false}, '
    '"nodes"\\: {"read"\\: true, "write"\\: false}, '
    '"graphs"\\: {"read"\\: true, "write"\\: false}, '
    '"analysis"\\: {"read"\\: true, "write"\\: false}, '
    '"communication"\\: {"read"\\: true, "write"\\: false}, '
    '"settings"\\: {"read"\\: true, "write"\\: false}}\''
)


def upgrade() -> None:
    # --- users ---
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN auth_provider SET DEFAULT 'local'"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user'"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN is_active SET DEFAULT TRUE"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN is_anonymous SET DEFAULT FALSE"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN totp_enabled SET DEFAULT FALSE"))
    op.execute(
        sa.text(f"ALTER TABLE users ALTER COLUMN permissions SET DEFAULT {_DEFAULT_PERMISSIONS_SQL}")
    )

    # --- nodes ---
    op.execute(sa.text("ALTER TABLE nodes ALTER COLUMN is_licensed SET DEFAULT FALSE"))

    # --- sources ---
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN poll_interval_seconds SET DEFAULT 300"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN historical_days_back SET DEFAULT 1"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN mqtt_port SET DEFAULT 1883"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN mqtt_use_tls SET DEFAULT FALSE"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN enabled SET DEFAULT TRUE"))

    # --- channels ---
    op.execute(sa.text("ALTER TABLE channels ALTER COLUMN uplink_enabled SET DEFAULT FALSE"))
    op.execute(sa.text("ALTER TABLE channels ALTER COLUMN downlink_enabled SET DEFAULT FALSE"))

    # --- messages ---
    op.execute(sa.text("ALTER TABLE messages ALTER COLUMN channel SET DEFAULT 0"))


def downgrade() -> None:
    # --- users ---
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN auth_provider DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN role DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN is_active DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN is_anonymous DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN totp_enabled DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE users ALTER COLUMN permissions DROP DEFAULT"))

    # --- nodes ---
    op.execute(sa.text("ALTER TABLE nodes ALTER COLUMN is_licensed DROP DEFAULT"))

    # --- sources ---
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN poll_interval_seconds DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN historical_days_back DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN mqtt_port DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN mqtt_use_tls DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE sources ALTER COLUMN enabled DROP DEFAULT"))

    # --- channels ---
    op.execute(sa.text("ALTER TABLE channels ALTER COLUMN uplink_enabled DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE channels ALTER COLUMN downlink_enabled DROP DEFAULT"))

    # --- messages ---
    op.execute(sa.text("ALTER TABLE messages ALTER COLUMN channel DROP DEFAULT"))
