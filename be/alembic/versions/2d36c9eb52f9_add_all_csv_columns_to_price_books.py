"""add_all_csv_columns_to_price_books

Revision ID: 2d36c9eb52f9
Revises: de04e52d28d0
Create Date: 2026-01-29 23:08:07.851703

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2d36c9eb52f9'
down_revision: Union[str, Sequence[str], None] = 'de04e52d28d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns from CSV
    op.add_column('price_books', sa.Column('local_content', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('sub_scope', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('zain_item_category', sa.Text(), nullable=True))
    op.add_column('price_books', sa.Column('serialized', sa.String(100), nullable=True))
    op.add_column('price_books', sa.Column('active_or_passive', sa.String(100), nullable=True))
    op.add_column('price_books', sa.Column('uom', sa.String(100), nullable=True))
    op.add_column('price_books', sa.Column('discount', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('unit_price_before_discount', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('po_total_amt_before_discount', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('special_discount', sa.Text(), nullable=True))
    op.add_column('price_books', sa.Column('claimed_percentage_after_special_discount', sa.Text(), nullable=True))
    op.add_column('price_books', sa.Column('unit_price_sar_after_special_discount', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('old_up', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('delta', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('final_total_price_after_discount', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('fv_percent_as_per_rrb', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('fv', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('total_fv_sar', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('revised_fv_percent', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('fv_unit_price_after_descope', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('to_go_contract_price_eur', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('r_ssp_eur', sa.String(200), nullable=True))

    # Remove old columns that are no longer needed
    op.drop_column('price_books', 'merge_pol_contract_civil')
    op.drop_column('price_books', 'merge_unit_extended')
    op.drop_column('price_books', 'unit_price_unit_after_rebate')
    op.drop_column('price_books', 'date')
    op.drop_column('price_books', 'final_excel_file')
    op.drop_column('price_books', 'fy')
    op.drop_column('price_books', 'fv_line_code')
    op.drop_column('price_books', 'reversed_fvn')
    op.drop_column('price_books', 'total_fvn_aar')


def downgrade() -> None:
    """Downgrade schema."""
    # Add back old columns
    op.add_column('price_books', sa.Column('merge_pol_contract_civil', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('merge_unit_extended', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('unit_price_unit_after_rebate', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('date', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('final_excel_file', sa.String(500), nullable=True))
    op.add_column('price_books', sa.Column('fy', sa.String(100), nullable=True))
    op.add_column('price_books', sa.Column('fv_line_code', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('reversed_fvn', sa.String(200), nullable=True))
    op.add_column('price_books', sa.Column('total_fvn_aar', sa.String(200), nullable=True))

    # Remove new columns
    op.drop_column('price_books', 'r_ssp_eur')
    op.drop_column('price_books', 'to_go_contract_price_eur')
    op.drop_column('price_books', 'fv_unit_price_after_descope')
    op.drop_column('price_books', 'revised_fv_percent')
    op.drop_column('price_books', 'total_fv_sar')
    op.drop_column('price_books', 'fv')
    op.drop_column('price_books', 'fv_percent_as_per_rrb')
    op.drop_column('price_books', 'final_total_price_after_discount')
    op.drop_column('price_books', 'delta')
    op.drop_column('price_books', 'old_up')
    op.drop_column('price_books', 'unit_price_sar_after_special_discount')
    op.drop_column('price_books', 'claimed_percentage_after_special_discount')
    op.drop_column('price_books', 'special_discount')
    op.drop_column('price_books', 'po_total_amt_before_discount')
    op.drop_column('price_books', 'unit_price_before_discount')
    op.drop_column('price_books', 'discount')
    op.drop_column('price_books', 'uom')
    op.drop_column('price_books', 'active_or_passive')
    op.drop_column('price_books', 'serialized')
    op.drop_column('price_books', 'zain_item_category')
    op.drop_column('price_books', 'sub_scope')
    op.drop_column('price_books', 'local_content')
