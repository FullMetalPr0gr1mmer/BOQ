"""
SQLAlchemy Model Parser for Text-to-SQL RAG System

This script parses SQLAlchemy models and extracts:
1. Table names
2. Columns (name, type, nullable, default, primary_key, etc.)
3. Foreign keys with explicit join conditions
4. Relationships with target models and join paths
5. Enums and their values
6. Docstrings and inline comments

This is CRITICAL for preventing hallucinations and wrong joins.

Author: Senior AI Architect
Created: 2025-11-06
"""

import ast
import inspect
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from sqlalchemy import Column, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.inspection import inspect as sqla_inspect


@dataclass
class ColumnInfo:
    """Structured information about a database column."""
    name: str
    type: str
    nullable: bool
    primary_key: bool
    foreign_key: Optional[str]
    default: Optional[str]
    unique: bool
    indexed: bool
    description: Optional[str]


@dataclass
class RelationshipInfo:
    """Structured information about a SQLAlchemy relationship."""
    name: str
    target_model: str
    join_condition: str  # CRITICAL: Explicit join path
    back_populates: Optional[str]
    relationship_type: str  # "one-to-many", "many-to-one", "many-to-many"
    cascade: Optional[str]


@dataclass
class TableInfo:
    """Complete information about a database table."""
    table_name: str
    model_name: str
    columns: List[ColumnInfo]
    relationships: List[RelationshipInfo]
    enums: Dict[str, List[str]]
    docstring: Optional[str]
    module_path: str


class SQLAlchemyParser:
    """
    Parser for SQLAlchemy models.

    This class dynamically loads SQLAlchemy models and extracts all metadata
    needed for accurate Text-to-SQL generation.
    """

    def __init__(self, models_directory: str):
        """
        Initialize the parser.

        Args:
            models_directory: Path to the Models directory (e.g., "C:/WORK/BOQ/be/Models")
        """
        self.models_directory = Path(models_directory)
        self.parsed_tables: List[TableInfo] = []

        # Add the parent directory to sys.path for imports
        parent_dir = str(self.models_directory.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

    def find_all_model_files(self) -> List[Path]:
        """Find all Python files in the Models directory."""
        model_files = []
        for py_file in self.models_directory.rglob("*.py"):
            if py_file.name != "__init__.py":
                model_files.append(py_file)
        return model_files

    def extract_docstring(self, model_class) -> Optional[str]:
        """Extract and clean the docstring from a model class."""
        docstring = inspect.getdoc(model_class)
        if docstring:
            # Clean up the docstring
            lines = [line.strip() for line in docstring.split('\n') if line.strip()]
            return ' '.join(lines)
        return None

    def parse_column(self, column_name: str, column_obj, model_class) -> ColumnInfo:
        """
        Parse a SQLAlchemy Column object.

        Extracts all metadata including type, constraints, and foreign keys.
        """
        # Get column type
        col_type = str(column_obj.type)

        # Check for foreign key
        foreign_key = None
        if column_obj.foreign_keys:
            fk = list(column_obj.foreign_keys)[0]
            foreign_key = f"{fk.column.table.name}.{fk.column.name}"

        # Extract default value
        default_val = None
        if column_obj.default is not None:
            default_val = str(column_obj.default.arg) if hasattr(column_obj.default, 'arg') else str(column_obj.default)

        # Try to extract description from docstring or comments
        description = self._extract_column_description(model_class, column_name)

        return ColumnInfo(
            name=column_name,
            type=col_type,
            nullable=column_obj.nullable,
            primary_key=column_obj.primary_key,
            foreign_key=foreign_key,
            default=default_val,
            unique=column_obj.unique or False,
            indexed=column_obj.index or False,
            description=description
        )

    def _extract_column_description(self, model_class, column_name: str) -> Optional[str]:
        """
        Extract column description from model docstring.

        Looks for patterns like "column_name (type): Description"
        """
        docstring = inspect.getdoc(model_class)
        if not docstring:
            return None

        # Simple heuristic: look for lines containing the column name
        for line in docstring.split('\n'):
            if column_name in line and ':' in line:
                parts = line.split(':', 1)
                if len(parts) == 2:
                    return parts[1].strip()
        return None

    def parse_relationship(self, rel_name: str, rel_property, model_class) -> Optional[RelationshipInfo]:
        """
        Parse a SQLAlchemy relationship.

        This is CRITICAL for preventing wrong joins. We extract:
        1. The target model
        2. The explicit join condition (foreign key mapping)
        3. The relationship type (one-to-many, many-to-one)
        """
        try:
            # Get the mapper
            mapper = rel_property.mapper
            target_model = mapper.class_.__name__

            # Determine relationship type
            relationship_type = "many-to-one"  # default
            if rel_property.uselist:
                relationship_type = "one-to-many"

            # Extract the join condition (CRITICAL!)
            join_condition = self._extract_join_condition(rel_property, model_class)

            # Get back_populates
            back_populates = rel_property.back_populates if hasattr(rel_property, 'back_populates') else None

            # Get cascade
            cascade = str(rel_property.cascade) if hasattr(rel_property, 'cascade') else None

            return RelationshipInfo(
                name=rel_name,
                target_model=target_model,
                join_condition=join_condition,
                back_populates=back_populates,
                relationship_type=relationship_type,
                cascade=cascade
            )
        except Exception as e:
            print(f"Warning: Could not parse relationship {rel_name}: {e}")
            return None

    def _extract_join_condition(self, rel_property, model_class) -> str:
        """
        Extract the explicit JOIN condition from a relationship.

        Example output: "User.id == AuditLog.user_id"

        This is THE MOST CRITICAL function for preventing wrong joins!
        """
        try:
            # Get the mapper and target mapper
            mapper = sqla_inspect(model_class)
            rel_mapper = rel_property.mapper

            # Get the join condition pairs
            local_remote_pairs = rel_property.local_remote_pairs

            if local_remote_pairs:
                conditions = []
                for local_col, remote_col in local_remote_pairs:
                    local_name = f"{mapper.class_.__name__}.{local_col.name}"
                    remote_name = f"{rel_mapper.class_.__name__}.{remote_col.name}"
                    conditions.append(f"{local_name} == {remote_name}")
                return " AND ".join(conditions)

            # Fallback: try to infer from foreign keys
            return self._infer_join_from_foreign_keys(model_class, rel_property)

        except Exception as e:
            print(f"Warning: Could not extract join condition: {e}")
            return "JOIN condition could not be determined"

    def _infer_join_from_foreign_keys(self, model_class, rel_property) -> str:
        """Fallback method to infer join condition from foreign keys."""
        try:
            mapper = sqla_inspect(model_class)
            target_mapper = rel_property.mapper

            # Look for foreign keys pointing to the target table
            for col in mapper.columns:
                if col.foreign_keys:
                    for fk in col.foreign_keys:
                        if fk.column.table.name == target_mapper.tables[0].name:
                            return f"{model_class.__name__}.{col.name} == {target_mapper.class_.__name__}.{fk.column.name}"

            return "JOIN condition unknown"
        except:
            return "JOIN condition unknown"

    def extract_enums_from_file(self, file_path: Path) -> Dict[str, List[str]]:
        """
        Extract enum definitions from a Python file using AST parsing.

        This allows us to capture business logic like "status can only be active, pending, or disabled"
        """
        enums = {}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Check if it's an Enum class
                    is_enum = any(
                        isinstance(base, ast.Name) and base.id == 'Enum'
                        for base in node.bases
                    )
                    if is_enum:
                        enum_name = node.name
                        enum_values = []

                        for item in node.body:
                            if isinstance(item, ast.Assign):
                                for target in item.targets:
                                    if isinstance(target, ast.Name):
                                        enum_values.append(target.id)

                        enums[enum_name] = enum_values
        except Exception as e:
            print(f"Warning: Could not extract enums from {file_path}: {e}")

        return enums

    def parse_model_file(self, file_path: Path) -> List[TableInfo]:
        """
        Parse a single model file and extract all tables.

        Returns a list because a file can contain multiple model classes.
        """
        tables = []

        # Extract enums first
        enums = self.extract_enums_from_file(file_path)

        # Convert file path to module path
        rel_path = file_path.relative_to(self.models_directory.parent)
        module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Find all SQLAlchemy model classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a SQLAlchemy model
                if hasattr(obj, '__tablename__') and hasattr(obj, '__table__'):
                    table_info = self._parse_model_class(obj, enums, module_path)
                    if table_info:
                        tables.append(table_info)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return tables

    def _parse_model_class(self, model_class, enums: Dict, module_path: str) -> Optional[TableInfo]:
        """Parse a single SQLAlchemy model class."""
        try:
            # Get table name
            table_name = model_class.__tablename__
            model_name = model_class.__name__

            # Get docstring
            docstring = self.extract_docstring(model_class)

            # Parse columns
            columns = []
            mapper = sqla_inspect(model_class)
            for col in mapper.columns:
                column_info = self.parse_column(col.name, col, model_class)
                columns.append(column_info)

            # Parse relationships (CRITICAL for joins!)
            relationships = []
            for rel_name, rel_property in mapper.relationships.items():
                rel_info = self.parse_relationship(rel_name, rel_property, model_class)
                if rel_info:
                    relationships.append(rel_info)

            return TableInfo(
                table_name=table_name,
                model_name=model_name,
                columns=columns,
                relationships=relationships,
                enums=enums,
                docstring=docstring,
                module_path=module_path
            )

        except Exception as e:
            print(f"Error parsing model class {model_class}: {e}")
            return None

    def parse_all_models(self) -> List[TableInfo]:
        """
        Parse all SQLAlchemy models in the Models directory.

        Uses a two-pass approach:
        1. Import all model files first (registers tables with SQLAlchemy)
        2. Then parse the registered classes (resolves all relationships)

        This prevents errors from circular dependencies and forward references.

        Returns a complete list of TableInfo objects.
        """
        model_files = self.find_all_model_files()
        print(f"Found {len(model_files)} model files")

        # PASS 1: Import all modules first to register all tables
        print("\n[PASS 1] Importing all models to register tables...")
        imported_modules = []
        for file_path in model_files:
            try:
                rel_path = file_path.relative_to(self.models_directory.parent)
                module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')
                module = importlib.import_module(module_path)
                imported_modules.append((file_path, module, module_path))
                print(f"  [OK] Imported {file_path.name}")
            except Exception as e:
                print(f"  [ERROR] Failed to import {file_path.name}: {e}")

        # PASS 2: Now parse all the registered classes
        print(f"\n[PASS 2] Parsing {len(imported_modules)} imported modules...")
        all_tables = []
        for file_path, module, module_path in imported_modules:
            print(f"Parsing {file_path.name}...")

            # Extract enums
            enums = self.extract_enums_from_file(file_path)

            # Find all SQLAlchemy model classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a SQLAlchemy model
                if hasattr(obj, '__tablename__') and hasattr(obj, '__table__'):
                    table_info = self._parse_model_class(obj, enums, module_path)
                    if table_info:
                        all_tables.append(table_info)
                        print(f"  [OK] Parsed table: {table_info.table_name}")

        self.parsed_tables = all_tables
        print(f"\nSuccessfully parsed {len(all_tables)} tables")
        return all_tables

    def format_for_embedding(self, table_info: TableInfo) -> List[Dict[str, Any]]:
        """
        Format a TableInfo object into text chunks ready for embedding.

        We create multiple chunks per table:
        1. Table overview chunk
        2. Column details chunks
        3. Relationship/join chunks (CRITICAL!)

        This granular chunking allows precise retrieval.
        """
        chunks = []

        # Chunk 1: Table Overview
        overview = f"""
TABLE: {table_info.table_name}
MODEL: {table_info.model_name}
MODULE: {table_info.module_path}

DESCRIPTION:
{table_info.docstring or 'No description available'}

COLUMNS:
{self._format_columns_summary(table_info.columns)}
"""
        chunks.append({
            "content": overview.strip(),
            "metadata": {
                "type": "table_overview",
                "table_name": table_info.table_name,
                "model_name": table_info.model_name
            }
        })

        # Chunk 2: Detailed Column Information (one chunk with all columns)
        column_details = f"TABLE: {table_info.table_name}\n\nCOLUMN DETAILS:\n\n"
        for col in table_info.columns:
            column_details += self._format_column_detail(col, table_info.table_name)

        chunks.append({
            "content": column_details.strip(),
            "metadata": {
                "type": "columns",
                "table_name": table_info.table_name
            }
        })

        # Chunk 3: Relationships and JOIN paths (CRITICAL for preventing wrong joins!)
        if table_info.relationships:
            for rel in table_info.relationships:
                join_chunk = f"""
TABLE: {table_info.table_name}
MODEL: {table_info.model_name}

RELATIONSHIP: {rel.name}
TYPE: {rel.relationship_type}
TARGET MODEL: {rel.target_model}

JOIN CONDITION:
{rel.join_condition}

BACK POPULATES: {rel.back_populates or 'None'}
CASCADE: {rel.cascade or 'None'}

USAGE EXAMPLE:
SELECT * FROM {table_info.table_name}
JOIN {rel.target_model.lower() + 's'} ON {rel.join_condition}
"""
                chunks.append({
                    "content": join_chunk.strip(),
                    "metadata": {
                        "type": "relationship",
                        "table_name": table_info.table_name,
                        "target_model": rel.target_model,
                        "relationship_name": rel.name
                    }
                })

        # Chunk 4: Enums (business logic constraints)
        if table_info.enums:
            for enum_name, enum_values in table_info.enums.items():
                enum_chunk = f"""
TABLE: {table_info.table_name}
ENUM: {enum_name}

ALLOWED VALUES:
{', '.join(enum_values)}

BUSINESS RULE:
The {enum_name} field can only contain one of these values: {', '.join(enum_values)}

EXAMPLE SQL:
WHERE {enum_name.lower()} IN ({', '.join([f"'{v}'" for v in enum_values])})
"""
                chunks.append({
                    "content": enum_chunk.strip(),
                    "metadata": {
                        "type": "enum",
                        "table_name": table_info.table_name,
                        "enum_name": enum_name
                    }
                })

        return chunks

    def _format_columns_summary(self, columns: List[ColumnInfo]) -> str:
        """Format a brief summary of all columns."""
        lines = []
        for col in columns:
            constraints = []
            if col.primary_key:
                constraints.append("PRIMARY KEY")
            if col.foreign_key:
                constraints.append(f"FK -> {col.foreign_key}")
            if col.unique:
                constraints.append("UNIQUE")
            if not col.nullable:
                constraints.append("NOT NULL")

            constraint_str = f" [{', '.join(constraints)}]" if constraints else ""
            lines.append(f"  - {col.name}: {col.type}{constraint_str}")

        return '\n'.join(lines)

    def _format_column_detail(self, col: ColumnInfo, table_name: str) -> str:
        """Format detailed information about a single column."""
        detail = f"COLUMN: {table_name}.{col.name}\n"
        detail += f"  Type: {col.type}\n"
        detail += f"  Nullable: {col.nullable}\n"

        if col.primary_key:
            detail += f"  Primary Key: Yes\n"
        if col.foreign_key:
            detail += f"  Foreign Key: References {col.foreign_key}\n"
        if col.unique:
            detail += f"  Unique: Yes\n"
        if col.indexed:
            detail += f"  Indexed: Yes\n"
        if col.default:
            detail += f"  Default: {col.default}\n"
        if col.description:
            detail += f"  Description: {col.description}\n"

        detail += "\n"
        return detail

    def export_to_json(self, output_path: str):
        """Export all parsed tables to JSON format."""
        import json

        data = [asdict(table) for table in self.parsed_tables]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(data)} tables to {output_path}")

    def export_chunks_for_embedding(self, output_path: str):
        """
        Export all chunks in a format ready for embedding.

        This is the primary output for Task 2 (vectorization).
        """
        import json

        all_chunks = []
        for table in self.parsed_tables:
            chunks = self.format_for_embedding(table)
            all_chunks.extend(chunks)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(all_chunks)} chunks to {output_path}")
        return all_chunks


def main():
    """Example usage of the SQLAlchemy parser."""

    # Configure paths
    MODELS_DIR = "C:/WORK/BOQ/be/Models"
    OUTPUT_JSON = "C:/WORK/BOQ/be/AI/knowledge_base/sqlalchemy_tables.json"
    OUTPUT_CHUNKS = "C:/WORK/BOQ/be/AI/knowledge_base/sqlalchemy_chunks.json"

    # Create parser
    parser = SQLAlchemyParser(MODELS_DIR)

    # Parse all models
    tables = parser.parse_all_models()

    # Print summary
    print("\n" + "="*80)
    print("PARSING SUMMARY")
    print("="*80)

    for table in tables:
        print(f"\nTable: {table.table_name} ({table.model_name})")
        print(f"  Columns: {len(table.columns)}")
        print(f"  Relationships: {len(table.relationships)}")
        print(f"  Enums: {len(table.enums)}")

        # Show relationships (critical for joins)
        if table.relationships:
            print(f"  Join Paths:")
            for rel in table.relationships:
                print(f"    - {rel.name} -> {rel.target_model}: {rel.join_condition}")

    # Export results
    parser.export_to_json(OUTPUT_JSON)
    parser.export_chunks_for_embedding(OUTPUT_CHUNKS)

    print("\n" + "="*80)
    print("PARSING COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
