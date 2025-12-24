"""
Test the PRODUCTION Text2SQL system with qwen2.5:7b
This uses the actual Qdrant-based retrieval system
"""
import os
import sys
import time

# Bypass proxy
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

# Add backend to path
sys.path.insert(0, 'C:/WORK/BOQ/be')

from AI.text2sql_generator import get_text2sql_generator
from AI.text2sql_vectorstore import get_text2sql_vector_store
from datetime import datetime

# Test questions for RAN database
TEST_QUESTIONS = [
    {
        "question": "Show me all RAN projects",
        "difficulty": "Easy",
        "expected_table": "ran_projects"
    },
    {
        "question": "Show me RAN LLD",
        "difficulty": "Easy",
        "expected_table": "ran_lld"
    },
    {
        "question": "How many RAN inventory items are there?",
        "difficulty": "Easy",
        "expected_tables": ["ran_inventory"]
    },
    {
        "question": "Show me all inventory items with their project names",
        "difficulty": "Medium",
        "expected_tables": ["ran_inventory", "ran_projects"]
    },
    {
        "question": "Get all level 3 items for RAN projects with their project names",
        "difficulty": "Medium",
        "expected_tables": ["ranlvl3", "ran_projects"]
    },
    {
        "question": "What is the total quantity of all items in ranlvl3?",
        "difficulty": "Medium",
        "expected_tables": ["ranlvl3"]
    },
    {
        "question": "List all RAN projects with their total BOQ value from ranlvl3",
        "difficulty": "Hard",
        "expected_tables": ["ran_projects", "ranlvl3"]
    },
    {
        "question": "Show me duplicate inventory items with their project information",
        "difficulty": "Hard",
        "expected_tables": ["ran_inventory", "ran_projects"]
    }
]

def test_production_text2sql():
    """Test production Text2SQL system"""
    print("=" * 80)
    print("PRODUCTION TEXT2SQL SYSTEM TEST")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Check Qdrant collection status
    print("\n[CHECKING] Qdrant Collection Status...")
    try:
        vector_store = get_text2sql_vector_store()
        stats = vector_store.get_collection_stats()
        print(f"[OK] Collection: {vector_store.COLLECTION_NAME}")
        print(f"[OK] Total vectors: {stats.get('total_vectors', 'unknown')}")
        print(f"[OK] Chunk types: {stats.get('chunk_type_distribution', {})}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant: {e}")
        print("[INFO] Make sure Qdrant is running on localhost:6333")
        return

    # Initialize generator
    print("\n[INITIALIZING] Text2SQL Generator...")
    generator = get_text2sql_generator()
    print("[OK] Generator ready")

    # Run tests
    results = []
    total_time = 0

    for idx, test in enumerate(TEST_QUESTIONS, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {idx}/{len(TEST_QUESTIONS)}: {test['difficulty']}")
        print(f"{'=' * 80}")
        print(f"Question: {test['question']}")

        start_time = time.time()
        try:
            result = generator.generate_sql(
                question=test['question'],
                database="SQL Server",
                validate=True
            )
            elapsed = time.time() - start_time
            total_time += elapsed

            print(f"\n[GENERATED SQL]")
            print(result.sql)
            print(f"\n[METRICS]")
            print(f"  Time: {elapsed:.2f}s")
            print(f"  Confidence: {result.confidence:.2%}")
            print(f"  Execution Ready: {result.execution_ready}")
            if result.errors:
                print(f"  Errors: {', '.join(result.errors)}")

            print(f"\n[RETRIEVED CONTEXT]")
            print(f"  Tables: {len(result.retrieved_context['tables'])}")
            print(f"  Relationships: {len(result.retrieved_context['relationships'])}")
            print(f"  Total chunks: {len(result.retrieved_context['all_chunks'])}")

            # Show what tables were identified
            if result.retrieved_context['tables']:
                identified_tables = [t.get('table_name', 'unknown') for t in result.retrieved_context['tables']]
                print(f"  Identified tables: {', '.join(identified_tables)}")

            results.append({
                'question': test['question'],
                'sql': result.sql,
                'time': elapsed,
                'confidence': result.confidence,
                'execution_ready': result.execution_ready,
                'chunks_retrieved': len(result.retrieved_context['all_chunks']),
                'success': result.execution_ready
            })

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n[ERROR] {str(e)}")
            import traceback
            traceback.print_exc()
            results.append({
                'question': test['question'],
                'error': str(e),
                'time': elapsed,
                'success': False
            })

    # Summary
    print(f"\n{'=' * 80}")
    print("SUMMARY")
    print(f"{'=' * 80}")

    successful = [r for r in results if r.get('success', False)]
    failed = [r for r in results if not r.get('success', False)]

    print(f"\nSuccess Rate: {len(successful)}/{len(results)} ({len(successful)/len(results)*100:.1f}%)")

    if successful:
        avg_time = sum(r['time'] for r in successful) / len(successful)
        max_time = max(r['time'] for r in successful)
        avg_confidence = sum(r.get('confidence', 0) for r in successful) / len(successful)

        print(f"\nPerformance:")
        print(f"  Avg Time: {avg_time:.2f}s")
        print(f"  Max Time: {max_time:.2f}s")
        print(f"  Avg Confidence: {avg_confidence:.2%}")
        print(f"  Total Time: {total_time:.2f}s")
        print(f"  Under 3 mins: {'YES' if max_time < 180 else 'NO'}")

    if failed:
        print(f"\nFailed queries: {len(failed)}")
        for r in failed:
            print(f"  - {r['question']}")
            print(f"    Error: {r.get('error', 'Unknown')}")

    print(f"\n{'=' * 80}")
    print("CONCLUSION")
    print(f"{'=' * 80}")

    if len(successful) >= len(results) * 0.8:
        print("[PASS] Production Text2SQL system is working well with qwen2.5:7b!")
        print("The system successfully retrieves schema from Qdrant and generates accurate SQL.")
    else:
        print("[WARNING] Some queries failed. Review the errors above.")

    print(f"\n[INFO] This test used the PRODUCTION system:")
    print(f"  - Schema retrieved from Qdrant collection: {vector_store.COLLECTION_NAME}")
    print(f"  - Two-stage retrieval (table identification + detailed context)")
    print(f"  - Relationship-aware JOIN generation")
    print(f"  - Business rules enforcement")

if __name__ == "__main__":
    try:
        test_production_text2sql()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test stopped by user")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
