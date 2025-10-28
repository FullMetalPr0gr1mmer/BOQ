"""
RAG (Retrieval-Augmented Generation) Engine for document Q&A
"""
import os
import re
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

# PDF processing
from pypdf import PdfReader
import pdfplumber

# Document processing
from docx import Document as DocxDocument

# Database
from sqlalchemy.orm import Session
from Models.AI import Document, DocumentChunk
from AI.vectorstore import get_vector_store
from AI.ollama_client import get_ollama_client

logger = logging.getLogger(__name__)


class RAGEngine:
    """
    Handles document processing, chunking, embedding, and Q&A
    """

    # Chunking parameters
    CHUNK_SIZE = 500  # characters per chunk
    CHUNK_OVERLAP = 100  # overlap between chunks

    def __init__(self):
        self.vector_store = get_vector_store()
        self.ollama_client = get_ollama_client()

    def process_document(
        self,
        file_path: str,
        document_id: int,
        db: Session,
        extract_tags: bool = True
    ) -> Dict[str, Any]:
        """
        Process a document: extract text, chunk, embed, and optionally generate metadata

        Args:
            file_path: Path to document file
            document_id: Database document ID
            db: Database session
            extract_tags: Whether to use AI to extract tags and metadata

        Returns:
            Processing results
        """
        try:
            # Get document from database
            document = db.query(Document).filter(Document.id == document_id).first()
            if not document:
                raise ValueError(f"Document {document_id} not found")

            # Update status
            document.processing_status = "processing"
            db.commit()

            # Extract text based on file type
            file_ext = Path(file_path).suffix.lower()
            logger.info(f"[PROCESS-{document_id}] Extracting text from {file_ext} file")

            if file_ext == '.pdf':
                text_content, metadata = self._extract_pdf(file_path)
            elif file_ext in ['.docx', '.doc']:
                text_content, metadata = self._extract_docx(file_path)
            elif file_ext == '.txt':
                text_content, metadata = self._extract_txt(file_path)
            else:
                raise ValueError(f"Unsupported file type: {file_ext}")

            logger.info(f"[PROCESS-{document_id}] Text extracted: {len(text_content)} characters")

            # Chunk text
            logger.info(f"[PROCESS-{document_id}] Chunking text...")
            chunks = self._chunk_text(text_content, metadata)
            logger.info(f"[PROCESS-{document_id}] Text chunked: {len(chunks)} chunks created")

            # Generate embeddings and store in Qdrant
            logger.info(f"[PROCESS-{document_id}] Generating embeddings and storing in Qdrant...")
            vector_ids = self.vector_store.add_document_chunks(document_id, chunks)
            logger.info(f"[PROCESS-{document_id}] Embeddings generated and stored: {len(vector_ids)} vectors")

            # Save chunks to database
            logger.info(f"[PROCESS-{document_id}] Saving {len(chunks)} chunks to database...")
            for i, (chunk, vector_id) in enumerate(zip(chunks, vector_ids)):
                db_chunk = DocumentChunk(
                    document_id=document_id,
                    chunk_text=chunk['text'],
                    chunk_index=chunk['chunk_index'],
                    vector_id=vector_id,
                    page_number=chunk.get('page_number'),
                    chunk_metadata=chunk.get('metadata', {})
                )
                db.add(db_chunk)
                if (i + 1) % 10 == 0 or (i + 1) == len(chunks):
                    logger.info(f"[PROCESS-{document_id}] Saved {i+1}/{len(chunks)} chunks to DB")

            logger.info(f"[PROCESS-{document_id}] All chunks added to session, committing...")
            db.commit()
            logger.info(f"[PROCESS-{document_id}] Chunks committed to database")

            # Extract tags and summary if requested
            if extract_tags:
                logger.info(f"[PROCESS-{document_id}] Extracting metadata with AI...")
                tags, summary, doc_type, entities = self._extract_metadata(text_content[:3000])
                document.tags = tags
                document.summary = summary
                document.document_type = doc_type
                document.extracted_entities = entities
                logger.info(f"[PROCESS-{document_id}] Metadata extracted: {len(tags)} tags")

            # Update document status
            logger.info(f"[PROCESS-{document_id}] Updating document status to completed...")
            document.processing_status = "completed"
            db.commit()
            logger.info(f"[PROCESS-{document_id}] Document status updated and committed")

            logger.info(f"Successfully processed document {document_id}: {len(chunks)} chunks")

            return {
                "status": "success",
                "chunks_created": len(chunks),
                "tags": document.tags,
                "summary": document.summary
            }

        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            document.processing_status = "failed"
            document.processing_error = str(e)
            db.commit()
            raise

    def _extract_pdf(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from PDF"""
        text_parts = []
        metadata = {"pages": 0}

        try:
            # Use pdfplumber for better table extraction
            with pdfplumber.open(file_path) as pdf:
                metadata["pages"] = len(pdf.pages)

                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text:
                        # Add page marker for chunking
                        text_parts.append(f"[PAGE {page_num}]\n{text}")

        except Exception as e:
            # Fallback to pypdf
            logger.warning(f"pdfplumber failed, using pypdf: {e}")
            reader = PdfReader(file_path)
            metadata["pages"] = len(reader.pages)

            for page_num, page in enumerate(reader.pages, start=1):
                text = page.extract_text()
                if text:
                    text_parts.append(f"[PAGE {page_num}]\n{text}")

        full_text = "\n\n".join(text_parts)
        return full_text, metadata

    def _extract_docx(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)
        paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
        text = "\n\n".join(paragraphs)

        metadata = {
            "paragraphs": len(paragraphs)
        }

        return text, metadata

    def _extract_txt(self, file_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text from TXT file"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()

        metadata = {
            "lines": text.count('\n')
        }

        return text, metadata

    def _chunk_text(self, text: str, file_metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks

        Args:
            text: Full document text
            file_metadata: Metadata from file extraction

        Returns:
            List of chunk dictionaries
        """
        chunks = []
        current_page = 1

        # Split by page markers if present
        page_pattern = r'\[PAGE (\d+)\]'
        page_splits = re.split(page_pattern, text)

        current_text = ""
        current_page = 1

        for i, part in enumerate(page_splits):
            if i % 2 == 1:  # Page number
                current_page = int(part)
            else:  # Text content
                if not part.strip():
                    continue

                # Add to current text
                current_text = part

                # Chunk this page's text
                start = 0
                chunk_index = len(chunks)

                while start < len(current_text):
                    end = start + self.CHUNK_SIZE

                    # Try to break at sentence boundary
                    if end < len(current_text):
                        # Look for sentence end
                        sentence_end = max(
                            current_text.rfind('. ', start, end),
                            current_text.rfind('.\n', start, end),
                            current_text.rfind('! ', start, end),
                            current_text.rfind('? ', start, end)
                        )
                        if sentence_end > start:
                            end = sentence_end + 1

                    chunk_text = current_text[start:end].strip()

                    if chunk_text:
                        chunks.append({
                            "text": chunk_text,
                            "chunk_index": chunk_index,
                            "page_number": current_page,
                            "metadata": {
                                "start_char": start,
                                "end_char": end
                            }
                        })
                        chunk_index += 1

                    # Move to next chunk with overlap
                    if end < len(current_text):
                        new_start = end - self.CHUNK_OVERLAP
                        # Ensure start always advances to prevent infinite loop
                        start = new_start if new_start > start else end
                    else:
                        start = end

        return chunks

    def _extract_metadata(self, text_sample: str) -> Tuple[List[str], str, str, Dict[str, Any]]:
        """
        Use Ollama to extract tags, summary, and entities from document

        Args:
            text_sample: First few thousand characters of document

        Returns:
            (tags, summary, document_type, entities)
        """
        prompt = f"""Analyze this document excerpt and provide:
1. 5-10 relevant tags (e.g., "invoice", "technical_spec", "antenna", "5G")
2. A one-sentence summary
3. Document type (e.g., "technical specification", "invoice", "contract", "drawing")
4. Key entities mentioned (sites, equipment, dates)

Document excerpt:
{text_sample}

Respond in JSON format:
{{
    "tags": ["tag1", "tag2", ...],
    "summary": "One sentence summary",
    "document_type": "type",
    "entities": {{
        "sites": ["site1", "site2"],
        "equipment": ["equipment1"],
        "dates": ["2024-01-15"]
    }}
}}
"""

        try:
            response = self.ollama_client.generate(prompt, json_mode=True)
            import json
            result = json.loads(response)

            return (
                result.get("tags", []),
                result.get("summary", ""),
                result.get("document_type", "unknown"),
                result.get("entities", {})
            )
        except Exception as e:
            logger.error(f"Error extracting metadata: {e}")
            return [], "", "unknown", {}

    def search_documents(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.3,  # Lowered from 0.7 to be more permissive
        document_ids: Optional[List[int]] = None
    ) -> List[Dict[str, Any]]:
        """
        Semantic search across documents

        Args:
            query: Search query
            limit: Max results
            score_threshold: Minimum similarity (lowered to 0.3 for better recall)
            document_ids: Filter by document IDs

        Returns:
            Search results
        """
        logger.info(f"[SEARCH] Query: '{query}', limit={limit}, threshold={score_threshold}, doc_ids={document_ids}")
        results = self.vector_store.search(
            query=query,
            limit=limit,
            score_threshold=score_threshold,
            document_ids=document_ids
        )
        logger.info(f"[SEARCH] Found {len(results)} results")
        if results:
            logger.info(f"[SEARCH] Top result score: {results[0]['similarity_score']:.4f}")
        return results

    def answer_question(
        self,
        question: str,
        db: Session,
        document_ids: Optional[List[int]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """
        Answer a question using RAG

        Args:
            question: User's question
            db: Database session
            document_ids: Limit to specific documents
            conversation_history: Previous messages for context

        Returns:
            Answer with sources
        """
        # Search for relevant chunks
        # For meta-questions about the document, use hybrid strategy
        is_meta_question = any(phrase in question.lower() for phrase in [
            'what is this document', 'what does this document', 'document about',
            'summary of', 'overview of', 'introduction to', 'this pdf', 'this file'
        ])

        if is_meta_question:
            logger.info(f"[RAG] Meta-question detected, using hybrid search (page 1 + semantic)")

            # Strategy 1: Get first chunks from page 1 (guaranteed title/intro)
            from Models.AI import DocumentChunk
            page1_chunks = []
            if document_ids:
                page1_chunks = db.query(DocumentChunk).filter(
                    DocumentChunk.document_id.in_(document_ids),
                    DocumentChunk.page_number == 1
                ).order_by(DocumentChunk.chunk_index).limit(3).all()

                # Convert to search result format
                page1_results = []
                for chunk in page1_chunks:
                    page1_results.append({
                        'vector_id': chunk.vector_id,
                        'document_id': chunk.document_id,
                        'text': chunk.chunk_text,
                        'page_number': chunk.page_number,
                        'chunk_index': chunk.chunk_index,
                        'similarity_score': 0.9,  # High score for page 1 chunks
                        'metadata': chunk.chunk_metadata or {}
                    })
                logger.info(f"[RAG] Retrieved {len(page1_results)} chunks from page 1")

            # Strategy 2: Semantic search for additional context
            semantic_results = self.search_documents(
                query=question,
                limit=5,
                document_ids=document_ids
            )
            logger.info(f"[RAG] Retrieved {len(semantic_results)} chunks from semantic search")

            # Merge and deduplicate by vector_id
            seen_vector_ids = set()
            search_results = []

            # Add page 1 chunks first (highest priority)
            for result in page1_results:
                if result['vector_id'] not in seen_vector_ids:
                    search_results.append(result)
                    seen_vector_ids.add(result['vector_id'])

            # Add semantic search results
            for result in semantic_results:
                if result['vector_id'] not in seen_vector_ids and len(search_results) < 5:
                    search_results.append(result)
                    seen_vector_ids.add(result['vector_id'])

            logger.info(f"[RAG] After deduplication: {len(search_results)} unique chunks")

        else:
            # Normal search for specific questions
            search_results = self.search_documents(
                query=question,
                limit=5,
                document_ids=document_ids
            )

            # Deduplicate by vector_id
            seen_vector_ids = set()
            deduped_results = []
            for result in search_results:
                if result['vector_id'] not in seen_vector_ids:
                    deduped_results.append(result)
                    seen_vector_ids.add(result['vector_id'])
            search_results = deduped_results
            logger.info(f"[RAG] After deduplication: {len(search_results)} unique chunks")

        if not search_results:
            return {
                "answer": "I couldn't find any relevant information in the documents to answer your question.",
                "sources": [],
                "confidence": 0.0
            }

        # Build context from search results
        context_parts = []
        for i, result in enumerate(search_results, 1):
            context_parts.append(f"[Source {i}] {result['text']}")

        context = "\n\n".join(context_parts)

        # Build prompt
        system_prompt = """You are a helpful assistant that answers questions based on provided document excerpts.
Always cite your sources using [Source N] notation.
If the information is not in the provided context, say so clearly."""

        # Add conversation history if available
        messages = []
        if conversation_history:
            messages.extend(conversation_history)

        messages.append({
            "role": "user",
            "content": f"""Context from documents:
{context}

Question: {question}

Please answer based on the context above, citing sources."""
        })

        # Get answer from Ollama
        answer = self.ollama_client.chat(messages, system_prompt=system_prompt)

        # Calculate confidence based on similarity scores
        avg_score = sum(r['similarity_score'] for r in search_results) / len(search_results)

        # Get document details for sources
        sources = []
        for result in search_results:
            doc = db.query(Document).filter(Document.id == result['document_id']).first()
            if doc:
                sources.append({
                    "document_id": doc.id,
                    "filename": doc.filename,
                    "chunk_text": result['text'][:200] + "...",
                    "page_number": result.get('page_number'),
                    "similarity_score": result['similarity_score']
                })

        return {
            "answer": answer,
            "sources": sources,
            "confidence": avg_score
        }


# Singleton instance
_rag_engine_instance: Optional[RAGEngine] = None


def get_rag_engine() -> RAGEngine:
    """Get or create RAGEngine singleton"""
    global _rag_engine_instance
    if _rag_engine_instance is None:
        _rag_engine_instance = RAGEngine()
    return _rag_engine_instance
