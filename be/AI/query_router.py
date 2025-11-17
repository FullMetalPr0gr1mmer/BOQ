"""
Intelligent Query Router - Prevents Hallucinations

This router detects the query type and routes to the appropriate system:
- Database queries → Direct SQL execution (NO conversational LLM)
- Document questions → Document RAG
- General chat → LLM conversation

This PREVENTS the hallucination issue where LLM generates fake context
before executing database queries.

Author: Senior AI Architect
Created: 2025-11-06
"""
import re
from enum import Enum
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Types of queries the system can handle."""
    DATABASE = "database"
    DOCUMENT = "document"
    CHAT = "chat"


class QueryRouter:
    """
    Smart router that detects query intent and routes to appropriate system.

    Key Feature: Database queries bypass conversational LLM to prevent hallucinations.
    """

    # Database-specific keywords
    DATABASE_KEYWORDS = [
        # Action verbs
        'fetch', 'get', 'show', 'list', 'find', 'retrieve', 'select',
        'count', 'sum', 'calculate', 'analyze', 'aggregate',
        'how many', 'how much', 'total', 'average',

        # Your actual table names (add all your tables here)
        'users', 'projects', 'audit', 'roles', 'sites',
        'lvl1', 'lvl2', 'lvl3', 'lvl4',
        'ran_lld', 'ran_inventory', 'ran_antenna', 'ran_project',
        'rop_lvl1', 'rop_lvl2', 'rop_project', 'rop_packages',
        'boq_reference', 'dismantling', 'inventory', 'lld',
        'monthly_distribution', 'document_chunks', 'chat_history',

        # Database-specific terms
        'database', 'table', 'sql', 'query', 'records', 'rows',
        'pid_po', 'site_id', 'project_id', 'user_id'
    ]

    # Document-specific keywords
    DOCUMENT_KEYWORDS = [
        'document', 'pdf', 'file', 'uploaded', 'attachment',
        'according to', 'what does', 'in the', 'from the',
        'rfp', 'contract', 'specification', 'manual',
        'documentation', 'guide', 'report'
    ]

    # Direct table patterns (e.g., "fetch me ran_lld", "get users")
    DIRECT_TABLE_PATTERN = re.compile(
        r'\b(fetch|get|show|retrieve|select|give me|display)\s+(me\s+)?'
        r'(all\s+)?(the\s+)?'
        r'([a-z_]+)',
        re.IGNORECASE
    )

    def __init__(self):
        """Initialize the query router."""
        pass

    def detect_query_type(self, question: str) -> QueryType:
        """
        Detect the type of query.

        Priority order:
        1. Direct table requests (highest priority)
        2. Database keywords
        3. Document keywords
        4. Default to chat

        Args:
            question: User's question

        Returns:
            QueryType enum
        """
        question_lower = question.lower().strip()

        # Priority 1: Direct table patterns (e.g., "fetch me ran_lld")
        if self._is_direct_table_request(question_lower):
            logger.info(f"Detected DIRECT TABLE REQUEST: {question}")
            return QueryType.DATABASE

        # Priority 2: Database keywords
        if self._has_database_keywords(question_lower):
            logger.info(f"Detected DATABASE QUERY: {question}")
            return QueryType.DATABASE

        # Priority 3: Document keywords
        if self._has_document_keywords(question_lower):
            logger.info(f"Detected DOCUMENT QUERY: {question}")
            return QueryType.DOCUMENT

        # Default: Chat
        logger.info(f"Detected CHAT QUERY: {question}")
        return QueryType.CHAT

    def _is_direct_table_request(self, question: str) -> bool:
        """
        Check if this is a direct table request like "fetch me ran_lld".

        These should ALWAYS go to database, never to conversational LLM.
        """
        # Check direct pattern
        if self.DIRECT_TABLE_PATTERN.search(question):
            return True

        # Check if it's just a table name with minimal words
        words = question.split()
        if len(words) <= 4:  # Short queries like "get ran_lld"
            for word in words:
                if word in self.DATABASE_KEYWORDS:
                    return True

        return False

    def _has_database_keywords(self, question: str) -> bool:
        """Check if question contains database-related keywords."""
        # Check for keyword matches
        keyword_count = sum(
            1 for keyword in self.DATABASE_KEYWORDS
            if keyword in question
        )

        # If 2+ database keywords, it's likely a database query
        return keyword_count >= 2

    def _has_document_keywords(self, question: str) -> bool:
        """Check if question contains document-related keywords."""
        return any(keyword in question for keyword in self.DOCUMENT_KEYWORDS)

    def route_query(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Route query to appropriate system and return result.

        This is the main entry point for all queries.

        Args:
            question: User's question
            user_id: Optional user ID for tracking

        Returns:
            Dictionary with response data
        """
        query_type = self.detect_query_type(question)

        if query_type == QueryType.DATABASE:
            return self._handle_database_query(question, user_id)

        elif query_type == QueryType.DOCUMENT:
            return self._handle_document_query(question, user_id)

        else:
            return self._handle_chat_query(question, user_id)

    def _handle_database_query(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle database query - NO CONVERSATIONAL LLM.

        Goes straight to Text-to-SQL → SQL execution.
        This prevents hallucinations.
        """
        try:
            from AI.text2sql_generator import Text2SQLGenerator

            # Generate SQL
            generator = Text2SQLGenerator(temperature=0.1)
            result = generator.generate_sql(
                question=question,
                database="SQL Server",
                validate=True
            )

            logger.info(f"Generated SQL: {result.sql}")

            # Return SQL without execution (execution happens in your existing system)
            return {
                "type": "database",
                "query_type": "database",
                "sql": result.sql,
                "confidence": result.confidence,
                "execution_ready": result.execution_ready,
                "errors": result.errors,
                "retrieved_context": {
                    "tables": len(result.retrieved_context.get('tables', [])),
                    "relationships": len(result.retrieved_context.get('relationships', [])),
                    "business_rules": len(result.retrieved_context.get('business_rules', []))
                },
                # NO conversational message - prevents hallucination!
                "message": None,
                "instruction": "Execute this SQL query to get the data."
            }

        except Exception as e:
            logger.error(f"Database query error: {e}")
            return {
                "type": "error",
                "query_type": "database",
                "error": str(e),
                "message": f"Error generating SQL: {e}"
            }

    def _handle_document_query(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle document query - Use document RAG.
        """
        try:
            from AI.vectorstore import get_vector_store
            from AI.ollama_client import get_ollama_client

            # Search documents
            vs = get_vector_store()
            results = vs.search(question, limit=5, score_threshold=0.6)

            if not results:
                return {
                    "type": "document",
                    "query_type": "document",
                    "message": "No relevant documents found for your question.",
                    "sources": []
                }

            # Generate answer from documents
            llm = get_ollama_client()
            context = "\n\n".join([
                f"[Document {i+1} - Page {r.get('page_number', 'N/A')}]\n{r['text']}"
                for i, r in enumerate(results)
            ])

            answer = llm.generate(
                prompt=f"Question: {question}",
                system_prompt=f"""You are a helpful assistant. Answer the question based ONLY on the provided documents.

Documents:
{context}

IMPORTANT: Only use information from the documents above. If the answer is not in the documents, say so.""",
                temperature=0.3
            )

            return {
                "type": "document",
                "query_type": "document",
                "message": answer,
                "sources": [
                    {
                        "document_id": r.get('document_id'),
                        "page_number": r.get('page_number'),
                        "text": r['text'][:200] + "...",
                        "score": r['similarity_score']
                    }
                    for r in results
                ]
            }

        except Exception as e:
            logger.error(f"Document query error: {e}")
            return {
                "type": "error",
                "query_type": "document",
                "error": str(e),
                "message": f"Error searching documents: {e}"
            }

    def _handle_chat_query(
        self,
        question: str,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle general chat query - Use conversational LLM.
        """
        try:
            from AI.ollama_client import get_ollama_client

            llm = get_ollama_client()
            response = llm.generate(
                prompt=question,
                system_prompt="You are a helpful assistant. Provide clear, concise answers.",
                temperature=0.7
            )

            return {
                "type": "chat",
                "query_type": "chat",
                "message": response
            }

        except Exception as e:
            logger.error(f"Chat query error: {e}")
            return {
                "type": "error",
                "query_type": "chat",
                "error": str(e),
                "message": f"Error generating response: {e}"
            }


# Singleton instance
_query_router_instance: Optional[QueryRouter] = None


def get_query_router() -> QueryRouter:
    """
    Get or create QueryRouter singleton instance.

    Returns:
        QueryRouter instance
    """
    global _query_router_instance
    if _query_router_instance is None:
        _query_router_instance = QueryRouter()
    return _query_router_instance


# Convenience function
def route_query(question: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to route a query.

    Args:
        question: User's question
        user_id: Optional user ID

    Returns:
        Response dictionary

    Example:
        result = route_query("fetch me ran_lld")
        if result['type'] == 'database':
            sql = result['sql']
            # Execute SQL...
    """
    router = get_query_router()
    return router.route_query(question, user_id)
