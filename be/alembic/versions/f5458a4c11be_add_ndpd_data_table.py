"""Add NDPD data table

Revision ID: f5458a4c11be
Revises: ad531142ac2f
Create Date: 2025-12-18 23:06:03.994598

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5458a4c11be'
down_revision: Union[str, Sequence[str], None] = 'ad531142ac2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'ndpd_data',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('period', sa.String(length=50), nullable=False),
        sa.Column('ct', sa.String(length=500), nullable=False),
        sa.Column('actual_sites', sa.Integer(), nullable=False),
        sa.Column('forecast_sites', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ndpd_data_id'), 'ndpd_data', ['id'], unique=False)
    op.create_index(op.f('ix_ndpd_data_period'), 'ndpd_data', ['period'], unique=False)
    op.create_index(op.f('ix_ndpd_data_ct'), 'ndpd_data', ['ct'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ndpd_data_ct'), table_name='ndpd_data')
    op.drop_index(op.f('ix_ndpd_data_period'), table_name='ndpd_data')
    op.drop_index(op.f('ix_ndpd_data_id'), table_name='ndpd_data')
    op.drop_table('ndpd_data')
