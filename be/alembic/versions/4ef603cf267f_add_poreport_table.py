"""Add POReport table

Revision ID: 4ef603cf267f
Revises: f5458a4c11be
Create Date: 2026-01-06 00:35:31.771043

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4ef603cf267f'
down_revision: Union[str, Sequence[str], None] = 'f5458a4c11be'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'po_report',
        sa.Column('id', sa.String(200), primary_key=True, nullable=False, index=True),
        sa.Column('report_name', sa.String(500), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(100), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('pid_po', sa.String(200), nullable=True),
        sa.ForeignKeyConstraint(['pid_po'], ['projects.pid_po'], ),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('po_report')
