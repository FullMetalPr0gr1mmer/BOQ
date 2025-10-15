"""move_upl_line_from_lvl3_to_inventory

Revision ID: a0b6d52b6057
Revises: f8c4ee8e0262
Create Date: 2025-10-15 14:29:07.476527

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a0b6d52b6057'
down_revision: Union[str, Sequence[str], None] = 'f8c4ee8e0262'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add upl_line column to inventory table
    op.add_column('inventory', sa.Column('upl_line', sa.String(length=200), nullable=True))

    # Remove upl_line column from lvl3 table
    op.drop_column('lvl3', 'upl_line')


def downgrade() -> None:
    """Downgrade schema."""
    # Add upl_line column back to lvl3 table
    op.add_column('lvl3', sa.Column('upl_line', sa.String(length=200), nullable=True))

    # Remove upl_line column from inventory table
    op.drop_column('inventory', 'upl_line')
