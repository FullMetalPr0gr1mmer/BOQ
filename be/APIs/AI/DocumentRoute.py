"""
AI Document Management API Routes
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List
import os
import shutil
from pathlib import Path
from datetime import datetime
import httpx

from Schemas.AI import (
    DocumentResponse,
    DocumentSearch,
    DocumentSearchResponse,
    DocumentQuestion,
    DocumentAnswer,
    DocumentSearchResult
)
from AI.rag_engine import get_rag_engine
from AI.agent import get_agent
from APIs.Core import get_current_user, get_db
from Models.Admin.User import User
from Models.AI import Document, DocumentChunk

import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/documents", tags=["AI Documents"])

# Upload directory
UPLOAD_DIR = Path("uploads/documents")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# n8n webhook URL for automatic processing
N8N_WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/boq-document-upload")


def process_document_background(document_id: int, file_path: str, db_url: str, extract_tags: bool):
    """Background task to process document - MUST RUN IN THREAD"""
    logger.info(f"[THREAD] Starting processing thread for document {document_id}")

    def _process():
        """Actual processing logic in thread"""
        logger.info(f"[THREAD] Thread started for document {document_id}")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from AI.rag_engine import get_rag_engine
        import time

        start_time = time.time()
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(bind=engine)
        db = SessionLocal()

        try:
            logger.info(f"[THREAD] Getting RAG engine for document {document_id}")
            rag_engine = get_rag_engine()
            logger.info(f"[THREAD] RAG engine loaded in {time.time()-start_time:.2f}s")

            logger.info(f"[THREAD] Processing document {document_id}")
            rag_engine.process_document(
                file_path=file_path,
                document_id=document_id,
                db=db,
                extract_tags=extract_tags
            )
            elapsed = time.time() - start_time
            logger.info(f"[THREAD] Successfully processed document {document_id} in {elapsed:.2f}s")
        except Exception as e:
            logger.error(f"[THREAD] Processing error for doc {document_id}: {e}")
            import traceback
            logger.error(f"[THREAD] Traceback: {traceback.format_exc()}")
        finally:
            db.close()
            logger.info(f"[THREAD] Closed DB session for document {document_id}")

    # Start in non-daemon thread so it survives FastAPI shutdown
    import threading
    thread = threading.Thread(target=_process, daemon=False, name=f"doc-process-{document_id}")
    thread.start()
    logger.info(f"[THREAD] Processing thread started for document {document_id}")


@router.post("/upload", response_model=DocumentResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    project_type: Optional[str] = Form(None),
    project_id: Optional[int] = Form(None),
    auto_process: bool = Form(True),
    extract_tags: bool = Form(True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload a document (PDF, DOCX, TXT) for AI processing

    The document will be:
    1. Stored in the file system
    2. Text extracted and chunked
    3. Embedded into vector database
    4. Optionally analyzed for tags and metadata

    Args:
        file: Document file to upload
        project_type: Optional project type ('boq', 'ran', 'rop')
        project_id: Optional project ID to link document
        auto_process: Automatically process document (default: true)
        extract_tags: Use AI to extract tags (default: true)
        current_user: Authenticated user
        db: Database session

    Returns:
        Document metadata and processing status
    """
    # Validate file type
    allowed_extensions = ['.pdf', '.docx', '.doc', '.txt']
    file_ext = Path(file.filename).suffix.lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type. Allowed: {', '.join(allowed_extensions)}"
        )

    # Check for duplicate file (same filename + size for this user)
    # Get file size first before checking duplicates
    file.file.seek(0, 2)  # Seek to end to get size
    file_size_check = file.file.tell()
    file.file.seek(0)  # Reset to beginning

    existing_document = db.query(Document).filter(
        Document.uploaded_by == current_user.id,
        Document.filename == file.filename,
        Document.file_size == file_size_check
    ).first()

    if existing_document:
        logger.info(f"Duplicate file detected: {file.filename} (size: {file_size_check}) already uploaded as document ID {existing_document.id}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"This file has already been uploaded. Document ID: {existing_document.id}"
        )

    try:
        # Generate unique filename
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = UPLOAD_DIR / safe_filename

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = os.path.getsize(file_path)

        # Create database record
        document = Document(
            project_type=project_type,
            project_id=project_id,
            filename=file.filename,
            file_path=str(file_path),
            file_type=file_ext.lstrip('.'),
            file_size=file_size,
            uploaded_by=current_user.id,
            processing_status='pending' if auto_process else 'uploaded'
        )

        db.add(document)
        db.commit()
        logger.info(f"AFTER COMMIT - Document committed to database")
        db.refresh(document)
        logger.info(f"AFTER REFRESH - Document ID: {document.id}")

        logger.info(f"Document {document.id} uploaded by user {current_user.id}: {file.filename}")

        # Process in background if requested
        logger.info(f"auto_process={auto_process}, type={type(auto_process)}")
        if auto_process:
            # Check if n8n is available
            use_n8n = os.getenv("USE_N8N_PROCESSING", "true").lower() == "true"
            logger.info(f"use_n8n={use_n8n}, USE_N8N_PROCESSING={os.getenv('USE_N8N_PROCESSING')}")

            if use_n8n:
                # Trigger n8n workflow for processing
                from APIs.Core import create_access_token
                token = create_access_token({"user_id": current_user.id})

                background_tasks.add_task(
                    trigger_n8n_processing,
                    document.id,
                    token
                )
            else:
                # Use direct background processing (call directly, not via background_tasks)
                db_url = os.getenv('DATABASE_URL')
                logger.info(f"Starting thread processing for document {document.id}")
                # Call directly - the function creates its own thread
                process_document_background(
                    document.id,
                    str(file_path),
                    db_url,
                    extract_tags
                )
                logger.info(f"Processing thread launched for document {document.id}")

        return DocumentResponse(
            document_id=document.id,
            filename=document.filename,
            file_type=document.file_type,
            file_size=document.file_size,
            processing_status=document.processing_status,
            tags=document.tags or [],
            summary=document.summary,
            upload_date=document.upload_date
        )

    except Exception as e:
        logger.error(f"Document upload error: {e}")
        # Clean up file if database insert failed
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading document: {str(e)}"
        )


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    project_type: Optional[str] = None,
    project_id: Optional[int] = None,
    limit: int = 50
):
    """
    List uploaded documents

    Args:
        current_user: Authenticated user
        db: Database session
        project_type: Filter by project type
        project_id: Filter by project ID
        limit: Max documents to return

    Returns:
        List of documents
    """
    try:
        query = db.query(Document)

        if project_type:
            query = query.filter(Document.project_type == project_type)

        if project_id:
            query = query.filter(Document.project_id == project_id)

        documents = query.order_by(Document.upload_date.desc()).limit(limit).all()

        return [
            DocumentResponse(
                document_id=doc.id,
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size,
                processing_status=doc.processing_status,
                tags=doc.tags or [],
                summary=doc.summary,
                upload_date=doc.upload_date
            )
            for doc in documents
        ]

    except Exception as e:
        logger.error(f"Error listing documents: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listing documents: {str(e)}"
        )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get document details

    Args:
        document_id: Document ID
        current_user: Authenticated user
        db: Database session

    Returns:
        Document metadata
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    return DocumentResponse(
        document_id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        processing_status=document.processing_status,
        tags=document.tags or [],
        summary=document.summary,
        upload_date=document.upload_date
    )


@router.delete("/{document_id}")
async def delete_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete a document and its embeddings

    Args:
        document_id: Document ID to delete
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        # Delete file
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()

        # Delete from vector store
        from AI import get_vector_store
        vector_store = get_vector_store()
        vector_store.delete_document(document_id)

        # Delete from database (cascades to chunks)
        db.delete(document)
        db.commit()

        logger.info(f"Deleted document {document_id} by user {current_user.id}")

        return {
            "success": True,
            "message": f"Document '{document.filename}' deleted"
        }

    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting document: {str(e)}"
        )


@router.post("/search", response_model=DocumentSearchResponse)
async def search_documents(
    request: DocumentSearch,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Semantic search across documents

    Args:
        request: Search parameters
        current_user: Authenticated user
        db: Database session

    Returns:
        Search results with similarity scores
    """
    try:
        start_time = datetime.utcnow()

        # Get document IDs for filtering
        document_ids = None
        if request.project_type or request.project_id or request.tags:
            query = db.query(Document.id)

            if request.project_type:
                query = query.filter(Document.project_type == request.project_type)

            if request.project_id:
                query = query.filter(Document.project_id == request.project_id)

            if request.tags:
                # Filter by tags (JSON array contains)
                for tag in request.tags:
                    query = query.filter(Document.tags.contains([tag]))

            document_ids = [row[0] for row in query.all()]

            if not document_ids:
                return DocumentSearchResponse(
                    query=request.query,
                    results=[],
                    total_results=0,
                    processing_time_ms=0
                )

        # Search using RAG engine
        rag_engine = get_rag_engine()
        search_results = rag_engine.search_documents(
            query=request.query,
            limit=request.limit,
            score_threshold=request.threshold,
            document_ids=document_ids
        )

        # Get document details
        results = []
        for result in search_results:
            doc = db.query(Document).filter(Document.id == result['document_id']).first()
            if doc:
                results.append(DocumentSearchResult(
                    document_id=doc.id,
                    filename=doc.filename,
                    chunk_text=result['text'],
                    page_number=result.get('page_number'),
                    similarity_score=result['similarity_score'],
                    tags=doc.tags or [],
                    project_info={
                        "type": doc.project_type,
                        "id": doc.project_id
                    } if doc.project_type else None
                ))

        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

        return DocumentSearchResponse(
            query=request.query,
            results=results,
            total_results=len(results),
            processing_time_ms=processing_time
        )

    except Exception as e:
        logger.error(f"Document search error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching documents: {str(e)}"
        )


@router.post("/ask", response_model=DocumentAnswer)
async def ask_question(
    request: DocumentQuestion,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Ask a question about documents using RAG

    Args:
        request: Question and filters
        current_user: Authenticated user
        db: Database session

    Returns:
        AI-generated answer with sources
    """
    try:
        # Get document IDs for filtering
        document_ids = request.document_ids
        if request.project_id and not document_ids:
            docs = db.query(Document.id).filter(
                Document.project_id == request.project_id,
                Document.processing_status == 'completed'
            ).all()
            document_ids = [row[0] for row in docs]

        # Get RAG answer
        rag_engine = get_rag_engine()
        result = rag_engine.answer_question(
            question=request.question,
            db=db,
            document_ids=document_ids
        )

        # Format sources
        sources = []
        for source in result['sources']:
            sources.append(DocumentSearchResult(
                document_id=source['document_id'],
                filename=source['filename'],
                chunk_text=source['chunk_text'],
                page_number=source.get('page_number'),
                similarity_score=source['similarity_score'],
                tags=[],
                project_info=None
            ))

        # Generate follow-up questions
        follow_ups = [
            "Can you provide more details?",
            "Are there any related specifications?",
            "What are the key requirements?"
        ]

        return DocumentAnswer(
            answer=result['answer'],
            sources=sources,
            confidence=result['confidence'],
            conversation_id=request.conversation_id or "single-shot",
            follow_up_questions=follow_ups
        )

    except Exception as e:
        logger.error(f"Document Q&A error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error answering question: {str(e)}"
        )


@router.get("/tags/all")
async def get_all_tags(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all unique tags from documents

    Args:
        current_user: Authenticated user
        db: Database session

    Returns:
        List of unique tags with counts
    """
    try:
        documents = db.query(Document).filter(
            Document.tags.isnot(None)
        ).all()

        # Collect all tags
        tag_counts = {}
        for doc in documents:
            if doc.tags:
                for tag in doc.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

        # Sort by count
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)

        return {
            "tags": [
                {"tag": tag, "count": count}
                for tag, count in sorted_tags
            ],
            "total_unique_tags": len(sorted_tags)
        }

    except Exception as e:
        logger.error(f"Error getting tags: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving tags: {str(e)}"
        )


# ============================================================
# n8n Integration Endpoints
# ============================================================

async def trigger_n8n_processing(document_id: int, token: str):
    """Trigger n8n webhook for document processing"""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                N8N_WEBHOOK_URL,
                json={
                    "document_id": document_id,
                    "token": token
                }
            )
            if response.status_code != 200:
                logger.error(f"n8n webhook failed for doc {document_id}: {response.text}")
    except Exception as e:
        logger.error(f"Error triggering n8n for doc {document_id}: {e}")


@router.post("/process/{document_id}")
async def process_document_endpoint(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Process a document (extract text, generate embeddings, extract tags)
    Used by n8n workflow

    Args:
        document_id: Document ID to process
        current_user: Authenticated user
        db: Database session

    Returns:
        Processing result with tags
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    try:
        # Update status
        document.processing_status = 'processing'
        db.commit()

        # Process with RAG engine
        rag_engine = get_rag_engine()
        rag_engine.process_document(
            file_path=document.file_path,
            document_id=document_id,
            db=db,
            extract_tags=True
        )

        # Refresh to get updated tags
        db.refresh(document)

        logger.info(f"Document {document_id} processed successfully")

        return {
            "success": True,
            "document_id": document_id,
            "tags": document.tags or [],
            "summary": document.summary,
            "status": document.processing_status
        }

    except Exception as e:
        document.processing_status = 'failed'
        db.commit()
        logger.error(f"Error processing document {document_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error processing document: {str(e)}"
        )


@router.patch("/{document_id}/status")
async def update_document_status(
    document_id: int,
    status: str = Form(...),
    error: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update document processing status
    Used by n8n workflow

    Args:
        document_id: Document ID
        status: New status (pending, processing, completed, failed)
        error: Optional error message if failed
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated document
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    document.processing_status = status
    db.commit()

    logger.info(f"Document {document_id} status updated to: {status}")

    return {
        "success": True,
        "document_id": document_id,
        "status": status
    }


@router.patch("/{document_id}/tags")
async def update_document_tags(
    document_id: int,
    tags: List[str] = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update document tags
    Used by n8n workflow

    Args:
        document_id: Document ID
        tags: List of tags to set
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated document
    """
    document = db.query(Document).filter(Document.id == document_id).first()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )

    document.tags = tags
    db.commit()

    logger.info(f"Document {document_id} tags updated: {tags}")

    return {
        "success": True,
        "document_id": document_id,
        "tags": tags
    }
