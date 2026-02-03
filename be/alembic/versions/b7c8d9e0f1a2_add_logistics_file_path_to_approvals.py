"""add logistics_file_path to approvals

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-02-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7c8d9e0f1a2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add logistics_file_path column to approvals table."""
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('logistics_file_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Remove logistics_file_path column from approvals table."""
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.drop_column('logistics_file_path')
