"""Add historical_days_back to sources

Revision ID: add_historical_days_back
Revises: c76176a43e62
Create Date: 2025-01-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_historical_days_back'
down_revision: Union[str, None] = 'c76176a43e62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('sources', sa.Column('historical_days_back', sa.Integer(), nullable=False, server_default='1'))


def downgrade() -> None:
    op.drop_column('sources', 'historical_days_back')

