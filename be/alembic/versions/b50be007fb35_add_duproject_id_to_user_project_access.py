"""Add DUproject_id to user_project_access

Revision ID: b50be007fb35
Revises: a068c6bdfd26
Create Date: 2025-11-24 14:14:53.905261

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b50be007fb35'
down_revision: Union[str, Sequence[str], None] = 'a068c6bdfd26'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('user_project_access', sa.Column('DUproject_id', sa.String(200), sa.ForeignKey('du_project.pid_po'), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('user_project_access', 'DUproject_id')
