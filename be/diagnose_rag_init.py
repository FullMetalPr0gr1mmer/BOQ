"""
Test 6: RAG Engine Initialization Test
Verify RAG engine can be initialized without hanging
"""
import sys
import time

def main():
    print("=" * 60)
    print("TEST 6: RAG ENGINE INITIALIZATION TEST")
    print("=" * 60)

    # Test get_rag_engine import
    print("\nImporting get_rag_engine...", end=" ")
    start = time.time()
    try:
        from AI.rag_engine import get_rag_engine
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test RAG engine initialization
    print("Initializing RAG engine...", end=" ")
    start = time.time()
    try:
        rag_engine = get_rag_engine()
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Test that components are accessible
    print("Checking RAG engine components...", end=" ")
    start = time.time()
    try:
        assert hasattr(rag_engine, 'vector_store'), "Missing vector_store"
        assert hasattr(rag_engine, 'ollama_client'), "Missing ollama_client"
        assert rag_engine.vector_store is not None, "vector_store is None"
        assert rag_engine.ollama_client is not None, "ollama_client is None"
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  - vector_store: {type(rag_engine.vector_store).__name__}")
        print(f"  - ollama_client: {type(rag_engine.ollama_client).__name__}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] RAG ENGINE INITIALIZATION WORKING")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
