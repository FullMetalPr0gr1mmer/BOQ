"""add_identity_to_od_boq_site_id

Revision ID: e6609a133295
Revises: d98ef14e8c40
Create Date: 2026-02-08 12:48:32.360563

Fix: Convert id column to IDENTITY (auto-increment) in SQL Server
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6609a133295'
down_revision: Union[str, Sequence[str], None] = 'd98ef14e8c40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Convert id column to IDENTITY by recreating the table."""

    # Step 1: Find and drop the foreign key constraint from du_od_boq_site_product
    op.execute("""
        DECLARE @ConstraintName nvarchar(200)
        SELECT @ConstraintName = Name FROM sys.foreign_keys
        WHERE parent_object_id = OBJECT_ID('du_od_boq_site_product')
        AND referenced_object_id = OBJECT_ID('du_od_boq_site')
        AND COL_NAME(parent_object_id, (SELECT parent_column_id FROM sys.foreign_key_columns WHERE constraint_object_id = object_id)) = 'site_record_id'
        IF @ConstraintName IS NOT NULL
            EXEC('ALTER TABLE du_od_boq_site_product DROP CONSTRAINT ' + @ConstraintName)
    """)

    # Step 2: Create a new table with IDENTITY on id column
    op.execute("""
        CREATE TABLE du_od_boq_site_new (
            id INT IDENTITY(1,1) NOT NULL,
            site_id NVARCHAR(100) NOT NULL,
            region NVARCHAR(100) NULL,
            distance NVARCHAR(100) NULL,
            scope NVARCHAR(100) NULL,
            subscope NVARCHAR(200) NULL,
            po_model NVARCHAR(500) NULL,
            project_id VARCHAR(200) NULL,
            ac_armod_cable NVARCHAR(100) NULL,
            additional_cost NVARCHAR(100) NULL,
            remark NVARCHAR(500) NULL,
            partner NVARCHAR(200) NULL,
            request_status NVARCHAR(100) NULL,
            requested_date NVARCHAR(100) NULL,
            du_po_number NVARCHAR(100) NULL,
            smp NVARCHAR(100) NULL,
            year_scope NVARCHAR(50) NULL,
            integration_status NVARCHAR(100) NULL,
            integration_date NVARCHAR(100) NULL,
            du_po_convention_name NVARCHAR(200) NULL,
            po_year_issuance NVARCHAR(50) NULL,
            CONSTRAINT PK_du_od_boq_site_new_id PRIMARY KEY (id),
            CONSTRAINT uix_site_subscope_new UNIQUE (site_id, subscope),
            CONSTRAINT FK_du_od_boq_site_project_new FOREIGN KEY (project_id) REFERENCES du_project(pid_po)
        )
    """)

    # Step 3: Copy data from old table to new table, preserving id values
    op.execute("""
        SET IDENTITY_INSERT du_od_boq_site_new ON

        INSERT INTO du_od_boq_site_new (
            id, site_id, region, distance, scope, subscope, po_model, project_id,
            ac_armod_cable, additional_cost, remark, partner, request_status,
            requested_date, du_po_number, smp, year_scope, integration_status,
            integration_date, du_po_convention_name, po_year_issuance
        )
        SELECT
            id, site_id, region, distance, scope, subscope, po_model, project_id,
            ac_armod_cable, additional_cost, remark, partner, request_status,
            requested_date, du_po_number, smp, year_scope, integration_status,
            integration_date, du_po_convention_name, po_year_issuance
        FROM du_od_boq_site
        ORDER BY id

        SET IDENTITY_INSERT du_od_boq_site_new OFF
    """)

    # Step 4: Drop old table
    op.execute("DROP TABLE du_od_boq_site")

    # Step 5: Rename new table to original name
    op.execute("EXEC sp_rename 'du_od_boq_site_new', 'du_od_boq_site'")

    # Step 6: Recreate indexes on the new table
    op.create_index(op.f('ix_du_od_boq_site_id'), 'du_od_boq_site', ['id'], unique=False)
    op.create_index('ix_du_od_boq_site_site_id', 'du_od_boq_site', ['site_id'], unique=False)
    op.create_index('ix_du_od_boq_site_scope', 'du_od_boq_site', ['scope'], unique=False)
    op.create_index('ix_du_od_boq_site_subscope', 'du_od_boq_site', ['subscope'], unique=False)
    op.create_index('ix_du_od_boq_site_project_id', 'du_od_boq_site', ['project_id'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_partner'), 'du_od_boq_site', ['partner'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_request_status'), 'du_od_boq_site', ['request_status'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_du_po_number'), 'du_od_boq_site', ['du_po_number'], unique=False)
    op.create_index(op.f('ix_du_od_boq_site_integration_status'), 'du_od_boq_site', ['integration_status'], unique=False)

    # Step 7: Recreate foreign key from du_od_boq_site_product to du_od_boq_site
    op.create_foreign_key(
        None,  # Let SQL Server auto-generate name
        'du_od_boq_site_product', 'du_od_boq_site',
        ['site_record_id'], ['id']
    )


def downgrade() -> None:
    """Downgrade not supported - would require recreating without IDENTITY."""
    pass
