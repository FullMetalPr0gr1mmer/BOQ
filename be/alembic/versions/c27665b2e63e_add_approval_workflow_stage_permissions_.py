"""Add approval workflow stage permissions to users

Revision ID: c27665b2e63e
Revises: 75c57e885be4
Create Date: 2026-01-07 13:01:52.119211

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c27665b2e63e'
down_revision: Union[str, Sequence[str], None] = '75c57e885be4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add approval workflow stage access permissions to users table
    op.add_column('users', sa.Column('can_access_approval', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('can_access_triggering', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('can_access_logistics', sa.Boolean(), nullable=False, server_default='0'))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove approval workflow stage access permissions from users table
    op.drop_column('users', 'can_access_logistics')
    op.drop_column('users', 'can_access_triggering')
    op.drop_column('users', 'can_access_approval')
