from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from Database.session import Base


class Document(Base):
    """
    Stores metadata for uploaded documents (PDFs, DOCX, etc.)
    Linked to projects for context-aware retrieval
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    # Link to project (can be BOQ, RAN, or ROP project)
    project_type = Column(String(20))  # 'boq', 'ran', 'rop'
    project_id = Column(Integer, nullable=True)  # Foreign key to respective project table

    # File information
    filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    file_type = Column(String(50), nullable=False)  # 'pdf', 'docx', 'txt'
    file_size = Column(Integer)  # Size in bytes

    # Metadata
    upload_date = Column(DateTime, default=datetime.utcnow)
    uploaded_by = Column(Integer, ForeignKey('users.id'))

    # AI-generated metadata
    tags = Column(JSON, default=list)  # Auto-generated tags: ['invoice', 'technical_spec', 'antenna']
    summary = Column(Text, nullable=True)  # AI-generated summary
    document_type = Column(String(100), nullable=True)  # Classified type
    extracted_entities = Column(JSON, default=dict)  # {'sites': [], 'equipment': [], 'dates': []}

    # Processing status
    processing_status = Column(String(20), default='pending')  # 'pending', 'processing', 'completed', 'failed'
    processing_error = Column(Text, nullable=True)

    # Relationships
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<Document(id={self.id}, filename='{self.filename}', type='{self.file_type}')>"


class DocumentChunk(Base):
    """
    Text chunks from documents for vector search
    Each chunk is embedded and stored in Qdrant
    """
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)

    # Chunk content
    chunk_text = Column(Text, nullable=False)
    chunk_index = Column(Integer, nullable=False)  # Order in document

    # Vector store reference
    vector_id = Column(String(100), nullable=False, unique=True)  # UUID in Qdrant

    # Metadata for retrieval
    page_number = Column(Integer, nullable=True)  # For PDFs
    section_title = Column(String(255), nullable=True)
    chunk_metadata = Column(JSON, default=dict)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, chunk={self.chunk_index})>"


class ChatHistory(Base):
    """
    Stores conversation history for context-aware AI responses
    """
    __tablename__ = "chat_history"

    id = Column(Integer, primary_key=True, index=True)

    # User and session
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    conversation_id = Column(String(100), nullable=False, index=True)  # UUID for session

    # Message
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)

    # Context
    project_type = Column(String(20), nullable=True)  # Current context
    project_id = Column(Integer, nullable=True)

    # Metadata
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    tokens_used = Column(Integer, default=0)

    # Function calls made by AI
    function_calls = Column(JSON, default=list)  # [{'name': 'create_project', 'args': {...}}]

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<ChatHistory(id={self.id}, conv_id='{self.conversation_id}', role='{self.role}')>"


class AIAction(Base):
    """
    Audit log for AI-performed actions
    Tracks what the AI did for compliance and debugging
    """
    __tablename__ = "ai_actions"

    id = Column(Integer, primary_key=True, index=True)

    # User and context
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    conversation_id = Column(String(100), nullable=False)

    # Action details
    action_type = Column(String(100), nullable=False)  # 'create_project', 'update_inventory', etc.
    action_params = Column(JSON, nullable=False)  # Function arguments
    action_result = Column(JSON, nullable=True)  # Function return value

    # Status
    status = Column(String(20), default='success')  # 'success', 'failed', 'cancelled'
    error_message = Column(Text, nullable=True)

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    execution_time_ms = Column(Integer)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])

    def __repr__(self):
        return f"<AIAction(id={self.id}, type='{self.action_type}', status='{self.status}')>"
