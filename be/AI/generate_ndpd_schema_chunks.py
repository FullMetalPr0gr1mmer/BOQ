"""
Generate NDPD (Network Deployment Planning Data) schema knowledge chunks for Text2SQL

This script creates high-quality schema knowledge for the NDPD table.
Optimized for project manager queries about deployment forecasting.

Created: 2025-12-22
"""
import json
from pathlib import Path


def generate_ndpd_schema_chunks():
    """Generate schema knowledge chunks for NDPD table"""

    chunks = []

    # ========================================
    # TABLE: ndpd_data (Network Deployment Planning Data)
    # ========================================
    chunks.append({
        "content": """TABLE: ndpd_data (Network Deployment Planning Data)

Main table for tracking actual vs forecasted site deployments across regions and carriers.

IMPORTANT: When user asks about ANY of these keywords, use ndpd_data table:
- "NDPD"
- "Network Deployment Planning"
- "site forecast", "forecast sites"
- "actual sites", "deployed sites"
- "deployment planning"
- "MEA" (Middle East Africa), "CEWA" (Central/East/West Africa)
- "Airtel", carrier deployments
- Period-based analysis (2025P01, 2025P02, etc.)

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- period (STRING, INDEXED): Time period (e.g., "2025P01" = 2025 Period 01, "2025P02" = 2025 Period 02)
- ct (STRING, INDEXED): Category/Cell Type - Regional deployment category (e.g., "MEA CEWA AIR CT Airtel Kenya")
- actual_sites (INTEGER): Number of sites actually deployed/completed
- forecast_sites (INTEGER): Number of sites forecasted/planned for deployment

Use this table when:
- User asks about "NDPD data" or "network deployment"
- User wants forecast vs actual comparison
- User asks about site deployments by region/carrier
- User wants to analyze deployment performance
- User mentions periods like "2025P01" or "Period 1"

Example queries:
- "Show me NDPD data" → SELECT * FROM ndpd_data
- "How many sites forecasted?" → SELECT SUM(forecast_sites) FROM ndpd_data
- "Actual vs forecast for 2025P01" → SELECT period, SUM(actual_sites), SUM(forecast_sites) FROM ndpd_data WHERE period = '2025P01' GROUP BY period
- "Deployment performance by region" → SELECT ct, actual_sites, forecast_sites FROM ndpd_data
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ndpd_data",
            "priority": "high"
        }
    })

    # ========================================
    # COLUMNS: ndpd_data
    # ========================================
    chunks.append({
        "content": """COLUMNS: ndpd_data

Detailed column information for ndpd_data table:

id: INTEGER, PRIMARY KEY, AUTO INCREMENT
  - Unique identifier for each NDPD record
  - Use for specific record lookups: WHERE id = 123

period: STRING(50), INDEXED
  - Time period in format "YYYYPNN" where:
    - YYYY = Year (e.g., 2025)
    - P = "Period" separator
    - NN = Period number (01, 02, 03, etc.)
  - Examples: "2025P01", "2025P02", "2025P12"
  - Filter by period: WHERE period = '2025P01'
  - Filter by year: WHERE period LIKE '2025%'
  - Common queries:
    - Current period: WHERE period = '2025P01'
    - All periods in 2025: WHERE period LIKE '2025%'
    - Specific quarter: WHERE period IN ('2025P01', '2025P02', '2025P03')

ct: STRING(500), INDEXED
  - Category/Cell Type - Regional deployment category
  - Format: "{Region} {Sub-region} {Carrier} CT {Carrier Name} {Country/Region}"
  - Examples:
    - "MEA CEWA AIR CT Airtel Kenya"
    - "MEA CEWA AIR CT Airtel Nigeria"
    - "MEA ENT NA CT Libya"
  - Breakdown:
    - MEA = Middle East Africa
    - CEWA = Central/East/West Africa
    - AIR = Airtel
    - ENT = Enterprise
    - CT = Cell Type/Category
  - Search patterns:
    - By carrier: WHERE ct LIKE '%Airtel%'
    - By country: WHERE ct LIKE '%Kenya%'
    - By region: WHERE ct LIKE '%MEA CEWA%'

actual_sites: INTEGER
  - Number of sites actually deployed/completed
  - Represents reality - what was achieved
  - Use for performance analysis
  - Aggregations:
    - Total deployed: SUM(actual_sites)
    - Average per category: AVG(actual_sites)
    - Maximum deployment: MAX(actual_sites)

forecast_sites: INTEGER
  - Number of sites forecasted/planned for deployment
  - Represents target/goal
  - Use for planning and variance analysis
  - Aggregations:
    - Total forecasted: SUM(forecast_sites)
    - Total variance: SUM(forecast_sites - actual_sites)
    - Achievement rate: SUM(actual_sites) * 100.0 / SUM(forecast_sites)
""",
        "metadata": {
            "type": "columns",
            "table_name": "ndpd_data"
        }
    })

    # ========================================
    # BUSINESS RULES: NDPD
    # ========================================
    chunks.append({
        "content": """BUSINESS RULE: NDPD Table Selection and Queries

When user asks about Network Deployment Planning, use these EXACT patterns:

1. BASIC QUERIES:
   - "Show me NDPD data" → SELECT * FROM ndpd_data
   - "How many NDPD records?" → SELECT COUNT(*) FROM ndpd_data
   - "NDPD for period 2025P01" → SELECT * FROM ndpd_data WHERE period = '2025P01'

2. FORECAST VS ACTUAL ANALYSIS:
   - "Actual vs forecast" → SELECT SUM(actual_sites) as actual, SUM(forecast_sites) as forecast FROM ndpd_data
   - "Deployment variance" → SELECT period, SUM(forecast_sites - actual_sites) as variance FROM ndpd_data GROUP BY period
   - "Achievement rate" → SELECT period, (SUM(actual_sites) * 100.0 / SUM(forecast_sites)) as achievement_pct FROM ndpd_data GROUP BY period

3. PERIOD-BASED QUERIES:
   - "2025P01 data" → SELECT * FROM ndpd_data WHERE period = '2025P01'
   - "All 2025 data" → SELECT * FROM ndpd_data WHERE period LIKE '2025%'
   - "Compare periods" → SELECT period, SUM(actual_sites), SUM(forecast_sites) FROM ndpd_data GROUP BY period

4. REGION/CARRIER QUERIES:
   - "Airtel deployments" → SELECT * FROM ndpd_data WHERE ct LIKE '%Airtel%'
   - "Kenya sites" → SELECT * FROM ndpd_data WHERE ct LIKE '%Kenya%'
   - "By region" → SELECT ct, SUM(actual_sites), SUM(forecast_sites) FROM ndpd_data GROUP BY ct

5. PERFORMANCE METRICS:
   - "Top performers" → SELECT TOP 10 ct, actual_sites, forecast_sites FROM ndpd_data WHERE actual_sites > forecast_sites ORDER BY (actual_sites - forecast_sites) DESC
   - "Underperformers" → SELECT ct, actual_sites, forecast_sites FROM ndpd_data WHERE actual_sites < forecast_sites
   - "Perfect execution" → SELECT * FROM ndpd_data WHERE actual_sites = forecast_sites

IMPORTANT:
- Use lowercase "ndpd_data" for table name (NOT "NDPD_Data" or "ndpdData")
- period column stores strings like '2025P01' (use quotes in WHERE clauses)
- ct column is case-sensitive - use LIKE with wildcards
- For percentage calculations, use: (actual * 100.0 / forecast) to avoid integer division
""",
        "metadata": {
            "type": "business_rule",
            "category": "ndpd_queries",
            "priority": "high"
        }
    })

    chunks.append({
        "content": """BUSINESS RULE: NDPD Aggregation and Analysis Patterns

Common project manager queries and their SQL patterns:

1. TOTAL DEPLOYMENTS:
   Query: "How many total sites deployed?"
   SQL: SELECT SUM(actual_sites) as total_deployed FROM ndpd_data

   Query: "Total forecast for 2025?"
   SQL: SELECT SUM(forecast_sites) as total_forecast FROM ndpd_data WHERE period LIKE '2025%'

2. VARIANCE ANALYSIS:
   Query: "What's the variance between actual and forecast?"
   SQL: SELECT
          SUM(actual_sites) as total_actual,
          SUM(forecast_sites) as total_forecast,
          SUM(forecast_sites - actual_sites) as variance,
          (SUM(actual_sites) * 100.0 / SUM(forecast_sites)) as achievement_percentage
        FROM ndpd_data

3. PERIOD COMPARISON:
   Query: "Compare P01 vs P02"
   SQL: SELECT
          period,
          SUM(actual_sites) as actual,
          SUM(forecast_sites) as forecast
        FROM ndpd_data
        WHERE period IN ('2025P01', '2025P02')
        GROUP BY period

4. TOP/BOTTOM PERFORMERS:
   Query: "Which regions exceeded forecast?"
   SQL: SELECT ct, actual_sites, forecast_sites, (actual_sites - forecast_sites) as over_delivery
        FROM ndpd_data
        WHERE actual_sites > forecast_sites
        ORDER BY over_delivery DESC

   Query: "Bottom 5 underperformers"
   SQL: SELECT TOP 5 ct, actual_sites, forecast_sites, (forecast_sites - actual_sites) as shortfall
        FROM ndpd_data
        WHERE actual_sites < forecast_sites
        ORDER BY shortfall DESC

5. CARRIER/REGION BREAKDOWN:
   Query: "Airtel performance across all regions"
   SQL: SELECT ct, SUM(actual_sites) as actual, SUM(forecast_sites) as forecast
        FROM ndpd_data
        WHERE ct LIKE '%Airtel%'
        GROUP BY ct

6. ACHIEVEMENT RATE BY CATEGORY:
   Query: "Achievement rate by carrier"
   SQL: SELECT
          CASE
            WHEN ct LIKE '%Airtel%' THEN 'Airtel'
            WHEN ct LIKE '%Libya%' THEN 'Libya'
            ELSE 'Other'
          END as carrier,
          (SUM(actual_sites) * 100.0 / SUM(forecast_sites)) as achievement_pct
        FROM ndpd_data
        GROUP BY CASE
                   WHEN ct LIKE '%Airtel%' THEN 'Airtel'
                   WHEN ct LIKE '%Libya%' THEN 'Libya'
                   ELSE 'Other'
                 END
""",
        "metadata": {
            "type": "business_rule",
            "category": "ndpd_analysis",
            "priority": "high"
        }
    })

    chunks.append({
        "content": """BUSINESS RULE: CRITICAL - NDPD is the ONLY deployment tracking table

IMPORTANT: There is NO "Regions" table, NO "Deployments" table, NO "Targets" table.
ALL deployment and forecast data is in the ndpd_data table ONLY.

When user asks about:
- "regions exceeded forecast" → Use ndpd_data (NOT a Regions table)
- "missed target" or "underperformed" → Use ndpd_data (NOT a Deployments table)
- "deployment performance" → Use ndpd_data
- Any deployment-related query → Use ndpd_data

NEVER hallucinate tables that don't exist. ONLY use ndpd_data for NDPD queries.

Correct patterns:
- "regions exceeded forecast" → SELECT ct, actual_sites, forecast_sites FROM ndpd_data WHERE actual_sites > forecast_sites
- "missed target" → SELECT * FROM ndpd_data WHERE actual_sites < forecast_sites
- "underperforming regions" → SELECT ct FROM ndpd_data WHERE actual_sites < forecast_sites ORDER BY (forecast_sites - actual_sites) DESC
""",
        "metadata": {
            "type": "business_rule",
            "category": "ndpd_critical",
            "priority": "critical"
        }
    })

    chunks.append({
        "content": """BUSINESS RULE: NDPD Column Name Recognition

When users ask questions, map these terms to correct columns:

PERIOD MAPPING:
User says → Use column
- "period", "time period", "when", "P01", "2025P01" → period
- "in 2025", "for 2025" → period LIKE '2025%'
- "period 1", "first period" → period LIKE '%P01'

CT (Category) MAPPING:
User says → Use column
- "region", "category", "carrier", "country" → ct
- "Airtel", "Kenya", "Nigeria", "Libya" → ct LIKE '%keyword%'
- "MEA", "CEWA", "deployment category" → ct

ACTUAL SITES MAPPING:
User says → Use column
- "actual", "deployed", "completed", "built", "done" → actual_sites
- "how many sites deployed", "actual deployments" → actual_sites
- "what was delivered" → actual_sites

FORECAST SITES MAPPING:
User says → Use column
- "forecast", "planned", "target", "goal", "expected" → forecast_sites
- "how many sites planned", "forecasted deployment" → forecast_sites
- "what was the plan" → forecast_sites

VARIANCE/COMPARISON MAPPING:
User says → Calculate as
- "variance", "difference", "gap" → (forecast_sites - actual_sites)
- "over-delivery", "exceeded forecast" → (actual_sites - forecast_sites) where actual > forecast
- "shortfall", "under-delivered" → (forecast_sites - actual_sites) where forecast > actual
- "achievement rate", "performance %" → (actual_sites * 100.0 / forecast_sites)

EXAMPLES:
- "Show deployed sites in Kenya" → SELECT actual_sites FROM ndpd_data WHERE ct LIKE '%Kenya%'
- "What's the target for Airtel?" → SELECT SUM(forecast_sites) FROM ndpd_data WHERE ct LIKE '%Airtel%'
- "Period 1 performance" → SELECT SUM(actual_sites), SUM(forecast_sites) FROM ndpd_data WHERE period LIKE '%P01'
""",
        "metadata": {
            "type": "business_rule",
            "category": "ndpd_terminology",
            "priority": "high"
        }
    })

    return chunks


def main():
    """Generate and save NDPD schema chunks"""
    print("="*80)
    print("GENERATING NDPD SCHEMA KNOWLEDGE CHUNKS")
    print("="*80)

    chunks = generate_ndpd_schema_chunks()

    # Save to JSON file
    output_path = Path(__file__).parent / "knowledge_base" / "ndpd_chunks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Generated {len(chunks)} NDPD schema chunks")
    print(f"[SAVED] to: {output_path}")

    # Print summary
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk['metadata'].get('type', 'unknown')
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    print("\n[STATS] Chunk Distribution:")
    for chunk_type, count in sorted(type_counts.items()):
        print(f"  {chunk_type}: {count}")

    print("\n[READY] NDPD schema chunks ready for embedding!")
    print("="*80)


if __name__ == "__main__":
    main()
