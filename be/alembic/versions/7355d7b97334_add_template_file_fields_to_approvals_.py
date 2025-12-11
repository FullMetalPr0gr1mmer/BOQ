"""Add template file fields to approvals table

Revision ID: 7355d7b97334
Revises: bb4dac027fc7
Create Date: 2025-12-11 13:26:46.606317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7355d7b97334'
down_revision: Union[str, Sequence[str], None] = 'bb4dac027fc7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('approvals', sa.Column('template_filename', sa.String(255), nullable=True))
    op.add_column('approvals', sa.Column('template_file_path', sa.String(500), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('approvals', 'template_file_path')
    op.drop_column('approvals', 'template_filename')
