"""add unit_price to od_boq_product

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-02-17 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd4e5f6a7b8c9'
down_revision: Union[str, Sequence[str], None] = 'c3d4e5f6a7b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unit_price column to du_od_boq_product table."""
    op.add_column('du_od_boq_product',
        sa.Column('unit_price', sa.Float(), nullable=True)
    )


def downgrade() -> None:
    """Remove unit_price column from du_od_boq_product table."""
    op.drop_column('du_od_boq_product', 'unit_price')
