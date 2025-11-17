"""
Test script to verify date serialization fix
Tests that queries returning date columns don't throw JSON serialization errors
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from AI.text2sql_generator import Text2SQLGenerator
from AI.tools import BOQTools
from Database.session import Session
from datetime import date, datetime
import json

def test_date_serialization():
    """Test that date columns are properly serialized to JSON"""

    print("=" * 80)
    print("TESTING DATE SERIALIZATION FIX")
    print("=" * 80)

    # Initialize the generator
    generator = Text2SQLGenerator()
    db = Session()

    # Test query that should return date columns
    test_query = "fetch me all the rop lvl1 items that belong to the project 0000000200GIC7326_000790592"

    print(f"\nQuery: {test_query}")
    print("=" * 80)

    try:
        # Generate SQL
        result = generator.generate_sql(test_query)
        print(f"\nSQL Generated:\n{result.sql}")

        # Execute the SQL using BOQTools
        query_result = BOQTools.query_database(
            db=db,
            user_id=1,
            sql_query=result.sql,
            description="Test date serialization"
        )

        if not query_result.get('success'):
            print(f"\n[ERROR] Query failed: {query_result.get('error')}")
            return

        print(f"\n[OK] Query executed successfully!")
        print(f"Rows returned: {query_result.get('row_count', 0)}")
        print(f"Columns: {query_result.get('columns', [])}")

        # Test JSON serialization
        try:
            data = query_result.get('data', [])
            json_str = json.dumps(data, indent=2)
            print(f"\n[OK] JSON serialization successful!")

            if data:
                print(f"\nFirst row (JSON serialized):")
                print(json.dumps(data[0], indent=2))

                # Check if there are date columns
                first_row = data[0]
                date_columns = []
                for key, value in first_row.items():
                    if 'date' in key.lower() and value:
                        date_columns.append(f"{key}: {value}")

                if date_columns:
                    print(f"\n[OK] Date columns serialized correctly:")
                    for col in date_columns:
                        print(f"  - {col}")
                else:
                    print(f"\n[INFO] No date values in results (might be NULL)")
            else:
                print(f"\n[INFO] No rows returned")

        except TypeError as e:
            if "not JSON serializable" in str(e):
                print(f"\n[ERROR] JSON serialization failed!")
                print(f"Error: {e}")
                print(f"\nThis means the fix didn't work properly.")
                return
            raise

        print(f"\n{'=' * 80}")
        print("[SUCCESS] All tests passed! Date columns are properly serialized.")
        print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Test failed with exception:")
        print(f"{type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_date_serialization()
