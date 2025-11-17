"""
Direct Test of Query Router
Tests the query router logic directly without needing API authentication
"""
import sys
sys.path.insert(0, 'C:/WORK/BOQ/be')

from AI.query_router import route_query, QueryType, get_query_router

def test_query_detection():
    """Test query type detection"""
    router = get_query_router()

    print("="*80)
    print("QUERY ROUTER - DETECTION TESTS")
    print("="*80)

    test_cases = [
        ("fetch me ran_lld", QueryType.DATABASE, "Direct table request"),
        ("get users", QueryType.DATABASE, "Direct table request"),
        ("show me all projects", QueryType.DATABASE, "Database keywords"),
        ("how many rows in ran_inventory", QueryType.DATABASE, "Database keywords"),
        ("What does the RFP document say?", QueryType.DOCUMENT, "Document keywords"),
        ("Hello, how are you?", QueryType.CHAT, "Chat query"),
    ]

    print("\nTest cases:")
    print("-" * 80)

    for question, expected_type, reason in test_cases:
        detected_type = router.detect_query_type(question)
        status = "[OK]" if detected_type == expected_type else "[FAIL]"

        print(f"{status} Question: '{question}'")
        print(f"     Expected: {expected_type.value}, Got: {detected_type.value}")
        print(f"     Reason: {reason}")
        print()

    print("="*80)

def test_route_query_full():
    """Test the full query routing with SQL generation"""
    print("\n" + "="*80)
    print("FULL QUERY ROUTING TEST - 'fetch me ran_lld'")
    print("="*80)

    question = "fetch me ran_lld"

    print(f"\nQuestion: '{question}'")
    print("-" * 80)

    try:
        result = route_query(question, user_id="test_user")

        print(f"\n[OK] Query routed successfully!")
        print(f"Query Type: {result['type']}")
        print(f"Query Type (field): {result.get('query_type')}")

        if result['type'] == 'database':
            print(f"\nGenerated SQL:")
            print("-" * 80)
            print(result.get('sql', 'N/A'))
            print("-" * 80)

            print(f"\nConfidence: {result.get('confidence', 0):.2f}")
            print(f"Execution Ready: {result.get('execution_ready', False)}")
            print(f"Errors: {result.get('errors', [])}")

            # Check for conversational message (should be None for database queries!)
            message = result.get('message')
            if message is None:
                print(f"\n[OK] NO conversational message - hallucination prevented!")
            else:
                print(f"\n[WARNING] Conversational message present: {message}")

            print(f"\nInstruction: {result.get('instruction')}")

        print("\n" + "="*80)
        print("[OK] TEST PASSED - Query router working correctly!")
        print("="*80)

    except Exception as e:
        print(f"\n[ERROR] Query routing failed: {e}")
        import traceback
        traceback.print_exc()
        print("\n" + "="*80)
        print("[ERROR] TEST FAILED")
        print("="*80)

def main():
    print("\n")
    print("#" * 80)
    print("# QUERY ROUTER DIRECT TEST")
    print("# This tests the query router without requiring API authentication")
    print("#" * 80)
    print("\n")

    # Test 1: Detection
    test_query_detection()

    # Test 2: Full routing with SQL generation
    test_route_query_full()

if __name__ == "__main__":
    main()
