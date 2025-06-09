import os
import asyncio
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager

import asyncpg
from asyncpg import Pool
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DB_URL")

class DatabaseManager:
    def __init__(self):
        self.pool: Optional[Pool] = None
        self.schema_initialized = False
    
    async def initialize(self):
        """Initialize the database connection pool"""
        if not self.pool:
            self.pool = await asyncpg.create_pool(
                DATABASE_URL,
                min_size=1,
                max_size=10,
                command_timeout=60,
                statement_cache_size=100  # Enable prepared statements for local PostgreSQL
            )
            await self.ensure_schema()
    
    async def close(self):
        """Close the database connection pool"""
        if self.pool:
            await self.pool.close()
            self.pool = None
    
    async def ensure_schema(self):
        """Ensure database tables exist with proper schema"""
        if self.schema_initialized:
            return
            
        async with self.pool.acquire() as conn:
            # Create agent schema for our backend data
            await conn.execute("CREATE SCHEMA IF NOT EXISTS agent")
            
            # For fresh deployments, drop and recreate tables to ensure proper schema
            # This is safe for a boilerplate since users start fresh
            await conn.execute("DROP TABLE IF EXISTS agent.text_history CASCADE")
            await conn.execute("DROP TABLE IF EXISTS agent.api_history CASCADE")
            await conn.execute("DROP TABLE IF EXISTS agent.threads CASCADE")
            
            # Create threads table with user_id from start
            await conn.execute("""
                CREATE TABLE agent.threads (
                    id VARCHAR(255) PRIMARY KEY,
                    thread_type VARCHAR(50) NOT NULL CHECK (thread_type IN ('api', 'text', 'temp')),
                    user_id VARCHAR(255),
                    user_name VARCHAR(255),
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
                )
            """)
            
            # Create index for user threads
            await conn.execute("""
                CREATE INDEX idx_threads_user ON agent.threads(user_id, last_activity DESC)
            """)
            
            # Create api_history table
            await conn.execute("""
                CREATE TABLE agent.api_history (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL REFERENCES agent.threads(id) ON DELETE CASCADE,
                    response_id VARCHAR(255) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                    UNIQUE(thread_id, response_id)
                )
            """)
            
            # Create text_history table
            await conn.execute("""
                CREATE TABLE agent.text_history (
                    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                    thread_id VARCHAR(255) NOT NULL REFERENCES agent.threads(id) ON DELETE CASCADE,
                    user_input TEXT NOT NULL,
                    assistant_response TEXT NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                    sequence_number INTEGER NOT NULL
                )
            """)
            
            # Create indexes
            await conn.execute("""
                CREATE INDEX idx_api_history_thread_expires 
                ON agent.api_history(thread_id, expires_at DESC)
            """)
            
            await conn.execute("""
                CREATE INDEX idx_text_history_thread_seq 
                ON agent.text_history(thread_id, sequence_number)
            """)
            
        self.schema_initialized = True
    
    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool"""
        async with self.pool.acquire() as conn:
            yield conn
    
    # Thread management methods
    async def create_thread(self, thread_id: str, thread_type: str, user_id: Optional[str] = None, user_name: Optional[str] = None) -> None:
        """Create a new thread entry with optional user association"""
        async with self.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent.threads (id, thread_type, user_id, user_name)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    last_activity = NOW()
            """, thread_id, thread_type, user_id, user_name)
    
    async def get_thread(self, thread_id: str) -> Optional[Dict[str, Any]]:
        """Get thread information"""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT id, thread_type, user_id, user_name, created_at, last_activity
                FROM agent.threads
                WHERE id = $1
            """, thread_id)
            return dict(row) if row else None
    
    async def get_user_threads(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all threads for a user"""
        async with self.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, thread_type, user_name, created_at, last_activity
                FROM agent.threads
                WHERE user_id = $1
                ORDER BY last_activity DESC
            """, user_id)
            return [dict(row) for row in rows]
    
    # API history methods
    async def add_api_history_entry(self, thread_id: str, response_id: str, created_at: datetime, expires_at: datetime) -> None:
        """Add an API history entry"""
        async with self.acquire() as conn:
            await conn.execute("""
                INSERT INTO agent.api_history (thread_id, response_id, created_at, expires_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (thread_id, response_id) DO NOTHING
            """, thread_id, response_id, created_at, expires_at)
            
            # Update thread last_activity
            await conn.execute("""
                UPDATE agent.threads SET last_activity = NOW() WHERE id = $1
            """, thread_id)
    
    async def get_latest_valid_api_response(self, thread_id: str) -> Optional[str]:
        """Get the latest valid (non-expired) API response ID"""
        async with self.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT response_id
                FROM agent.api_history
                WHERE thread_id = $1 AND expires_at > NOW()
                ORDER BY created_at DESC
                LIMIT 1
            """, thread_id)
            return row['response_id'] if row else None
    
    async def get_api_history(self, thread_id: str) -> List[Dict[str, Any]]:
        """Get all API history entries for a thread"""
        async with self.acquire() as conn:
            rows = await conn.fetch("""
                SELECT response_id, created_at, expires_at
                FROM agent.api_history
                WHERE thread_id = $1
                ORDER BY created_at DESC
            """, thread_id)
            return [dict(row) for row in rows]
    
    # Text history methods
    async def add_text_history_entry(self, thread_id: str, user_input: str, assistant_response: str) -> None:
        """Add a text history entry"""
        async with self.acquire() as conn:
            # Get the next sequence number
            row = await conn.fetchrow("""
                SELECT COALESCE(MAX(sequence_number), 0) + 1 as next_seq
                FROM agent.text_history
                WHERE thread_id = $1
            """, thread_id)
            next_seq = row['next_seq']
            
            await conn.execute("""
                INSERT INTO agent.text_history (thread_id, user_input, assistant_response, sequence_number)
                VALUES ($1, $2, $3, $4)
            """, thread_id, user_input, assistant_response, next_seq)
            
            # Update thread last_activity
            await conn.execute("""
                UPDATE agent.threads SET last_activity = NOW() WHERE id = $1
            """, thread_id)
    
    async def get_text_history(self, thread_id: str) -> str:
        """Get formatted text history for a thread"""
        async with self.acquire() as conn:
            rows = await conn.fetch("""
                SELECT user_input, assistant_response
                FROM agent.text_history
                WHERE thread_id = $1
                ORDER BY sequence_number
            """, thread_id)
            
            if not rows:
                return ""
            
            history_parts = []
            for row in rows:
                history_parts.append(f"User: {row['user_input']}")
                history_parts.append(f"Assistant: {row['assistant_response']}")
                history_parts.append("")
            
            return "\n".join(history_parts)

# Global database manager instance
db_manager = DatabaseManager()

# Helper functions for backwards compatibility
async def ensure_db_initialized():
    """Ensure database is initialized before use"""
    if not db_manager.pool:
        await db_manager.initialize()