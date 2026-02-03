"""add_prf_and_vat_to_du_rpa_invoice

Revision ID: a1b2c3d4e5f6
Revises: ccee4facaf05
Create Date: 2026-02-03 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'ccee4facaf05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add prf_percentage and vat_rate columns to du_rpa_invoice."""
    op.add_column('du_rpa_invoice', sa.Column('prf_percentage', sa.Float(), nullable=True))
    op.add_column('du_rpa_invoice', sa.Column('vat_rate', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove prf_percentage and vat_rate columns from du_rpa_invoice."""
    op.drop_column('du_rpa_invoice', 'vat_rate')
    op.drop_column('du_rpa_invoice', 'prf_percentage')
