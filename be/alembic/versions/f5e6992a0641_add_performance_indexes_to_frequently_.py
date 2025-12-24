"""Add performance indexes to frequently queried columns

Revision ID: f5e6992a0641
Revises: 7355d7b97334
Create Date: 2025-12-17 15:50:20.066483

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f5e6992a0641'
down_revision: Union[str, Sequence[str], None] = '7355d7b97334'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add performance indexes to frequently queried columns.

    Note: Most tables already have indexes defined in their models.
    This migration adds missing indexes for user_project_access table.

    Existing indexes (already in models):
    - inventory.pid_po (index=True)
    - lvl3.project_id (index=True)
    - ranlvl3.project_id (index=True)
    - ran_inventory.pid_po (index=True)

    New indexes being added:
    - user_project_access.user_id
    - user_project_access.project_id
    - user_project_access.Ranproject_id
    - user_project_access.Ropproject_id
    - user_project_access.DUproject_id
    """
    # User access indexes (missing in model definition)
    # These improve performance for user permission queries
    op.create_index('idx_user_access_user_id', 'user_project_access', ['user_id'])
    op.create_index('idx_user_access_project_id', 'user_project_access', ['project_id'])
    op.create_index('idx_user_access_ranproject_id', 'user_project_access', ['Ranproject_id'])
    op.create_index('idx_user_access_ropproject_id', 'user_project_access', ['Ropproject_id'])
    op.create_index('idx_user_access_duproject_id', 'user_project_access', ['DUproject_id'])


def downgrade() -> None:
    """Downgrade schema - Remove performance indexes."""
    op.drop_index('idx_user_access_duproject_id', table_name='user_project_access')
    op.drop_index('idx_user_access_ropproject_id', table_name='user_project_access')
    op.drop_index('idx_user_access_ranproject_id', table_name='user_project_access')
    op.drop_index('idx_user_access_project_id', table_name='user_project_access')
    op.drop_index('idx_user_access_user_id', table_name='user_project_access')
