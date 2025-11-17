"""
Schema Knowledge Embedding Script - Task 2

This script loads all chunks from Task 1 and embeds them into Qdrant.

Run this script whenever you:
1. First time setup
2. Update your SQLAlchemy or Pydantic models
3. Add new business rules

Usage:
    python embed_schema_knowledge.py

Options:
    --clear: Clear existing collection before embedding
    --input: Path to chunks JSON file (default: knowledge_base/all_chunks_combined.json)

Author: Senior AI Architect
Created: 2025-11-06
"""
import json
import sys
import argparse
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AI.text2sql_vectorstore import get_text2sql_vector_store

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def load_chunks(chunks_path: str) -> list:
    """
    Load chunks from JSON file.

    Args:
        chunks_path: Path to chunks JSON file

    Returns:
        List of chunk dictionaries
    """
    logger.info(f"Loading chunks from {chunks_path}...")

    try:
        with open(chunks_path, 'r', encoding='utf-8') as f:
            chunks = json.load(f)

        logger.info(f"Loaded {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Error loading chunks: {e}")
        raise


def validate_chunks(chunks: list) -> bool:
    """
    Validate that chunks have the expected structure.

    Args:
        chunks: List of chunks

    Returns:
        True if valid, False otherwise
    """
    logger.info("Validating chunk structure...")

    if not chunks:
        logger.error("No chunks to validate")
        return False

    required_fields = ['content', 'metadata']
    errors = []

    for i, chunk in enumerate(chunks):
        # Check required fields
        for field in required_fields:
            if field not in chunk:
                errors.append(f"Chunk {i}: Missing required field '{field}'")

        # Check metadata has 'type'
        if 'metadata' in chunk and 'type' not in chunk['metadata']:
            errors.append(f"Chunk {i}: Missing 'type' in metadata")

    if errors:
        logger.error(f"Validation failed with {len(errors)} errors:")
        for error in errors[:10]:  # Show first 10 errors
            logger.error(f"  - {error}")
        return False

    logger.info("Validation passed!")
    return True


def analyze_chunks(chunks: list):
    """
    Print analysis of chunk distribution.

    Args:
        chunks: List of chunks
    """
    logger.info("\n" + "="*80)
    logger.info("CHUNK ANALYSIS")
    logger.info("="*80)

    # Count by type
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk['metadata'].get('type', 'unknown')
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    logger.info(f"\nTotal chunks: {len(chunks)}")
    logger.info("\nChunk type distribution:")
    for chunk_type, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        logger.info(f"  {chunk_type}: {count}")

    # Count tables covered
    tables = set()
    for chunk in chunks:
        if 'table_name' in chunk['metadata']:
            tables.add(chunk['metadata']['table_name'])

    logger.info(f"\nTables covered: {len(tables)}")
    if tables:
        logger.info(f"Tables: {', '.join(sorted(tables))}")

    # Count relationships
    relationships = [c for c in chunks if c['metadata'].get('type') == 'relationship']
    logger.info(f"\nRelationship chunks: {len(relationships)} (CRITICAL for preventing wrong joins!)")

    # Count business rules
    business_rules = [c for c in chunks if 'business' in c['metadata'].get('type', '').lower()]
    logger.info(f"Business rule chunks: {len(business_rules)}")

    logger.info("="*80)


def embed_chunks(
    chunks: list,
    vector_store,
    clear_existing: bool = False
) -> list:
    """
    Embed chunks into Qdrant.

    Args:
        chunks: List of chunk dictionaries
        vector_store: Text2SQLVectorStore instance
        clear_existing: Whether to clear existing collection first

    Returns:
        List of vector IDs
    """
    if clear_existing:
        logger.info("Clearing existing collection...")
        vector_store.clear_collection()
        logger.info("Collection cleared")

    logger.info("\n" + "="*80)
    logger.info("EMBEDDING CHUNKS INTO QDRANT")
    logger.info("="*80)

    # Add chunks to vector store
    vector_ids = vector_store.add_schema_chunks(chunks)

    logger.info(f"\nSuccessfully embedded {len(vector_ids)} chunks")

    return vector_ids


def verify_embeddings(vector_store):
    """
    Verify that embeddings were created successfully.

    Args:
        vector_store: Text2SQLVectorStore instance
    """
    logger.info("\n" + "="*80)
    logger.info("VERIFYING EMBEDDINGS")
    logger.info("="*80)

    stats = vector_store.get_collection_stats()

    logger.info(f"\nCollection: {vector_store.COLLECTION_NAME}")
    logger.info(f"Total vectors: {stats.get('total_vectors', 0)}")
    logger.info(f"Vector size: {stats.get('vector_size', 0)}")
    logger.info(f"Distance metric: {stats.get('distance_metric', 'unknown')}")

    if 'chunk_type_distribution' in stats:
        logger.info("\nChunk type distribution in Qdrant:")
        for chunk_type, count in sorted(stats['chunk_type_distribution'].items()):
            logger.info(f"  {chunk_type}: {count}")

    logger.info("="*80)


def test_search(vector_store):
    """
    Test search functionality with sample queries.

    Args:
        vector_store: Text2SQLVectorStore instance
    """
    logger.info("\n" + "="*80)
    logger.info("TESTING SEARCH FUNCTIONALITY")
    logger.info("="*80)

    test_queries = [
        "Show me all users",
        "How do I join users and audit logs?",
        "What is an active project?",
    ]

    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        results = vector_store.search(query, limit=3)

        logger.info(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            logger.info(f"  {i}. [{result['type']}] Score: {result['similarity_score']:.3f}")
            logger.info(f"     {result['content'][:100]}...")

    logger.info("="*80)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Embed Text-to-SQL schema knowledge into Qdrant"
    )
    parser.add_argument(
        '--input',
        default='AI/knowledge_base/all_chunks_combined.json',
        help='Path to chunks JSON file'
    )
    parser.add_argument(
        '--clear',
        action='store_true',
        help='Clear existing collection before embedding'
    )
    parser.add_argument(
        '--skip-test',
        action='store_true',
        help='Skip search functionality test'
    )

    args = parser.parse_args()

    logger.info("="*80)
    logger.info("TEXT-TO-SQL SCHEMA KNOWLEDGE EMBEDDING - TASK 2")
    logger.info("="*80)

    # Resolve input path
    input_path = Path(__file__).parent.parent / args.input

    # Load chunks
    chunks = load_chunks(str(input_path))

    # Validate chunks
    if not validate_chunks(chunks):
        logger.error("Validation failed. Aborting.")
        sys.exit(1)

    # Analyze chunks
    analyze_chunks(chunks)

    # Get vector store instance
    logger.info("\nInitializing vector store...")
    vector_store = get_text2sql_vector_store()

    # Embed chunks
    vector_ids = embed_chunks(
        chunks=chunks,
        vector_store=vector_store,
        clear_existing=args.clear
    )

    # Verify embeddings
    verify_embeddings(vector_store)

    # Test search (unless skipped)
    if not args.skip_test:
        test_search(vector_store)

    # Final summary
    logger.info("\n" + "="*80)
    logger.info("EMBEDDING COMPLETE!")
    logger.info("="*80)
    logger.info(f"Successfully embedded {len(vector_ids)} chunks")
    logger.info(f"Collection: {vector_store.COLLECTION_NAME}")
    logger.info("\nYour Text-to-SQL knowledge base is ready!")
    logger.info("You can now proceed to Task 3: Build the Query Pipeline")
    logger.info("="*80)


if __name__ == "__main__":
    main()
