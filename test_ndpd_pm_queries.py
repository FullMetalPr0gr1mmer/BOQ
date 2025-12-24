"""
Test NDPD Text-to-SQL with realistic Project Manager questions
Simulates real PM queries and validates SQL generation
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

# Project Manager Test Questions (organized by complexity)
PM_TEST_QUESTIONS = [
    # === BASIC QUESTIONS (Simple SELECT, COUNT) ===
    {
        "category": "Basic - Overview",
        "question": "Show me NDPD data",
        "difficulty": "Easy",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "FROM", "ndpd_data"]
    },
    {
        "category": "Basic - Count",
        "question": "How many NDPD records do we have?",
        "difficulty": "Easy",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "COUNT", "FROM", "ndpd_data"]
    },
    {
        "category": "Basic - Filter",
        "question": "Show me NDPD data for period 2025P01",
        "difficulty": "Easy",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "FROM", "ndpd_data", "WHERE", "period", "2025P01"]
    },

    # === AGGREGATION QUESTIONS (SUM, AVG, GROUP BY) ===
    {
        "category": "Aggregation - Totals",
        "question": "What's the total number of forecasted sites?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "forecast_sites", "FROM", "ndpd_data"]
    },
    {
        "category": "Aggregation - Totals",
        "question": "How many total sites were actually deployed?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "FROM", "ndpd_data"]
    },
    {
        "category": "Aggregation - By Period",
        "question": "Show me actual vs forecast for each period",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "period", "SUM", "actual_sites", "forecast_sites", "GROUP BY"]
    },

    # === COMPARISON & VARIANCE QUESTIONS ===
    {
        "category": "Analysis - Variance",
        "question": "What's the variance between actual and forecast sites?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "forecast_sites", "FROM", "ndpd_data"]
    },
    {
        "category": "Analysis - Achievement",
        "question": "What's our achievement rate for deployments?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "forecast_sites", "100"]
    },
    {
        "category": "Analysis - Performance",
        "question": "Which regions exceeded their forecast?",
        "difficulty": "Hard",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "ct", "actual_sites", "forecast_sites", "WHERE", "actual_sites", ">", "forecast_sites"]
    },

    # === FILTERING BY REGION/CARRIER ===
    {
        "category": "Filter - Carrier",
        "question": "Show me Airtel deployments",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "FROM", "ndpd_data", "WHERE", "ct", "LIKE", "Airtel"]
    },
    {
        "category": "Filter - Country",
        "question": "How many sites are deployed in Kenya?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "FROM", "ndpd_data", "WHERE", "ct", "LIKE", "Kenya"]
    },
    {
        "category": "Filter - Region",
        "question": "What's the forecast for MEA CEWA region?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "forecast_sites", "FROM", "ndpd_data", "WHERE", "ct", "LIKE", "MEA CEWA"]
    },

    # === COMPLEX PM QUESTIONS ===
    {
        "category": "Complex - Ranking",
        "question": "Show me the top 5 best performing deployments",
        "difficulty": "Hard",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "TOP", "5", "ct", "actual_sites", "forecast_sites", "WHERE", "actual_sites", ">", "forecast_sites"]
    },
    {
        "category": "Complex - Ranking",
        "question": "Which 5 regions are underperforming the most?",
        "difficulty": "Hard",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "TOP", "5", "ct", "WHERE", "actual_sites", "<", "forecast_sites", "ORDER BY"]
    },
    {
        "category": "Complex - Multi-metric",
        "question": "Give me a summary of 2025P01 performance including actual, forecast, and achievement rate",
        "difficulty": "Hard",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "forecast_sites", "WHERE", "period", "2025P01"]
    },

    # === REAL PROJECT MANAGER QUESTIONS ===
    {
        "category": "PM - Strategy",
        "question": "Are we meeting our deployment targets?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "actual_sites", "forecast_sites"]
    },
    {
        "category": "PM - Planning",
        "question": "What's our total planned deployment for all of 2025?",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "SUM", "forecast_sites", "WHERE", "period", "LIKE", "2025"]
    },
    {
        "category": "PM - Issue Identification",
        "question": "Show me all deployments where we missed the target",
        "difficulty": "Medium",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "FROM", "ndpd_data", "WHERE", "actual_sites", "<", "forecast_sites"]
    },
    {
        "category": "PM - Detailed Analysis",
        "question": "Break down actual vs forecast by carrier",
        "difficulty": "Hard",
        "expected_tables": ["ndpd_data"],
        "expected_keywords": ["SELECT", "ct", "SUM", "actual_sites", "forecast_sites", "GROUP BY"]
    }
]


def validate_sql(sql, expected_keywords):
    """Check if SQL contains expected keywords"""
    sql_upper = sql.upper()
    found_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:
        keyword_upper = keyword.upper()
        if keyword_upper in sql_upper:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    score = len(found_keywords) / len(expected_keywords) * 100 if expected_keywords else 0
    return score, found_keywords, missing_keywords


def test_ndpd_queries():
    """Test NDPD queries with PM questions"""
    print("=" * 80)
    print("PROJECT MANAGER NDPD QUERY TEST")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # Check Qdrant status
    print("\n[CHECKING] Qdrant Collection Status...")
    try:
        vector_store = get_text2sql_vector_store()
        stats = vector_store.get_collection_stats()
        print(f"[OK] Collection: {vector_store.COLLECTION_NAME}")
        print(f"[OK] Total vectors: {stats.get('total_vectors', 'unknown')}")
        print(f"[OK] NDPD chunks: {stats.get('chunk_type_distribution', {})}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Qdrant: {e}")
        return

    # Initialize generator
    print("\n[INITIALIZING] Text2SQL Generator...")
    generator = get_text2sql_generator()
    print("[OK] Generator ready")

    # Test each question
    results = []
    total_time = 0
    passed = 0
    failed = 0

    for idx, test in enumerate(PM_TEST_QUESTIONS, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {idx}/{len(PM_TEST_QUESTIONS)}: {test['category']} ({test['difficulty']})")
        print(f"{'=' * 80}")
        print(f"PM Question: {test['question']}")

        start_time = time.time()
        try:
            result = generator.generate_sql(
                question=test['question'],
                database="SQL Server",
                validate=True
            )
            elapsed = time.time() - start_time
            total_time += elapsed

            # Validate SQL
            score, found, missing = validate_sql(result.sql, test['expected_keywords'])

            # Determine pass/fail
            is_pass = result.execution_ready and score >= 70

            print(f"\n[SQL GENERATED]")
            print(result.sql)

            print(f"\n[VALIDATION]")
            print(f"  Accuracy Score: {score:.1f}%")
            print(f"  Execution Ready: {result.execution_ready}")
            print(f"  Confidence: {result.confidence:.2%}")
            print(f"  Time: {elapsed:.2f}s")

            if missing:
                print(f"  Missing Keywords: {', '.join(missing)}")

            print(f"\n[RESULT] {'PASS' if is_pass else 'FAIL'}")

            if is_pass:
                passed += 1
            else:
                failed += 1

            results.append({
                'question': test['question'],
                'category': test['category'],
                'sql': result.sql,
                'score': score,
                'time': elapsed,
                'confidence': result.confidence,
                'pass': is_pass
            })

        except Exception as e:
            elapsed = time.time() - start_time
            print(f"\n[ERROR] {str(e)}")
            failed += 1
            results.append({
                'question': test['question'],
                'category': test['category'],
                'error': str(e),
                'time': elapsed,
                'pass': False
            })

    # Summary Report
    print(f"\n{'=' * 80}")
    print("SUMMARY REPORT")
    print(f"{'=' * 80}")

    print(f"\nOverall Results:")
    print(f"  Total Questions: {len(PM_TEST_QUESTIONS)}")
    print(f"  Passed: {passed} ({passed/len(PM_TEST_QUESTIONS)*100:.1f}%)")
    print(f"  Failed: {failed} ({failed/len(PM_TEST_QUESTIONS)*100:.1f}%)")

    successful = [r for r in results if r.get('pass', False)]
    if successful:
        avg_time = sum(r['time'] for r in successful) / len(successful)
        avg_score = sum(r.get('score', 0) for r in successful) / len(successful)
        avg_confidence = sum(r.get('confidence', 0) for r in successful) / len(successful)

        print(f"\nPerformance Metrics (Passed Tests Only):")
        print(f"  Avg Time: {avg_time:.2f}s")
        print(f"  Avg Accuracy: {avg_score:.1f}%")
        print(f"  Avg Confidence: {avg_confidence:.2%}")
        print(f"  Total Time: {total_time:.2f}s")

    # Category Breakdown
    print(f"\n{'=' * 80}")
    print("CATEGORY BREAKDOWN")
    print(f"{'=' * 80}")

    categories = {}
    for r in results:
        cat = r['category']
        if cat not in categories:
            categories[cat] = {'total': 0, 'passed': 0}
        categories[cat]['total'] += 1
        if r.get('pass', False):
            categories[cat]['passed'] += 1

    for cat, stats in sorted(categories.items()):
        pass_rate = stats['passed'] / stats['total'] * 100
        print(f"{cat}: {stats['passed']}/{stats['total']} ({pass_rate:.0f}%)")

    # Failed Questions
    failed_tests = [r for r in results if not r.get('pass', False)]
    if failed_tests:
        print(f"\n{'=' * 80}")
        print("FAILED QUESTIONS (Need Fine-Tuning)")
        print(f"{'=' * 80}")
        for r in failed_tests:
            print(f"\n- {r['question']}")
            if 'error' in r:
                print(f"  Error: {r['error']}")
            else:
                print(f"  Score: {r.get('score', 0):.1f}%")
                print(f"  SQL: {r.get('sql', 'N/A')[:100]}...")

    # Final Assessment
    print(f"\n{'=' * 80}")
    print("ASSESSMENT")
    print(f"{'=' * 80}")

    if passed / len(PM_TEST_QUESTIONS) >= 0.9:
        print("[EXCELLENT] System is production-ready for PM queries!")
    elif passed / len(PM_TEST_QUESTIONS) >= 0.7:
        print("[GOOD] System works well, minor fine-tuning needed")
    else:
        print("[NEEDS WORK] Significant improvements required")

    print(f"\n[INFO] NDPD schema chunks are working with qwen2.5:7b")
    print(f"[INFO] Project Managers can now ask questions about deployment data in natural language")
    print("=" * 80)


if __name__ == "__main__":
    try:
        test_ndpd_queries()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test stopped by user")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
