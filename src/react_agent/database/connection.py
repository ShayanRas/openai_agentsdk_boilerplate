"""
Database connection pool management for Supabase PostgreSQL database.
"""

import os
import logging
from typing import Optional
import asyncio
from contextlib import asynccontextmanager
import dotenv

import psycopg_pool
from psycopg import AsyncConnection
from psycopg.rows import dict_row

# Load environment variables
dotenv.load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

# Global connection pool
_pool: Optional[psycopg_pool.AsyncConnectionPool] = None


def initialize_db_pool() -> Optional[psycopg_pool.AsyncConnectionPool]:
    """Initialize the global database connection pool.
    
    This should be called once at application startup.
    
    Returns:
        The initialized connection pool, or None if initialization failed.
    """
    global _pool
    
    if _pool is not None:
        logger.info("Database pool already initialized")
        return _pool
    
    # Get database connection string from environment variables
    db_url = os.getenv("SUPABASE_DB_URL")
    
    if not db_url:
        logger.warning(
            "SUPABASE_DB_URL environment variable is not set. "
            "Database functionality will be disabled."
        )
        return None
    
    logger.info("Initializing database connection pool")
    
    try:
        # Create the connection pool
        _pool = psycopg_pool.AsyncConnectionPool(
            conninfo=db_url,
            min_size=1,
            max_size=10,
            kwargs={"row_factory": dict_row}
        )
        logger.info("Database connection pool initialized successfully")
        return _pool
    except Exception as e:
        logger.error(f"Failed to initialize database connection pool: {e}")
        return None


def get_db_pool() -> psycopg_pool.AsyncConnectionPool:
    """Get the global database connection pool.
    
    Returns:
        The database connection pool.
        
    Raises:
        RuntimeError: If the pool has not been initialized or initialization failed.
    """
    global _pool
    
    if _pool is None:
        # Try to initialize the pool if it hasn't been initialized yet
        initialize_db_pool()
        
        # If it's still None after initialization attempt, raise an error
        if _pool is None:
            raise RuntimeError(
                "Database pool could not be initialized. "
                "Check your database connection settings."
            )
    
    return _pool


@asynccontextmanager
async def get_db_connection():
    """Get a database connection from the pool.
    
    This is an async context manager that acquires a connection from the pool,
    yields it, and then returns it to the pool when the context exits.
    
    Yields:
        An AsyncConnection object from the pool.
        
    Raises:
        RuntimeError: If the pool has not been initialized.
    """
    pool = get_db_pool()
    
    async with pool.connection() as conn:
        yield conn


async def test_connection() -> bool:
    """Test the database connection.
    
    Returns:
        True if the connection is successful, False otherwise.
    """
    try:
        async with get_db_connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("SELECT 1")
                result = await cur.fetchone()
                return result is not None and result[0] == 1
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        return False
