"""add_multi_smp_fields_to_approval

Revision ID: 4e432b562d18
Revises: c27665b2e63e
Create Date: 2026-01-08 15:52:43.805551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4e432b562d18'
down_revision: Union[str, Sequence[str], None] = 'c27665b2e63e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new multi-SMP fields
    op.add_column('approvals', sa.Column('planning_smp_id', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('planning_so_number', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('implementation_smp_id', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('implementation_so_number', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('dismantling_smp_id', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('dismantling_so_number', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('epac_req', sa.String(length=200), nullable=True))
    op.add_column('approvals', sa.Column('inservice_date', sa.String(length=200), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    # Remove multi-SMP fields
    op.drop_column('approvals', 'inservice_date')
    op.drop_column('approvals', 'epac_req')
    op.drop_column('approvals', 'dismantling_so_number')
    op.drop_column('approvals', 'dismantling_smp_id')
    op.drop_column('approvals', 'implementation_so_number')
    op.drop_column('approvals', 'implementation_smp_id')
    op.drop_column('approvals', 'planning_so_number')
    op.drop_column('approvals', 'planning_smp_id')
