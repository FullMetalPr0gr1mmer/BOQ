"""
Text-to-SQL Vector Store - Task 2 Implementation

This module manages the Text-to-SQL schema knowledge base in Qdrant.
It's separate from the document Q&A vectorstore to allow specialized:
- Metadata structures optimized for schema retrieval
- Different search strategies (hybrid filtering by chunk type)
- Dedicated collection for schema knowledge

Author: Senior AI Architect
Created: 2025-11-06
"""
import uuid
import os
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter,
    FieldCondition, MatchValue, MatchAny
)
import ollama
import logging

logger = logging.getLogger(__name__)


class Text2SQLVectorStore:
    """
    Specialized vector store for Text-to-SQL schema knowledge.

    This store contains:
    - Table schemas (columns, types, constraints)
    - Relationship information (JOIN conditions)
    - Business rules (domain knowledge)
    - Enum definitions (allowed values)

    Optimized for retrieving precise, relevant schema context for SQL generation.
    """

    COLLECTION_NAME = "text2sql_schema"
    EMBEDDING_MODEL = "nomic-embed-text"  # Same as your existing setup
    VECTOR_SIZE = 768

    # Chunk type priorities for ranking
    CHUNK_TYPE_PRIORITY = {
        "relationship": 10,      # Highest - prevents wrong joins!
        "business_rule": 9,      # Critical for understanding domain logic
        "table_overview": 8,     # Important for identifying relevant tables
        "columns": 7,            # Needed for SELECT clauses
        "business_rules": 6,     # Pydantic validation rules
        "enum": 5,               # Constraint information
        "schema_overview": 4,    # Pydantic schema context
    }

    def __init__(
        self,
        qdrant_host: str = "localhost",
        qdrant_port: int = 6333,
        ollama_host: str = "http://localhost:11434"
    ):
        """
        Initialize Text-to-SQL vector store.

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
            ollama_host: Ollama server URL
        """
        # Disable proxy for localhost
        os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
        os.environ['no_proxy'] = 'localhost,127.0.0.1'

        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        self.ollama_client = ollama.Client(host=ollama_host)
        logger.info(f"Initialized Text2SQLVectorStore with model: {self.EMBEDDING_MODEL}")
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist."""
        try:
            self.client.get_collection(self.COLLECTION_NAME)
            logger.info(f"Collection '{self.COLLECTION_NAME}' already exists")
        except Exception:
            logger.info(f"Creating collection '{self.COLLECTION_NAME}'")
            self.client.create_collection(
                collection_name=self.COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=self.VECTOR_SIZE,
                    distance=Distance.COSINE
                )
            )
            logger.info(f"Collection '{self.COLLECTION_NAME}' created successfully")

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text using Ollama.

        Args:
            text: Input text

        Returns:
            Embedding vector (768-dimensional)
        """
        try:
            response = self.ollama_client.embeddings(
                model=self.EMBEDDING_MODEL,
                prompt=text
            )
            return response['embedding']
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    def embed_batch(self, texts: List[str], batch_size: int = 10) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of input texts
            batch_size: Process texts in batches (for progress tracking)

        Returns:
            List of embedding vectors
        """
        embeddings = []
        total = len(texts)

        for i in range(0, total, batch_size):
            batch = texts[i:i + batch_size]
            logger.info(f"Embedding batch {i//batch_size + 1}/{(total + batch_size - 1)//batch_size} ({len(batch)} texts)")

            for text in batch:
                try:
                    response = self.ollama_client.embeddings(
                        model=self.EMBEDDING_MODEL,
                        prompt=text
                    )
                    embeddings.append(response['embedding'])
                except Exception as e:
                    logger.error(f"Error embedding text: {e}")
                    # Use zero vector as fallback
                    embeddings.append([0.0] * self.VECTOR_SIZE)

        return embeddings

    def add_schema_chunks(self, chunks: List[Dict[str, Any]]) -> List[str]:
        """
        Add schema knowledge chunks to the vector store.

        Expected chunk format:
        {
            "content": "text content...",
            "metadata": {
                "type": "table_overview" | "columns" | "relationship" | "enum" | "business_rule",
                "table_name": "users",  # optional
                "schema_name": "UserSchema",  # optional
                ...
            }
        }

        Args:
            chunks: List of chunk dictionaries

        Returns:
            List of generated vector IDs
        """
        if not chunks:
            logger.warning("No chunks provided to add_schema_chunks")
            return []

        logger.info(f"Processing {len(chunks)} schema chunks for embedding...")

        # Extract texts for embedding
        texts = [chunk['content'] for chunk in chunks]

        # Generate embeddings
        logger.info("Generating embeddings...")
        embeddings = self.embed_batch(texts)

        # Create Qdrant points
        logger.info("Creating Qdrant points...")
        points = []
        vector_ids = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = str(uuid.uuid4())
            vector_ids.append(vector_id)

            # Extract metadata
            metadata = chunk.get('metadata', {})
            chunk_type = metadata.get('type', 'unknown')

            # Build payload with metadata for filtering
            payload = {
                "content": chunk['content'],
                "type": chunk_type,
                "priority": self.CHUNK_TYPE_PRIORITY.get(chunk_type, 0),
            }

            # Add optional metadata fields
            if 'table_name' in metadata:
                payload['table_name'] = metadata['table_name']
            if 'model_name' in metadata:
                payload['model_name'] = metadata['model_name']
            if 'schema_name' in metadata:
                payload['schema_name'] = metadata['schema_name']
            if 'target_model' in metadata:
                payload['target_model'] = metadata['target_model']
            if 'relationship_name' in metadata:
                payload['relationship_name'] = metadata['relationship_name']
            if 'enum_name' in metadata:
                payload['enum_name'] = metadata['enum_name']
            if 'term' in metadata:
                payload['term'] = metadata['term']
            if 'tables' in metadata:
                payload['tables'] = metadata['tables']
            if 'related_model' in metadata:
                payload['related_model'] = metadata['related_model']

            points.append(
                PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload=payload
                )
            )

        # Upload to Qdrant in batches
        logger.info(f"Uploading {len(points)} points to Qdrant...")
        batch_size = 100
        for i in range(0, len(points), batch_size):
            batch = points[i:i + batch_size]
            self.client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=batch
            )
            logger.info(f"Uploaded batch {i//batch_size + 1}/{(len(points) + batch_size - 1)//batch_size}")

        logger.info(f"Successfully added {len(points)} schema chunks to vector store")
        return vector_ids

    def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.6,
        chunk_types: Optional[List[str]] = None,
        table_names: Optional[List[str]] = None,
        prioritize_relationships: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant schema chunks.

        This is the core retrieval function for Text-to-SQL generation.

        Args:
            query: User's natural language question
            limit: Maximum number of results to return
            score_threshold: Minimum similarity score (0-1)
            chunk_types: Filter by chunk types (e.g., ["relationship", "table_overview"])
            table_names: Filter by specific table names
            prioritize_relationships: Boost relationship chunks in ranking

        Returns:
            List of search results with content, score, and metadata
        """
        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Build filters
        filters = []

        if chunk_types:
            filters.append(
                FieldCondition(
                    key="type",
                    match=MatchAny(any=chunk_types)
                )
            )

        if table_names:
            filters.append(
                FieldCondition(
                    key="table_name",
                    match=MatchAny(any=table_names)
                )
            )

        query_filter = Filter(must=filters) if filters else None

        # Search Qdrant
        # Fetch more results if we're prioritizing relationships (we'll re-rank)
        fetch_limit = limit * 2 if prioritize_relationships else limit

        search_results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=fetch_limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )

        # Format and optionally re-rank results
        results = []
        for hit in search_results:
            result = {
                "vector_id": hit.id,
                "content": hit.payload.get("content"),
                "similarity_score": hit.score,
                "type": hit.payload.get("type"),
                "priority": hit.payload.get("priority", 0),
                "table_name": hit.payload.get("table_name"),
                "model_name": hit.payload.get("model_name"),
                "schema_name": hit.payload.get("schema_name"),
                "metadata": {
                    k: v for k, v in hit.payload.items()
                    if k not in ["content", "type", "priority", "table_name", "model_name", "schema_name"]
                }
            }
            results.append(result)

        # Re-rank: boost high-priority chunks (relationships, business rules)
        if prioritize_relationships:
            results = self._rerank_by_priority(results)

        # Return top N after re-ranking
        return results[:limit]

    def _rerank_by_priority(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Re-rank results by combining similarity score with chunk type priority.

        This ensures that high-priority chunks (like relationships) are surfaced
        even if their similarity score is slightly lower.

        Args:
            results: Search results from Qdrant

        Returns:
            Re-ranked results
        """
        for result in results:
            # Compute combined score: 70% similarity + 30% priority
            similarity = result['similarity_score']
            priority = result['priority'] / 10.0  # Normalize priority to 0-1
            result['combined_score'] = 0.7 * similarity + 0.3 * priority

        # Sort by combined score
        results.sort(key=lambda x: x['combined_score'], reverse=True)

        return results

    def search_by_tables(
        self,
        query: str,
        table_names: List[str],
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for schema information about specific tables.

        Useful when you already know which tables are relevant.

        Args:
            query: User's question
            table_names: List of table names to focus on
            limit: Maximum results

        Returns:
            Search results filtered to specified tables
        """
        return self.search(
            query=query,
            limit=limit,
            table_names=table_names,
            prioritize_relationships=True
        )

    def get_relationships_for_tables(
        self,
        table_names: List[str],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get all relationship chunks for specific tables.

        CRITICAL for preventing wrong joins!

        Args:
            table_names: Tables to get relationships for
            limit: Max results

        Returns:
            Relationship chunks for specified tables
        """
        # Use a generic query that matches relationships
        query = f"JOIN relationships for tables: {', '.join(table_names)}"

        return self.search(
            query=query,
            limit=limit,
            chunk_types=["relationship"],
            table_names=table_names
        )

    def get_business_rules(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get relevant business rules for a query.

        Args:
            query: User's question
            limit: Max results

        Returns:
            Business rule chunks
        """
        return self.search(
            query=query,
            limit=limit,
            chunk_types=["business_rule", "business_rules"]
        )

    def clear_collection(self):
        """
        Delete all vectors in the collection.

        WARNING: This deletes all schema knowledge!
        Use only for re-indexing.
        """
        try:
            self.client.delete_collection(self.COLLECTION_NAME)
            logger.info(f"Deleted collection '{self.COLLECTION_NAME}'")
            self._ensure_collection_exists()
        except Exception as e:
            logger.error(f"Error clearing collection: {e}")
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection.

        Returns:
            Collection statistics including chunk type distribution
        """
        try:
            collection_info = self.client.get_collection(self.COLLECTION_NAME)

            # Get chunk type distribution by scrolling through all points
            scroll_result = self.client.scroll(
                collection_name=self.COLLECTION_NAME,
                limit=1000  # Adjust if you have more than 1000 chunks
            )

            type_counts = {}
            for point in scroll_result[0]:
                chunk_type = point.payload.get('type', 'unknown')
                type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

            return {
                "total_vectors": collection_info.points_count,
                "vector_size": collection_info.config.params.vectors.size,
                "distance_metric": collection_info.config.params.vectors.distance.value,
                "chunk_type_distribution": type_counts
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}


# Singleton instance
_text2sql_vector_store_instance: Optional[Text2SQLVectorStore] = None


def get_text2sql_vector_store() -> Text2SQLVectorStore:
    """
    Get or create Text2SQLVectorStore singleton instance.

    Returns:
        Text2SQLVectorStore instance
    """
    global _text2sql_vector_store_instance
    if _text2sql_vector_store_instance is None:
        _text2sql_vector_store_instance = Text2SQLVectorStore()
    return _text2sql_vector_store_instance
