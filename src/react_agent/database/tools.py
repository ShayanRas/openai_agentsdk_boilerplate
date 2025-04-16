"""
Database tools for interacting with the Supabase PostgreSQL database.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import InjectedToolArg
from typing_extensions import Annotated

from react_agent.database.connection import get_db_connection

# Configure logging
logger = logging.getLogger(__name__)

async def db_query(
    query: str,
    params: Optional[List[Any]] = None,
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> List[Dict[str, Any]]:
    """Execute a SQL query against the database.
    
    Use this tool to run read-only SQL queries against the Supabase PostgreSQL database.
    Only SELECT queries are allowed for security reasons.
    
    Args:
        query: The SQL query to execute (must be a SELECT query).
        params: Optional list of parameters to bind to the query.
        config: Runtime configuration (automatically injected).
    
    Returns:
        A list of dictionaries representing the query results.
    """
    # Security check: only allow SELECT queries
    if not query.strip().lower().startswith("select"):
        raise ValueError("Only SELECT queries are allowed for security reasons.")
    
    try:
        # This will attempt to initialize the pool if it's not already initialized
        from react_agent.database.connection import get_db_pool
        
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                if params:
                    await cur.execute(query, params)
                else:
                    await cur.execute(query)
                
                results = await cur.fetchall()
                return results
    except RuntimeError as e:
        # This happens when the database connection pool couldn't be initialized
        logger.error(f"Database connection not available: {e}")
        return [{
            "error": "Database connection not available",
            "message": "The database connection could not be established. Please check your database configuration."
        }]
    except Exception as e:
        logger.error(f"Error executing database query: {e}")
        return [{
            "error": "Database query error",
            "message": str(e)
        }]

async def db_get_tables(
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> List[Dict[str, Any]]:
    """Get a list of tables in the database.
    
    Use this tool to discover the available tables in the Supabase PostgreSQL database.
    
    Args:
        config: Runtime configuration (automatically injected).
    
    Returns:
        A list of dictionaries containing table information.
    """
    try:
        query = """
        SELECT 
            table_schema,
            table_name,
            table_type
        FROM 
            information_schema.tables
        WHERE 
            table_schema NOT IN ('pg_catalog', 'information_schema')
        ORDER BY 
            table_schema, table_name
        """
        
        return await db_query(query, None, config=config)
    except Exception as e:
        logger.error(f"Error getting tables: {e}")
        return [{
            "error": "Database error",
            "message": str(e)
        }]

async def db_get_table_schema(
    table_name: str,
    *, 
    config: Annotated[RunnableConfig, InjectedToolArg]
) -> List[Dict[str, Any]]:
    """Get the schema of a specific table.
    
    Use this tool to discover the columns and their types for a specific table.
    
    Args:
        table_name: The name of the table to get the schema for.
        config: Runtime configuration (automatically injected).
    
    Returns:
        A list of dictionaries containing column information.
    """
    try:
        # Extract schema and table name if provided in format "schema.table"
        parts = table_name.split(".")
        if len(parts) == 2:
            schema_name, table_name = parts
        else:
            schema_name = "public"  # Default schema
        
        query = """
        SELECT 
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM 
            information_schema.columns
        WHERE 
            table_schema = %s AND table_name = %s
        ORDER BY 
            ordinal_position
        """
        
        return await db_query(query, [schema_name, table_name], config=config)
    except Exception as e:
        logger.error(f"Error getting table schema: {e}")
        return [{
            "error": "Database error",
            "message": str(e)
        }]
