"""change_sub_scope_to_text

Revision ID: ccee4facaf05
Revises: 2d36c9eb52f9
Create Date: 2026-01-29 23:12:34.927136

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ccee4facaf05'
down_revision: Union[str, Sequence[str], None] = '2d36c9eb52f9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Change sub_scope from VARCHAR(200) to TEXT/NVARCHAR(MAX)
    op.execute("ALTER TABLE price_books ALTER COLUMN sub_scope NVARCHAR(MAX)")


def downgrade() -> None:
    """Downgrade schema."""
    # Revert sub_scope back to VARCHAR(200)
    op.execute("ALTER TABLE price_books ALTER COLUMN sub_scope VARCHAR(200)")
