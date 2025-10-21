"""Add upl_line to lvl3 table

Revision ID: f3cc23fa93fd
Revises: 2b7c3543f578
Create Date: 2025-10-21 15:27:00.249856

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3cc23fa93fd'
down_revision: Union[str, Sequence[str], None] = '2b7c3543f578'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('lvl3', sa.Column('upl_line', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('lvl3', 'upl_line')
