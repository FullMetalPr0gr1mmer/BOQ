"""
Embed NDPD schema knowledge chunks into Qdrant
"""
import json
import os
from pathlib import Path

# Bypass proxy
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

from AI.text2sql_vectorstore import get_text2sql_vector_store


def main():
    """Load and embed NDPD schema chunks"""
    print("="*80)
    print("EMBEDDING NDPD SCHEMA CHUNKS INTO QDRANT")
    print("="*80)

    # Load NDPD chunks
    chunks_path = Path(__file__).parent / "knowledge_base" / "ndpd_chunks.json"

    if not chunks_path.exists():
        print(f"[ERROR] NDPD chunks file not found: {chunks_path}")
        print("[INFO] Run generate_ndpd_schema_chunks.py first")
        return

    with open(chunks_path, 'r', encoding='utf-8') as f:
        ndpd_chunks = json.load(f)

    print(f"\n[LOADED] {len(ndpd_chunks)} NDPD chunks from file")

    # Get vector store
    print("[CONNECTING] to Qdrant...")
    vector_store = get_text2sql_vector_store()

    # Check current collection stats
    print("\n[BEFORE] Collection stats:")
    stats = vector_store.get_collection_stats()
    print(f"  Total vectors: {stats.get('total_vectors', 'unknown')}")
    print(f"  Chunk types: {stats.get('chunk_type_distribution', {})}")

    # Add NDPD chunks
    print(f"\n[EMBEDDING] {len(ndpd_chunks)} NDPD chunks...")
    vector_ids = vector_store.add_schema_chunks(ndpd_chunks)

    print(f"\n[SUCCESS] Embedded {len(vector_ids)} NDPD chunks!")

    # Check updated stats
    print("\n[AFTER] Collection stats:")
    stats = vector_store.get_collection_stats()
    print(f"  Total vectors: {stats.get('total_vectors', 'unknown')}")
    print(f"  Chunk types: {stats.get('chunk_type_distribution', {})}")

    print("\n[COMPLETE] NDPD schema is now queryable via Text-to-SQL!")
    print("="*80)


if __name__ == "__main__":
    main()
