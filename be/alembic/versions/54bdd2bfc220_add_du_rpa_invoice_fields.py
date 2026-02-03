"""add_du_rpa_invoice_fields

Revision ID: 54bdd2bfc220
Revises: 7b0fc4ac8da0
Create Date: 2026-01-26 12:03:23.993675

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '54bdd2bfc220'
down_revision: Union[str, Sequence[str], None] = '7b0fc4ac8da0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns to du_rpa_invoice table
    op.add_column('du_rpa_invoice', sa.Column('ppo_number', sa.String(length=100), nullable=True))
    op.add_column('du_rpa_invoice', sa.Column('new_po_number', sa.String(length=100), nullable=True))
    op.add_column('du_rpa_invoice', sa.Column('pr_number', sa.String(length=100), nullable=True))
    op.add_column('du_rpa_invoice', sa.Column('model', sa.String(length=200), nullable=True))

    # Populate existing records with ppo_number
    op.execute("""
        UPDATE du_rpa_invoice
        SET ppo_number = 'LEGACY-' + CAST(id AS NVARCHAR)
        WHERE ppo_number IS NULL
    """)

    # Make ppo_number NOT NULL (MS-SQL requires existing_type)
    op.alter_column('du_rpa_invoice', 'ppo_number',
                   existing_type=sa.String(length=100),
                   nullable=False)

    # Create indexes
    op.create_index(op.f('ix_du_rpa_invoice_ppo_number'), 'du_rpa_invoice', ['ppo_number'], unique=True)
    op.create_index(op.f('ix_du_rpa_invoice_new_po_number'), 'du_rpa_invoice', ['new_po_number'], unique=False)
    op.create_index(op.f('ix_du_rpa_invoice_pr_number'), 'du_rpa_invoice', ['pr_number'], unique=False)

    # Add new columns to du_rpa_invoice_item table
    op.add_column('du_rpa_invoice_item', sa.Column('li_number', sa.String(length=100), nullable=True))
    op.add_column('du_rpa_invoice_item', sa.Column('unit_price', sa.Float(), nullable=True))
    op.add_column('du_rpa_invoice_item', sa.Column('pac_date', sa.Date(), nullable=True))

    # Create index
    op.create_index(op.f('ix_du_rpa_invoice_item_li_number'), 'du_rpa_invoice_item', ['li_number'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes first
    op.drop_index(op.f('ix_du_rpa_invoice_item_li_number'), table_name='du_rpa_invoice_item')
    op.drop_index(op.f('ix_du_rpa_invoice_pr_number'), table_name='du_rpa_invoice')
    op.drop_index(op.f('ix_du_rpa_invoice_new_po_number'), table_name='du_rpa_invoice')
    op.drop_index(op.f('ix_du_rpa_invoice_ppo_number'), table_name='du_rpa_invoice')

    # Drop columns from du_rpa_invoice_item
    op.drop_column('du_rpa_invoice_item', 'pac_date')
    op.drop_column('du_rpa_invoice_item', 'unit_price')
    op.drop_column('du_rpa_invoice_item', 'li_number')

    # Drop columns from du_rpa_invoice
    op.drop_column('du_rpa_invoice', 'model')
    op.drop_column('du_rpa_invoice', 'pr_number')
    op.drop_column('du_rpa_invoice', 'new_po_number')
    op.drop_column('du_rpa_invoice', 'ppo_number')
