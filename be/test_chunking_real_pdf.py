"""
Test: Reproduce chunking with REAL PDF
"""
import re
import time
from AI.rag_engine import RAGEngine

def main():
    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print("=" * 60)
    print("Testing with REAL PDF")
    print("=" * 60)

    # Extract PDF text (same as the actual code)
    print("\n1. Extracting PDF text...", end=" ")
    start = time.time()
    rag = RAGEngine()
    text, metadata = rag._extract_pdf(file_path)
    print(f"[{time.time()-start:.2f}s]")
    print(f"   Text length: {len(text)} chars")
    print(f"   Pages: {metadata.get('pages', 0)}")

    # Show first 500 chars
    print(f"\n   First 500 chars:")
    print(f"   {repr(text[:500])}")

    # Chunk text with timeout
    print("\n2. Chunking text (with 30s timeout)...")
    start = time.time()

    # Add safety check
    import signal

    def timeout_handler(signum, frame):
        raise TimeoutError("Chunking took too long!")

    # Set 30s timeout
    try:
        # Windows doesn't support signal.alarm, so we'll use a different approach
        import threading

        result = []
        error = []

        def chunk_with_logging():
            try:
                print("   Starting chunking...")
                chunks = rag._chunk_text(text, metadata)
                result.append(chunks)
                print(f"   Chunking completed!")
            except Exception as e:
                error.append(e)

        thread = threading.Thread(target=chunk_with_logging)
        thread.daemon = True
        thread.start()

        # Wait up to 30 seconds
        thread.join(timeout=30)

        if thread.is_alive():
            print(f"\n[TIMEOUT] Chunking hung after 30s!")
            print(f"This confirms the hang is in _chunk_text()")

            # Let's check if it's stuck in regex
            print(f"\nChecking for problematic patterns in text...")
            page_pattern = r'\[PAGE (\d+)\]'
            print(f"   Splitting by page pattern...", end=" ")
            split_start = time.time()
            page_splits = re.split(page_pattern, text)
            print(f"[{time.time()-split_start:.2f}s]")
            print(f"   Number of splits: {len(page_splits)}")

            # Check each split
            for i, part in enumerate(page_splits[:10]):  # First 10 only
                print(f"   Split {i}: {len(part)} chars, is_num={i%2==1}")
                if i % 2 == 0 and len(part) > 0:
                    print(f"      First 100 chars: {repr(part[:100])}")

            return False
        else:
            elapsed = time.time() - start
            print(f"[{elapsed:.2f}s]")

            if error:
                print(f"[ERROR] {error[0]}")
                import traceback
                traceback.print_exc()
                return False

            if result:
                chunks = result[0]
                print(f"   Chunks created: {len(chunks)}")
                print("\n" + "=" * 60)
                print("[SUCCESS] Chunking works fine!")
                print("=" * 60)
                return True

    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    main()
