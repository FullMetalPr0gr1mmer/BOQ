"""
Test 4: Qdrant Connection Test
Verify Qdrant database works
"""
import sys
import time
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

def main():
    print("=" * 60)
    print("TEST 4: QDRANT CONNECTION TEST")
    print("=" * 60)

    host = "localhost"
    port = 6333
    test_collection = "test_collection_diagnose"

    # Test connection
    print(f"\nConnecting to Qdrant at {host}:{port}...", end=" ")
    start = time.time()
    try:
        client = QdrantClient(host=host, port=port)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test health check
    print("Checking Qdrant health...", end=" ")
    start = time.time()
    try:
        # List collections as health check
        collections = client.get_collections()
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Existing collections: {len(collections.collections)}")
        for coll in collections.collections:
            print(f"    - {coll.name}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test create collection
    print(f"Creating test collection '{test_collection}'...", end=" ")
    start = time.time()
    try:
        # Delete if exists
        try:
            client.delete_collection(test_collection)
        except:
            pass

        client.create_collection(
            collection_name=test_collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test insert vectors
    print("Inserting test vectors...", end=" ")
    start = time.time()
    try:
        points = [
            PointStruct(
                id=i,
                vector=[0.1] * 384,  # Dummy vector
                payload={"text": f"Test chunk {i}", "doc_id": 999}
            )
            for i in range(10)
        ]
        client.upsert(collection_name=test_collection, points=points)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Inserted: 10 vectors")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test search
    print("Searching vectors...", end=" ")
    start = time.time()
    try:
        results = client.search(
            collection_name=test_collection,
            query_vector=[0.1] * 384,
            limit=3
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Found: {len(results)} results")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Cleanup
    print("Cleaning up test collection...", end=" ")
    start = time.time()
    try:
        client.delete_collection(test_collection)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")

    print("\n" + "=" * 60)
    print("[SUCCESS] QDRANT CONNECTION WORKING")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
