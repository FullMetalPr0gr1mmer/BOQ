"""
Fix Qdrant collection dimension mismatch

This script recreates the boq_documents collection with 768 dimensions
to match the nomic-embed-text model.
"""
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_collection_dimensions():
    """Recreate boq_documents collection with correct dimensions"""

    client = QdrantClient(host="localhost", port=6333)
    collection_name = "boq_documents"

    try:
        # Get current collection info
        collection_info = client.get_collection(collection_name)
        current_size = collection_info.config.params.vectors.size

        logger.info(f"Current collection '{collection_name}' has {current_size} dimensions")

        if current_size == 768:
            logger.info("Collection already has correct dimensions (768). No action needed.")
            return

        logger.info(f"Collection has wrong dimensions ({current_size}). Need to recreate with 768 dimensions.")

        # Ask for confirmation
        print("\n" + "=" * 80)
        print("WARNING: This will DELETE the existing collection and all its data!")
        print("=" * 80)
        print(f"Current collection: {collection_name}")
        print(f"Current dimensions: {current_size}")
        print(f"Target dimensions: 768")
        print("\nAll existing document embeddings will be lost and need to be re-uploaded.")
        print("=" * 80)

        response = input("\nDo you want to proceed? (yes/no): ").strip().lower()

        if response != 'yes':
            logger.info("Operation cancelled by user.")
            return

        # Delete old collection
        logger.info(f"Deleting collection '{collection_name}'...")
        client.delete_collection(collection_name)
        logger.info("Collection deleted successfully")

        # Create new collection with 768 dimensions
        logger.info(f"Creating new collection '{collection_name}' with 768 dimensions...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=768,
                distance=Distance.COSINE
            )
        )
        logger.info("Collection created successfully")

        # Verify
        new_collection_info = client.get_collection(collection_name)
        new_size = new_collection_info.config.params.vectors.size
        logger.info(f"Verification: New collection has {new_size} dimensions")

        print("\n" + "=" * 80)
        print("SUCCESS: Collection recreated with 768 dimensions")
        print("=" * 80)
        print("Next steps:")
        print("1. Re-upload all your documents through the UI")
        print("2. Documents will be embedded with nomic-embed-text (768-dim)")
        print("=" * 80)

    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_collection_dimensions()
