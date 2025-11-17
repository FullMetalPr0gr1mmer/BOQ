"""
Main AI Agent for BOQ Application
Handles function calling, conversation management, and action execution
"""
import json
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
import logging

from AI.ollama_client import get_ollama_client
from AI.tools import BOQTools
from AI.rag_engine import get_rag_engine
from AI.query_router import route_query
from Models.AI import ChatHistory, AIAction
from Models.Admin.User import User

logger = logging.getLogger(__name__)


class BOQAgent:
    """
    Intelligent agent that can understand natural language and execute actions
    """

    SYSTEM_PROMPT = """You are an intelligent assistant for a Bill of Quantities (BOQ) management application.
You help users manage projects, inventory, sites, documents, and data across three domains:
1. BOQ (Bill of Quantities) - Construction/equipment project management
2. RAN (Radio Access Network) - Network infrastructure projects
3. ROP (Resource Optimization Planning) - Resource planning and optimization

You have access to various functions to interact with the application. When a user asks you to do something,
determine if you need to call a function or if you can answer directly.

Always be helpful, accurate, and confirm actions before executing destructive operations.
When citing information from documents, always reference the source.

Current capabilities:
- Create and search projects (BOQ, RAN, ROP)
- Manage inventory and sites
- Search and analyze project data
- Answer questions using uploaded documents
- Compare projects and analyze pricing

CRITICAL DATABASE QUERY RULES:
1. ALWAYS use 'get_database_schema' function BEFORE writing ANY SQL query
2. NEVER assume column names - always verify with schema first
3. Common table naming patterns:
   - BOQ projects: 'projects' table (NOT 'boq_projects')
   - RAN projects: 'ran_projects' table
   - ROP/LE projects: 'rop_projects' table (users may say "LE", "LE-Automation", or "le automation")
4. Use 'get_database_schema' without parameters to list all available tables
5. Use 'get_database_schema' with table_name to get specific table columns

QUERY STRATEGY:
1. If unsure about table names, call get_database_schema() first to list all tables
2. Call get_database_schema(table_name="...") to verify columns before querying
3. Use the SQL Server query templates below
4. Write the SQL query with verified column names

SQL SERVER QUERY TEMPLATES (This is SQL Server, NOT MySQL/PostgreSQL):

Counting Records:
SELECT COUNT(*) FROM {table_name}
SELECT COUNT(*) FROM {table_name} WHERE {column} = '{value}'

Top N Records (SQL Server uses TOP, NOT LIMIT):
SELECT TOP {n} * FROM {table_name}
SELECT TOP {n} * FROM {table_name} ORDER BY {column} DESC
SELECT TOP {n} {col1}, {col2}, {col3} FROM {table_name} WHERE {condition}

Filtering:
SELECT * FROM {table_name} WHERE {column} = '{value}'
SELECT * FROM {table_name} WHERE {column} LIKE '%{value}%'
SELECT * FROM {table_name} WHERE {column} IN ('{val1}', '{val2}')

Aggregation:
SELECT {column}, COUNT(*) as count FROM {table_name} GROUP BY {column}
SELECT AVG({column}) FROM {table_name}
SELECT SUM({column}) FROM {table_name}

Joining Tables:
SELECT t1.*, t2.{column} FROM {table1} t1
INNER JOIN {table2} t2 ON t1.{key} = t2.{key}

CRITICAL: This database is SQL Server. NEVER use MySQL/PostgreSQL syntax like LIMIT.
The system will auto-translate LIMIT to TOP, but it's better to use correct syntax from the start.

EXAMPLES:
- "How many RAN antenna serials?" → SELECT COUNT(*) FROM ran_antenna_serials
- "Show top 5 RAN antenna serials" → SELECT TOP 5 * FROM ran_antenna_serials ORDER BY id DESC
- "RAN Level 3 items" → SELECT * FROM ranlvl3
- "LE automation projects" → SELECT * FROM rop_projects

If you're not sure about something, ask for clarification rather than guessing."""

    def __init__(self):
        self.ollama_client = get_ollama_client()
        self.rag_engine = get_rag_engine()
        self.tools = BOQTools()

    def chat(
        self,
        message: str,
        user_id: int,
        db: Session,
        conversation_id: Optional[str] = None,
        project_context: Optional[Dict[str, Any]] = None,
        chat_context: Optional[str] = 'chat'
    ) -> Dict[str, Any]:
        """
        Main chat interface

        Args:
            message: User's message
            user_id: Current user ID
            db: Database session
            conversation_id: Optional conversation UUID for continuity
            project_context: Optional current project context
            chat_context: Context of the chat - 'chat' for tasks/database, 'documents' for document Q&A

        Returns:
            Response with text, actions, and data
        """
        # Generate conversation ID if not provided
        if not conversation_id:
            conversation_id = str(uuid.uuid4())

        # Get conversation history
        history = self._get_conversation_history(db, conversation_id, limit=10)

        # Build system prompt with context
        system_prompt = self.SYSTEM_PROMPT
        if project_context:
            system_prompt += f"\n\nCurrent context: User is viewing {project_context.get('type')} project ID {project_context.get('id')}"

        # Get user info for permissions
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            role_name = user.role.name if user.role else 'user'
            system_prompt += f"\n\nCurrent user: {user.username} (role: {role_name})"

        # Save user message
        self._save_message(db, user_id, conversation_id, "user", message, project_context)

        # STEP 1: Intelligent Query Routing (prevents hallucinations)
        # Detect direct database queries and route to Text-to-SQL FIRST
        # This prevents conversational LLM from generating fake context before having data
        if chat_context == 'chat':  # Only route in chat tab (not documents tab)
            router_result = route_query(message, user_id=str(user_id))

            if router_result['type'] == 'database':
                logger.info(f"[QUERY ROUTER] Detected DATABASE query, routing to Text-to-SQL")

                # Execute SQL directly (bypass conversational LLM)
                sql = router_result['sql']
                confidence = router_result['confidence']
                execution_ready = router_result['execution_ready']

                if execution_ready:
                    # Execute the SQL query using query_database tool
                    try:
                        result = self.tools.query_database(
                            db=db,
                            user_id=user_id,
                            sql_query=sql,
                            description="Text-to-SQL query"
                        )

                        if result['success']:
                            # Format data summary
                            row_count = result.get('row_count', 0)
                            truncated = result.get('truncated', False)
                            columns = result.get('columns', [])
                            data = result.get('data', [])

                            # Build context for LLM with actual data
                            data_context = f"""I executed this SQL query:
```sql
{sql}
```

Results: {row_count} rows returned{' (showing first 100)' if truncated else ''}

Columns: {', '.join(columns)}

Sample data (first 3 rows):
{json.dumps(data[:3], indent=2)}
"""

                            # Ask LLM to provide a natural language summary of the results
                            followup_messages = [
                                {
                                    "role": "user",
                                    "content": f"Original question: {message}"
                                },
                                {
                                    "role": "assistant",
                                    "content": data_context
                                },
                                {
                                    "role": "user",
                                    "content": "Please explain what data was found in a friendly, natural way. Include key information from the results (like column names, counts, sample values) to help the user understand what they got. Be specific and helpful."
                                }
                            ]

                            friendly_response = self.ollama_client.chat(
                                followup_messages,
                                system_prompt=system_prompt,
                                temperature=0.7
                            )

                            # Combine SQL + friendly explanation
                            response_text = f"{friendly_response}\n\n---\n\n**Executed SQL:**\n```sql\n{sql}\n```\n\nQuery returned {row_count} rows{' (showing first 100)' if truncated else ''}"

                            # Save assistant response
                            self._save_message(
                                db, user_id, conversation_id, "assistant",
                                response_text, project_context,
                                function_calls=[{
                                    "name": "query_database",
                                    "arguments": {"sql_query": sql},
                                    "result": result
                                }]
                            )

                            return {
                                "response": response_text,
                                "conversation_id": conversation_id,
                                "actions_taken": ["query_database"],
                                "data": result,
                                "sources": None
                            }
                        else:
                            error_msg = f"SQL execution failed: {result.get('error')}"
                            self._save_message(db, user_id, conversation_id, "assistant", error_msg, project_context)
                            return {
                                "response": error_msg,
                                "conversation_id": conversation_id,
                                "actions_taken": [],
                                "data": None,
                                "sources": None
                            }
                    except Exception as e:
                        error_msg = f"Error executing SQL: {str(e)}"
                        logger.error(error_msg)
                        self._save_message(db, user_id, conversation_id, "assistant", error_msg, project_context)
                        return {
                            "response": error_msg,
                            "conversation_id": conversation_id,
                            "actions_taken": [],
                            "data": None,
                            "sources": None
                        }
                else:
                    # SQL has errors
                    error_msg = f"Generated SQL has validation errors: {router_result.get('errors')}\n\n```sql\n{sql}\n```"
                    self._save_message(db, user_id, conversation_id, "assistant", error_msg, project_context)
                    return {
                        "response": error_msg,
                        "conversation_id": conversation_id,
                        "actions_taken": [],
                        "data": None,
                        "sources": None
                    }

        # RAG decision based on chat_context:
        # - 'documents' tab: ALWAYS use RAG (user wants document Q&A)
        # - 'chat' tab: SKIP RAG (user wants database/task queries)
        if chat_context == 'documents':
            logger.info(f"[RAG] Using RAG - user is in Documents tab")
            rag_response = self._try_rag_response(message, db, project_context)
        else:
            # In chat tab, skip RAG for database/task queries
            is_followup = self._is_followup_question(message, history)
            is_db_query = self._is_database_query(message)

            if is_followup:
                logger.info(f"[RAG] Skipping RAG - detected follow-up question about previous context")
            if is_db_query:
                logger.info(f"[RAG] Skipping RAG - detected explicit database query")

            # Always skip RAG in chat tab
            logger.info(f"[RAG] Skipping RAG - user is in Chat tab (for tasks/database)")
            rag_response = None

        if rag_response:
            # Save assistant response
            self._save_message(
                db, user_id, conversation_id, "assistant",
                rag_response['answer'], project_context
            )

            return {
                "response": rag_response['answer'],
                "conversation_id": conversation_id,
                "sources": rag_response.get('sources', []),
                "actions_taken": [],
                "data": None
            }

        # Prepare messages for LLM
        messages = []
        for msg in history:
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        messages.append({
            "role": "user",
            "content": message
        })

        # Get available functions
        functions = self.tools.get_function_schemas()

        # Call LLM with function calling
        response = self.ollama_client.function_call(
            prompt=message,
            functions=functions,
            system_prompt=system_prompt
        )

        # Handle response
        if response['type'] == 'function_call':
            # Execute function
            result = self._execute_function(
                response['function'],
                response['arguments'],
                user_id,
                db,
                conversation_id
            )

            # Generate natural language response about the action
            action_summary = f"Function '{response['function']}' executed with result: {json.dumps(result)}"

            # Ask LLM to format a user-friendly response
            followup_messages = messages + [
                {
                    "role": "assistant",
                    "content": f"I called {response['function']} and got: {json.dumps(result)}"
                },
                {
                    "role": "user",
                    "content": "Please summarize what you did in a friendly, natural way. Include key information from the results (like item names, quantities, project names, IDs, prices) to help the user understand the data. Avoid mentioning function names or raw JSON structure. Be specific and helpful."
                }
            ]

            friendly_response = self.ollama_client.chat(
                followup_messages,
                system_prompt=system_prompt,
                temperature=0.7
            )

            # Save assistant response
            self._save_message(
                db, user_id, conversation_id, "assistant",
                friendly_response, project_context,
                function_calls=[{
                    "name": response['function'],
                    "arguments": response['arguments'],
                    "result": result
                }]
            )

            return {
                "response": friendly_response,
                "conversation_id": conversation_id,
                "actions_taken": [response['function']],
                "data": result,
                "sources": None
            }

        else:
            # Text response (no function call needed)
            text_response = response['content']

            # Save assistant response
            self._save_message(
                db, user_id, conversation_id, "assistant",
                text_response, project_context
            )

            return {
                "response": text_response,
                "conversation_id": conversation_id,
                "actions_taken": [],
                "data": None,
                "sources": None
            }

    def _is_database_query(self, question: str) -> bool:
        """
        Detect if question is explicitly about database/project data

        Args:
            question: User's question

        Returns:
            True if question is asking for database/project data (should skip RAG)
        """
        database_keywords = [
            # Query intent keywords
            'how many', 'count', 'fetch', 'list all', 'show me', 'get all',
            'retrieve', 'find all', 'give me all', 'show all',

            # Existence/quantity keywords
            'projects do we have', 'items do we have', 'serials do we have',
            'do we have', 'are there any', 'total number',

            # Explicit database references
            'search in the database', 'search database', 'from database',
            'in the database', 'query database', 'database query',

            # Project type keywords (strong indicators of database queries)
            'boq project', 'ran project', 'rop project',
            'le project', 'le-automation', 'le automation',

            # Table name references
            'level 3', 'lvl3', 'ranlvl3', 'level 1', 'lvl1',
            'inventory', 'antenna serial', 'package',

            # Data retrieval verbs
            'list', 'show', 'display', 'give', 'provide',
            'what are the', 'which are the'
        ]

        question_lower = question.lower()

        # Check for any database keyword
        has_db_keyword = any(keyword in question_lower for keyword in database_keywords)

        if has_db_keyword:
            logger.info(f"[RAG] Detected database query keyword in: '{question}'")
            return True

        return False

    def _is_followup_question(self, question: str, history: list) -> bool:
        """
        Check if question references previous conversation context

        Args:
            question: User's current question
            history: Conversation history

        Returns:
            True if this appears to be a follow-up question about previous results
        """
        # Referential indicators that suggest the question is about previous context
        referential_phrases = [
            'each', 'these', 'those', 'them', 'it', 'they',
            'which project', 'what project', 'belongs to', 'belong to',
            'from the', 'in the results', 'you just', 'you showed',
            'the items', 'the data', 'above', 'previous',
            'tell me about', 'more about', 'details about'
        ]

        question_lower = question.lower()
        has_reference = any(phrase in question_lower for phrase in referential_phrases)

        if not has_reference:
            return False

        # Check if there's recent function call in history (last 4 messages)
        if not history or len(history) == 0:
            return False

        recent_messages = history[-4:] if len(history) >= 4 else history

        # Look for assistant messages with function_calls in metadata
        for msg in recent_messages:
            if isinstance(msg, dict):
                # Check if this message has function_calls
                if msg.get('function_calls') and len(msg.get('function_calls', [])) > 0:
                    logger.info(f"[CONTEXT] Detected follow-up question with recent function results")
                    return True

        return False

    def _try_rag_response(
        self,
        question: str,
        db: Session,
        project_context: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Try to answer using RAG on documents

        Returns:
            RAG response or None if no relevant docs found
        """
        try:
            document_ids = None

            # If in project context, limit to that project's documents
            if project_context:
                from Models.AI import Document
                docs = db.query(Document).filter(
                    Document.project_type == project_context.get('type'),
                    Document.project_id == project_context.get('id'),
                    Document.processing_status == 'completed'
                ).all()
                document_ids = [doc.id for doc in docs]

                if not document_ids:
                    logger.info(f"[RAG] No completed documents in project context")
                    return None
                logger.info(f"[RAG] Found {len(document_ids)} documents in project context")
            else:
                # No project context - search ALL completed documents (and recently uploaded ones)
                from Models.AI import Document
                from datetime import datetime, timedelta

                # Get completed documents
                completed_docs = db.query(Document).filter(
                    Document.processing_status == 'completed'
                ).all()

                # Also include documents uploaded in last 2 minutes that might still be processing
                recent_cutoff = datetime.utcnow() - timedelta(minutes=2)
                recent_docs = db.query(Document).filter(
                    Document.upload_date >= recent_cutoff,
                    Document.processing_status.in_(['processing', 'completed'])
                ).all()

                # Combine and deduplicate
                all_docs = {doc.id: doc for doc in (completed_docs + recent_docs)}

                if all_docs:
                    document_ids = list(all_docs.keys())
                    logger.info(f"[RAG] No project context, searching {len(document_ids)} total documents (including recent uploads)")
                else:
                    logger.info(f"[RAG] No documents found")
                    return None

            # Ask RAG engine
            logger.info(f"[RAG] Asking RAG engine: '{question}'")
            result = self.rag_engine.answer_question(
                question=question,
                db=db,
                document_ids=document_ids
            )

            logger.info(f"[RAG] Result confidence: {result['confidence']:.4f}")

            # Only return if confidence is high enough (lowered from 0.6 to 0.3)
            if result['confidence'] > 0.3:
                logger.info(f"[RAG] Using RAG response (confidence > 0.3)")
                return result
            else:
                logger.info(f"[RAG] Confidence too low, not using RAG")

        except Exception as e:
            logger.error(f"RAG error: {e}")
            import traceback
            traceback.print_exc()

        return None

    def _execute_function(
        self,
        function_name: str,
        arguments: Dict[str, Any],
        user_id: int,
        db: Session,
        conversation_id: str
    ) -> Dict[str, Any]:
        """
        Execute a tool function

        Args:
            function_name: Function to call
            arguments: Function arguments
            user_id: Current user ID
            db: Database session
            conversation_id: Conversation ID

        Returns:
            Function result
        """
        start_time = datetime.utcnow()

        try:
            # Get function from tools
            if hasattr(self.tools, function_name):
                func = getattr(self.tools, function_name)
                result = func(db=db, user_id=user_id, **arguments)
                status = "success" if result.get('success') else "failed"
                error = result.get('error')
            else:
                result = {"success": False, "error": f"Function '{function_name}' not found"}
                status = "failed"
                error = result['error']

            # Log action
            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            action_log = AIAction(
                user_id=user_id,
                conversation_id=conversation_id,
                action_type=function_name,
                action_params=arguments,
                action_result=result,
                status=status,
                error_message=error,
                execution_time_ms=execution_time
            )
            db.add(action_log)
            db.commit()

            logger.info(f"Executed {function_name} for user {user_id}: {status}")

            return result

        except Exception as e:
            logger.error(f"Error executing {function_name}: {e}")

            execution_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)

            action_log = AIAction(
                user_id=user_id,
                conversation_id=conversation_id,
                action_type=function_name,
                action_params=arguments,
                action_result=None,
                status="failed",
                error_message=str(e),
                execution_time_ms=execution_time
            )
            db.add(action_log)
            db.commit()

            return {"success": False, "error": str(e)}

    def _get_conversation_history(
        self,
        db: Session,
        conversation_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history

        Args:
            db: Database session
            conversation_id: Conversation UUID
            limit: Max messages to return

        Returns:
            List of messages
        """
        messages = db.query(ChatHistory).filter(
            ChatHistory.conversation_id == conversation_id
        ).order_by(ChatHistory.timestamp.desc()).limit(limit).all()

        # Reverse to get chronological order
        messages = list(reversed(messages))

        return [
            {
                "role": msg.role,
                "content": msg.content
            }
            for msg in messages
        ]

    def _save_message(
        self,
        db: Session,
        user_id: int,
        conversation_id: str,
        role: str,
        content: str,
        project_context: Optional[Dict[str, Any]] = None,
        function_calls: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Save message to chat history

        Args:
            db: Database session
            user_id: User ID
            conversation_id: Conversation UUID
            role: 'user' or 'assistant'
            content: Message content
            project_context: Optional project context
            function_calls: Optional list of function calls made
        """
        message = ChatHistory(
            user_id=user_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            project_type=project_context.get('type') if project_context else None,
            project_id=project_context.get('id') if project_context else None,
            function_calls=function_calls or []
        )
        db.add(message)
        db.commit()


# Singleton instance
_agent_instance: Optional[BOQAgent] = None


def get_agent() -> BOQAgent:
    """Get or create BOQAgent singleton"""
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = BOQAgent()
    return _agent_instance
