"""add_indexes_to_price_books

Revision ID: 6e4d7f579e10
Revises: 290817cf8c65
Create Date: 2026-01-28 17:37:24.728007

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6e4d7f579e10'
down_revision: Union[str, Sequence[str], None] = '290817cf8c65'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add indexes for commonly queried columns

    # Index on po_number for filtering and search
    op.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_po_number' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            CREATE INDEX ix_price_books_po_number ON price_books (po_number)
        END
    """)

    # Index on created_at for sorting
    op.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_created_at' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            CREATE INDEX ix_price_books_created_at ON price_books (created_at DESC)
        END
    """)

    # Index on uploaded_by for filtering by user
    op.execute("""
        IF NOT EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_uploaded_by' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            CREATE INDEX ix_price_books_uploaded_by ON price_books (uploaded_by)
        END
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop indexes
    op.execute("""
        IF EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_po_number' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            DROP INDEX ix_price_books_po_number ON price_books
        END
    """)

    op.execute("""
        IF EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_created_at' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            DROP INDEX ix_price_books_created_at ON price_books
        END
    """)

    op.execute("""
        IF EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_uploaded_by' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            DROP INDEX ix_price_books_uploaded_by ON price_books
        END
    """)
