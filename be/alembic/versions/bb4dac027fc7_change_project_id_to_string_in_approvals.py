"""Change project_id to String in approvals

Revision ID: bb4dac027fc7
Revises: 1b337442532d
Create Date: 2025-12-09 17:05:45.397103

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'bb4dac027fc7'
down_revision: Union[str, Sequence[str], None] = '1b337442532d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change project_id from Integer to String(200)
    op.alter_column('approvals', 'project_id',
                   type_=sa.String(200),
                   existing_type=sa.Integer(),
                   nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert project_id back to Integer
    op.alter_column('approvals', 'project_id',
                   type_=sa.Integer(),
                   existing_type=sa.String(200),
                   nullable=False)
