"""Add smp_id so_number and triggering_file_path to approvals

Revision ID: 75c57e885be4
Revises: 80849e9309b6
Create Date: 2026-01-06 15:44:55.878183

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '75c57e885be4'
down_revision: Union[str, Sequence[str], None] = '80849e9309b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add smp_id, so_number, and triggering_file_path to approvals table."""
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.add_column(sa.Column('smp_id', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('so_number', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('triggering_file_path', sa.String(length=500), nullable=True))


def downgrade() -> None:
    """Downgrade schema - Remove smp_id, so_number, and triggering_file_path from approvals table."""
    with op.batch_alter_table('approvals', schema=None) as batch_op:
        batch_op.drop_column('triggering_file_path')
        batch_op.drop_column('so_number')
        batch_op.drop_column('smp_id')
