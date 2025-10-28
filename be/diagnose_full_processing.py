"""
Test 7: Full Document Processing Test
Process a real document end-to-end
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
    print("TEST 7: FULL DOCUMENT PROCESSING TEST")
    print("=" * 60)

    # Get DB connection
    db_url = os.getenv('DATABASE_URL')
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    # Document details
    document_id = 1017
    file_path = "uploads/documents/20251026_081008_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print(f"\nDocument ID: {document_id}")
    print(f"File Path: {file_path}")
    print("=" * 60)

    # Check document exists in DB
    print("\nChecking document in database...", end=" ")
    try:
        doc = db.execute(text(f"SELECT id, filename, processing_status FROM documents WHERE id = {document_id}")).fetchone()
        if doc:
            print(f"[PASS]")
            print(f"  Filename: {doc[1]}")
            print(f"  Current status: {doc[2]}")
        else:
            print(f"[FAIL] - Document not found")
            return False
    except Exception as e:
        print(f"[FAIL]")
        print(f"  Error: {e}")
        return False

    # Initialize RAG engine
    print("Initializing RAG engine...", end=" ")
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
        import traceback
        traceback.print_exc()
        return False

    # Process document
    print("Processing document (this may take 1-2 minutes)...", end=" ")
    print()  # New line for progress
    start = time.time()
    try:
        result = rag_engine.process_document(
            file_path=file_path,
            document_id=document_id,
            db=db,
            extract_tags=True  # Test with full metadata extraction
        )
        elapsed = time.time() - start
        print(f"[PASS] ({elapsed:.2f}s)")
        print(f"  Chunks created: {result.get('chunks_created', 0)}")
        print(f"  Tags: {result.get('tags', [])}")
        print(f"  Summary: {result.get('summary', 'None')[:100]}...")
    except Exception as e:
        elapsed = time.time() - start
        print(f"[FAIL] ({elapsed:.2f}s)")
        print(f"  Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify chunks in database
    print("Verifying chunks in database...", end=" ")
    try:
        chunk_count = db.execute(text(f"SELECT COUNT(*) FROM document_chunks WHERE document_id = {document_id}")).fetchone()[0]
        doc_status = db.execute(text(f"SELECT processing_status FROM documents WHERE id = {document_id}")).fetchone()[0]
        print(f"[PASS]")
        print(f"  Chunks: {chunk_count}")
        print(f"  Status: {doc_status}")

        if chunk_count > 0 and doc_status == "completed":
            print("\n" + "=" * 60)
            print("[SUCCESS] DOCUMENT PROCESSING WORKING")
            print("=" * 60)
            return True
        else:
            print(f"\n[WARNING] Processing completed but unexpected state")
            print(f"  Expected: chunks > 0 and status = 'completed'")
            print(f"  Got: chunks = {chunk_count}, status = '{doc_status}'")
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
