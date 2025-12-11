"""
Feedback Loop System - Task 4 Implementation

This module implements the feedback loop for continuous improvement:
1. Store (Question, SQL) pairs when users confirm correctness
2. Use stored examples as few-shot learning
3. Retrieve similar past examples for new questions
4. Gradually improve accuracy from 80% → 90%+

This is the KEY to achieving 90%+ accuracy over time.

Author: Senior AI Architect
Created: 2025-11-06
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging

from AI.text2sql_vectorstore import get_text2sql_vector_store

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """
    Manages the feedback loop for Text-to-SQL continuous improvement.

    When users correct or confirm SQL:
    1. Store (Question, Correct_SQL) as a few-shot example
    2. Embed the question for similarity search
    3. Future similar questions retrieve this example
    4. LLM sees the pattern and generates better SQL
    """

    def __init__(
        self,
        storage_path: str = None,
        vector_store=None
    ):
        """
        Initialize feedback loop.

        Args:
            storage_path: Path to store few-shot examples JSON
            vector_store: Text2SQLVectorStore instance
        """
        if storage_path is None:
            base_dir = Path(__file__).parent
            storage_path = base_dir / "knowledge_base" / "few_shot_examples.json"

        self.storage_path = Path(storage_path)
        self.vector_store = vector_store or get_text2sql_vector_store()
        self.examples = self._load_examples()

    def _load_examples(self) -> List[Dict[str, Any]]:
        """
        Load existing few-shot examples from storage.

        Returns:
            List of example dictionaries
        """
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    examples = json.load(f)
                logger.info(f"Loaded {len(examples)} few-shot examples")
                return examples
            except Exception as e:
                logger.error(f"Error loading examples: {e}")
                return []
        else:
            logger.info("No existing few-shot examples found")
            return []

    def _save_examples(self):
        """Save examples to storage."""
        try:
            # Ensure directory exists
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.examples, f, indent=2, ensure_ascii=False)

            logger.info(f"Saved {len(self.examples)} few-shot examples")
        except Exception as e:
            logger.error(f"Error saving examples: {e}")

    def add_example(
        self,
        question: str,
        correct_sql: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add a new few-shot example.

        This is called when:
        - User clicks "thumbs up" on generated SQL
        - User provides corrected SQL after "thumbs down"

        Args:
            question: User's natural language question
            correct_sql: The correct SQL query
            metadata: Optional metadata (user_id, timestamp, etc.)

        Returns:
            Example ID (UUID)
        """
        example_id = str(uuid.uuid4())

        example = {
            "id": example_id,
            "question": question,
            "sql": correct_sql,
            "created_at": datetime.now().isoformat(),
            "metadata": metadata or {}
        }

        # Add to in-memory storage
        self.examples.append(example)

        # Save to disk
        self._save_examples()

        # Embed into vector store for retrieval
        self._embed_example(example)

        logger.info(f"Added few-shot example: {example_id}")

        return example_id

    def _embed_example(self, example: Dict[str, Any]):
        """
        Embed a few-shot example into the vector store.

        Format as a chunk so it can be retrieved alongside schema knowledge.

        Args:
            example: Example dictionary
        """
        chunk = {
            "content": self._format_example_as_chunk(example),
            "metadata": {
                "type": "few_shot_example",
                "example_id": example["id"],
                "question": example["question"]
            }
        }

        try:
            self.vector_store.add_schema_chunks([chunk])
            logger.info(f"Embedded few-shot example: {example['id']}")
        except Exception as e:
            logger.error(f"Error embedding example: {e}")

    def _format_example_as_chunk(self, example: Dict[str, Any]) -> str:
        """
        Format an example as a text chunk for embedding.

        Args:
            example: Example dictionary

        Returns:
            Formatted text
        """
        return f"""FEW-SHOT EXAMPLE:

QUESTION:
{example['question']}

CORRECT SQL:
{example['sql']}

NOTE: This is a verified correct example. Use it as a reference pattern.
"""

    def get_similar_examples(
        self,
        question: str,
        limit: int = 3,
        score_threshold: float = 0.5  # LOWERED from 0.7 to 0.5 for better recall
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar few-shot examples for a question.

        This is used during SQL generation to provide the LLM with
        relevant examples.

        Args:
            question: User's question
            limit: Maximum number of examples
            score_threshold: Minimum similarity score

        Returns:
            List of similar examples
        """
        # Search vector store for similar questions
        results = self.vector_store.search(
            query=question,
            limit=limit,
            chunk_types=["few_shot_example"],
            score_threshold=score_threshold
        )

        # Extract examples
        similar_examples = []
        for result in results:
            example_id = result['metadata'].get('example_id')
            if example_id:
                # Find full example in storage
                example = self._get_example_by_id(example_id)
                if example:
                    example['similarity_score'] = result['similarity_score']
                    similar_examples.append(example)

        logger.info(f"Found {len(similar_examples)} similar examples for question")
        return similar_examples

    def _get_example_by_id(self, example_id: str) -> Optional[Dict[str, Any]]:
        """
        Get an example by ID.

        Args:
            example_id: Example UUID

        Returns:
            Example dictionary or None
        """
        for example in self.examples:
            if example['id'] == example_id:
                return example
        return None

    def format_examples_for_prompt(
        self,
        examples: List[Dict[str, Any]]
    ) -> str:
        """
        Format few-shot examples for inclusion in prompt.

        Args:
            examples: List of example dictionaries

        Returns:
            Formatted text for prompt
        """
        if not examples:
            return ""

        sections = ["=== FEW-SHOT EXAMPLES (Learn from these patterns) ===", ""]

        for i, example in enumerate(examples, 1):
            sections.append(f"Example {i}:")
            sections.append(f"Question: {example['question']}")
            sections.append(f"SQL: {example['sql']}")
            sections.append("")

        return "\n".join(sections)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the feedback loop.

        Returns:
            Statistics dictionary
        """
        return {
            "total_examples": len(self.examples),
            "storage_path": str(self.storage_path),
            "oldest_example": self.examples[0]["created_at"] if self.examples else None,
            "newest_example": self.examples[-1]["created_at"] if self.examples else None
        }


# Singleton instance
_feedback_loop_instance: Optional[FeedbackLoop] = None


def get_feedback_loop() -> FeedbackLoop:
    """
    Get or create FeedbackLoop singleton instance.

    Returns:
        FeedbackLoop instance
    """
    global _feedback_loop_instance
    if _feedback_loop_instance is None:
        _feedback_loop_instance = FeedbackLoop()
    return _feedback_loop_instance


def add_feedback(question: str, correct_sql: str, user_id: Optional[str] = None):
    """
    Convenience function to add feedback.

    Args:
        question: User's question
        correct_sql: Correct SQL
        user_id: Optional user ID for tracking

    Example:
        # User clicks "thumbs up" or provides correction
        add_feedback(
            question="Show me all active users",
            correct_sql="SELECT * FROM users WHERE status = 'active'"
        )
    """
    feedback_loop = get_feedback_loop()
    metadata = {}
    if user_id:
        metadata['user_id'] = user_id

    feedback_loop.add_example(question, correct_sql, metadata)


def get_examples_for_question(question: str, limit: int = 3) -> str:
    """
    Get formatted few-shot examples for a question.

    This is used in text2sql_generator to enhance prompts.

    Args:
        question: User's question
        limit: Maximum examples

    Returns:
        Formatted examples text for prompt
    """
    feedback_loop = get_feedback_loop()
    examples = feedback_loop.get_similar_examples(question, limit)
    return feedback_loop.format_examples_for_prompt(examples)
