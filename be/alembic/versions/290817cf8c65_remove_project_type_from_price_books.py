"""remove_project_type_from_price_books

Revision ID: 290817cf8c65
Revises: c4963384bb93
Create Date: 2026-01-28 17:22:11.498115

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '290817cf8c65'
down_revision: Union[str, Sequence[str], None] = 'c4963384bb93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop index on project_type column if it exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_project_type' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            DROP INDEX ix_price_books_project_type ON price_books
        END
    """)

    # Drop project_type column from price_books table if it exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_type'
        )
        BEGIN
            ALTER TABLE price_books DROP COLUMN project_type
        END
    """)

    # Drop any p1-p24 columns and sen_counter if they exist
    # These columns appear in the error but are not in the model
    for i in range(1, 25):
        op.execute(f"""
            IF EXISTS (
                SELECT * FROM INFORMATION_SCHEMA.COLUMNS
                WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'p{i}'
            )
            BEGIN
                ALTER TABLE price_books DROP COLUMN p{i}
            END
        """)

    op.execute("""
        IF EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'sen_counter'
        )
        BEGIN
            ALTER TABLE price_books DROP COLUMN sen_counter
        END
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Add back project_type column if needed (nullable to avoid data loss)
    op.execute("""
        IF NOT EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_type'
        )
        BEGIN
            ALTER TABLE price_books ADD project_type VARCHAR(255) NULL
        END
    """)

    # Re-create index on project_type if column exists
    op.execute("""
        IF EXISTS (
            SELECT * FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'price_books' AND COLUMN_NAME = 'project_type'
        )
        AND NOT EXISTS (
            SELECT * FROM sys.indexes
            WHERE name = 'ix_price_books_project_type' AND object_id = OBJECT_ID('price_books')
        )
        BEGIN
            CREATE INDEX ix_price_books_project_type ON price_books (project_type)
        END
    """)
