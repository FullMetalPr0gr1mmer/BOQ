"""
Text-to-SQL Generator - Task 3 Implementation

This module implements the complete query pipeline for Text-to-SQL generation:
1. Two-stage retrieval (identify tables → fetch detailed schema)
2. Context assembly (organize chunks by type)
3. Prompt construction for Llama 3.1
4. SQL generation with validation

This is the main interface for converting natural language to SQL.


Created: 2025-11-06
"""
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from AI.text2sql_vectorstore import get_text2sql_vector_store
from AI.ollama_client import get_ollama_client
from AI.feedback_loop import get_examples_for_question

logger = logging.getLogger(__name__)


@dataclass
class Text2SQLResult:
    """Result of Text-to-SQL generation."""
    sql: str
    confidence: float
    retrieved_context: Dict[str, Any]
    execution_ready: bool
    errors: List[str]


class Text2SQLGenerator:
    """
    Complete Text-to-SQL generation pipeline.

    This class orchestrates:
    - Retrieval of relevant schema knowledge
    - Context assembly and formatting
    - Prompt construction
    - SQL generation via Llama 3.1
    - Validation and error handling
    """

    def __init__(
        self,
        vector_store=None,
        llm_client=None,
        temperature: float = 0.05,  # Very low temperature for deterministic SQL (REDUCED from 0.1)
        max_context_chunks: int = 5  # REDUCED from 15 to 5 for precision - less noise!
    ):
        """
        Initialize Text2SQL generator.

        Args:
            vector_store: Text2SQLVectorStore instance
            llm_client: OllamaClient instance
            temperature: LLM temperature (0-1, lower = more deterministic)
            max_context_chunks: Maximum context chunks to retrieve
        """
        self.vector_store = vector_store or get_text2sql_vector_store()
        self.llm_client = llm_client or get_ollama_client()
        self.temperature = temperature
        self.max_context_chunks = max_context_chunks

    def generate_sql(
        self,
        question: str,
        database: str = "SQL Server",
        validate: bool = True
    ) -> Text2SQLResult:
        """
        Generate SQL from natural language question.

        This is the main entry point for Text-to-SQL generation.

        Args:
            question: Natural language question
            database: Database type (for SQL dialect)
            validate: Whether to validate generated SQL

        Returns:
            Text2SQLResult with generated SQL and metadata
        """
        logger.info(f"Generating SQL for question: {question}")

        # Stage 1: Identify relevant tables
        relevant_tables = self._identify_relevant_tables(question)
        logger.info(f"Identified relevant tables: {relevant_tables}")

        # Stage 2: Fetch detailed context
        context = self._fetch_detailed_context(question, relevant_tables)
        logger.info(f"Retrieved {len(context['all_chunks'])} context chunks")

        # Stage 3: Assemble context for prompt
        formatted_context = self._format_context_for_prompt(context)

        # Stage 3.5: Get few-shot examples (feedback loop)
        few_shot_examples = get_examples_for_question(question, limit=3)

        # Stage 4: Build prompt
        prompt = self._build_prompt(question, formatted_context, database, few_shot_examples)

        # Stage 5: Generate SQL
        sql = self._generate_sql_with_llm(prompt)
        logger.info(f"Generated SQL: {sql[:100]}...")

        # Stage 6: Validate (optional)
        errors = []
        execution_ready = True
        if validate:
            errors = self._validate_sql(sql)
            execution_ready = len(errors) == 0

        # Calculate confidence (simple heuristic)
        confidence = self._calculate_confidence(context, sql, errors)

        return Text2SQLResult(
            sql=sql,
            confidence=confidence,
            retrieved_context=context,
            execution_ready=execution_ready,
            errors=errors
        )

    def _identify_relevant_tables(
        self,
        question: str,
        max_tables: int = 2  # REDUCED from 5 to 2 for precision - focus on most relevant!
    ) -> List[str]:
        """
        Stage 1: Identify which tables are relevant to the question.

        Uses a multi-strategy approach:
        1. Semantic search with HIGH threshold (ensures precision)
        2. Keyword extraction (handles direct table name mentions)

        Args:
            question: User's question
            max_tables: Maximum number of tables to identify

        Returns:
            List of relevant table names
        """
        tables = []
        seen = set()

        # Strategy 1: Semantic search with BALANCED threshold
        # 0.55 balances precision and recall - catches all RAN tables
        results = self.vector_store.search(
            query=question,
            limit=max_tables * 2,  # Fetch fewer candidates for precision
            chunk_types=["table_overview"],
            score_threshold=0.55  # OPTIMIZED: 0.55 for best RAN performance!
        )

        for result in results:
            table_name = result.get('table_name')
            if table_name and table_name not in seen:
                tables.append(table_name)
                seen.add(table_name)
                if len(tables) >= max_tables:
                    break

        # Strategy 2: Keyword extraction fallback
        # Extract potential table names from the question directly
        # Handles cases like "ran lld" → "ran_lld", "user table" → "users"
        if len(tables) < max_tables:
            keyword_tables = self._extract_table_keywords(question)
            for table_name in keyword_tables:
                if table_name not in seen and len(tables) < max_tables:
                    # Verify this table exists by searching with lower threshold
                    verify_results = self.vector_store.search(
                        query=f"table {table_name}",
                        limit=1,
                        chunk_types=["table_overview"],
                        score_threshold=0.4  # Lower for keyword fallback
                    )
                    if verify_results and verify_results[0].get('table_name') == table_name:
                        tables.append(table_name)
                        seen.add(table_name)

        return tables

    def _extract_table_keywords(self, question: str) -> List[str]:
        """
        Extract potential table names from question using keyword patterns.

        Handles patterns like:
        - "from ran_lld" → ["ran_lld"]
        - "ran lld table" → ["ran_lld"]
        - "users and projects" → ["users", "projects"]

        Args:
            question: User's question

        Returns:
            List of potential table names
        """
        import re

        potential_tables = []

        # Pattern 1: Explicit "from X" or "in X table"
        from_pattern = r'from\s+(\w+)'
        in_pattern = r'in\s+(\w+)(?:\s+table)?'

        for match in re.finditer(from_pattern, question, re.IGNORECASE):
            potential_tables.append(match.group(1).lower())

        for match in re.finditer(in_pattern, question, re.IGNORECASE):
            potential_tables.append(match.group(1).lower())

        # Pattern 2: Common table name patterns with underscores
        # Match things like "ran_lld", "user_access", etc.
        underscore_pattern = r'\b([a-z]+_[a-z_]+)\b'
        for match in re.finditer(underscore_pattern, question, re.IGNORECASE):
            potential_tables.append(match.group(1).lower())

        # Pattern 3: Words followed by "table" or "records"
        # "ran lld table" → "ran_lld"
        table_keyword_pattern = r'(\w+(?:\s+\w+)*?)\s+(?:table|records|data)'
        for match in re.finditer(table_keyword_pattern, question, re.IGNORECASE):
            # Convert spaces to underscores
            table_candidate = match.group(1).lower().replace(' ', '_')
            potential_tables.append(table_candidate)

        return list(set(potential_tables))  # Deduplicate

    def _fetch_detailed_context(
        self,
        question: str,
        relevant_tables: List[str]
    ) -> Dict[str, Any]:
        """
        Stage 2: Fetch detailed schema information for relevant tables.

        This retrieves:
        - Table schemas (columns, types)
        - Relationships (JOIN conditions) - CRITICAL!
        - Business rules
        - Enums

        Args:
            question: User's question
            relevant_tables: Tables identified in stage 1

        Returns:
            Dictionary with organized chunks by type
        """
        context = {
            'tables': [],
            'columns': [],
            'relationships': [],
            'business_rules': [],
            'enums': [],
            'schemas': [],
            'all_chunks': []
        }

        # Fetch table-specific context
        if relevant_tables:
            table_results = self.vector_store.search(
                query=question,
                limit=self.max_context_chunks,
                table_names=relevant_tables,
                prioritize_relationships=True,
                score_threshold=0.5  # BALANCED: 0.5 for good context retrieval
            )

            for result in table_results:
                chunk_type = result['type']
                if chunk_type == 'table_overview':
                    context['tables'].append(result)
                elif chunk_type == 'columns':
                    context['columns'].append(result)
                elif chunk_type == 'relationship':
                    context['relationships'].append(result)
                elif chunk_type == 'enum':
                    context['enums'].append(result)
                elif chunk_type == 'schema_overview':
                    context['schemas'].append(result)

                context['all_chunks'].append(result)

        # Always fetch relevant business rules (not table-specific)
        business_results = self.vector_store.get_business_rules(
            query=question,
            limit=5
        )
        context['business_rules'] = business_results
        context['all_chunks'].extend(business_results)

        # Fetch relationships for identified tables (CRITICAL for JOINs!)
        if relevant_tables:
            relationship_results = self.vector_store.get_relationships_for_tables(
                table_names=relevant_tables,
                limit=10
            )
            # Add relationships not already included
            existing_rel_ids = {r['vector_id'] for r in context['relationships']}
            for rel in relationship_results:
                if rel['vector_id'] not in existing_rel_ids:
                    context['relationships'].append(rel)
                    context['all_chunks'].append(rel)

        return context

    def _format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Stage 3: Format retrieved context into structured text for the prompt.

        Organizes chunks into clear sections:
        [TABLES]
        [RELATIONSHIPS] - Most important!
        [BUSINESS_RULES]
        [ADDITIONAL_INFO]

        Args:
            context: Retrieved context from stage 2

        Returns:
            Formatted context string
        """
        sections = []

        # Section 1: Table Schemas
        if context['tables'] or context['columns']:
            sections.append("=== DATABASE SCHEMA ===")
            sections.append("")

            # Combine table overviews and column details
            table_info = {}
            for chunk in context['tables']:
                table_name = chunk.get('table_name', 'unknown')
                table_info[table_name] = chunk['content']

            for chunk in context['columns']:
                table_name = chunk.get('table_name', 'unknown')
                if table_name in table_info:
                    table_info[table_name] += "\n\n" + chunk['content']
                else:
                    table_info[table_name] = chunk['content']

            for table_content in table_info.values():
                sections.append(table_content)
                sections.append("")

        # Section 2: Relationships (MOST IMPORTANT for preventing wrong joins!)
        if context['relationships']:
            sections.append("=== JOIN RELATIONSHIPS (CRITICAL - USE THESE EXACT JOIN CONDITIONS) ===")
            sections.append("")
            for rel in context['relationships']:
                sections.append(rel['content'])
                sections.append("")

        # Section 3: Business Rules
        if context['business_rules']:
            sections.append("=== BUSINESS RULES ===")
            sections.append("")
            for rule in context['business_rules']:
                sections.append(rule['content'])
                sections.append("")

        # Section 4: Enums (value constraints)
        if context['enums']:
            sections.append("=== ALLOWED VALUES ===")
            sections.append("")
            for enum in context['enums']:
                sections.append(enum['content'])
                sections.append("")

        return "\n".join(sections)

    def _build_prompt(
        self,
        question: str,
        formatted_context: str,
        database: str,
        few_shot_examples: str = ""
    ) -> str:
        """
        Stage 4: Build the complete prompt for Llama 3.1.

        This is THE MOST CRITICAL function for achieving 90%+ accuracy.

        Args:
            question: User's question
            formatted_context: Formatted schema context
            database: Database type
            few_shot_examples: Few-shot examples from feedback loop

        Returns:
            Complete prompt string
        """
        system_prompt = f"""You are an expert {database} database engineer. Your job is to write a single, accurate, and efficient SQL query based on the provided database schema.

CRITICAL RULES:
1. You MUST ONLY use tables and columns that are EXPLICITLY listed in the DATABASE SCHEMA section below
2. You MUST NOT invent, hallucinate, or assume any table or column names
3. For JOINs, you MUST use the EXACT join conditions provided in the "JOIN RELATIONSHIPS" section
4. You MUST follow the business rules provided in the "BUSINESS RULES" section
5. Pay strict attention to:
   - Column names (use exact names from schema)
   - Data types (respect the types shown)
   - Foreign key relationships (use the explicit JOIN conditions)
   - Business logic definitions (e.g., what "active" means)

OUTPUT FORMAT:
- Return ONLY the SQL query
- Do NOT include explanations, markdown, or code blocks
- Do NOT add comments in the SQL (unless specifically requested)
- Do NOT include semicolons at the end
- Use proper {database} SQL syntax

{formatted_context}

{few_shot_examples}

=== USER QUESTION ===
{question}

=== GENERATED SQL ===
"""

        return system_prompt

    def _generate_sql_with_llm(self, prompt: str) -> str:
        """
        Stage 5: Call Llama 3.1 to generate SQL.

        Args:
            prompt: Complete prompt with context

        Returns:
            Generated SQL query
        """
        try:
            response = self.llm_client.generate(
                prompt="Generate the SQL query for the question above.",
                system_prompt=prompt,
                temperature=self.temperature,
                max_tokens=500
            )

            # Clean the response
            sql = self._clean_sql_response(response)
            return sql

        except Exception as e:
            logger.error(f"Error generating SQL: {e}")
            return f"-- Error generating SQL: {e}"

    def _clean_sql_response(self, response: str) -> str:
        """
        Clean LLM response to extract pure SQL.

        Removes:
        - Markdown code blocks
        - Explanations
        - Comments (optional)

        Args:
            response: Raw LLM response

        Returns:
            Cleaned SQL query
        """
        # Remove markdown code blocks
        response = re.sub(r'```sql\s*', '', response)
        response = re.sub(r'```\s*', '', response)

        # Remove leading/trailing whitespace
        response = response.strip()

        # Remove trailing semicolon
        response = response.rstrip(';')

        return response

    def _validate_sql(self, sql: str) -> List[str]:
        """
        Stage 6: Validate the generated SQL.

        Basic checks:
        - Not empty
        - Starts with SELECT/INSERT/UPDATE/DELETE
        - Basic syntax validation (optional)

        Args:
            sql: Generated SQL query

        Returns:
            List of error messages (empty if valid)
        """
        errors = []

        if not sql or sql.startswith('--'):
            errors.append("No SQL generated or generation failed")
            return errors

        # Check if it starts with a valid SQL keyword
        sql_upper = sql.strip().upper()
        valid_keywords = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'WITH']
        if not any(sql_upper.startswith(kw) for kw in valid_keywords):
            errors.append(f"SQL must start with one of: {', '.join(valid_keywords)}")

        # Basic parentheses balance check
        if sql.count('(') != sql.count(')'):
            errors.append("Unbalanced parentheses in SQL")

        # Check for common mistakes
        if 'FROM FROM' in sql_upper:
            errors.append("Duplicate FROM keyword detected")

        if 'JOIN JOIN' in sql_upper:
            errors.append("Duplicate JOIN keyword detected")

        return errors

    def _calculate_confidence(
        self,
        context: Dict[str, Any],
        sql: str,
        errors: List[str]
    ) -> float:
        """
        Calculate confidence score for the generated SQL.

        Factors:
        - Number of retrieved chunks (more context = higher confidence)
        - Presence of relationship chunks (JOINs covered = higher confidence)
        - Validation errors (errors = lower confidence)
        - SQL complexity vs context coverage

        Args:
            context: Retrieved context
            sql: Generated SQL
            errors: Validation errors

        Returns:
            Confidence score (0-1)
        """
        confidence = 0.5  # Base confidence

        # Boost for having table context
        if context['tables'] or context['columns']:
            confidence += 0.2

        # Boost for having relationship context (CRITICAL for JOINs)
        if context['relationships'] and 'JOIN' in sql.upper():
            confidence += 0.2

        # Boost for having business rules
        if context['business_rules']:
            confidence += 0.1

        # Penalty for errors
        if errors:
            confidence -= 0.3

        # Penalty if no context retrieved
        if not context['all_chunks']:
            confidence -= 0.4

        # Clamp to [0, 1]
        confidence = max(0.0, min(1.0, confidence))

        return confidence


# Convenience function for quick SQL generation
def text_to_sql(question: str, database: str = "SQL Server") -> str:
    """
    Quick function to generate SQL from a question.

    Args:
        question: Natural language question
        database: Database type

    Returns:
        Generated SQL query

    Example:
        sql = text_to_sql("Show me all active users")
        print(sql)
    """
    generator = Text2SQLGenerator()
    result = generator.generate_sql(question, database)

    if result.execution_ready:
        return result.sql
    else:
        logger.warning(f"Generated SQL has errors: {result.errors}")
        return result.sql


# Singleton instance
_text2sql_generator_instance: Optional[Text2SQLGenerator] = None


def get_text2sql_generator() -> Text2SQLGenerator:
    """
    Get or create Text2SQLGenerator singleton instance.

    Returns:
        Text2SQLGenerator instance
    """
    global _text2sql_generator_instance
    if _text2sql_generator_instance is None:
        _text2sql_generator_instance = Text2SQLGenerator()
    return _text2sql_generator_instance
