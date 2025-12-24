"""Add token_blacklist table for logout functionality

Revision ID: ad531142ac2f
Revises: c06aeb6215bc
Create Date: 2025-12-17 16:12:48.534920

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ad531142ac2f'
down_revision: Union[str, Sequence[str], None] = 'c06aeb6215bc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create token_blacklist table for logout functionality.

    This table stores revoked access tokens to prevent their reuse after logout.
    Tokens are automatically cleaned up after they naturally expire.
    """
    op.create_table(
        'token_blacklist',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('blacklisted_at', sa.DateTime(), nullable=False, server_default=sa.text('GETDATE()')),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_token_blacklist_id', 'token_blacklist', ['id'])
    op.create_index('ix_token_blacklist_token', 'token_blacklist', ['token'], unique=True)
    op.create_index('idx_blacklist_expires_at', 'token_blacklist', ['expires_at'])


def downgrade() -> None:
    """Downgrade schema - Drop token_blacklist table."""
    op.drop_index('idx_blacklist_expires_at', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_token', table_name='token_blacklist')
    op.drop_index('ix_token_blacklist_id', table_name='token_blacklist')
    op.drop_table('token_blacklist')
