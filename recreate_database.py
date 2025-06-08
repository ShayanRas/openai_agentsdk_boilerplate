#!/usr/bin/env python3
"""
Database Recreation Script
This script drops all existing tables and recreates them with the proper schema.
"""

import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DB_URL", "postgresql://postgres.wcummuhdtjjvuukmzjyx:HoomanKhare2008!@aws-0-us-east-1.pooler.supabase.com:6543/postgres")

async def recreate_database():
    """Drop all tables and recreate with proper schema"""
    print("🔄 Connecting to database...")
    
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        print("🗑️  Dropping existing tables...")
        
        # Drop tables in reverse order of dependencies
        drop_statements = [
            "DROP TABLE IF EXISTS text_history CASCADE",
            "DROP TABLE IF EXISTS api_history CASCADE", 
            "DROP TABLE IF EXISTS threads CASCADE"
        ]
        
        for statement in drop_statements:
            await conn.execute(statement)
            print(f"   ✓ {statement}")
        
        print("\n🏗️  Creating tables with proper schema...")
        
        # Create threads table
        await conn.execute("""
            CREATE TABLE threads (
                id VARCHAR(255) PRIMARY KEY,
                thread_type VARCHAR(50) NOT NULL CHECK (thread_type IN ('api', 'text', 'temp')),
                user_id VARCHAR(255),
                user_name VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                last_activity TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            )
        """)
        print("   ✓ Created threads table")
        
        # Create api_history table
        await conn.execute("""
            CREATE TABLE api_history (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                thread_id VARCHAR(255) NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                response_id VARCHAR(255) NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL,
                expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
                UNIQUE(thread_id, response_id)
            )
        """)
        print("   ✓ Created api_history table")
        
        # Create text_history table
        await conn.execute("""
            CREATE TABLE text_history (
                id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
                thread_id VARCHAR(255) NOT NULL REFERENCES threads(id) ON DELETE CASCADE,
                user_input TEXT NOT NULL,
                assistant_response TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                sequence_number INTEGER NOT NULL
            )
        """)
        print("   ✓ Created text_history table")
        
        print("\n📊 Creating indexes...")
        
        # Create indexes
        indexes = [
            ("idx_threads_user", "CREATE INDEX idx_threads_user ON threads(user_id, last_activity DESC)"),
            ("idx_api_history_thread_expires", "CREATE INDEX idx_api_history_thread_expires ON api_history(thread_id, expires_at DESC)"),  
            ("idx_text_history_thread_seq", "CREATE INDEX idx_text_history_thread_seq ON text_history(thread_id, sequence_number)")
        ]
        
        for index_name, statement in indexes:
            await conn.execute(statement)
            print(f"   ✓ Created {index_name}")
        
        print("\n✅ Database recreation completed successfully!")
        print("📋 Schema summary:")
        print("   • threads: id, thread_type, user_id, user_name, created_at, last_activity")
        print("   • api_history: id, thread_id, response_id, created_at, expires_at")
        print("   • text_history: id, thread_id, user_input, assistant_response, created_at, sequence_number")
        print("   • All foreign keys and indexes properly configured")
        
    except Exception as e:
        print(f"❌ Error during database recreation: {e}")
        raise
    
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(recreate_database())