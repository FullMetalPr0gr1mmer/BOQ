"""widen site_id column in du_rpa_invoice

Revision ID: b2c3d4e5f6a7
Revises: a5b6c7d8e9f0
Create Date: 2026-02-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a5b6c7d8e9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Widen site_id from String(100) to String(500) to support multi-site PPOs."""
    op.alter_column(
        'du_rpa_invoice',
        'site_id',
        existing_type=sa.String(100),
        type_=sa.String(500),
        existing_nullable=True
    )


def downgrade() -> None:
    """Revert site_id back to String(100)."""
    op.alter_column(
        'du_rpa_invoice',
        'site_id',
        existing_type=sa.String(500),
        type_=sa.String(100),
        existing_nullable=True
    )
