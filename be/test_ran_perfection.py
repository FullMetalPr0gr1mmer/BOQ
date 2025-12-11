"""
RAN Text2SQL - PERFECTION TEST SUITE
Tests from simple to extremely complex queries
"""
from AI.text2sql_generator import Text2SQLGenerator
import logging

logging.basicConfig(level=logging.WARNING)  # Suppress INFO logs for cleaner output

def test_ran_text2sql():
    """Comprehensive test suite for RAN Text2SQL"""

    test_cases = [
        # ===== BASIC QUERIES =====
        {
            "name": "Basic SELECT - RAN projects",
            "query": "show me all RAN projects",
            "expected_tables": ["ran_projects"],
            "difficulty": "easy"
        },
        {
            "name": "Basic COUNT",
            "query": "how many RAN projects",
            "expected_tables": ["ran_projects"],
            "expected_pattern": "COUNT",
            "difficulty": "easy"
        },
        {
            "name": "RAN Level 3",
            "query": "show me RAN level 3 items",
            "expected_tables": ["ranlvl3"],
            "difficulty": "easy"
        },
        {
            "name": "RAN Inventory",
            "query": "show me RAN inventory",
            "expected_tables": ["ran_inventory"],
            "difficulty": "easy"
        },
        {
            "name": "RAN Antennas",
            "query": "show me RAN antennas",
            "expected_tables": ["ran_antenna_serials"],
            "difficulty": "easy"
        },
        {
            "name": "RAN LLD",
            "query": "show me RAN LLD",
            "expected_tables": ["ran_lld"],
            "difficulty": "easy"
        },

        # ===== FILTERING QUERIES =====
        {
            "name": "Filter by PO",
            "query": "show me RAN projects with PO MW123",
            "expected_tables": ["ran_projects"],
            "expected_pattern": "WHERE.*po.*MW123",
            "difficulty": "medium"
        },
        {
            "name": "Filter by site",
            "query": "show me RAN inventory for site ABC123",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "WHERE.*site_id.*ABC123",
            "difficulty": "medium"
        },
        {
            "name": "Filter duplicates",
            "query": "show me duplicate RAN inventory items",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "WHERE.*duplicate.*=.*1",
            "difficulty": "medium"
        },
        {
            "name": "Filter by serial number",
            "query": "find RAN inventory with serial number 12345",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "WHERE.*serial_number.*12345",
            "difficulty": "medium"
        },

        # ===== AGGREGATION QUERIES =====
        {
            "name": "Count lvl3 items",
            "query": "how many RAN lvl3 items",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "COUNT",
            "difficulty": "medium"
        },
        {
            "name": "Total quantity",
            "query": "total quantity in RAN lvl3",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "SUM.*total_quantity",
            "difficulty": "medium"
        },
        {
            "name": "Total price",
            "query": "sum of total price in RAN lvl3",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "SUM.*total_price",
            "difficulty": "medium"
        },
        {
            "name": "Count inventory per site",
            "query": "count RAN inventory items per site",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "GROUP BY.*site_id",
            "difficulty": "hard"
        },
        {
            "name": "Average quantity",
            "query": "average quantity in RAN lvl3",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "AVG.*total_quantity",
            "difficulty": "medium"
        },

        # ===== SORTING QUERIES =====
        {
            "name": "Top 10 RAN projects",
            "query": "show me top 10 RAN projects",
            "expected_tables": ["ran_projects"],
            "expected_pattern": "TOP 10",
            "difficulty": "medium"
        },
        {
            "name": "RAN lvl3 by quantity",
            "query": "show me RAN lvl3 items ordered by quantity",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "ORDER BY.*total_quantity",
            "difficulty": "medium"
        },
        {
            "name": "RAN lvl3 by price DESC",
            "query": "show me RAN lvl3 sorted by price descending",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "ORDER BY.*total_price.*DESC",
            "difficulty": "medium"
        },

        # ===== JOIN QUERIES =====
        {
            "name": "RAN projects with inventory",
            "query": "show me RAN projects with their inventory",
            "expected_tables": ["ran_projects", "ran_inventory"],
            "expected_pattern": "JOIN.*ran_inventory.*ON.*pid_po",
            "difficulty": "hard"
        },
        {
            "name": "RAN projects with lvl3",
            "query": "show me RAN projects with their level 3 items",
            "expected_tables": ["ran_projects", "ranlvl3"],
            "expected_pattern": "JOIN.*ranlvl3.*ON.*pid_po",
            "difficulty": "hard"
        },
        {
            "name": "RAN lvl3 with project names",
            "query": "show me RAN level 3 items with project names",
            "expected_tables": ["ranlvl3", "ran_projects"],
            "expected_pattern": "JOIN.*ran_projects",
            "difficulty": "hard"
        },

        # ===== COMPLEX MULTI-CONDITION QUERIES =====
        {
            "name": "Complex filter - RAN inventory",
            "query": "show me RAN inventory for site ABC123 where serial number contains 456",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "WHERE.*site_id.*AND.*serial_number",
            "difficulty": "hard"
        },
        {
            "name": "Complex aggregation",
            "query": "total price of RAN lvl3 items grouped by category",
            "expected_tables": ["ranlvl3"],
            "expected_pattern": "SUM.*GROUP BY.*category",
            "difficulty": "hard"
        },
        {
            "name": "Count with filter",
            "query": "how many RAN inventory items have duplicates",
            "expected_tables": ["ran_inventory"],
            "expected_pattern": "COUNT.*WHERE.*duplicate",
            "difficulty": "hard"
        }
    ]

    generator = Text2SQLGenerator()

    print("=" * 100)
    print("RAN TEXT2SQL - PERFECTION TEST SUITE")
    print("=" * 100)
    print()

    results = {
        "easy": {"passed": 0, "total": 0},
        "medium": {"passed": 0, "total": 0},
        "hard": {"passed": 0, "total": 0}
    }

    failed_tests = []

    for i, test in enumerate(test_cases, 1):
        print(f"\n[TEST {i}/{len(test_cases)}] {test['name']} ({test['difficulty'].upper()})")
        print(f"  Query: \"{test['query']}\"")

        result = generator.generate_sql(test['query'], database='SQL Server')

        # Check if execution ready
        passed = result.execution_ready

        # Check table identification
        retrieved_tables = [t.get('table_name') for t in result.retrieved_context.get('tables', [])]
        expected_tables = test.get('expected_tables', [])

        tables_match = any(t in retrieved_tables for t in expected_tables) if expected_tables else True

        # Check SQL pattern if specified
        import re
        pattern_match = True
        if 'expected_pattern' in test:
            pattern_match = bool(re.search(test['expected_pattern'], result.sql, re.IGNORECASE | re.DOTALL))

        # Overall pass/fail
        test_passed = passed and tables_match and pattern_match

        # Update results
        difficulty = test['difficulty']
        results[difficulty]['total'] += 1
        if test_passed:
            results[difficulty]['passed'] += 1
        else:
            failed_tests.append({
                "name": test['name'],
                "query": test['query'],
                "sql": result.sql,
                "tables": retrieved_tables,
                "expected_tables": expected_tables,
                "errors": result.errors
            })

        # Print result
        status = "[PASS]" if test_passed else "[FAIL]"
        print(f"  SQL: {result.sql}")
        print(f"  Tables: {retrieved_tables}")
        print(f"  Status: {status}")

        if not test_passed:
            if not tables_match:
                print(f"    [!] Expected tables: {expected_tables}")
            if not pattern_match:
                print(f"    [!] Expected pattern: {test['expected_pattern']}")
            if result.errors:
                print(f"    [!] Errors: {result.errors}")

    # Summary
    print("\n" + "=" * 100)
    print("TEST SUMMARY")
    print("=" * 100)

    total_passed = sum(r['passed'] for r in results.values())
    total_tests = sum(r['total'] for r in results.values())

    print(f"\nEasy:   {results['easy']['passed']}/{results['easy']['total']} passed")
    print(f"Medium: {results['medium']['passed']}/{results['medium']['total']} passed")
    print(f"Hard:   {results['hard']['passed']}/{results['hard']['total']} passed")
    print(f"\nOVERALL: {total_passed}/{total_tests} ({total_passed/total_tests*100:.1f}%)")

    if failed_tests:
        print("\n" + "=" * 100)
        print("FAILED TESTS")
        print("=" * 100)
        for fail in failed_tests:
            print(f"\n[X] {fail['name']}")
            print(f"  Query: {fail['query']}")
            print(f"  Generated: {fail['sql']}")
            print(f"  Expected tables: {fail['expected_tables']}")
            print(f"  Got tables: {fail['tables']}")
            if fail['errors']:
                print(f"  Errors: {fail['errors']}")

    print("\n" + "=" * 100)

    return total_passed == total_tests

if __name__ == "__main__":
    success = test_ran_text2sql()
    exit(0 if success else 1)
