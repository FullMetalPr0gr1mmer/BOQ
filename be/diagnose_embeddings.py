"""
Test 3: Embedding Model Test
Verify SentenceTransformer works and generates embeddings
"""
import sys
import time
import os

# Force offline mode
os.environ['HF_HUB_OFFLINE'] = '1'
os.environ['TRANSFORMERS_OFFLINE'] = '1'

from sentence_transformers import SentenceTransformer

def main():
    print("=" * 60)
    print("TEST 3: EMBEDDING MODEL TEST")
    print("=" * 60)

    model_name = "all-MiniLM-L6-v2"

    # Test model loading
    print(f"\nLoading model: {model_name}...", end=" ")
    start = time.time()
    try:
        model = SentenceTransformer(model_name)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test single embedding
    print("Generating single embedding...", end=" ")
    test_text = "This is a test document about LEGO-style prompting."
    start = time.time()
    try:
        embedding = model.encode(test_text, normalize_embeddings=True)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Embedding dimensions: {len(embedding)}")
        print(f"  First 5 values: {embedding[:5]}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test batch embeddings
    print("Generating batch embeddings (10 texts)...", end=" ")
    test_texts = [f"Document chunk {i}" for i in range(10)]
    start = time.time()
    try:
        embeddings = model.encode(test_texts, normalize_embeddings=True)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Batch size: {len(embeddings)}")
        print(f"  Average time per embedding: {elapsed/len(embeddings):.3f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Test larger batch
    print("Generating large batch (50 texts)...", end=" ")
    test_texts = [f"This is chunk {i} of the document." for i in range(50)]
    start = time.time()
    try:
        embeddings = model.encode(test_texts, normalize_embeddings=True)
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Batch size: {len(embeddings)}")
        print(f"  Average time per embedding: {elapsed/len(embeddings):.3f}s")
        print(f"  Estimated time for 100 chunks: {(elapsed/len(embeddings))*100:.1f}s")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] EMBEDDING MODEL WORKING")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
