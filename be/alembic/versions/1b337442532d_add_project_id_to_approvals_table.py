"""Add project_id to approvals table

Revision ID: 1b337442532d
Revises: 5462e281eb94
Create Date: 2025-12-09 16:48:02.197110

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b337442532d'
down_revision: Union[str, Sequence[str], None] = '5462e281eb94'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('approvals', sa.Column('project_id', sa.Integer(), nullable=False, server_default='0'))
    # Remove server_default after adding the column
    op.alter_column('approvals', 'project_id', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('approvals', 'project_id')
