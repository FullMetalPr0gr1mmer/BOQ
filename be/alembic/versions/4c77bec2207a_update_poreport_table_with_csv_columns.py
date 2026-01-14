"""Update POReport table with CSV columns

Revision ID: 4c77bec2207a
Revises: 4ef603cf267f
Create Date: 2026-01-06 12:34:28.056391

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c77bec2207a'
down_revision: Union[str, Sequence[str], None] = '4ef603cf267f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop old columns
    op.drop_column('po_report', 'report_name')
    op.drop_column('po_report', 'description')
    op.drop_column('po_report', 'status')
    op.drop_column('po_report', 'notes')

    # Add new CSV columns
    op.add_column('po_report', sa.Column('pur_doc', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('customer_site_ref', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('project', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('so_number', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('material_des', sa.Text(), nullable=True))
    op.add_column('po_report', sa.Column('rr_date', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('site_name', sa.String(500), nullable=True))
    op.add_column('po_report', sa.Column('wbs_element', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('supplier', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('name_1', sa.String(500), nullable=True))
    op.add_column('po_report', sa.Column('order_date', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('gr_date', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('supplier_invoice', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('ir_docdate', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('pstng_date', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('po_value_sar', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('invoiced_value_sar', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('percent_invoiced', sa.String(50), nullable=True))
    op.add_column('po_report', sa.Column('balance_value_sar', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('svo_number', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('header_text', sa.Text(), nullable=True))
    op.add_column('po_report', sa.Column('smp_id', sa.String(200), nullable=True))
    op.add_column('po_report', sa.Column('remarks', sa.Text(), nullable=True))
    op.add_column('po_report', sa.Column('aind', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('accounting_indicator_desc', sa.Text(), nullable=True))

    # Create indexes for frequently searched columns
    op.create_index('ix_po_report_pur_doc', 'po_report', ['pur_doc'])
    op.create_index('ix_po_report_customer_site_ref', 'po_report', ['customer_site_ref'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.drop_index('ix_po_report_customer_site_ref', table_name='po_report')
    op.drop_index('ix_po_report_pur_doc', table_name='po_report')

    # Drop new columns
    op.drop_column('po_report', 'accounting_indicator_desc')
    op.drop_column('po_report', 'aind')
    op.drop_column('po_report', 'remarks')
    op.drop_column('po_report', 'smp_id')
    op.drop_column('po_report', 'header_text')
    op.drop_column('po_report', 'svo_number')
    op.drop_column('po_report', 'balance_value_sar')
    op.drop_column('po_report', 'percent_invoiced')
    op.drop_column('po_report', 'invoiced_value_sar')
    op.drop_column('po_report', 'po_value_sar')
    op.drop_column('po_report', 'pstng_date')
    op.drop_column('po_report', 'ir_docdate')
    op.drop_column('po_report', 'supplier_invoice')
    op.drop_column('po_report', 'gr_date')
    op.drop_column('po_report', 'order_date')
    op.drop_column('po_report', 'name_1')
    op.drop_column('po_report', 'supplier')
    op.drop_column('po_report', 'wbs_element')
    op.drop_column('po_report', 'site_name')
    op.drop_column('po_report', 'rr_date')
    op.drop_column('po_report', 'material_des')
    op.drop_column('po_report', 'so_number')
    op.drop_column('po_report', 'project')
    op.drop_column('po_report', 'customer_site_ref')
    op.drop_column('po_report', 'pur_doc')

    # Restore old columns
    op.add_column('po_report', sa.Column('notes', sa.Text(), nullable=True))
    op.add_column('po_report', sa.Column('status', sa.String(100), nullable=True))
    op.add_column('po_report', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('po_report', sa.Column('report_name', sa.String(500), nullable=False))
