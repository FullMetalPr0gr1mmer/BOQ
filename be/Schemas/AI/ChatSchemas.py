from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class ChatMessage(BaseModel):
    """Request schema for chat endpoint"""
    message: str = Field(..., description="User's message to the AI")
    conversation_id: Optional[str] = Field(None, description="Session UUID for conversation continuity")
    project_context: Optional[Dict[str, Any]] = Field(
        None,
        description="Current project context: {'type': 'boq', 'id': 123}"
    )
    stream: bool = Field(False, description="Enable streaming responses")


class ChatResponse(BaseModel):
    """Response schema for chat endpoint"""
    response: str = Field(..., description="AI's text response")
    conversation_id: str = Field(..., description="Session UUID")
    actions_taken: List[str] = Field(default_factory=list, description="Functions called by AI")
    data: Optional[Dict[str, Any]] = Field(None, description="Structured data from actions")
    sources: Optional[List[Dict[str, Any]]] = Field(None, description="Document sources cited")
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class FunctionCall(BaseModel):
    """Schema for AI function calls"""
    name: str = Field(..., description="Function name")
    arguments: Dict[str, Any] = Field(..., description="Function arguments")
    result: Optional[Any] = Field(None, description="Function return value")
    status: str = Field("pending", description="'pending', 'success', 'failed'")
    error: Optional[str] = Field(None, description="Error message if failed")


class ConversationHistory(BaseModel):
    """Schema for retrieving conversation history"""
    conversation_id: str
    messages: List[Dict[str, Any]]
    created_at: datetime
    last_message_at: datetime
    message_count: int


class DocumentUpload(BaseModel):
    """Schema for document upload metadata"""
    project_type: Optional[str] = Field(None, description="'boq', 'ran', or 'rop'")
    project_id: Optional[int] = Field(None, description="Project ID to link document")
    auto_process: bool = Field(True, description="Automatically extract and embed text")
    extract_tags: bool = Field(True, description="Auto-generate tags using AI")


class DocumentResponse(BaseModel):
    """Response schema for document upload"""
    document_id: int
    filename: str
    file_type: str
    file_size: int
    processing_status: str
    tags: List[str] = Field(default_factory=list)
    summary: Optional[str] = None
    upload_date: datetime


class DocumentSearch(BaseModel):
    """Request schema for document search"""
    query: str = Field(..., description="Search query")
    project_type: Optional[str] = Field(None, description="Filter by project type")
    project_id: Optional[int] = Field(None, description="Filter by specific project")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    limit: int = Field(10, ge=1, le=100, description="Number of results")
    threshold: float = Field(0.7, ge=0.0, le=1.0, description="Similarity threshold")


class DocumentSearchResult(BaseModel):
    """Single search result"""
    document_id: int
    filename: str
    chunk_text: str
    page_number: Optional[int] = None
    similarity_score: float
    tags: List[str]
    project_info: Optional[Dict[str, Any]] = None


class DocumentSearchResponse(BaseModel):
    """Response schema for document search"""
    query: str
    results: List[DocumentSearchResult]
    total_results: int
    processing_time_ms: int


class DocumentQuestion(BaseModel):
    """Request schema for Q&A on documents"""
    question: str = Field(..., description="Question to ask about documents")
    document_ids: Optional[List[int]] = Field(None, description="Limit to specific documents")
    project_id: Optional[int] = Field(None, description="Limit to specific project")
    conversation_id: Optional[str] = Field(None, description="For follow-up questions")


class DocumentAnswer(BaseModel):
    """Response schema for document Q&A"""
    answer: str = Field(..., description="AI-generated answer")
    sources: List[DocumentSearchResult] = Field(..., description="Source chunks used")
    confidence: float = Field(..., description="Confidence score 0-1")
    conversation_id: str
    follow_up_questions: List[str] = Field(default_factory=list, description="Suggested follow-ups")
