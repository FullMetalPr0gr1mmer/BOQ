"""Add approvals table

Revision ID: 5462e281eb94
Revises: b50be007fb35
Create Date: 2025-12-09 15:33:46.791456

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5462e281eb94'
down_revision: Union[str, Sequence[str], None] = 'b50be007fb35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'approvals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('project_type', sa.String(50), nullable=False),
        sa.Column('stage', sa.String(20), nullable=False, server_default='approval'),
        sa.Column('status', sa.String(30), nullable=False, server_default='pending_approval'),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_approvals_id'), 'approvals', ['id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_approvals_id'), table_name='approvals')
    op.drop_table('approvals')
