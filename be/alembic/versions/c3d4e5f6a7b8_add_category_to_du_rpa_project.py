"""add category to du_rpa_project

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-02-17 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6a7b8'
down_revision: Union[str, Sequence[str], None] = 'b2c3d4e5f6a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add category column to du_rpa_project with default 'ppo_based'."""
    op.add_column(
        'du_rpa_project',
        sa.Column('category', sa.String(50), nullable=False, server_default='ppo_based')
    )


def downgrade() -> None:
    """Remove category column from du_rpa_project."""
    op.drop_column('du_rpa_project', 'category')
