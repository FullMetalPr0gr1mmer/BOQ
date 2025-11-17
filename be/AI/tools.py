"""
Function tools for AI agent to interact with BOQ application
"""
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from datetime import datetime, date
from decimal import Decimal
import logging

# Import models
from Models.BOQ.Project import Project
from Models.BOQ.Site import Site
from Models.BOQ.Inventory import Inventory
from Models.BOQ.Levels import Lvl1, Lvl3, ItemsForLvl3
from Models.RAN.RANProject import RanProject
from Models.RAN.RANInventory import RANInventory
from Models.LE.ROPProject import ROPProject

logger = logging.getLogger(__name__)


class BOQTools:
    """
    Tools for AI to perform actions in BOQ application
    Each method is a callable function with JSON schema
    """

    @staticmethod
    def get_function_schemas() -> List[Dict[str, Any]]:
        """
        Return JSON schemas for all available functions
        Used for function calling with LLM
        """
        return [
            {
                "name": "create_boq_project",
                "description": "Create a new BOQ (Bill of Quantities) project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "Project name"},
                        "pid_po": {"type": "string", "description": "Combined PID_PO identifier"},
                        "pid": {"type": "string", "description": "Project ID"},
                        "po": {"type": "string", "description": "Purchase Order number"}
                    },
                    "required": ["project_name", "po"]
                }
            },
            {
                "name": "create_ran_project",
                "description": "Create a new RAN (Radio Access Network) project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "RAN project name"},
                        "pid_po": {"type": "string", "description": "Combined PID_PO identifier"},
                        "pid": {"type": "string", "description": "Project ID"},
                        "po": {"type": "string", "description": "Purchase Order number"}
                    },
                    "required": ["project_name", "po"]
                }
            },
            {
                "name": "create_rop_project",
                "description": "Create a new ROP (Resource Optimization Planning) project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_name": {"type": "string", "description": "ROP project name"},
                        "pid": {"type": "string", "description": "Project ID"},
                        "po": {"type": "string", "description": "Purchase Order number"}
                    },
                    "required": ["project_name"]
                }
            },
            {
                "name": "search_projects",
                "description": "Search for projects across all types (BOQ, RAN, ROP)",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query (matches project name, PID, PO)"},
                        "project_type": {"type": "string", "enum": ["boq", "ran", "rop", "all"], "description": "Filter by project type"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 10}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "list_all_projects",
                "description": "List all projects or count them, optionally filtered by type or specific criteria like PO number",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "enum": ["boq", "ran", "rop", "all"], "description": "Filter by project type (default: all)"},
                        "po_filter": {"type": "string", "description": "Filter by PO number (e.g., 'MW' for MW projects)"},
                        "limit": {"type": "integer", "description": "Maximum results to return (default: 100)"},
                        "count_only": {"type": "boolean", "description": "If true, return only the count without details (default: false)"}
                    }
                }
            },
            {
                "name": "get_project_summary",
                "description": "Get detailed summary of a specific project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "enum": ["boq", "ran", "rop"], "description": "Project type"},
                        "project_id": {"type": "integer", "description": "Project ID"}
                    },
                    "required": ["project_type", "project_id"]
                }
            },
            {
                "name": "fetch_sites",
                "description": "Fetch sites with optional filtering",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "site_name": {"type": "string", "description": "Filter by site name"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 50}
                    }
                }
            },
            {
                "name": "add_inventory_item",
                "description": "Add an inventory item to BOQ",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "site": {"type": "string", "description": "Site name"},
                        "slot": {"type": "string", "description": "Slot identifier"},
                        "port": {"type": "string", "description": "Port identifier"},
                        "status": {"type": "string", "description": "Equipment status"},
                        "serial_number": {"type": "string", "description": "Serial number"},
                        "part_number": {"type": "string", "description": "Part number"}
                    },
                    "required": ["site"]
                }
            },
            {
                "name": "search_inventory",
                "description": "Search BOQ inventory items ONLY (not RAN). For RAN inventory, use query_database with ran_inventory or ran_antenna_serials tables. For counting items, always use query_database.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "site": {"type": "string", "description": "Filter by site"},
                        "status": {"type": "string", "description": "Filter by status"},
                        "limit": {"type": "integer", "description": "Maximum results", "default": 20}
                    },
                    "required": ["query"]
                }
            },
            {
                "name": "create_lvl3_item",
                "description": "Create a Level 3 BOQ item",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "lvl1_id": {"type": "integer", "description": "Parent Level 1 ID"},
                        "description": {"type": "string", "description": "Item description"},
                        "uom": {"type": "string", "description": "Unit of measure"},
                        "quantity": {"type": "number", "description": "Quantity"},
                        "rate": {"type": "number", "description": "Unit rate"}
                    },
                    "required": ["lvl1_id", "description", "quantity"]
                }
            },
            {
                "name": "analyze_project_pricing",
                "description": "Analyze pricing data for a project",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_type": {"type": "string", "enum": ["boq", "ran"], "description": "Project type"},
                        "project_id": {"type": "integer", "description": "Project ID"}
                    },
                    "required": ["project_type", "project_id"]
                }
            },
            {
                "name": "compare_projects",
                "description": "Compare two projects side by side",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project1_type": {"type": "string", "description": "First project type"},
                        "project1_id": {"type": "integer", "description": "First project ID"},
                        "project2_type": {"type": "string", "description": "Second project type"},
                        "project2_id": {"type": "integer", "description": "Second project ID"}
                    },
                    "required": ["project1_type", "project1_id", "project2_type", "project2_id"]
                }
            },
            {
                "name": "query_database",
                "description": "Execute a read-only SQL SELECT query on the database to get information. Use this for counting, aggregating, filtering, or analyzing any data. IMPORTANT: ALWAYS call 'get_database_schema' FIRST to verify table and column names before writing your SQL query. DO NOT assume column names exist. Available tables: projects, ran_projects, rop_projects, lvl1, lvl3, items_for_lvl3, inventory, sites, dismantling, ran_inventory, ranlvl3, users, roles, documents, chat_history, and more.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {"type": "string", "description": "A SELECT SQL query to execute (read-only, no INSERT/UPDATE/DELETE/DROP allowed). Verify column names with get_database_schema first!"},
                        "description": {"type": "string", "description": "Brief description of what this query is trying to find"}
                    },
                    "required": ["sql_query", "description"]
                }
            },
            {
                "name": "get_database_schema",
                "description": "Get the schema (table structure and columns) for database tables to help construct SQL queries",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "table_name": {"type": "string", "description": "Optional: specific table name to get schema for. If not provided, returns list of all tables"}
                    }
                }
            }
        ]

    # Implementation methods

    @staticmethod
    def create_boq_project(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create BOQ project"""
        try:
            project = Project(
                project_name=kwargs.get('project_name'),
                pid=kwargs.get('pid', ''),
                po=kwargs.get('po', ''),
                pid_po=kwargs.get('pid', '')+kwargs.get('po', ''),
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            logger.info(f"Created BOQ project {project.id} by user {user_id}")

            return {
                "success": True,
                "project_id": project.id,
                "project_name": project.project_name,
                "message": f"Successfully created BOQ project '{project.project_name}'"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating BOQ project: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_ran_project(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create RAN project"""
        try:
            project = RanProject(
              project_name=kwargs.get('project_name'),
                pid=kwargs.get('pid', ''),
                po=kwargs.get('po', ''),
                pid_po=kwargs.get('pid', '')+kwargs.get('po', ''),
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            logger.info(f"Created RAN project {project.id} by user {user_id}")

            return {
                "success": True,
                "project_id": project.id,
                "project_name": project.project_name,
                "message": f"Successfully created RAN project '{project.project_name}'"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating RAN project: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def create_rop_project(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Create ROP project"""
        try:
            project = ROPProject(
                project_name=kwargs.get('project_name'),
                PID=kwargs.get('pid', ''),
                PO=kwargs.get('po', '')
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            logger.info(f"Created ROP project {project.id} by user {user_id}")

            return {
                "success": True,
                "project_id": project.id,
                "project_name": project.project_name,
                "message": f"Successfully created ROP project '{project.project_name}'"
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating ROP project: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def search_projects(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Search projects"""
        query = kwargs.get('query', '').lower()
        project_type = kwargs.get('project_type', 'all')
        limit = kwargs.get('limit', 10)

        results = []

        try:
            # Search BOQ projects
            if project_type in ['boq', 'all']:
                boq_projects = db.query(Project).filter(
                    (Project.project_name.ilike(f'%{query}%')) |
                    (Project.pid.ilike(f'%{query}%')) |
                    (Project.po.ilike(f'%{query}%'))
                ).limit(limit).all()

                for proj in boq_projects:
                    results.append({
                        "type": "boq",
                        "id": proj.pid_po,
                        "name": proj.project_name,
                        "pid": proj.pid,
                        "po": proj.po
                    })

            # Search RAN projects
            if project_type in ['ran', 'all']:
                ran_projects = db.query(RanProject).filter(
                    (RanProject.project_name.ilike(f'%{query}%')) |
                    (RanProject.pid.ilike(f'%{query}%')) |
                    (RanProject.po.ilike(f'%{query}%'))
                ).limit(limit).all()

                for proj in ran_projects:
                    results.append({
                        "type": "ran",
                        "id": proj.pid_po,
                        "name": proj.project_name,
                        "pid": proj.pid,
                        "po": proj.po
                    })

            # Search ROP projects
            if project_type in ['rop', 'all']:
                rop_projects = db.query(ROPProject).filter(
                    (ROPProject.project_name.ilike(f'%{query}%')) |
                    (ROPProject.pid.ilike(f'%{query}%')) |
                    (ROPProject.po.ilike(f'%{query}%'))
                ).limit(limit).all()

                for proj in rop_projects:
                    results.append({
                        "type": "rop",
                        "id": proj.pid_po,
                        "name": proj.project_name,
                        "pid": proj.pid,
                        "po": proj.po
                    })

            return {
                "success": True,
                "results": results[:limit],
                "count": len(results)
            }

        except Exception as e:
            logger.error(f"Error searching projects: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def list_all_projects(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """List all projects with optional filters"""
        project_type = kwargs.get('project_type', 'all')
        po_filter = kwargs.get('po_filter')
        limit = kwargs.get('limit', 100)
        count_only = kwargs.get('count_only', False)

        results = []
        total_count = 0

        try:
            # Query BOQ projects
            if project_type in ['boq', 'all']:
                boq_query = db.query(Project)
                if po_filter:
                    boq_query = boq_query.filter(Project.po.ilike(f'%{po_filter}%'))

                if count_only:
                    boq_count = boq_query.count()
                    total_count += boq_count
                else:
                    boq_projects = boq_query.limit(limit).all()
                    for proj in boq_projects:
                        results.append({
                            "type": "boq",
                            "id": proj.pid_po,  # Use primary key
                            "name": proj.project_name,
                            "pid": proj.pid,
                            "po": proj.po
                        })

            # Query RAN projects
            if project_type in ['ran', 'all']:
                ran_query = db.query(RanProject)
                if po_filter:
                    ran_query = ran_query.filter(RanProject.po.ilike(f'%{po_filter}%'))

                if count_only:
                    ran_count = ran_query.count()
                    total_count += ran_count
                else:
                    ran_projects = ran_query.limit(limit).all()
                    for proj in ran_projects:
                        results.append({
                            "type": "ran",
                            "id": proj.pid_po,  # Use primary key
                            "name": proj.project_name,
                            "pid": proj.pid,
                            "po": proj.po
                        })

            # Query ROP projects
            if project_type in ['rop', 'all']:
                rop_query = db.query(ROPProject)
                # ROP projects also have PO filter
                if po_filter:
                    rop_query = rop_query.filter(ROPProject.po.ilike(f'%{po_filter}%'))

                if count_only:
                    rop_count = rop_query.count()
                    total_count += rop_count
                else:
                    rop_projects = rop_query.limit(limit).all()
                    for proj in rop_projects:
                        results.append({
                            "type": "rop",
                            "id": proj.pid_po,  # Use primary key
                            "name": proj.project_name,
                            "pid": proj.pid,
                            "po": proj.po
                        })

            if count_only:
                return {
                    "success": True,
                    "count": total_count,
                    "project_type": project_type,
                    "po_filter": po_filter
                }
            else:
                return {
                    "success": True,
                    "results": results[:limit],
                    "count": len(results),
                    "project_type": project_type,
                    "po_filter": po_filter
                }

        except Exception as e:
            logger.error(f"Error listing projects: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def get_project_summary(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Get project summary"""
        project_type = kwargs.get('project_type')
        project_id = kwargs.get('project_id')

        try:
            if project_type == 'boq':
                project = db.query(Project).filter(Project.id == project_id).first()
                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get counts
                lvl1_count = db.query(Lvl1).filter(Lvl1.project_id == project_id).count()
                lvl3_count = db.query(Lvl3).filter(Lvl3.lvl1.has(project_id=project_id)).count()

                return {
                    "success": True,
                    "project": {
                        "id": project.id,
                        "name": project.project_name,
                        "pid": project.PID,
                        "po": project.PO,
                        "type": "boq",
                        "stats": {
                            "lvl1_items": lvl1_count,
                            "lvl3_items": lvl3_count
                        }
                    }
                }

            elif project_type == 'ran':
                project = db.query(RanProject).filter(RanProject.id == project_id).first()
                if not project:
                    return {"success": False, "error": "Project not found"}

                inventory_count = db.query(RANInventory).filter(
                    RANInventory.project_id == project_id
                ).count()

                return {
                    "success": True,
                    "project": {
                        "id": project.id,
                        "name": project.project_name,
                        "pid": project.PID,
                        "po": project.PO,
                        "type": "ran",
                        "stats": {
                            "inventory_items": inventory_count
                        }
                    }
                }

            elif project_type == 'rop':
                project = db.query(ROPProject).filter(ROPProject.id == project_id).first()
                if not project:
                    return {"success": False, "error": "Project not found"}

                return {
                    "success": True,
                    "project": {
                        "id": project.id,
                        "name": project.project_name,
                        "type": "rop"
                    }
                }

        except Exception as e:
            logger.error(f"Error getting project summary: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def fetch_sites(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Fetch sites"""
        try:
            query = db.query(Site)

            site_name = kwargs.get('site_name')
            if site_name:
                query = query.filter(Site.site_name.ilike(f'%{site_name}%'))

            limit = kwargs.get('limit', 50)
            sites = query.limit(limit).all()

            return {
                "success": True,
                "sites": [
                    {
                        "id": site.id,
                        "site_name": site.site_name
                    }
                    for site in sites
                ],
                "count": len(sites)
            }

        except Exception as e:
            logger.error(f"Error fetching sites: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def add_inventory_item(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Add inventory item"""
        try:
            item = Inventory(
                site=kwargs.get('site'),
                slot=kwargs.get('slot', ''),
                port=kwargs.get('port', ''),
                status=kwargs.get('status', ''),
                serial_number=kwargs.get('serial_number', ''),
                part_number=kwargs.get('part_number', '')
            )
            db.add(item)
            db.commit()
            db.refresh(item)

            return {
                "success": True,
                "inventory_id": item.id,
                "message": f"Added inventory item for site {item.site}"
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error adding inventory item: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def search_inventory(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """Search inventory"""
        try:
            query_text = kwargs.get('query', '').lower()
            query_obj = db.query(Inventory)

            # Apply filters
            if query_text:
                query_obj = query_obj.filter(
                    (Inventory.site_name.ilike(f'%{query_text}%')) |
                    (Inventory.serial_no.ilike(f'%{query_text}%')) |
                    (Inventory.part_no.ilike(f'%{query_text}%'))
                )

            site = kwargs.get('site')
            if site:
                query_obj = query_obj.filter(Inventory.site_name.ilike(f'%{site}%'))

            status = kwargs.get('status')
            if status:
                query_obj = query_obj.filter(Inventory.status.ilike(f'%{status}%'))

            limit = kwargs.get('limit', 20)
            items = query_obj.limit(limit).all()

            return {
                "success": True,
                "results": [
                    {
                        "id": item.id,
                        "site": item.site_name,
                        "slot": item.slot_id,
                        "port": item.port_id,
                        "status": item.status,
                        "serial_number": item.serial_no,
                        "part_number": item.part_no
                    }
                    for item in items
                ],
                "count": len(items)
            }

        except Exception as e:
            logger.error(f"Error searching inventory: {e}")
            return {"success": False, "error": str(e)}

    @staticmethod
    def _detect_database_dialect(db: Session) -> str:
        """
        Detect the database dialect from the database connection

        Returns:
            Database dialect name (e.g., 'mssql', 'postgresql', 'mysql', 'sqlite')
        """
        try:
            dialect_name = db.bind.dialect.name
            logger.info(f"Detected database dialect: {dialect_name}")
            return dialect_name
        except Exception as e:
            logger.warning(f"Could not detect database dialect: {e}, defaulting to 'unknown'")
            return 'unknown'

    @staticmethod
    def _translate_sql_to_dialect(sql_query: str, dialect: str) -> str:
        """
        Translate SQL query to match the target database dialect

        Args:
            sql_query: Original SQL query
            dialect: Target database dialect

        Returns:
            Translated SQL query
        """
        import re

        sql = sql_query.strip()
        sql_upper = sql.upper()

        # SQL Server specific translations
        if dialect in ['mssql', 'microsoft']:
            # Convert LIMIT to TOP
            # Pattern: LIMIT N or LIMIT N OFFSET M
            limit_pattern = r'\s+LIMIT\s+(\d+)(?:\s+OFFSET\s+\d+)?'
            match = re.search(limit_pattern, sql, re.IGNORECASE)

            if match:
                limit_value = match.group(1)
                # Remove the LIMIT clause
                sql = re.sub(limit_pattern, '', sql, flags=re.IGNORECASE)
                # Insert TOP after SELECT
                sql = re.sub(
                    r'\bSELECT\b',
                    f'SELECT TOP {limit_value}',
                    sql,
                    count=1,
                    flags=re.IGNORECASE
                )
                logger.info(f"Translated LIMIT {limit_value} to TOP {limit_value} for SQL Server")

        # PostgreSQL/MySQL translations (if needed in future)
        elif dialect in ['postgresql', 'mysql', 'sqlite']:
            # Convert TOP to LIMIT (reverse translation)
            top_pattern = r'\bSELECT\s+TOP\s+(\d+)\b'
            match = re.search(top_pattern, sql, re.IGNORECASE)

            if match:
                limit_value = match.group(1)
                sql = re.sub(top_pattern, 'SELECT', sql, flags=re.IGNORECASE)
                sql = sql + f' LIMIT {limit_value}'
                logger.info(f"Translated TOP {limit_value} to LIMIT {limit_value} for {dialect}")

        return sql

    @staticmethod
    def _convert_to_json_serializable(value: Any) -> Any:
        """
        Convert non-JSON-serializable types to JSON-serializable types.

        Handles:
        - date/datetime objects → ISO format strings
        - Decimal → float
        - bytes → string

        Args:
            value: Value to convert

        Returns:
            JSON-serializable value
        """
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        elif isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, bytes):
            return value.decode('utf-8', errors='replace')
        return value

    @staticmethod
    def query_database(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Execute a read-only SQL query on the database
        SECURITY: Only allows SELECT queries, blocks destructive operations
        AUTO-TRANSLATES: Converts SQL syntax to match database dialect
        """
        sql_query = kwargs.get('sql_query', '').strip()
        description = kwargs.get('description', 'Database query')

        # Security validation - only allow SELECT queries
        sql_upper = sql_query.upper()

        # Block dangerous keywords
        dangerous_keywords = [
            'INSERT', 'UPDATE', 'DELETE', 'DROP', 'CREATE', 'ALTER',
            'TRUNCATE', 'GRANT', 'REVOKE', 'EXEC', 'EXECUTE', 'sp_',
            'xp_', '--', ';--', '/*', '*/', 'UNION', 'INTO OUTFILE',
            'LOAD_FILE', 'INFORMATION_SCHEMA.TABLES'
        ]

        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                logger.warning(f"Blocked dangerous SQL query from user {user_id}: {sql_query}")
                return {
                    "success": False,
                    "error": f"Query contains prohibited keyword: {keyword}. Only SELECT queries are allowed."
                }

        # Must start with SELECT
        if not sql_upper.startswith('SELECT'):
            return {
                "success": False,
                "error": "Only SELECT queries are allowed"
            }

        try:
            from sqlalchemy import text

            # Detect database dialect
            dialect = BOQTools._detect_database_dialect(db)

            # Auto-translate SQL to match database dialect
            original_query = sql_query
            sql_query = BOQTools._translate_sql_to_dialect(sql_query, dialect)

            if sql_query != original_query:
                logger.info(f"Auto-translated query from: {original_query}")
                logger.info(f"                       to: {sql_query}")

            # Add safety limit if not present
            sql_upper_updated = sql_query.upper()
            if 'LIMIT' not in sql_upper_updated and 'TOP' not in sql_upper_updated:
                # For SQL Server, use TOP
                if dialect in ['mssql', 'microsoft']:
                    sql_query = sql_query.replace('SELECT', 'SELECT TOP 1000', 1)
                else:
                    # For PostgreSQL/MySQL, use LIMIT
                    sql_query = sql_query + ' LIMIT 1000'

            result = db.execute(text(sql_query))

            # Fetch results
            rows = result.fetchall()
            columns = result.keys()

            # Convert to list of dicts with JSON-serializable values
            data = []
            for row in rows:
                row_dict = {}
                for col, value in zip(columns, row):
                    row_dict[col] = BOQTools._convert_to_json_serializable(value)
                data.append(row_dict)

            logger.info(f"User {user_id} executed query: {description} - returned {len(data)} rows")

            return {
                "success": True,
                "description": description,
                "row_count": len(data),
                "columns": list(columns),
                "data": data[:100],  # Return max 100 rows to avoid huge responses
                "truncated": len(data) > 100
            }

        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            return {
                "success": False,
                "error": f"Query execution error: {str(e)}"
            }

    @staticmethod
    def get_database_schema(db: Session, user_id: int, **kwargs) -> Dict[str, Any]:
        """
        Get database table schema information
        """
        table_name = kwargs.get('table_name')

        try:
            from sqlalchemy import text, inspect

            # Get inspector
            inspector = inspect(db.bind)

            # If specific table requested
            if table_name:
                if table_name not in inspector.get_table_names():
                    return {
                        "success": False,
                        "error": f"Table '{table_name}' not found"
                    }

                columns = inspector.get_columns(table_name)

                return {
                    "success": True,
                    "table": table_name,
                    "columns": [
                        {
                            "name": col['name'],
                            "type": str(col['type']),
                            "nullable": col.get('nullable', True),
                            "default": str(col.get('default', '')) if col.get('default') else None
                        }
                        for col in columns
                    ]
                }

            # Otherwise return all tables
            tables = inspector.get_table_names()

            # Get basic info about each table
            table_info = []
            for table in tables:
                columns = inspector.get_columns(table)
                table_info.append({
                    "name": table,
                    "column_count": len(columns),
                    "columns": [col['name'] for col in columns]
                })

            return {
                "success": True,
                "tables": table_info,
                "table_count": len(tables)
            }

        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    # Additional tool methods would go here...
