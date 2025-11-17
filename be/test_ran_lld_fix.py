"""
Test script to verify ran_lld query fix
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from AI.text2sql_generator import Text2SQLGenerator

def test_ran_lld_query():
    """Test the previously failing ran_lld query"""

    print("=" * 80)
    print("TESTING RAN_LLD QUERY FIX")
    print("=" * 80)

    # Initialize the generator
    generator = Text2SQLGenerator()

    # Test queries that were failing before
    test_queries = [
        "fetch me 3 ran lld records",
        "fetch me 3 ran_lld records",
        "show me ran lld table",
        "get data from ran lld"
    ]

    for query in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Query: {query}")
        print(f"{'=' * 80}")

        # Generate SQL
        result = generator.generate_sql(query)

        print(f"\nSQL Generated:\n{result.sql}")
        print(f"\nConfidence: {result.confidence}")
        print(f"\nExecution Ready: {result.execution_ready}")
        print(f"\nErrors: {result.errors if result.errors else 'None'}")

        # Verify table name is correct
        if 'ran_lld' in result.sql.lower():
            print(f"\n[OK] SUCCESS: Query correctly identified 'ran_lld' table!")
        elif 'ranlld' in result.sql.lower() or 'ranlldrecords' in result.sql.lower():
            print(f"\n[ERROR] FAILURE: Query generated wrong table name (should be 'ran_lld')")
        else:
            print(f"\n[?] UNCERTAIN: Table name not clearly identified in SQL")

        # Show retrieved context stats
        if result.retrieved_context:
            print(f"\nRetrieved Context:")
            print(f"  - Total chunks: {len(result.retrieved_context.get('all_chunks', []))}")
            print(f"  - Tables identified: {result.retrieved_context.get('tables', [])}")

if __name__ == "__main__":
    test_ran_lld_query()
