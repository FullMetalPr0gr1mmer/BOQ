"""Add AI tables for documents and chat

Revision ID: a068c6bdfd26
Revises: f3cc23fa93fd
Create Date: 2025-10-22 11:38:18.649748

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a068c6bdfd26'
down_revision: Union[str, Sequence[str], None] = 'f3cc23fa93fd'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create documents table
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_type', sa.String(20), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('filename', sa.String(255), nullable=False),
        sa.Column('file_path', sa.String(500), nullable=False),
        sa.Column('file_type', sa.String(50), nullable=False),
        sa.Column('file_size', sa.Integer(), nullable=True),
        sa.Column('upload_date', sa.DateTime(), nullable=True),
        sa.Column('uploaded_by', sa.Integer(), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('document_type', sa.String(100), nullable=True),
        sa.Column('extracted_entities', sa.JSON(), nullable=True),
        sa.Column('processing_status', sa.String(20), nullable=True),
        sa.Column('processing_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_documents_id'), 'documents', ['id'], unique=False)

    # Create document_chunks table
    op.create_table(
        'document_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('document_id', sa.Integer(), nullable=False),
        sa.Column('chunk_text', sa.Text(), nullable=False),
        sa.Column('chunk_index', sa.Integer(), nullable=False),
        sa.Column('vector_id', sa.String(100), nullable=False),
        sa.Column('page_number', sa.Integer(), nullable=True),
        sa.Column('section_title', sa.String(255), nullable=True),
        sa.Column('chunk_metadata', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['document_id'], ['documents.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('vector_id')
    )
    op.create_index(op.f('ix_document_chunks_id'), 'document_chunks', ['id'], unique=False)

    # Create chat_history table
    op.create_table(
        'chat_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(100), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('project_type', sa.String(20), nullable=True),
        sa.Column('project_id', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('function_calls', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_chat_history_id'), 'chat_history', ['id'], unique=False)
    op.create_index(op.f('ix_chat_history_conversation_id'), 'chat_history', ['conversation_id'], unique=False)
    op.create_index(op.f('ix_chat_history_timestamp'), 'chat_history', ['timestamp'], unique=False)

    # Create ai_actions table
    op.create_table(
        'ai_actions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('conversation_id', sa.String(100), nullable=False),
        sa.Column('action_type', sa.String(100), nullable=False),
        sa.Column('action_params', sa.JSON(), nullable=False),
        sa.Column('action_result', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(20), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=True),
        sa.Column('execution_time_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ai_actions_id'), 'ai_actions', ['id'], unique=False)
    op.create_index(op.f('ix_ai_actions_timestamp'), 'ai_actions', ['timestamp'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_ai_actions_timestamp'), table_name='ai_actions')
    op.drop_index(op.f('ix_ai_actions_id'), table_name='ai_actions')
    op.drop_table('ai_actions')

    op.drop_index(op.f('ix_chat_history_timestamp'), table_name='chat_history')
    op.drop_index(op.f('ix_chat_history_conversation_id'), table_name='chat_history')
    op.drop_index(op.f('ix_chat_history_id'), table_name='chat_history')
    op.drop_table('chat_history')

    op.drop_index(op.f('ix_document_chunks_id'), table_name='document_chunks')
    op.drop_table('document_chunks')

    op.drop_index(op.f('ix_documents_id'), table_name='documents')
    op.drop_table('documents')
