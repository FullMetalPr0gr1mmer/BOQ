"""
Test: Reproduce the chunking hang
"""
import re
import time

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

def chunk_text(text):
    """Reproduce the exact _chunk_text logic"""
    chunks = []
    current_page = 1

    # Split by page markers if present
    page_pattern = r'\[PAGE (\d+)\]'
    page_splits = re.split(page_pattern, text)

    print(f"Page splits: {len(page_splits)} parts")

    current_text = ""
    current_page = 1

    iteration = 0
    max_iterations = 1000  # Safety limit

    for i, part in enumerate(page_splits):
        print(f"  Processing part {i}: {len(part)} chars, is_page_num={i%2==1}")

        if i % 2 == 1:  # Page number
            current_page = int(part)
            print(f"    Page number: {current_page}")
        else:  # Text content
            if not part.strip():
                print(f"    Empty part, skipping")
                continue

            # Add to current text
            current_text = part
            print(f"    Processing text: {len(current_text)} chars")

            # Chunk this page's text
            start = 0
            chunk_index = len(chunks)

            while start < len(current_text):
                iteration += 1
                if iteration > max_iterations:
                    print(f"[ABORT] Hit max iterations ({max_iterations})")
                    return chunks

                end = start + CHUNK_SIZE
                print(f"      Chunk {chunk_index}: start={start}, end={end}, text_len={len(current_text)}")

                # Try to break at sentence boundary
                if end < len(current_text):
                    # Look for sentence end
                    sentence_end = max(
                        current_text.rfind('. ', start, end),
                        current_text.rfind('.\n', start, end),
                        current_text.rfind('! ', start, end),
                        current_text.rfind('? ', start, end)
                    )
                    print(f"        Sentence boundary search: {sentence_end}")
                    if sentence_end > start:
                        end = sentence_end + 1
                        print(f"        Adjusted end to: {end}")

                chunk_text = current_text[start:end].strip()

                if chunk_text:
                    chunks.append({
                        "text": chunk_text[:50] + "...",  # Truncate for display
                        "chunk_index": chunk_index,
                        "page_number": current_page,
                    })
                    chunk_index += 1
                    print(f"        Created chunk {chunk_index-1}")

                # Move to next chunk with overlap
                old_start = start
                start = end - CHUNK_OVERLAP if end < len(current_text) else end
                print(f"        Moving start: {old_start} -> {start} (delta={start-old_start})")

                if start <= old_start:
                    print(f"[ERROR] Start not advancing! old={old_start}, new={start}")
                    print(f"  end={end}, len={len(current_text)}, end<len={end < len(current_text)}")
                    return chunks

    return chunks

def main():
    # Create a simple test text
    test_text = "This is sentence one. This is sentence two. " * 100  # ~4400 chars

    print("=" * 60)
    print(f"Testing with {len(test_text)} characters")
    print("=" * 60)

    start = time.time()
    chunks = chunk_text(test_text)
    elapsed = time.time() - start

    print("\n" + "=" * 60)
    print(f"Completed in {elapsed:.2f}s")
    print(f"Created {len(chunks)} chunks")
    print("=" * 60)

if __name__ == "__main__":
    main()
