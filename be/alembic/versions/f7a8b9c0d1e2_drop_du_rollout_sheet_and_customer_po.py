"""drop_du_rollout_sheet_and_customer_po_tables

Revision ID: f7a8b9c0d1e2
Revises: e6609a133295
Create Date: 2026-02-09

Remove du_rollout_sheet and du_customer_po tables as these features
have been deprecated and their functionality moved to the OD BOQ system.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f7a8b9c0d1e2'
down_revision: Union[str, Sequence[str], None] = 'e6609a133295'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the du_rollout_sheet and du_customer_po tables."""
    # Drop du_customer_po table
    op.drop_table('du_customer_po')

    # Drop du_rollout_sheet table
    op.drop_table('du_rollout_sheet')


def downgrade() -> None:
    """Recreate the tables if needed (with basic structure)."""
    # Recreate du_rollout_sheet table
    op.create_table(
        'du_rollout_sheet',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('site_id', sa.String(255), nullable=True),
        sa.Column('scope', sa.String(255), nullable=True),
        sa.Column('year_target_scope', sa.String(255), nullable=True),
        sa.Column('partner', sa.String(255), nullable=True),
        sa.Column('project_id', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )

    # Recreate du_customer_po table
    op.create_table(
        'du_customer_po',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('line', sa.String(255), nullable=True),
        sa.Column('cat', sa.String(255), nullable=True),
        sa.Column('item_job', sa.String(255), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('project_id', sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
