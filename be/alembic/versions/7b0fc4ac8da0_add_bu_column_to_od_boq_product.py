"""add_bu_column_to_od_boq_product

Revision ID: 7b0fc4ac8da0
Revises: 0d423207336b
Create Date: 2026-01-19 12:27:29.585318

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7b0fc4ac8da0'
down_revision: Union[str, Sequence[str], None] = '0d423207336b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add bu column to du_od_boq_product table
    op.add_column('du_od_boq_product',
        sa.Column('bu', sa.String(100), nullable=True)
    )
    # Add index on bu column for better query performance
    op.create_index(op.f('ix_du_od_boq_product_bu'), 'du_od_boq_product', ['bu'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Remove index and column in reverse order
    op.drop_index(op.f('ix_du_od_boq_product_bu'), table_name='du_od_boq_product')
    op.drop_column('du_od_boq_product', 'bu')
