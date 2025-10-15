"""remove_upl_line_from_inventory

Revision ID: 2b7c3543f578
Revises: a0b6d52b6057
Create Date: 2025-10-15 16:11:38.750640

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b7c3543f578'
down_revision: Union[str, Sequence[str], None] = 'a0b6d52b6057'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Remove upl_line column from inventory table
    op.drop_column('inventory', 'upl_line')


def downgrade() -> None:
    """Downgrade schema."""
    # Add upl_line column back to inventory table
    op.add_column('inventory', sa.Column('upl_line', sa.String(length=200), nullable=True))
