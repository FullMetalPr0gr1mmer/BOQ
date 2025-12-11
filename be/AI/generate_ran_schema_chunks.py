"""
Generate RAN-specific schema knowledge chunks for Text2SQL

This script creates high-quality schema knowledge ONLY for ZAIN RAN tables.
Optimized for precision and accuracy.

Author: Senior AI Architect
Created: 2025-12-10
"""
import json
from pathlib import Path

def generate_ran_schema_chunks():
    """Generate schema knowledge chunks for RAN tables"""

    chunks = []

    # ========================================
    # TABLE 1: ran_projects (Main project table)
    # ========================================
    chunks.append({
        "content": """TABLE: ran_projects

Primary table for ZAIN RAN (Radio Access Network) projects.

Columns:
- pid_po (STRING, PRIMARY KEY): Combined Project ID + Purchase Order (e.g., "PROJ001_PO123")
- pid (STRING, INDEXED): Project ID
- po (STRING, INDEXED): Purchase Order number
- project_name (STRING, INDEXED): Name of the RAN project

This is the MAIN table for RAN projects. Use this table when:
- User asks about "RAN projects"
- User wants to count/list RAN projects
- User wants project information (name, PID, PO)

Example queries:
- "show me all RAN projects" → SELECT * FROM ran_projects
- "how many RAN projects" → SELECT COUNT(*) FROM ran_projects
- "find RAN project with PO MW123" → SELECT * FROM ran_projects WHERE po LIKE '%MW123%'
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ran_projects",
            "priority": "high"
        }
    })

    # ========================================
    # TABLE 2: ran_inventory (Equipment inventory)
    # ========================================
    chunks.append({
        "content": """TABLE: ran_inventory

RAN equipment inventory tracking serial numbers and site assignments.

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- mrbts (STRING, INDEXED): MRBTS identifier
- site_id (STRING, INDEXED): Site ID where equipment is located
- identification_code (STRING, INDEXED): Equipment identification code
- user_label (STRING): User-assigned label
- serial_number (STRING, INDEXED): Equipment serial number
- duplicate (BOOLEAN): Flag for duplicate entries (TRUE/FALSE)
- duplicate_remarks (STRING): Notes about duplicates
- pid_po (STRING, FOREIGN KEY → ran_projects.pid_po): Project reference

Use this table when:
- User asks about "RAN inventory"
- User wants to find equipment by serial number
- User asks about site equipment
- User wants to check for duplicates

Example queries:
- "show me RAN inventory" → SELECT * FROM ran_inventory
- "find RAN inventory for site ABC123" → SELECT * FROM ran_inventory WHERE site_id = 'ABC123'
- "how many RAN inventory items" → SELECT COUNT(*) FROM ran_inventory
- "find duplicates in RAN inventory" → SELECT * FROM ran_inventory WHERE duplicate = 1
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ran_inventory"
        }
    })

    chunks.append({
        "content": """COLUMNS: ran_inventory

Detailed column information for ran_inventory table:

id: INTEGER, PRIMARY KEY, AUTO INCREMENT
  - Unique identifier for each inventory item

mrbts: STRING(200), INDEXED
  - MRBTS (Mobile Radio Base Transceiver Station) identifier
  - Search: WHERE mrbts = 'value' or WHERE mrbts LIKE '%value%'

site_id: STRING(200), INDEXED
  - Site ID where equipment is installed
  - Commonly used for filtering: WHERE site_id = 'ABC123'

identification_code: STRING(200), INDEXED
  - Equipment identification/model code

serial_number: STRING(200), INDEXED
  - Unique serial number of equipment
  - Often used for lookups: WHERE serial_number = '12345'

duplicate: BOOLEAN (0/1)
  - Flag indicating if this is a duplicate entry
  - Filter duplicates: WHERE duplicate = 1 or WHERE duplicate = 0

pid_po: STRING(200), FOREIGN KEY
  - References ran_projects.pid_po
  - Use for JOINs with ran_projects
""",
        "metadata": {
            "type": "columns",
            "table_name": "ran_inventory"
        }
    })

    # ========================================
    # TABLE 3: ranlvl3 (Level 3 BOQ items)
    # ========================================
    chunks.append({
        "content": """TABLE: ranlvl3

RAN Level 3 Bill of Quantities (BOQ) items. Main items in RAN BOQ.

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- project_id (STRING, FOREIGN KEY → ran_projects.pid_po): Project reference
- item_name (STRING, INDEXED): Name of the BOQ item
- key (STRING): Item key/code
- service_type (JSON STRING): Type of service (Software/Hardware/Service)
- uom (STRING, INDEXED): Unit of Measure
- total_quantity (INTEGER): Total quantity
- total_price (FLOAT): Total price
- po_line (STRING): Purchase order line number
- upl_line (STRING): UPL line number
- category (STRING): Item category
- ran_category (STRING): RAN-specific category

Use this table when:
- User asks about "RAN level 3" or "RAN lvl3"
- User wants BOQ items for RAN
- User asks about quantities or pricing
- User mentions "RAN items"

Example queries:
- "show me RAN level 3 items" → SELECT * FROM ranlvl3
- "how many RAN lvl3 items" → SELECT COUNT(*) FROM ranlvl3
- "RAN items for project X" → SELECT * FROM ranlvl3 WHERE project_id = 'X'
- "total RAN lvl3 quantity" → SELECT SUM(total_quantity) FROM ranlvl3
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ranlvl3",
            "priority": "high"
        }
    })

    chunks.append({
        "content": """COLUMNS: ranlvl3

Detailed column information for ranlvl3 table:

id: INTEGER, PRIMARY KEY
  - Unique identifier for level 3 item

project_id: STRING(200), FOREIGN KEY, INDEXED
  - References ran_projects.pid_po
  - Use for filtering by project: WHERE project_id = 'PROJ001_PO123'

item_name: STRING(200), INDEXED
  - Name of the BOQ item
  - Search: WHERE item_name LIKE '%keyword%'

total_quantity: INTEGER
  - Total quantity of this item
  - Aggregate: SUM(total_quantity), AVG(total_quantity)

total_price: FLOAT
  - Total price for this item
  - Aggregate: SUM(total_price), AVG(total_price)

uom: STRING(200), INDEXED
  - Unit of Measure (e.g., "Each", "Meter", "Set")

category: STRING(200)
  - General category

ran_category: STRING(100)
  - RAN-specific category classification
""",
        "metadata": {
            "type": "columns",
            "table_name": "ranlvl3"
        }
    })

    # ========================================
    # TABLE 4: items_for_ranlvl3 (Sub-items)
    # ========================================
    chunks.append({
        "content": """TABLE: items_for_ranlvl3

Sub-items under RAN Level 3. Detail breakdown of ranlvl3 items.

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- ranlvl3_id (INTEGER, FOREIGN KEY → ranlvl3.id): Parent level 3 item
- item_name (STRING, INDEXED): Sub-item name
- item_details (STRING): Detailed description
- vendor_part_number (STRING, INDEXED): Vendor part number
- service_type (JSON STRING): Service type
- category (STRING): Item category
- uom (INTEGER): Unit of measure
- quantity (INTEGER): Quantity
- price (FLOAT): Unit price
- upl_line (STRING): UPL line number

Use this table when:
- User asks about "sub-items" or "detail items"
- User wants vendor part numbers
- User needs item-level details under level 3

Example queries:
- "show me RAN sub-items" → SELECT * FROM items_for_ranlvl3
- "items under RAN lvl3 ID 5" → SELECT * FROM items_for_ranlvl3 WHERE ranlvl3_id = 5
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "items_for_ranlvl3"
        }
    })

    # ========================================
    # TABLE 5: ran_antenna_serials
    # ========================================
    chunks.append({
        "content": """TABLE: ran_antenna_serials

RAN antenna serial number tracking.

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- mrbts (STRING): MRBTS identifier
- antenna_model (STRING): Model of antenna
- serial_number (STRING): Antenna serial number
- project_id (STRING, FOREIGN KEY → ran_projects.pid_po): Project reference

Use this table when:
- User asks about "antennas" or "antenna serials"
- User wants to find antenna by serial number
- User asks "how many antennas"

Example queries:
- "show me RAN antennas" → SELECT * FROM ran_antenna_serials
- "how many RAN antennas" → SELECT COUNT(*) FROM ran_antenna_serials
- "find antenna serial 12345" → SELECT * FROM ran_antenna_serials WHERE serial_number = '12345'
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ran_antenna_serials",
            "priority": "medium"
        }
    })

    # ========================================
    # TABLE 6: ran_lld (Low Level Design)
    # ========================================
    chunks.append({
        "content": """TABLE: ran_lld (RAN Low Level Design)

RAN Low Level Design (LLD) data. This table stores low-level design information for RAN sites.

IMPORTANT: When user mentions ANY of these keywords, use ran_lld table:
- "RAN LLD"
- "RAN low level design"
- "LLD"
- "low level design"
- "show me RAN LLD"
- "RAN design"

Columns:
- id (INTEGER, PRIMARY KEY): Auto-increment ID
- site_id (STRING, INDEXED): Site ID
- new_antennas (STRING): New antennas information
- total_antennas (INTEGER): Total number of antennas
- technical_boq (STRING): Technical BOQ reference
- key (STRING): LLD key
- pid_po (STRING, FOREIGN KEY → ran_projects.pid_po): Project reference

Use this table when:
- User asks about "RAN LLD" or "low level design"
- User wants site-level design information
- User asks about antenna counts per site
- User says "show me RAN LLD"

Example queries:
- "show me RAN LLD" → SELECT * FROM ran_lld
- "show RAN LLD" → SELECT * FROM ran_lld
- "RAN LLD" → SELECT * FROM ran_lld
- "RAN LLD for site ABC" → SELECT * FROM ran_lld WHERE site_id = 'ABC'
- "total antennas in RAN LLD" → SELECT SUM(total_antennas) FROM ran_lld
- "how many RAN LLD records" → SELECT COUNT(*) FROM ran_lld
""",
        "metadata": {
            "type": "table_overview",
            "table_name": "ran_lld",
            "priority": "high"
        }
    })

    # ========================================
    # RELATIONSHIPS
    # ========================================
    chunks.append({
        "content": """RELATIONSHIP: ran_projects to ran_inventory

How to JOIN ran_projects with ran_inventory:

SELECT p.project_name, i.site_id, i.serial_number
FROM ran_projects p
INNER JOIN ran_inventory i ON p.pid_po = i.pid_po
WHERE p.project_name LIKE '%keyword%'

IMPORTANT JOIN CONDITION:
ran_projects.pid_po = ran_inventory.pid_po

Use this JOIN when:
- User wants inventory for a specific RAN project
- User asks "show me inventory for RAN project X"
""",
        "metadata": {
            "type": "relationship",
            "table_name": "ran_projects",
            "related_table": "ran_inventory"
        }
    })

    chunks.append({
        "content": """RELATIONSHIP: ran_projects to ranlvl3

How to JOIN ran_projects with ranlvl3:

SELECT p.project_name, l.item_name, l.total_quantity, l.total_price
FROM ran_projects p
INNER JOIN ranlvl3 l ON p.pid_po = l.project_id
WHERE p.project_name = 'ProjectName'

IMPORTANT JOIN CONDITION:
ran_projects.pid_po = ranlvl3.project_id

Use this JOIN when:
- User wants level 3 items for a specific RAN project
- User asks "show me RAN lvl3 for project X"
""",
        "metadata": {
            "type": "relationship",
            "table_name": "ran_projects",
            "related_table": "ranlvl3"
        }
    })

    chunks.append({
        "content": """RELATIONSHIP: ranlvl3 to items_for_ranlvl3

How to JOIN ranlvl3 with its sub-items:

SELECT l.item_name AS parent_item, i.item_name AS sub_item, i.quantity, i.price
FROM ranlvl3 l
INNER JOIN items_for_ranlvl3 i ON l.id = i.ranlvl3_id
WHERE l.project_id = 'PROJ001_PO123'

IMPORTANT JOIN CONDITION:
ranlvl3.id = items_for_ranlvl3.ranlvl3_id

Use this JOIN when:
- User wants detail breakdown of level 3 items
- User asks "show me sub-items for RAN lvl3"
""",
        "metadata": {
            "type": "relationship",
            "table_name": "ranlvl3",
            "related_table": "items_for_ranlvl3"
        }
    })

    # ========================================
    # BUSINESS RULES
    # ========================================
    chunks.append({
        "content": """BUSINESS RULE: RAN Table Selection

When user asks about RAN, use these EXACT table names (lowercase):

1. "RAN projects" → USE ran_projects table (lowercase, underscore)
2. "RAN inventory" → USE ran_inventory table (lowercase, underscore)
3. "RAN level 3" or "RAN lvl3" → USE ranlvl3 table (lowercase, no underscore)
4. "RAN antennas" → USE ran_antenna_serials table (lowercase, underscore)
5. "RAN LLD" or "show me RAN LLD" → USE ran_lld table (lowercase, underscore)

IMPORTANT TABLE NAMING:
- ALL RAN table names are lowercase
- Use underscores (ran_lld, ran_projects) NOT camelCase (RanLLD, RanProjects)
- Exception: ranlvl3 has no underscore

NEVER use non-RAN tables (projects, lvl3, inventory) when user specifically says "RAN".

Always prefix with "ran_" for RAN-specific queries.
""",
        "metadata": {
            "type": "business_rule",
            "category": "table_selection",
            "priority": "high"
        }
    })

    chunks.append({
        "content": """BUSINESS RULE: Counting in RAN

When user asks "how many" for RAN:

- "how many RAN projects" → SELECT COUNT(*) FROM ran_projects
- "how many RAN inventory items" → SELECT COUNT(*) FROM ran_inventory
- "how many RAN lvl3 items" → SELECT COUNT(*) FROM ranlvl3
- "how many RAN antennas" → SELECT COUNT(*) FROM ran_antenna_serials
- "how many RAN LLD records" → SELECT COUNT(*) FROM ran_lld

Use COUNT(*) for total records.
Use COUNT(DISTINCT column) only when explicitly needed.
""",
        "metadata": {
            "type": "business_rule",
            "category": "counting"
        }
    })

    chunks.append({
        "content": """BUSINESS RULE: SQL Server Syntax

This is a SQL Server database. Use SQL Server syntax:

✅ CORRECT:
- SELECT TOP 10 * FROM ran_projects
- SELECT * FROM ran_projects WHERE project_name LIKE '%keyword%'
- SELECT COUNT(*) FROM ran_projects

❌ WRONG:
- SELECT * FROM ran_projects LIMIT 10  (MySQL/PostgreSQL syntax)
- SELECT * FROM ran_projects WHERE project_name ILIKE '%keyword%'  (PostgreSQL)

Always use:
- TOP instead of LIMIT
- LIKE instead of ILIKE (SQL Server is case-insensitive by default)
""",
        "metadata": {
            "type": "business_rule",
            "category": "sql_syntax"
        }
    })

    return chunks


def main():
    """Generate and save RAN schema chunks"""
    print("="*80)
    print("GENERATING RAN SCHEMA KNOWLEDGE CHUNKS")
    print("="*80)

    chunks = generate_ran_schema_chunks()

    # Save to JSON file
    output_path = Path(__file__).parent / "knowledge_base" / "ran_chunks.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)

    print(f"\n[SUCCESS] Generated {len(chunks)} RAN schema chunks")
    print(f"[SAVED] to: {output_path}")

    # Print summary
    type_counts = {}
    for chunk in chunks:
        chunk_type = chunk['metadata'].get('type', 'unknown')
        type_counts[chunk_type] = type_counts.get(chunk_type, 0) + 1

    print("\n[STATS] Chunk Distribution:")
    for chunk_type, count in sorted(type_counts.items()):
        print(f"  {chunk_type}: {count}")

    print("\n[READY] RAN schema chunks ready for embedding!")
    print("="*80)


if __name__ == "__main__":
    main()
