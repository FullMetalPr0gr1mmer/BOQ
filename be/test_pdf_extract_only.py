"""
Test: Just extract PDF and show what we get
"""
import time
from AI.rag_engine import RAGEngine

def main():
    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print("=" * 60)
    print("PDF EXTRACTION TEST")
    print("=" * 60)

    rag = RAGEngine()

    print("\nExtracting PDF...", end=" ")
    start = time.time()
    text, metadata = rag._extract_pdf(file_path)
    elapsed = time.time() - start

    print(f"[{elapsed:.2f}s]")
    print(f"Text length: {len(text)} chars")
    print(f"Pages: {metadata.get('pages', 0)}")

    # Show structure
    print(f"\nFirst 2000 characters:")
    print("=" * 60)
    print(text[:2000])
    print("=" * 60)

    # Check for page markers
    import re
    page_pattern = r'\[PAGE (\d+)\]'
    page_markers = re.findall(page_pattern, text)
    print(f"\nPage markers found: {len(page_markers)}")
    if page_markers:
        print(f"  Pages: {page_markers}")

    # Try the split
    print(f"\nSplitting by page pattern...")
    start = time.time()
    page_splits = re.split(page_pattern, text)
    elapsed = time.time() - start
    print(f"  Split time: {elapsed:.2f}s")
    print(f"  Number of parts: {len(page_splits)}")

    for i in range(min(5, len(page_splits))):
        part = page_splits[i]
        is_page_num = i % 2 == 1
        print(f"  Part {i}: {len(part)} chars, is_page_num={is_page_num}")
        if not is_page_num and len(part) > 0:
            print(f"    First 200 chars: {repr(part[:200])}")

if __name__ == "__main__":
    main()
