"""
Test 7B: Document Processing WITHOUT Metadata
Test if processing works without Ollama metadata extraction
"""
import sys
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("=" * 60)
    print("TEST 7B: DOCUMENT PROCESSING (NO METADATA)")
    print("=" * 60)

    # Get DB connection
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Use a different document to avoid conflicts
    document_id = 21  # Second upload
    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print(f"\nDocument ID: {document_id}")
    print(f"File Path: {file_path}")
    print("Testing WITHOUT Ollama metadata extraction")
    print("=" * 60)

    # Initialize RAG engine
    print("\nInitializing RAG engine...", end=" ")
    start = time.time()
    try:
        from AI.rag_engine import get_rag_engine
        rag_engine = get_rag_engine()
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        return False

    # Process document WITHOUT metadata extraction
    print("Processing document (WITHOUT tags/summary)...")
    print("This should take <30 seconds...")
    start = time.time()
    try:
        result = rag_engine.process_document(
            file_path=file_path,
            document_id=document_id,
            db=db,
            extract_tags=False  # SKIP metadata extraction
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Chunks created: {result.get('chunks_created', 0)}")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify
    print("Verifying chunks...", end=" ")
    try:
        chunk_count = db.execute(text(f"SELECT COUNT(*) FROM document_chunks WHERE document_id = {document_id}")).fetchone()[0]
        doc_status = db.execute(text(f"SELECT processing_status FROM documents WHERE id = {document_id}")).fetchone()[0]
        print(f"[PASS]")
        print(f"  Chunks: {chunk_count}")
        print(f"  Status: {doc_status}")

        if chunk_count > 0:
            print("\n" + "=" * 60)
            print("[SUCCESS] PROCESSING WORKS WITHOUT METADATA")
            print("[CONCLUSION] Ollama metadata extraction is the bottleneck")
            print("=" * 60)
            return True
        else:
            print("\n[FAILED] No chunks created")
            return False

    except Exception as e:
        print(f"[FAIL]")
        print(f"  Error: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
