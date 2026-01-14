"""Remove foreign key and pid_po from po_report

Revision ID: 80849e9309b6
Revises: 4c77bec2207a
Create Date: 2026-01-06 14:35:25.066551

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '80849e9309b6'
down_revision: Union[str, Sequence[str], None] = '4c77bec2207a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Remove foreign key and pid_po column from po_report."""
    # For SQL Server, we need to find and drop the foreign key constraint dynamically
    # since constraint names are auto-generated
    import sqlalchemy as sa
    from sqlalchemy import text

    bind = op.get_bind()

    # Query to find the actual foreign key constraint name
    fk_query = text("""
        SELECT fk.name
        FROM sys.foreign_keys AS fk
        INNER JOIN sys.foreign_key_columns AS fkc
            ON fk.object_id = fkc.constraint_object_id
        WHERE OBJECT_NAME(fk.parent_object_id) = 'po_report'
            AND COL_NAME(fkc.parent_object_id, fkc.parent_column_id) = 'pid_po'
    """)

    result = bind.execute(fk_query)
    row = result.fetchone()

    if row:
        constraint_name = row[0]
        # Drop the foreign key constraint
        with op.batch_alter_table('po_report', schema=None) as batch_op:
            batch_op.drop_constraint(constraint_name, type_='foreignkey')
            batch_op.drop_column('pid_po')
    else:
        # If no foreign key exists, just drop the column
        with op.batch_alter_table('po_report', schema=None) as batch_op:
            batch_op.drop_column('pid_po')


def downgrade() -> None:
    """Downgrade schema - Add back foreign key and pid_po column to po_report."""
    # Add the pid_po column back
    with op.batch_alter_table('po_report', schema=None) as batch_op:
        batch_op.add_column(sa.Column('pid_po', sa.String(length=200), nullable=True))
        batch_op.create_foreign_key('po_report_pid_po_fkey', 'projects', ['pid_po'], ['pid_po'])
