"""
Main Parser Script - Task 1 Complete Solution

This script runs both parsers (SQLAlchemy + Pydantic) and the business glossary
to create a complete knowledge base for the Text-to-SQL RAG system.

Usage:
    python parse_all.py

Output:
    - sqlalchemy_tables.json: Structured SQLAlchemy model data
    - sqlalchemy_chunks.json: Text chunks ready for embedding
    - pydantic_schemas.json: Structured Pydantic schema data
    - pydantic_chunks.json: Business logic chunks ready for embedding
    - business_logic_chunks.json: Parsed business glossary chunks
    - all_chunks_combined.json: ALL chunks combined for Task 2

Author: Senior AI Architect
Created: 2025-11-06
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from AI.parsers.sqlalchemy_parser import SQLAlchemyParser
from AI.parsers.pydantic_parser import PydanticParser


class BusinessLogicParser:
    """
    Parser for the business logic glossary.

    Converts the human-written glossary into chunks for embedding.
    """

    def __init__(self, glossary_path: str):
        self.glossary_path = Path(glossary_path)

    def parse_glossary(self) -> List[Dict[str, Any]]:
        """Parse the business logic glossary file."""
        chunks = []

        try:
            with open(self.glossary_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Split by the separator '---'
            entries = content.split('---')

            for entry in entries:
                entry = entry.strip()
                if not entry or 'TERM:' not in entry:
                    continue

                # Parse the entry
                lines = entry.split('\n')
                term = None
                definition = None
                sql_example = None
                tables_involved = None

                current_section = None
                current_content = []

                for line in lines:
                    line_stripped = line.strip()

                    if line_stripped.startswith('TERM:'):
                        term = line_stripped.replace('TERM:', '').strip()
                        current_section = 'term'
                    elif line_stripped.startswith('DEFINITION:'):
                        if current_content and current_section:
                            self._save_section(current_section, current_content, locals())
                        definition = line_stripped.replace('DEFINITION:', '').strip()
                        current_section = 'definition'
                        current_content = [definition] if definition else []
                    elif line_stripped.startswith('SQL EXAMPLE:'):
                        if current_content and current_section:
                            self._save_section(current_section, current_content, locals())
                        current_section = 'sql'
                        current_content = []
                    elif line_stripped.startswith('TABLES INVOLVED:'):
                        if current_content and current_section:
                            self._save_section(current_section, current_content, locals())
                        tables_involved = line_stripped.replace('TABLES INVOLVED:', '').strip()
                        current_section = 'tables'
                    elif line_stripped.startswith('NOTE:'):
                        # Skip notes for now
                        continue
                    elif line_stripped and current_section:
                        current_content.append(line_stripped)

                # Save the last section
                if current_content and current_section:
                    if current_section == 'definition':
                        definition = ' '.join(current_content)
                    elif current_section == 'sql':
                        sql_example = '\n'.join(current_content)

                # Create chunk if we have a valid term
                if term and definition:
                    chunk_content = f"""
BUSINESS RULE: {term}

DEFINITION:
{definition}

SQL EXAMPLE:
{sql_example or 'Not provided'}

TABLES INVOLVED:
{tables_involved or 'Not specified'}
"""
                    chunks.append({
                        "content": chunk_content.strip(),
                        "metadata": {
                            "type": "business_rule",
                            "term": term,
                            "tables": tables_involved.split(', ') if tables_involved else []
                        }
                    })

        except Exception as e:
            print(f"Error parsing business glossary: {e}")

        return chunks

    def _save_section(self, section, content, local_vars):
        """Helper to save section content."""
        if section == 'definition':
            local_vars['definition'] = ' '.join(content)
        elif section == 'sql':
            local_vars['sql_example'] = '\n'.join(content)


def main():
    """
    Main function to run all parsers and create the complete knowledge base.
    """
    print("="*80)
    print("TEXT-TO-SQL KNOWLEDGE BASE PARSER - TASK 1")
    print("="*80)
    print()

    # Configure paths
    BASE_DIR = Path(__file__).parent.parent.parent
    MODELS_DIR = BASE_DIR / "Models"
    SCHEMAS_DIR = BASE_DIR / "Schemas"
    GLOSSARY_PATH = BASE_DIR / "AI" / "knowledge_base" / "business_logic_glossary.txt"
    OUTPUT_DIR = BASE_DIR / "AI" / "knowledge_base"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ==========================================================================
    # STEP 1: Parse SQLAlchemy Models
    # ==========================================================================
    print("\n" + "="*80)
    print("STEP 1: PARSING SQLALCHEMY MODELS")
    print("="*80)

    sqlalchemy_parser = SQLAlchemyParser(str(MODELS_DIR))
    sqlalchemy_tables = sqlalchemy_parser.parse_all_models()

    # Export SQLAlchemy results
    sqlalchemy_parser.export_to_json(str(OUTPUT_DIR / "sqlalchemy_tables.json"))
    sqlalchemy_chunks = sqlalchemy_parser.export_chunks_for_embedding(
        str(OUTPUT_DIR / "sqlalchemy_chunks.json")
    )

    print(f"\n[OK] Parsed {len(sqlalchemy_tables)} tables")
    print(f"[OK] Created {len(sqlalchemy_chunks)} SQLAlchemy chunks")

    # ==========================================================================
    # STEP 2: Parse Pydantic Schemas
    # ==========================================================================
    print("\n" + "="*80)
    print("STEP 2: PARSING PYDANTIC SCHEMAS")
    print("="*80)

    pydantic_parser = PydanticParser(str(SCHEMAS_DIR))
    pydantic_schemas = pydantic_parser.parse_all_schemas()

    # Export Pydantic results
    pydantic_parser.export_to_json(str(OUTPUT_DIR / "pydantic_schemas.json"))
    pydantic_chunks = pydantic_parser.export_chunks_for_embedding(
        str(OUTPUT_DIR / "pydantic_chunks.json")
    )

    print(f"\n[OK] Parsed {len(pydantic_schemas)} schemas")
    print(f"[OK] Created {len(pydantic_chunks)} Pydantic chunks")

    # ==========================================================================
    # STEP 3: Parse Business Logic Glossary
    # ==========================================================================
    print("\n" + "="*80)
    print("STEP 3: PARSING BUSINESS LOGIC GLOSSARY")
    print("="*80)

    business_parser = BusinessLogicParser(str(GLOSSARY_PATH))
    business_chunks = business_parser.parse_glossary()

    # Export business logic chunks
    with open(OUTPUT_DIR / "business_logic_chunks.json", 'w', encoding='utf-8') as f:
        json.dump(business_chunks, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Parsed {len(business_chunks)} business rules")

    # ==========================================================================
    # STEP 4: Combine All Chunks
    # ==========================================================================
    print("\n" + "="*80)
    print("STEP 4: COMBINING ALL CHUNKS")
    print("="*80)

    all_chunks = sqlalchemy_chunks + pydantic_chunks + business_chunks

    # Export combined chunks (THIS IS THE PRIMARY OUTPUT FOR TASK 2!)
    with open(OUTPUT_DIR / "all_chunks_combined.json", 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Total chunks created: {len(all_chunks)}")
    print(f"  - SQLAlchemy chunks: {len(sqlalchemy_chunks)}")
    print(f"  - Pydantic chunks: {len(pydantic_chunks)}")
    print(f"  - Business logic chunks: {len(business_chunks)}")

    # ==========================================================================
    # STEP 5: Generate Summary Report
    # ==========================================================================
    print("\n" + "="*80)
    print("SUMMARY REPORT")
    print("="*80)

    # Count different chunk types
    chunk_types = {}
    for chunk in all_chunks:
        chunk_type = chunk['metadata']['type']
        chunk_types[chunk_type] = chunk_types.get(chunk_type, 0) + 1

    print("\nChunk Distribution:")
    for chunk_type, count in sorted(chunk_types.items()):
        print(f"  - {chunk_type}: {count}")

    print("\nTables with Relationships:")
    tables_with_joins = [t for t in sqlalchemy_tables if t.relationships]
    print(f"  {len(tables_with_joins)} out of {len(sqlalchemy_tables)} tables have relationships")

    if tables_with_joins:
        print("\n  Sample Join Paths:")
        for table in tables_with_joins[:3]:
            print(f"    - {table.table_name}:")
            for rel in table.relationships[:2]:
                print(f"      -> {rel.name}: {rel.join_condition}")

    print("\nBusiness Rules Coverage:")
    tables_in_rules = set()
    for chunk in business_chunks:
        if 'tables' in chunk['metadata']:
            tables_in_rules.update(chunk['metadata']['tables'])
    print(f"  {len(tables_in_rules)} tables covered by business rules")

    # ==========================================================================
    # FINAL OUTPUT
    # ==========================================================================
    print("\n" + "="*80)
    print("TASK 1 COMPLETE! [SUCCESS]")
    print("="*80)
    print(f"\nOutput files created in: {OUTPUT_DIR}")
    print("\nFiles ready for Task 2 (Vectorization):")
    print(f"  - all_chunks_combined.json ({len(all_chunks)} chunks)")
    print("\nYou can now proceed to Task 2: Build the RAG System")
    print("="*80)


if __name__ == "__main__":
    main()
