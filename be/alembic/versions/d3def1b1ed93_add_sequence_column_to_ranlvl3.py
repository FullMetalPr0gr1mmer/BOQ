"""add_sequence_column_to_ranlvl3

Revision ID: d3def1b1ed93
Revises: aa7a523fbe3b
Create Date: 2026-01-13 09:27:08.277857

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd3def1b1ed93'
down_revision: Union[str, Sequence[str], None] = 'aa7a523fbe3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('ranlvl3', sa.Column('sequence', sa.Integer(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('ranlvl3', 'sequence')
