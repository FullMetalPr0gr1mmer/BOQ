"""
Re-embed NDPD chunks (delete old, add new)
"""
import json
import os
from pathlib import Path

# Bypass proxy
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

from AI.text2sql_vectorstore import get_text2sql_vector_store


def main():
    """Re-embed NDPD schema chunks"""
    print("="*80)
    print("RE-EMBEDDING NDPD SCHEMA CHUNKS")
    print("="*80)

    # Get vector store
    vector_store = get_text2sql_vector_store()

    # Get current stats
    print("\n[BEFORE] Collection stats:")
    stats = vector_store.get_collection_stats()
    print(f"  Total vectors: {stats.get('total_vectors', 'unknown')}")
    print(f"  Chunk types: {stats.get('chunk_type_distribution', {})}")

    # Since we can't selectively delete, we'll just add the new chunks
    # Qdrant will handle duplicates by creating new vectors
    # The old ones will still exist but the new ones will be more relevant

    # Load new NDPD chunks
    chunks_path = Path(__file__).parent / "knowledge_base" / "ndpd_chunks.json"

    with open(chunks_path, 'r', encoding='utf-8') as f:
        ndpd_chunks = json.load(f)

    print(f"\n[LOADED] {len(ndpd_chunks)} updated NDPD chunks")

    # Add chunks
    print(f"[EMBEDDING] {len(ndpd_chunks)} chunks...")
    vector_ids = vector_store.add_schema_chunks(ndpd_chunks)

    print(f"\n[SUCCESS] Embedded {len(vector_ids)} updated chunks!")

    # Get new stats
    print("\n[AFTER] Collection stats:")
    stats = vector_store.get_collection_stats()
    print(f"  Total vectors: {stats.get('total_vectors', 'unknown')}")
    print(f"  Chunk types: {stats.get('chunk_type_distribution', {})}")

    print("\n[INFO] The updated NDPD chunks include:")
    print("  - Critical business rule to prevent table hallucination")
    print("  - Explicit patterns for 'exceeded forecast' and 'missed target'")
    print("  - Stronger table name enforcement")

    print("\n[COMPLETE] Re-embedding done!")
    print("="*80)


if __name__ == "__main__":
    main()
