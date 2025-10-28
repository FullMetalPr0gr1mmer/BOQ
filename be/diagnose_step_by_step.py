"""
Test: Step-by-Step Processing with Timing
Identify exactly where processing hangs
"""
import sys
import time
from pathlib import Path

def main():
    print("=" * 60)
    print("STEP-BY-STEP PROCESSING TEST")
    print("=" * 60)

    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    # Step 1: Import RAG
    print("\nStep 1: Import RAG engine...", end=" ")
    start = time.time()
    from AI.rag_engine import RAGEngine
    print(f"[{time.time()-start:.2f}s]")

    # Step 2: Create instance
    print("Step 2: Create RAG instance...", end=" ")
    start = time.time()
    rag = RAGEngine()
    print(f"[{time.time()-start:.2f}s]")

    # Step 3: Extract PDF
    print("Step 3: Extract PDF text...", end=" ")
    start = time.time()
    text, metadata = rag._extract_pdf(file_path)
    print(f"[{time.time()-start:.2f}s]")
    print(f"  Text length: {len(text)}")
    print(f"  Pages: {metadata.get('pages', 0)}")

    # Step 4: Chunk text
    print("Step 4: Chunk text...", end=" ")
    start = time.time()
    chunks = rag._chunk_text(text, metadata)
    print(f"[{time.time()-start:.2f}s]")
    print(f"  Chunks: {len(chunks)}")

    # Step 5: Test embedding ONE chunk
    print("Step 5: Embed single chunk...", end=" ")
    start = time.time()
    single_embedding = rag.vector_store.embed_text(chunks[0]['text'])
    print(f"[{time.time()-start:.2f}s]")
    print(f"  Embedding dims: {len(single_embedding)}")

    # Step 6: Test embedding small batch
    print("Step 6: Embed 10 chunks...", end=" ")
    start = time.time()
    batch_texts = [c['text'] for c in chunks[:10]]
    batch_embeddings = rag.vector_store.embed_batch(batch_texts)
    print(f"[{time.time()-start:.2f}s]")

    # Step 7: Embed ALL chunks (this might hang)
    print(f"Step 7: Embed ALL {len(chunks)} chunks...")
    print("  (this is where it might hang)...", end=" ")
    sys.stdout.flush()
    start = time.time()
    try:
        all_embeddings = rag.vector_store.embed_batch([c['text'] for c in chunks])
        elapsed = time.time()-start
        print(f"[{elapsed:.2f}s]")
        print(f"  Speed: {len(chunks)/elapsed:.1f} chunks/sec")
    except KeyboardInterrupt:
        print("\n[INTERRUPTED]")
        return False
    except Exception as e:
        print(f"\n[FAILED] {e}")
        return False

    print("\n" + "=" * 60)
    print("[SUCCESS] ALL STEPS COMPLETED")
    print("If you got here, the issue is NOT in embedding")
    print("The issue must be in Qdrant upsert or database commits")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
