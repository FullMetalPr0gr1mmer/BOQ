"""
Pydantic Schema Parser for Text-to-SQL RAG System

This script parses Pydantic schemas and extracts:
1. Field names and types
2. Field descriptions from Field(description=...)
3. Validation rules (Literal, Enum, constraints)
4. Default values
5. Optional/required status
6. Nested schema relationships

This provides the BUSINESS LOGIC layer that prevents misunderstandings
like "What does 'active user' mean?" or "How is revenue calculated?"

Author: Senior AI Architect
Created: 2025-11-06
"""

import ast
import inspect
import importlib
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, get_origin, get_args, Union
from dataclasses import dataclass, asdict
from pydantic import BaseModel, Field
import typing


@dataclass
class FieldInfo:
    """Structured information about a Pydantic field."""
    name: str
    type: str
    required: bool
    default: Optional[str]
    description: Optional[str]
    validation_rules: List[str]
    examples: List[str]


@dataclass
class SchemaInfo:
    """Complete information about a Pydantic schema."""
    schema_name: str
    fields: List[FieldInfo]
    docstring: Optional[str]
    module_path: str
    related_model: Optional[str]  # Link to SQLAlchemy model if exists


class PydanticParser:
    """
    Parser for Pydantic schemas.

    Extracts business logic, validation rules, and field descriptions
    to help the LLM understand what fields mean and how to use them.
    """

    def __init__(self, schemas_directory: str):
        """
        Initialize the parser.

        Args:
            schemas_directory: Path to the Schemas directory (e.g., "C:/WORK/BOQ/be/Schemas")
        """
        self.schemas_directory = Path(schemas_directory)
        self.parsed_schemas: List[SchemaInfo] = []

        # Add the parent directory to sys.path for imports
        parent_dir = str(self.schemas_directory.parent)
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)

    def find_all_schema_files(self) -> List[Path]:
        """Find all Python files in the Schemas directory."""
        schema_files = []
        for py_file in self.schemas_directory.rglob("*.py"):
            if py_file.name != "__init__.py":
                schema_files.append(py_file)
        return schema_files

    def extract_docstring(self, schema_class) -> Optional[str]:
        """Extract and clean the docstring from a schema class."""
        docstring = inspect.getdoc(schema_class)
        if docstring:
            lines = [line.strip() for line in docstring.split('\n') if line.strip()]
            return ' '.join(lines)
        return None

    def parse_field(self, field_name: str, field_info: Any, schema_class) -> FieldInfo:
        """
        Parse a Pydantic field and extract all metadata.

        This includes type, validation rules, descriptions, and constraints.
        """
        # Get field type
        field_type = self._get_field_type(field_info)

        # Check if required
        required = self._is_required(field_info)

        # Get default value
        default_val = self._get_default_value(field_info)

        # Get description from Field(description=...)
        description = self._get_field_description(field_info)

        # Extract validation rules (THIS IS CRITICAL!)
        validation_rules = self._extract_validation_rules(field_name, field_info, field_type)

        # Extract examples if available
        examples = self._extract_examples(field_info)

        return FieldInfo(
            name=field_name,
            type=field_type,
            required=required,
            default=default_val,
            description=description,
            validation_rules=validation_rules,
            examples=examples
        )

    def _get_field_type(self, field_info: Any) -> str:
        """Extract the field type as a readable string."""
        try:
            if hasattr(field_info, 'annotation'):
                annotation = field_info.annotation
            elif hasattr(field_info, 'outer_type_'):
                annotation = field_info.outer_type_
            else:
                return "Unknown"

            # Handle Optional types
            origin = get_origin(annotation)
            if origin is Union:
                args = get_args(annotation)
                # Check if it's Optional (Union with None)
                if type(None) in args:
                    non_none_types = [arg for arg in args if arg is not type(None)]
                    if len(non_none_types) == 1:
                        return f"Optional[{self._format_type(non_none_types[0])}]"

            return self._format_type(annotation)
        except:
            return "Unknown"

    def _format_type(self, type_obj) -> str:
        """Format a type object as a readable string."""
        if hasattr(type_obj, '__name__'):
            return type_obj.__name__

        # Handle generic types
        origin = get_origin(type_obj)
        args = get_args(type_obj)

        if origin is list or origin is List:
            if args:
                return f"List[{self._format_type(args[0])}]"
            return "List"
        elif origin is dict or origin is Dict:
            if args:
                return f"Dict[{self._format_type(args[0])}, {self._format_type(args[1])}]"
            return "Dict"

        return str(type_obj)

    def _is_required(self, field_info: Any) -> bool:
        """Check if a field is required."""
        if hasattr(field_info, 'is_required'):
            return field_info.is_required()
        if hasattr(field_info, 'required'):
            return field_info.required
        # Default: if no default value, it's required
        return not hasattr(field_info, 'default') or field_info.default is None

    def _get_default_value(self, field_info: Any) -> Optional[str]:
        """Extract the default value if it exists."""
        if hasattr(field_info, 'default') and field_info.default is not None:
            return str(field_info.default)
        return None

    def _get_field_description(self, field_info: Any) -> Optional[str]:
        """Extract field description from Field(description=...)."""
        if hasattr(field_info, 'description') and field_info.description:
            return field_info.description
        if hasattr(field_info, 'field_info') and hasattr(field_info.field_info, 'description'):
            return field_info.field_info.description
        return None

    def _extract_validation_rules(self, field_name: str, field_info: Any, field_type: str) -> List[str]:
        """
        Extract validation rules from a Pydantic field.

        THIS IS CRITICAL for business logic! Examples:
        - "user_status can only be 'active', 'pending', or 'disabled'"
        - "quantity must be greater than 0"
        - "email must be a valid email address"
        """
        rules = []

        # Check for Literal types (explicit allowed values)
        if hasattr(field_info, 'annotation'):
            annotation = field_info.annotation
            origin = get_origin(annotation)

            # Handle Literal types
            if str(origin) == 'typing.Literal' or (hasattr(annotation, '__origin__') and
                str(annotation.__origin__) == 'typing.Literal'):
                args = get_args(annotation)
                if args:
                    allowed_values = ', '.join([f"'{v}'" for v in args])
                    rules.append(f"Must be one of: {allowed_values}")

            # Handle List types with constraints
            if origin is list or origin is List:
                args = get_args(annotation)
                if args:
                    inner_type = args[0]
                    # Check if inner type is Literal or Enum
                    inner_origin = get_origin(inner_type)
                    if str(inner_origin) == 'typing.Literal' or (hasattr(inner_type, '__origin__') and
                        str(inner_type.__origin__) == 'typing.Literal'):
                        inner_args = get_args(inner_type)
                        if inner_args:
                            allowed_values = ', '.join([f"'{v}'" for v in inner_args])
                            rules.append(f"List values must be one of: {allowed_values}")

        # Check for Enum types
        if 'Enum' in field_type:
            rules.append(f"Must be a valid {field_type} value")

        # Check for constraints from Field()
        if hasattr(field_info, 'field_info'):
            field_obj = field_info.field_info
            if hasattr(field_obj, 'constraints'):
                constraints = field_obj.constraints
                if hasattr(constraints, 'gt') and constraints.gt is not None:
                    rules.append(f"Must be greater than {constraints.gt}")
                if hasattr(constraints, 'ge') and constraints.ge is not None:
                    rules.append(f"Must be greater than or equal to {constraints.ge}")
                if hasattr(constraints, 'lt') and constraints.lt is not None:
                    rules.append(f"Must be less than {constraints.lt}")
                if hasattr(constraints, 'le') and constraints.le is not None:
                    rules.append(f"Must be less than or equal to {constraints.le}")
                if hasattr(constraints, 'min_length') and constraints.min_length is not None:
                    rules.append(f"Minimum length: {constraints.min_length}")
                if hasattr(constraints, 'max_length') and constraints.max_length is not None:
                    rules.append(f"Maximum length: {constraints.max_length}")
                if hasattr(constraints, 'regex') and constraints.regex is not None:
                    rules.append(f"Must match pattern: {constraints.regex}")

        # Check for email validation
        if 'email' in field_name.lower() or 'Email' in field_type:
            rules.append("Must be a valid email address")

        return rules

    def _extract_examples(self, field_info: Any) -> List[str]:
        """Extract example values from field metadata."""
        examples = []
        if hasattr(field_info, 'examples') and field_info.examples:
            examples = [str(ex) for ex in field_info.examples]
        if hasattr(field_info, 'field_info'):
            field_obj = field_info.field_info
            if hasattr(field_obj, 'examples') and field_obj.examples:
                examples = [str(ex) for ex in field_obj.examples]
        return examples

    def parse_schema_file(self, file_path: Path) -> List[SchemaInfo]:
        """
        Parse a single schema file and extract all Pydantic schemas.

        Returns a list because a file can contain multiple schema classes.
        """
        schemas = []

        # Convert file path to module path
        rel_path = file_path.relative_to(self.schemas_directory.parent)
        module_path = str(rel_path.with_suffix('')).replace(os.sep, '.')

        try:
            # Import the module
            module = importlib.import_module(module_path)

            # Find all Pydantic model classes
            for name, obj in inspect.getmembers(module, inspect.isclass):
                # Check if it's a Pydantic model
                if issubclass(obj, BaseModel) and obj is not BaseModel:
                    schema_info = self._parse_schema_class(obj, module_path)
                    if schema_info:
                        schemas.append(schema_info)

        except Exception as e:
            print(f"Error parsing {file_path}: {e}")

        return schemas

    def _parse_schema_class(self, schema_class, module_path: str) -> Optional[SchemaInfo]:
        """Parse a single Pydantic schema class."""
        try:
            schema_name = schema_class.__name__
            docstring = self.extract_docstring(schema_class)

            # Try to infer related SQLAlchemy model
            related_model = self._infer_related_model(schema_name)

            # Parse all fields
            fields = []
            if hasattr(schema_class, '__fields__'):
                # Pydantic v1
                for field_name, field_info in schema_class.__fields__.items():
                    field = self.parse_field(field_name, field_info, schema_class)
                    fields.append(field)
            elif hasattr(schema_class, 'model_fields'):
                # Pydantic v2
                for field_name, field_info in schema_class.model_fields.items():
                    field = self.parse_field(field_name, field_info, schema_class)
                    fields.append(field)

            return SchemaInfo(
                schema_name=schema_name,
                fields=fields,
                docstring=docstring,
                module_path=module_path,
                related_model=related_model
            )

        except Exception as e:
            print(f"Error parsing schema class {schema_class}: {e}")
            return None

    def _infer_related_model(self, schema_name: str) -> Optional[str]:
        """
        Try to infer the related SQLAlchemy model from the schema name.

        Examples:
        - UserSchema -> User
        - CreateProject -> Project
        - Lvl3Out -> Lvl3
        """
        # Remove common suffixes
        for suffix in ['Schema', 'Create', 'Update', 'Base', 'Out', 'Response', 'Request']:
            if schema_name.endswith(suffix):
                return schema_name[:-len(suffix)]

        return schema_name

    def parse_all_schemas(self) -> List[SchemaInfo]:
        """
        Parse all Pydantic schemas in the Schemas directory.

        Returns a complete list of SchemaInfo objects.
        """
        schema_files = self.find_all_schema_files()
        print(f"Found {len(schema_files)} schema files")

        all_schemas = []
        for file_path in schema_files:
            print(f"Parsing {file_path.name}...")
            schemas = self.parse_schema_file(file_path)
            all_schemas.extend(schemas)

        self.parsed_schemas = all_schemas
        print(f"\nSuccessfully parsed {len(all_schemas)} schemas")
        return all_schemas

    def format_for_embedding(self, schema_info: SchemaInfo) -> List[Dict[str, Any]]:
        """
        Format a SchemaInfo object into text chunks ready for embedding.

        We create business logic chunks that explain:
        1. What each field means
        2. What values are allowed
        3. Validation rules
        """
        chunks = []

        # Chunk 1: Schema Overview
        overview = f"""
SCHEMA: {schema_info.schema_name}
MODULE: {schema_info.module_path}
RELATED MODEL: {schema_info.related_model or 'Unknown'}

DESCRIPTION:
{schema_info.docstring or 'No description available'}

FIELDS:
{self._format_fields_summary(schema_info.fields)}
"""
        chunks.append({
            "content": overview.strip(),
            "metadata": {
                "type": "schema_overview",
                "schema_name": schema_info.schema_name,
                "related_model": schema_info.related_model
            }
        })

        # Chunk 2: Business Logic Rules (CRITICAL!)
        business_rules = []
        for field in schema_info.fields:
            if field.validation_rules or field.description:
                rule = self._format_business_rule(field, schema_info.schema_name)
                business_rules.append(rule)

        if business_rules:
            rules_chunk = f"""
SCHEMA: {schema_info.schema_name}
RELATED MODEL: {schema_info.related_model or 'Unknown'}

BUSINESS LOGIC RULES:

{chr(10).join(business_rules)}
"""
            chunks.append({
                "content": rules_chunk.strip(),
                "metadata": {
                    "type": "business_rules",
                    "schema_name": schema_info.schema_name,
                    "related_model": schema_info.related_model
                }
            })

        return chunks

    def _format_fields_summary(self, fields: List[FieldInfo]) -> str:
        """Format a brief summary of all fields."""
        lines = []
        for field in fields:
            req_str = "REQUIRED" if field.required else "OPTIONAL"
            default_str = f" (default: {field.default})" if field.default else ""
            lines.append(f"  - {field.name}: {field.type} [{req_str}]{default_str}")

        return '\n'.join(lines)

    def _format_business_rule(self, field: FieldInfo, schema_name: str) -> str:
        """
        Format a business rule for a field.

        This is what prevents the LLM from misunderstanding business logic!
        """
        rule = f"\nFIELD: {field.name} ({field.type})\n"

        if field.description:
            rule += f"  Description: {field.description}\n"

        if field.validation_rules:
            rule += f"  Validation Rules:\n"
            for validation in field.validation_rules:
                rule += f"    - {validation}\n"

        if field.examples:
            rule += f"  Examples: {', '.join(field.examples)}\n"

        if not field.required and field.default:
            rule += f"  Default Value: {field.default}\n"

        return rule

    def export_to_json(self, output_path: str):
        """Export all parsed schemas to JSON format."""
        import json

        data = [asdict(schema) for schema in self.parsed_schemas]

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(data)} schemas to {output_path}")

    def export_chunks_for_embedding(self, output_path: str):
        """
        Export all chunks in a format ready for embedding.

        This is the primary output for Task 2 (vectorization).
        """
        import json

        all_chunks = []
        for schema in self.parsed_schemas:
            chunks = self.format_for_embedding(schema)
            all_chunks.extend(chunks)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)

        print(f"Exported {len(all_chunks)} chunks to {output_path}")
        return all_chunks


def main():
    """Example usage of the Pydantic parser."""

    # Configure paths
    SCHEMAS_DIR = "C:/WORK/BOQ/be/Schemas"
    OUTPUT_JSON = "C:/WORK/BOQ/be/AI/knowledge_base/pydantic_schemas.json"
    OUTPUT_CHUNKS = "C:/WORK/BOQ/be/AI/knowledge_base/pydantic_chunks.json"

    # Create parser
    parser = PydanticParser(SCHEMAS_DIR)

    # Parse all schemas
    schemas = parser.parse_all_schemas()

    # Print summary
    print("\n" + "="*80)
    print("PARSING SUMMARY")
    print("="*80)

    for schema in schemas:
        print(f"\nSchema: {schema.schema_name}")
        print(f"  Related Model: {schema.related_model or 'Unknown'}")
        print(f"  Fields: {len(schema.fields)}")

        # Show business rules
        rules_count = sum(1 for f in schema.fields if f.validation_rules)
        if rules_count > 0:
            print(f"  Business Rules: {rules_count} fields with validation")

    # Export results
    parser.export_to_json(OUTPUT_JSON)
    parser.export_chunks_for_embedding(OUTPUT_CHUNKS)

    print("\n" + "="*80)
    print("PARSING COMPLETE!")
    print("="*80)


if __name__ == "__main__":
    main()
