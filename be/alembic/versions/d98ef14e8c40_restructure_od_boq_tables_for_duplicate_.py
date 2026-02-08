"""restructure_od_boq_tables_for_duplicate_sites

Revision ID: d98ef14e8c40
Revises: b7c8d9e0f1a2
Create Date: 2026-02-08 12:05:05.213667

Major changes:
1. Change du_od_boq_site primary key from site_id to auto-increment id
2. Allow duplicate site_id with different subscope (unique constraint on site_id + subscope)
3. Add new metadata columns to du_od_boq_site
4. Update du_od_boq_site_product to reference site.id instead of site_id
5. Auto-calculate consumed_in_year and remaining_in_po (no migration needed, just app logic)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd98ef14e8c40'
down_revision: Union[str, Sequence[str], None] = 'b7c8d9e0f1a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # Step 1: Drop foreign key constraints (use actual SQL Server generated names)
    op.drop_constraint('FK__du_od_boq__site___14B10FFA', 'du_od_boq_site_product', type_='foreignkey')
    op.drop_constraint('uix_site_product', 'du_od_boq_site_product', type_='unique')

    # Step 2: Add new id column to du_od_boq_site (NOT IDENTITY yet, just a regular column)
    op.add_column('du_od_boq_site', sa.Column('id', sa.Integer(), nullable=True))

    # Step 3: Populate id column with sequential values
    op.execute("""
        DECLARE @Counter INT = 1
        DECLARE @SiteID NVARCHAR(100)

        DECLARE site_cursor CURSOR FOR
        SELECT site_id FROM du_od_boq_site ORDER BY site_id

        OPEN site_cursor
        FETCH NEXT FROM site_cursor INTO @SiteID

        WHILE @@FETCH_STATUS = 0
        BEGIN
            UPDATE du_od_boq_site SET id = @Counter WHERE site_id = @SiteID
            SET @Counter = @Counter + 1
            FETCH NEXT FROM site_cursor INTO @SiteID
        END

        CLOSE site_cursor
        DEALLOCATE site_cursor
    """)

    # Step 4: Make id NOT NULL
    op.alter_column('du_od_boq_site', 'id', nullable=False, existing_type=sa.Integer(), type_=sa.Integer())

    # Step 5: Add site_record_id column to du_od_boq_site_product
    op.add_column('du_od_boq_site_product', sa.Column('site_record_id', sa.Integer(), nullable=True))

    # Step 6: Populate site_record_id based on site_id mapping
    op.execute("""
        UPDATE du_od_boq_site_product
        SET site_record_id = s.id
        FROM du_od_boq_site s
        WHERE du_od_boq_site_product.site_id = s.site_id
    """)

    # Step 7: Make site_record_id NOT NULL
    op.alter_column('du_od_boq_site_product', 'site_record_id', nullable=False, existing_type=sa.Integer(), type_=sa.Integer())

    # Step 8: Drop old primary key constraint and site_id column from site_product
    op.drop_index('ix_du_od_boq_site_product_site_id', table_name='du_od_boq_site_product')
    op.drop_column('du_od_boq_site_product', 'site_id')

    # Step 9: Drop old primary key from du_od_boq_site and create new one
    op.drop_constraint('PK__du_od_bo__B22FDBCAA6E02432', 'du_od_boq_site', type_='primary')
    op.create_primary_key('PK_du_od_boq_site_id', 'du_od_boq_site', ['id'])

    # Step 10: Create index on id
    op.create_index(op.f('ix_du_od_boq_site_id'), 'du_od_boq_site', ['id'], unique=False)

    # Step 11: Add new metadata columns to du_od_boq_site
    op.add_column('du_od_boq_site', sa.Column('ac_armod_cable', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('additional_cost', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('remark', sa.String(500), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('partner', sa.String(200), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('request_status', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('requested_date', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('du_po_number', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('smp', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('year_scope', sa.String(50), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('integration_status', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('integration_date', sa.String(100), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('du_po_convention_name', sa.String(200), nullable=True))
    op.add_column('du_od_boq_site', sa.Column('po_year_issuance', sa.String(50), nullable=True))

    # Step 12: Create indexes on new columns
    op.create_index(op.f('ix_du_od_boq_site_partner'), 'du_od_boq_site', ['partner'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_request_status'), 'du_od_boq_site', ['request_status'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_du_po_number'), 'du_od_boq_site', ['du_po_number'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_integration_status'), 'du_od_boq_site', ['integration_status'], unique=False)

    # Step 13: Add unique constraint on (site_id, subscope)
    op.create_unique_constraint('uix_site_subscope', 'du_od_boq_site', ['site_id', 'subscope'])

    # Step 14: Create index on site_record_id in site_product
    op.create_index(op.f('ix_du_od_boq_site_product_site_record_id'), 'du_od_boq_site_product', ['site_record_id'], unique=False)

    # Step 15: Re-create foreign key constraints (SQL Server will auto-generate name)
    op.create_foreign_key(
        None,  # Let SQL Server auto-generate the name
        'du_od_boq_site_product', 'du_od_boq_site',
        ['site_record_id'], ['id']
    )

    # Step 16: Add new unique constraint on (site_record_id, product_id)
    op.create_unique_constraint('uix_site_product', 'du_od_boq_site_product', ['site_record_id', 'product_id'])


def downgrade() -> None:
    """Downgrade schema."""

    # WARNING: This downgrade will lose data if there are duplicate site_ids with different subscopes

    # Step 1: Drop constraints
    op.drop_constraint('uix_site_product', 'du_od_boq_site_product', type_='unique')
    # Drop the new foreign key constraint (will be auto-named by SQL Server)
    op.execute("ALTER TABLE du_od_boq_site_product DROP CONSTRAINT IF EXISTS du_od_boq_site_product_site_record_id_fkey")
    # Also try with SQL Server auto-generated name pattern
    op.execute("""
        DECLARE @ConstraintName nvarchar(200)
        SELECT @ConstraintName = Name FROM sys.foreign_keys
        WHERE parent_object_id = OBJECT_ID('du_od_boq_site_product')
        AND referenced_object_id = OBJECT_ID('du_od_boq_site')
        AND COL_NAME(parent_object_id, (SELECT parent_column_id FROM sys.foreign_key_columns WHERE constraint_object_id = object_id)) = 'site_record_id'
        IF @ConstraintName IS NOT NULL
            EXEC('ALTER TABLE du_od_boq_site_product DROP CONSTRAINT ' + @ConstraintName)
    """)
    op.drop_index(op.f('ix_du_od_boq_site_product_site_record_id'), table_name='du_od_boq_site_product')

    # Step 2: Drop unique constraint on du_od_boq_site
    op.drop_constraint('uix_site_subscope', 'du_od_boq_site', type_='unique')

    # Step 3: Drop new column indexes
    op.drop_index(op.f('ix_du_od_boq_site_integration_status'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_du_po_number'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_request_status'), table_name='du_od_boq_site')
    op.drop_index(op.f('ix_du_od_boq_site_partner'), table_name='du_od_boq_site')

    # Step 4: Drop new metadata columns
    op.drop_column('du_od_boq_site', 'po_year_issuance')
    op.drop_column('du_od_boq_site', 'du_po_convention_name')
    op.drop_column('du_od_boq_site', 'integration_date')
    op.drop_column('du_od_boq_site', 'integration_status')
    op.drop_column('du_od_boq_site', 'year_scope')
    op.drop_column('du_od_boq_site', 'smp')
    op.drop_column('du_od_boq_site', 'du_po_number')
    op.drop_column('du_od_boq_site', 'requested_date')
    op.drop_column('du_od_boq_site', 'request_status')
    op.drop_column('du_od_boq_site', 'partner')
    op.drop_column('du_od_boq_site', 'remark')
    op.drop_column('du_od_boq_site', 'additional_cost')
    op.drop_column('du_od_boq_site', 'ac_armod_cable')

    # Step 5: Add back site_id column to site_product
    op.add_column('du_od_boq_site_product', sa.Column('site_id', sa.String(100), nullable=True))

    # Step 6: Populate site_id from site_record_id
    op.execute("""
        UPDATE du_od_boq_site_product
        SET site_id = s.site_id
        FROM du_od_boq_site s
        WHERE du_od_boq_site_product.site_record_id = s.id
    """)

    # Step 7: Make site_id NOT NULL
    op.alter_column('du_od_boq_site_product', 'site_id', nullable=False, existing_type=sa.String(100), type_=sa.String(100))

    # Step 8: Drop site_record_id
    op.drop_column('du_od_boq_site_product', 'site_record_id')

    # Step 9: Drop new primary key and id column from du_od_boq_site
    op.drop_index(op.f('ix_du_od_boq_site_id'), table_name='du_od_boq_site')
    op.drop_constraint('PK_du_od_boq_site_id', 'du_od_boq_site', type_='primary')
    op.drop_column('du_od_boq_site', 'id')

    # Step 10: Re-create old primary key on site_id (let SQL Server auto-generate the name)
    op.create_primary_key(None, 'du_od_boq_site', ['site_id'])

    # Step 11: Re-create index on site_id in site_product
    op.create_index(op.f('ix_du_od_boq_site_product_site_id'), 'du_od_boq_site_product', ['site_id'], unique=False)

    # Step 12: Re-create foreign key (SQL Server will auto-generate name)
    op.create_foreign_key(
        None,  # Let SQL Server auto-generate the name
        'du_od_boq_site_product', 'du_od_boq_site',
        ['site_id'], ['site_id']
    )

    # Step 13: Re-create unique constraint
    op.create_unique_constraint('uix_site_product', 'du_od_boq_site_product', ['site_id', 'product_id'])
