"""Add solar_production table

Revision ID: a1b2c3d4e5f6
Revises: c76176a43e62
Create Date: 2025-12-11 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'c76176a43e62'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'solar_production',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('source_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('sources.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('watt_hours', sa.Float(), nullable=False),
        sa.Column('fetched_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, index=True),
    )
    op.create_index(
        'ix_solar_production_unique',
        'solar_production',
        ['source_id', 'timestamp'],
        unique=True
    )


def downgrade() -> None:
    op.drop_index('ix_solar_production_unique', table_name='solar_production')
    op.drop_table('solar_production')
