"""add_od_boq_tables_site_product_siteproduct

Revision ID: 0d423207336b
Revises: d3def1b1ed93
Create Date: 2026-01-18 12:07:52.774932

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0d423207336b'
down_revision: Union[str, Sequence[str], None] = 'd3def1b1ed93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create du_od_boq_site table (parent)
    op.create_table(
        'du_od_boq_site',
        sa.Column('site_id', sa.String(length=100), nullable=False),
        sa.Column('region', sa.String(length=100), nullable=True),
        sa.Column('distance', sa.String(length=100), nullable=True),
        sa.Column('scope', sa.String(length=100), nullable=True),
        sa.Column('subscope', sa.String(length=200), nullable=True),
        sa.Column('po_model', sa.String(length=500), nullable=True),
        sa.Column('project_id', sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(['project_id'], ['du_project.pid_po'], ),
        sa.PrimaryKeyConstraint('site_id')
    )
    op.create_index(op.f('ix_du_od_boq_site_site_id'), 'du_od_boq_site', ['site_id'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_scope'), 'du_od_boq_site', ['scope'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_subscope'), 'du_od_boq_site', ['subscope'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_project_id'), 'du_od_boq_site', ['project_id'], unique=False)

    # Create du_od_boq_product table (product master)
    op.create_table(
        'du_od_boq_product',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.Column('line_number', sa.String(length=50), nullable=True),
        sa.Column('code', sa.String(length=50), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('total_po_qty', sa.Float(), nullable=True),
        sa.Column('consumed_in_year', sa.Float(), nullable=True),
        sa.Column('consumed_year', sa.Integer(), nullable=True),
        sa.Column('remaining_in_po', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_du_od_boq_product_id'), 'du_od_boq_product', ['id'], unique=False)
    op.create_index(op.f('ix_du_od_boq_product_description'), 'du_od_boq_product', ['description'], unique=False)
    op.create_index(op.f('ix_du_od_boq_product_code'), 'du_od_boq_product', ['code'], unique=False)
    op.create_index(op.f('ix_du_od_boq_product_category'), 'du_od_boq_product', ['category'], unique=False)

    # Create du_od_boq_site_product table (junction)
    op.create_table(
        'du_od_boq_site_product',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('site_id', sa.String(length=100), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('qty_per_site', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['product_id'], ['du_od_boq_product.id'], ),
        sa.ForeignKeyConstraint(['site_id'], ['du_od_boq_site.site_id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'product_id', name='uix_site_product')
    )
    op.create_index(op.f('ix_du_od_boq_site_product_id'), 'du_od_boq_site_product', ['id'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_product_site_id'), 'du_od_boq_site_product', ['site_id'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_product_product_id'), 'du_od_boq_site_product', ['product_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop tables in reverse order (due to foreign key constraints)
    op.drop_index(op.f('ix_du_od_boq_site_product_product_id'), table_name='du_od_boq_site_product')
    op.drop_index(op.f('ix_du_od_boq_site_product_site_id'), table_name='du_od_boq_site_product')
    op.drop_index(op.f('ix_du_od_boq_site_product_id'), table_name='du_od_boq_site_product')
    op.drop_table('du_od_boq_site_product')

    op.drop_index(op.f('ix_du_od_boq_product_category'), table_name='du_od_boq_product')
    op.drop_index(op.f('ix_du_od_boq_product_code'), table_name='du_od_boq_product')
    op.drop_index(op.f('ix_du_od_boq_product_description'), table_name='du_od_boq_product')
    op.drop_index(op.f('ix_du_od_boq_product_id'), table_name='du_od_boq_product')
    op.drop_table('du_od_boq_product')

    op.drop_index(op.f('ix_du_od_boq_site_project_id'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_subscope'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_scope'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_site_id'), table_name='du_od_boq_site')
    op.drop_table('du_od_boq_site')
