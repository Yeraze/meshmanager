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
    op.add_column("channels", sa.Column("psk", sa.String(48), nullable=True))


def downgrade() -> None:
    op.drop_column("channels", "psk")
