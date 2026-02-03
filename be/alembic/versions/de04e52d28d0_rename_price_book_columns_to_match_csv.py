"""rename_price_book_columns_to_match_csv

Revision ID: de04e52d28d0
Revises: 6e4d7f579e10
Create Date: 2026-01-29 22:44:54.988479

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de04e52d28d0'
down_revision: Union[str, Sequence[str], None] = '6e4d7f579e10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Rename columns to match CSV headers

    # item_name → project_name
    op.execute("EXEC sp_rename 'price_books.item_name', 'project_name', 'COLUMN'")

    # merge_pc_contract_civil → merge_poline_uplline
    op.execute("EXEC sp_rename 'price_books.merge_pc_contract_civil', 'merge_poline_uplline', 'COLUMN'")

    # url_line → upl_line
    op.execute("EXEC sp_rename 'price_books.url_line', 'upl_line', 'COLUMN'")

    # vendor_part_number_standard → vendor_part_number_item_code
    op.execute("EXEC sp_rename 'price_books.vendor_part_number_standard', 'vendor_part_number_item_code', 'COLUMN'")

    # merge_po → merge_po_poline_uplline
    op.execute("EXEC sp_rename 'price_books.merge_po', 'merge_po_poline_uplline', 'COLUMN'")

    # eol → merge_pol_contract_civil
    op.execute("EXEC sp_rename 'price_books.eol', 'merge_pol_contract_civil', 'COLUMN'")

    # unit_price_after_rebate → unit_price_unit_after_rebate
    op.execute("EXEC sp_rename 'price_books.unit_price_after_rebate', 'unit_price_unit_after_rebate', 'COLUMN'")


def downgrade() -> None:
    """Downgrade schema."""
    # Reverse the column renames

    op.execute("EXEC sp_rename 'price_books.project_name', 'item_name', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.merge_poline_uplline', 'merge_pc_contract_civil', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.upl_line', 'url_line', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.vendor_part_number_item_code', 'vendor_part_number_standard', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.merge_po_poline_uplline', 'merge_po', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.merge_pol_contract_civil', 'eol', 'COLUMN'")
    op.execute("EXEC sp_rename 'price_books.unit_price_unit_after_rebate', 'unit_price_after_rebate', 'COLUMN'")
