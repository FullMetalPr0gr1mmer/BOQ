"""
Test: Use the actual RAG engine's _chunk_text method
"""
import time
from AI.rag_engine import RAGEngine

def main():
    file_path = "uploads/documents/20251023_135930_LEGO-Style_Prompting_Guide_v1_2025-05-22.pdf"

    print("=" * 60)
    print("ACTUAL RAG ENGINE CHUNKING TEST")
    print("=" * 60)

    # Create RAG engine
    print("\nInitializing RAG engine...")
    start = time.time()
    rag = RAGEngine()
    print(f"  Initialized in {time.time()-start:.2f}s")

    # Extract PDF
    print("\nExtracting PDF...")
    start = time.time()
    text, metadata = rag._extract_pdf(file_path)
    print(f"  Extracted {len(text)} chars in {time.time()-start:.2f}s")

    # Chunk text
    print("\nChunking text...")
    start = time.time()
    chunks = rag._chunk_text(text, metadata)
    elapsed = time.time() - start

    print(f"\n" + "=" * 60)
    print(f"SUCCESS! Chunking completed in {elapsed:.2f}s")
    print(f"Created {len(chunks)} chunks")
    print("=" * 60)

    # Show first few chunks
    for i, chunk in enumerate(chunks[:3]):
        print(f"\nChunk {i}:")
        print(f"  Page: {chunk['page_number']}")
        print(f"  Length: {len(chunk['text'])} chars")
        print(f"  Preview: {chunk['text'][:100]}...")

if __name__ == "__main__":
    main()
