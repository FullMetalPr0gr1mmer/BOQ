"""Add project_id and section to audit_logs for project-scoped access control

Revision ID: a5b6c7d8e9f0
Revises: f7a8b9c0d1e2, c3a0ac1538bb
Create Date: 2026-02-11 10:00:00.000000

This migration merges the two existing heads and adds project tracking columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a5b6c7d8e9f0'
# Merge both existing heads into a single migration
down_revision: Union[str, Sequence[str], None] = ('f7a8b9c0d1e2', 'c3a0ac1538bb')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add project tracking columns to audit_logs for project-scoped access control."""
    from sqlalchemy import inspect
    from alembic import context

    # Get connection and inspector
    bind = op.get_bind()
    inspector = inspect(bind)

    # Get existing columns
    existing_columns = [col['name'] for col in inspector.get_columns('audit_logs')]

    # Add project_id column if it doesn't exist
    if 'project_id' not in existing_columns:
        op.add_column('audit_logs', sa.Column('project_id', sa.String(length=200), nullable=True))

    # Add section column if it doesn't exist
    if 'section' not in existing_columns:
        op.add_column('audit_logs', sa.Column('section', sa.Integer(), nullable=True))

    # Get existing indexes
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('audit_logs')]

    # Create indexes for efficient filtering (only if they don't exist)
    if 'ix_audit_logs_project_id' not in existing_indexes:
        op.create_index('ix_audit_logs_project_id', 'audit_logs', ['project_id'], unique=False)

    if 'ix_audit_logs_section' not in existing_indexes:
        op.create_index('ix_audit_logs_section', 'audit_logs', ['section'], unique=False)

    if 'ix_audit_logs_project_section' not in existing_indexes:
        op.create_index('ix_audit_logs_project_section', 'audit_logs', ['project_id', 'section'], unique=False)

    # Add indexes on action, timestamp, resource_type if they don't exist
    if 'ix_audit_logs_action' not in existing_indexes:
        op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)

    if 'ix_audit_logs_timestamp' not in existing_indexes:
        op.create_index('ix_audit_logs_timestamp', 'audit_logs', ['timestamp'], unique=False)

    if 'ix_audit_logs_resource_type' not in existing_indexes:
        op.create_index('ix_audit_logs_resource_type', 'audit_logs', ['resource_type'], unique=False)


def downgrade() -> None:
    """Remove project tracking columns from audit_logs."""
    from sqlalchemy import inspect

    bind = op.get_bind()
    inspector = inspect(bind)

    # Get existing indexes and columns
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('audit_logs')]
    existing_columns = [col['name'] for col in inspector.get_columns('audit_logs')]

    # Drop indexes only if they exist
    for idx_name in ['ix_audit_logs_resource_type', 'ix_audit_logs_timestamp',
                     'ix_audit_logs_action', 'ix_audit_logs_project_section',
                     'ix_audit_logs_section', 'ix_audit_logs_project_id']:
        if idx_name in existing_indexes:
            op.drop_index(idx_name, table_name='audit_logs')

    # Drop columns only if they exist
    if 'section' in existing_columns:
        op.drop_column('audit_logs', 'section')
    if 'project_id' in existing_columns:
        op.drop_column('audit_logs', 'project_id')
