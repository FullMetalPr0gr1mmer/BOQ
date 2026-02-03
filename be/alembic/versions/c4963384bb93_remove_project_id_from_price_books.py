"""remove_project_id_from_price_books

Revision ID: c4963384bb93
Revises: 54bdd2bfc220
Create Date: 2026-01-28 17:13:26.019435

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c4963384bb93'
down_revision: Union[str, Sequence[str], None] = '54bdd2bfc220'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop index on project_id column if it exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_project_id' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            DROP INDEX ix_price_books_project_id ON price_books
        END
    """)

    # Drop project_id column from price_books table if it exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_id'
        )
        BEGIN
            ALTER TABLE price_books DROP COLUMN project_id
        END
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Add back project_id column if needed (nullable to avoid data loss)
    op.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_id'
        )
        BEGIN
            ALTER TABLE price_books ADD project_id VARCHAR(255) NULL
        END
    """)

    # Re-create index on project_id if column exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_id'
        )
        AND NOT EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_project_id' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            CREATE INDEX ix_price_books_project_id ON price_books (project_id)
        END
    """)
