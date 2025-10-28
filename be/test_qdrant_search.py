"""
Test: Direct Qdrant search to see if vectors are actually there
"""
from AI.vectorstore import get_vector_store

def main():
    print("=" * 60)
    print("QDRANT SEARCH TEST")
    print("=" * 60)

    vector_store = get_vector_store()

    # Test search with different queries
    queries = [
        "What is this document about?",
        "LEGO prompting",
        "prompt engineering",
        "document summary",
    ]

    for query in queries:
        print(f"\nQuery: '{query}'")
        print("-" * 60)

        # Search with low threshold to see ALL results
        results = vector_store.search(
            query=query,
            limit=5,
            score_threshold=0.0,  # NO threshold
            document_ids=[1023]  # The latest uploaded document
        )

        if results:
            print(f"  Found {len(results)} results:")
            for i, result in enumerate(results, 1):
                print(f"  {i}. Score: {result['similarity_score']:.4f}")
                print(f"     Doc ID: {result['document_id']}, Page: {result['page_number']}")
                print(f"     Text: {result['text'][:100]}...")
        else:
            print("  NO RESULTS FOUND!")

    print("\n" + "=" * 60)

    # Also test without document_id filter
    print("\n\nSearching WITHOUT document_id filter:")
    print("-" * 60)
    query = "What is this document about?"
    results = vector_store.search(
        query=query,
        limit=5,
        score_threshold=0.0
    )

    if results:
        print(f"Found {len(results)} results across all documents:")
        for i, result in enumerate(results, 1):
            print(f"{i}. Score: {result['similarity_score']:.4f}, Doc ID: {result['document_id']}")
            print(f"   Text: {result['text'][:80]}...")
    else:
        print("NO RESULTS FOUND!")

if __name__ == "__main__":
    main()
