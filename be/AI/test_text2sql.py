"""
Test Script for Text-to-SQL System

Demonstrates the complete pipeline with example queries.

Usage:
    python AI/test_text2sql.py

Author: Senior AI Architect
Created: 2025-11-06
"""
import sys
from pathlib import Path
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from AI.text2sql_generator import Text2SQLGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_text2sql():
    """Test the Text-to-SQL generator with example queries."""

    print("="*80)
    print("TEXT-TO-SQL SYSTEM TEST")
    print("="*80)
    print()

    # Initialize generator
    print("Initializing Text2SQL generator...")
    generator = Text2SQLGenerator(temperature=0.1)
    print("[OK] Generator initialized")
    print()

    # Test queries
    test_queries = [
        {
            "question": "Show me all users",
            "description": "Simple query - single table"
        },
        {
            "question": "How many users are in the database?",
            "description": "Aggregation query"
        },
        {
            "question": "Show me all users with their roles",
            "description": "JOIN query - tests relationship retrieval"
        },
        {
            "question": "List all user actions from the audit log",
            "description": "JOIN query - users + audit_logs"
        },
        {
            "question": "What projects exist in the system?",
            "description": "Simple query - projects table"
        },
        {
            "question": "Show me active projects",
            "description": "Business logic query - tests business rules"
        },
    ]

    for i, test in enumerate(test_queries, 1):
        print("="*80)
        print(f"TEST {i}: {test['description']}")
        print("="*80)
        print(f"Question: {test['question']}")
        print()

        try:
            # Generate SQL
            result = generator.generate_sql(
                question=test['question'],
                database="SQL Server",
                validate=True
            )

            print(f"Confidence: {result.confidence:.2f}")
            print(f"Execution Ready: {result.execution_ready}")
            print()

            print("Retrieved Context:")
            print(f"  - Tables: {len(result.retrieved_context['tables'])}")
            print(f"  - Relationships: {len(result.retrieved_context['relationships'])}")
            print(f"  - Business Rules: {len(result.retrieved_context['business_rules'])}")
            print(f"  - Total Chunks: {len(result.retrieved_context['all_chunks'])}")
            print()

            if result.errors:
                print("[WARNING] Validation Errors:")
                for error in result.errors:
                    print(f"  - {error}")
                print()

            print("Generated SQL:")
            print("-" * 80)
            print(result.sql)
            print("-" * 80)
            print()

            # Show some retrieved context (for debugging)
            if result.retrieved_context['relationships']:
                print("Sample Retrieved JOIN Condition:")
                rel = result.retrieved_context['relationships'][0]
                print(f"  {rel['content'][:150]}...")
                print()

        except Exception as e:
            print(f"[ERROR] {e}")
            import traceback
            traceback.print_exc()
            print()

        print()

    print("="*80)
    print("TESTING COMPLETE!")
    print("="*80)


def test_simple_interface():
    """Test the simple text_to_sql() convenience function."""

    print("\n" + "="*80)
    print("TESTING SIMPLE INTERFACE")
    print("="*80)
    print()

    from AI.text2sql_generator import text_to_sql

    question = "Show me all users with their roles"
    print(f"Question: {question}")
    print()

    sql = text_to_sql(question)

    print("Generated SQL:")
    print("-" * 80)
    print(sql)
    print("-" * 80)
    print()


if __name__ == "__main__":
    # Run full test suite
    test_text2sql()

    # Test simple interface
    test_simple_interface()

    print("\nAll tests complete! [SUCCESS]")
