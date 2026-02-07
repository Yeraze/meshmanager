"""Add index on nodes.long_name for traceroute name resolution.

Revision ID: h5i6j7k8l9m0
Revises: g4h5i6j7k8l9
Create Date: 2026-02-07
"""

from alembic import op

revision = "h5i6j7k8l9m0"
down_revision = "g4h5i6j7k8l9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(op.f("ix_nodes_long_name"), "nodes", ["long_name"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_nodes_long_name"), table_name="nodes")
