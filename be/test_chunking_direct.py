"""
Test: Directly chunk the PDF text with detailed logging
"""
import re
import time
from AI.rag_engine import RAGEngine

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def chunk_with_logging(text, metadata):
    """Chunk text with detailed per-iteration logging"""
    chunks = []
    current_page = 1

    # Split by page markers
    page_pattern = r'\[PAGE (\d+)\]'
    page_splits = re.split(page_pattern, text)

    print(f"Total page splits: {len(page_splits)}")

    for i, part in enumerate(page_splits):
        if i % 2 == 1:  # Page number
            current_page = int(part)
            print(f"\n--- PAGE {current_page} ---")
        else:  # Text content
            if not part.strip():
                continue

            current_text = part
            print(f"Processing {len(current_text)} chars")

            start = 0
            chunk_index = len(chunks)
            iteration = 0
            max_iter = 100  # Safety limit

            while start < len(current_text):
                iteration += 1
                if iteration > max_iter:
                    print(f"[ABORT] Too many iterations on page {current_page}")
                    return chunks

                end = start + CHUNK_SIZE

                # Sentence boundary detection
                if end < len(current_text):
                    sentence_end = max(
                        current_text.rfind('. ', start, end),
                        current_text.rfind('.\n', start, end),
                        current_text.rfind('! ', start, end),
                        current_text.rfind('? ', start, end)
                    )
                    if sentence_end > start:
                        end = sentence_end + 1

                chunk_text = current_text[start:end].strip()

                if chunk_text:
                    chunks.append({
                        "text": chunk_text,
                        "chunk_index": chunk_index,
                        "page_number": current_page,
                    })
                    chunk_index += 1

                # Calculate new start
                old_start = start
                start = end - CHUNK_OVERLAP if end < len(current_text) else end

                # Progress every 5 chunks or on last chunk
                if chunk_index % 5 == 0 or start >= len(current_text):
                    print(f"  Chunk {chunk_index}: start {old_start}->{start}, end={end}, len={len(current_text)}")

                # Safety check
                if start <= old_start and end < len(current_text):
                    print(f"[ERROR] Infinite loop detected!")
                    print(f"  start: {old_start} -> {start}")
                    print(f"  end: {end}")
                    print(f"  current_text length: {len(current_text)}")
                    print(f"  end < len: {end < len(current_text)}")
                    print(f"  Calculation: {end} - {CHUNK_OVERLAP} = {end - CHUNK_OVERLAP}")
                    return chunks

    return chunks

def main():
    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print("=" * 60)
    print("DIRECT CHUNKING TEST")
    print("=" * 60)

    # Extract PDF
    rag = RAGEngine()
    print("\nExtracting PDF...")
    text, metadata = rag._extract_pdf(file_path)
    print(f"Extracted: {len(text)} chars, {metadata.get('pages', 0)} pages")

    # Chunk with logging
    print("\nChunking text...")
    start = time.time()
    chunks = chunk_with_logging(text, metadata)
    elapsed = time.time() - start

    print(f"\n" + "=" * 60)
    print(f"Completed in {elapsed:.2f}s")
    print(f"Created {len(chunks)} chunks")
    print("=" * 60)

if __name__ == "__main__":
    main()
