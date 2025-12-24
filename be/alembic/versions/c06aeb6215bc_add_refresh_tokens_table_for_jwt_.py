"""Add refresh_tokens table for JWT authentication

Revision ID: c06aeb6215bc
Revises: f5e6992a0641
Create Date: 2025-12-17 16:07:20.610786

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c06aeb6215bc'
down_revision: Union[str, Sequence[str], None] = 'f5e6992a0641'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Create refresh_tokens table for JWT authentication.

    This table stores refresh tokens to allow users to obtain new access tokens
    without re-authenticating. Includes automatic cleanup of expired tokens.
    """
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('token', sa.String(length=500), nullable=False),
        sa.Column('expires_at', sa.DateTime(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('GETDATE()')),
        sa.Column('revoked', sa.Boolean(), nullable=False, server_default=sa.text('0')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes for performance
    op.create_index('ix_refresh_tokens_id', 'refresh_tokens', ['id'])
    op.create_index('ix_refresh_tokens_token', 'refresh_tokens', ['token'], unique=True)
    op.create_index('ix_refresh_tokens_expires_at', 'refresh_tokens', ['expires_at'])
    op.create_index('idx_refresh_token_lookup', 'refresh_tokens', ['token', 'revoked', 'expires_at'])


def downgrade() -> None:
    """Downgrade schema - Drop refresh_tokens table."""
    op.drop_index('idx_refresh_token_lookup', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_expires_at', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_token', table_name='refresh_tokens')
    op.drop_index('ix_refresh_tokens_id', table_name='refresh_tokens')
    op.drop_table('refresh_tokens')
