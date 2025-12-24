"""
Test Text-to-SQL capabilities for RAN database
Compares qwen2.5:7b vs sqlcoder models
"""
import os
import time
import json
import re

# Bypass proxy for localhost
os.environ['NO_PROXY'] = 'localhost,127.0.0.1'
os.environ['no_proxy'] = 'localhost,127.0.0.1'

import ollama
from datetime import datetime

# RAN Database Schema
SCHEMA = """
-- RAN Database Schema (SQL Server)

-- Projects table
CREATE TABLE ran_projects (
    pid_po VARCHAR(200) PRIMARY KEY,
    pid VARCHAR(100),
    po VARCHAR(100),
    project_name VARCHAR(200)
);

-- Inventory table
CREATE TABLE ran_inventory (
    id INT PRIMARY KEY IDENTITY,
    mrbts VARCHAR(200),
    site_id VARCHAR(200),
    identification_code VARCHAR(200),
    user_label VARCHAR(200),
    serial_number VARCHAR(200),
    duplicate BIT DEFAULT 0,
    duplicate_remarks VARCHAR(200),
    pid_po VARCHAR(200) FOREIGN KEY REFERENCES ran_projects(pid_po)
);

-- Level 3 BOQ items
CREATE TABLE ranlvl3 (
    id INT PRIMARY KEY IDENTITY,
    project_id VARCHAR(200) FOREIGN KEY REFERENCES ran_projects(pid_po),
    item_name VARCHAR(200),
    key VARCHAR(200),
    service_type VARCHAR(MAX),  -- JSON array
    uom VARCHAR(200),
    total_quantity INT,
    total_price FLOAT,
    po_line VARCHAR(100),
    category VARCHAR(200),
    upl_line VARCHAR(100),
    ran_category VARCHAR(100)
);

-- Detailed items for Level 3
CREATE TABLE items_for_ranlvl3 (
    id INT PRIMARY KEY IDENTITY,
    ranlvl3_id INT FOREIGN KEY REFERENCES ranlvl3(id),
    item_name VARCHAR(200),
    item_details VARCHAR(200),
    vendor_part_number VARCHAR(200),
    service_type TEXT,  -- JSON array
    category VARCHAR(200),
    uom INT,
    quantity INT,
    price FLOAT,
    upl_line VARCHAR(100)
);

-- Low Level Design
CREATE TABLE ran_lld (
    id INT PRIMARY KEY IDENTITY,
    site_id VARCHAR(100),
    new_antennas VARCHAR(MAX),
    total_antennas INT,
    technical_boq VARCHAR(255),
    key VARCHAR(200),
    pid_po VARCHAR(200) FOREIGN KEY REFERENCES ran_projects(pid_po)
);

-- Antenna serials
CREATE TABLE ran_antenna_serials (
    id INT PRIMARY KEY IDENTITY,
    mrbts VARCHAR(200),
    antenna_model VARCHAR(200),
    serial_number VARCHAR(200),
    project_id VARCHAR(200) FOREIGN KEY REFERENCES ran_projects(pid_po)
);
"""

# Test cases with expected SQL patterns
TEST_CASES = [
    # === CATEGORY 1: Simple SELECT queries ===
    {
        "category": "Simple SELECT",
        "question": "Show me all RAN projects",
        "expected_keywords": ["SELECT", "FROM", "ran_projects"],
        "difficulty": "Easy"
    },
    {
        "category": "Simple SELECT",
        "question": "Get all inventory items for site ID 'CAIRO-001'",
        "expected_keywords": ["SELECT", "FROM", "ran_inventory", "WHERE", "site_id", "CAIRO-001"],
        "difficulty": "Easy"
    },
    {
        "category": "Simple SELECT",
        "question": "List all duplicate inventory items",
        "expected_keywords": ["SELECT", "FROM", "ran_inventory", "WHERE", "duplicate", "1", "True"],
        "difficulty": "Easy"
    },

    # === CATEGORY 2: JOIN queries ===
    {
        "category": "JOIN",
        "question": "Show all inventory items with their project names",
        "expected_keywords": ["SELECT", "JOIN", "ran_inventory", "ran_projects", "pid_po", "project_name"],
        "difficulty": "Medium"
    },
    {
        "category": "JOIN",
        "question": "Get all BOQ items for project 'PID123-PO456' with project details",
        "expected_keywords": ["SELECT", "JOIN", "ranlvl3", "ran_projects", "project_id", "pid_po"],
        "difficulty": "Medium"
    },
    {
        "category": "JOIN",
        "question": "List all antenna serials with their project names",
        "expected_keywords": ["SELECT", "JOIN", "ran_antenna_serials", "ran_projects", "project_id"],
        "difficulty": "Medium"
    },

    # === CATEGORY 3: Aggregation queries ===
    {
        "category": "Aggregation",
        "question": "How many inventory items are there per project?",
        "expected_keywords": ["SELECT", "COUNT", "GROUP BY", "ran_inventory", "pid_po"],
        "difficulty": "Medium"
    },
    {
        "category": "Aggregation",
        "question": "What is the total price of all items in each RAN project?",
        "expected_keywords": ["SELECT", "SUM", "total_price", "GROUP BY", "ranlvl3", "project_id"],
        "difficulty": "Medium"
    },
    {
        "category": "Aggregation",
        "question": "Count how many sites have antennas in each project",
        "expected_keywords": ["SELECT", "COUNT", "GROUP BY", "ran_lld", "pid_po"],
        "difficulty": "Medium"
    },

    # === CATEGORY 4: Complex queries ===
    {
        "category": "Complex",
        "question": "Show projects with total BOQ value greater than 100000, including item count",
        "expected_keywords": ["SELECT", "SUM", "COUNT", "GROUP BY", "HAVING", "ranlvl3"],
        "difficulty": "Hard"
    },
    {
        "category": "Complex",
        "question": "List all sites with their total antenna count and associated project name",
        "expected_keywords": ["SELECT", "JOIN", "ran_lld", "ran_projects", "total_antennas", "site_id"],
        "difficulty": "Hard"
    },
    {
        "category": "Complex",
        "question": "Get all hardware items (service_type = 2) from ranlvl3 with quantities and prices, grouped by category",
        "expected_keywords": ["SELECT", "WHERE", "service_type", "GROUP BY", "category", "ranlvl3"],
        "difficulty": "Hard"
    }
]

def extract_sql(response_text):
    """Extract SQL query from model response"""
    # Try to find SQL in code blocks
    sql_pattern = r'```(?:sql)?\s*(SELECT.*?)```'
    match = re.search(sql_pattern, response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # Try to find SELECT statement directly
    select_pattern = r'(SELECT\s+.*?(?:;|$))'
    match = re.search(select_pattern, response_text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip().rstrip(';')

    return response_text.strip()

def validate_sql(sql, expected_keywords):
    """Check if SQL contains expected keywords"""
    sql_upper = sql.upper()
    found_keywords = []
    missing_keywords = []

    for keyword in expected_keywords:
        if keyword.upper() in sql_upper:
            found_keywords.append(keyword)
        else:
            missing_keywords.append(keyword)

    score = len(found_keywords) / len(expected_keywords) * 100
    return score, found_keywords, missing_keywords

def test_text2sql(model_name, test_case):
    """Test a single text-to-SQL query"""
    prompt = f"""You are a SQL expert. Given the database schema below, write a SQL query to answer the question.

Database Schema:
{SCHEMA}

Question: {test_case['question']}

Provide ONLY the SQL query without any explanation. Use SQL Server syntax.
"""

    start_time = time.time()
    try:
        response = ollama.generate(
            model=model_name,
            prompt=prompt,
            options={'temperature': 0.0}  # Deterministic for SQL
        )
        elapsed = time.time() - start_time

        sql = extract_sql(response['response'])
        score, found, missing = validate_sql(sql, test_case['expected_keywords'])

        return {
            'success': True,
            'sql': sql,
            'time': elapsed,
            'score': score,
            'found_keywords': found,
            'missing_keywords': missing
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'time': time.time() - start_time,
            'score': 0
        }

def run_comparison():
    """Run comprehensive text-to-SQL comparison"""
    models = ['qwen2.5:7b', 'sqlcoder:latest']

    print("=" * 80)
    print("TEXT-TO-SQL PERFORMANCE TEST")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    results = {model: [] for model in models}

    for test_idx, test_case in enumerate(TEST_CASES, 1):
        print(f"\n{'=' * 80}")
        print(f"TEST {test_idx}/{len(TEST_CASES)}: {test_case['category']} ({test_case['difficulty']})")
        print(f"{'=' * 80}")
        print(f"Question: {test_case['question']}")

        for model in models:
            print(f"\n--- Testing {model} ---")
            result = test_text2sql(model, test_case)
            results[model].append(result)

            if result['success']:
                print(f"SQL Generated:\n{result['sql'][:200]}{'...' if len(result['sql']) > 200 else ''}")
                print(f"Accuracy Score: {result['score']:.1f}%")
                print(f"Time: {result['time']:.2f}s")
                if result['missing_keywords']:
                    print(f"Missing Keywords: {', '.join(result['missing_keywords'])}")
            else:
                print(f"[ERROR] {result['error']}")

    # Summary Report
    print(f"\n{'=' * 80}")
    print("SUMMARY REPORT")
    print(f"{'=' * 80}")

    for model in models:
        model_results = results[model]
        successful = [r for r in model_results if r['success']]

        if successful:
            avg_score = sum(r['score'] for r in successful) / len(successful)
            avg_time = sum(r['time'] for r in successful) / len(successful)
            max_time = max(r['time'] for r in successful)

            print(f"\n{model}:")
            print(f"  Success Rate:    {len(successful)}/{len(model_results)} ({len(successful)/len(model_results)*100:.1f}%)")
            print(f"  Avg Accuracy:    {avg_score:.1f}%")
            print(f"  Avg Time:        {avg_time:.2f}s")
            print(f"  Max Time:        {max_time:.2f}s")
            print(f"  Under 3 mins:    {'YES' if max_time < 180 else 'NO'}")
        else:
            print(f"\n{model}:")
            print(f"  [FAILED] No successful queries")

    # Category breakdown
    print(f"\n{'=' * 80}")
    print("CATEGORY BREAKDOWN")
    print(f"{'=' * 80}")

    categories = set(tc['category'] for tc in TEST_CASES)
    for category in categories:
        print(f"\n{category}:")
        for model in models:
            cat_results = [
                results[model][i]
                for i, tc in enumerate(TEST_CASES)
                if tc['category'] == category and results[model][i]['success']
            ]
            if cat_results:
                avg_score = sum(r['score'] for r in cat_results) / len(cat_results)
                print(f"  {model}: {avg_score:.1f}% avg accuracy")

    print(f"\n{'=' * 80}")
    print("RECOMMENDATION")
    print(f"{'=' * 80}")

    # Determine winner
    qwen_results = [r for r in results['qwen2.5:7b'] if r['success']]
    sql_results = [r for r in results['sqlcoder:latest'] if r['success']]

    if qwen_results and sql_results:
        qwen_score = sum(r['score'] for r in qwen_results) / len(qwen_results)
        sql_score = sum(r['score'] for r in sql_results) / len(sql_results)
        qwen_time = sum(r['time'] for r in qwen_results) / len(qwen_results)
        sql_time = sum(r['time'] for r in sql_results) / len(sql_results)

        if qwen_score > sql_score:
            print(f"qwen2.5:7b is BETTER for accuracy ({qwen_score:.1f}% vs {sql_score:.1f}%)")
        else:
            print(f"sqlcoder is BETTER for accuracy ({sql_score:.1f}% vs {qwen_score:.1f}%)")

        if qwen_time < sql_time:
            print(f"qwen2.5:7b is FASTER ({qwen_time:.2f}s vs {sql_time:.2f}s)")
        else:
            print(f"sqlcoder is FASTER ({sql_time:.2f}s vs {qwen_time:.2f}s)")

if __name__ == "__main__":
    try:
        run_comparison()
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Test stopped by user")
    except Exception as e:
        print(f"\n[ERROR] {e}")
        import traceback
        traceback.print_exc()
