"""
Vector store manager for document embeddings using Qdrant
"""
import uuid
import os
import ssl

# CRITICAL: Set offline mode BEFORE any imports that might use HuggingFace
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'
os.environ['HF_DATASETS_OFFLINE'] = '1'
# Disable SSL cert verification for local models
os.environ['CURL_CA_BUNDLE'] = ''
os.environ['REQUESTS_CA_BUNDLE'] = ''
os.environ['SSL_CERT_FILE'] = ''

from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, MatchAny
from sentence_transformers import SentenceTransformer
import logging

# Disable SSL verification warnings for local development
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages document embeddings in Qdrant vector database
    """

    COLLECTION_NAME = "boq_documents"
    EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # 384-dimensional embeddings
    VECTOR_SIZE = 384

    def __init__(self, qdrant_host: str = "localhost", qdrant_port: int = 6333):
        """
        Initialize Qdrant client and embedding model

        Args:
            qdrant_host: Qdrant server host
            qdrant_port: Qdrant server port
        """
        self.client = QdrantClient(host=qdrant_host, port=qdrant_port)
        # Load model from local cache only - environment variables prevent downloading
        logger.info(f"Loading embedding model '{self.EMBEDDING_MODEL}' in offline mode")
        self.embedding_model = SentenceTransformer(self.EMBEDDING_MODEL, device='cpu')
        logger.info(f"Successfully loaded embedding model from local cache")
        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Create collection if it doesn't exist"""
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

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for text

        Args:
            text: Input text

        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts

        Args:
            texts: List of input texts

        Returns:
            List of embedding vectors
        """
        embeddings = self.embedding_model.encode(texts, normalize_embeddings=True)
        return embeddings.tolist()

    def add_document_chunks(
        self,
        document_id: int,
        chunks: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Add document chunks to vector store

        Args:
            document_id: Document ID from database
            chunks: List of dicts with 'text', 'page_number', 'chunk_index', 'metadata'

        Returns:
            List of generated vector IDs
        """
        if not chunks:
            return []

        # Generate embeddings for all chunks
        logger.info(f"[VECTOR-{document_id}] Preparing to embed {len(chunks)} chunks")
        texts = [chunk['text'] for chunk in chunks]
        logger.info(f"[VECTOR-{document_id}] Extracted {len(texts)} texts, generating embeddings...")
        embeddings = self.embed_batch(texts)
        logger.info(f"[VECTOR-{document_id}] Embeddings generated: {len(embeddings)} vectors")

        # Create points for Qdrant
        logger.info(f"[VECTOR-{document_id}] Creating Qdrant points...")
        points = []
        vector_ids = []

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            vector_id = str(uuid.uuid4())
            vector_ids.append(vector_id)

            payload = {
                "document_id": document_id,
                "chunk_index": chunk.get('chunk_index', i),
                "page_number": chunk.get('page_number'),
                "text": chunk['text'],
                "metadata": chunk.get('metadata', {})
            }

            points.append(
                PointStruct(
                    id=vector_id,
                    vector=embedding,
                    payload=payload
                )
            )

        logger.info(f"[VECTOR-{document_id}] Created {len(points)} Qdrant points, uploading to Qdrant...")

        # Upload to Qdrant
        self.client.upsert(
            collection_name=self.COLLECTION_NAME,
            points=points
        )

        logger.info(f"[VECTOR-{document_id}] Successfully uploaded {len(points)} points to Qdrant")
        logger.info(f"Added {len(points)} chunks for document {document_id}")
        return vector_ids

    def search(
        self,
        query: str,
        limit: int = 10,
        score_threshold: float = 0.7,
        document_ids: Optional[List[int]] = None,
        project_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar document chunks

        Args:
            query: Search query text
            limit: Maximum number of results
            score_threshold: Minimum similarity score (0-1)
            document_ids: Filter by specific document IDs
            project_filter: Filter by project metadata

        Returns:
            List of search results with text, score, and metadata
        """
        # Generate query embedding
        query_embedding = self.embed_text(query)

        # Build filter
        filters = []
        if document_ids:
            filters.append(
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids)
                )
            )

        query_filter = Filter(must=filters) if filters else None

        # Search
        search_results = self.client.search(
            collection_name=self.COLLECTION_NAME,
            query_vector=query_embedding,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter
        )

        # Format results
        results = []
        for hit in search_results:
            results.append({
                "vector_id": hit.id,
                "document_id": hit.payload.get("document_id"),
                "text": hit.payload.get("text"),
                "page_number": hit.payload.get("page_number"),
                "chunk_index": hit.payload.get("chunk_index"),
                "similarity_score": hit.score,
                "metadata": hit.payload.get("metadata", {})
            })

        return results

    def delete_document(self, document_id: int):
        """
        Delete all chunks for a document

        Args:
            document_id: Document ID to delete
        """
        self.client.delete(
            collection_name=self.COLLECTION_NAME,
            points_selector=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )
        logger.info(f"Deleted all chunks for document {document_id}")

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the vector collection

        Returns:
            Collection statistics
        """
        collection_info = self.client.get_collection(self.COLLECTION_NAME)
        return {
            "total_vectors": collection_info.points_count,
            "vector_size": collection_info.config.params.vectors.size,
            "distance_metric": collection_info.config.params.vectors.distance.value
        }


# Singleton instance
_vector_store_instance: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """
    Get or create VectorStore singleton instance

    Returns:
        VectorStore instance
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        _vector_store_instance = VectorStore()
    return _vector_store_instance
