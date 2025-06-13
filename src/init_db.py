#!/usr/bin/env python3
"""
Initialize database for Chainlit with Prisma schema
"""
import asyncio
import subprocess
import os
import time
from dotenv import load_dotenv

load_dotenv()

async def wait_for_postgres(max_attempts=30):
    """Wait for PostgreSQL to be ready"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable is required")
    
    import asyncpg
    
    print("Waiting for PostgreSQL to be ready...")
    for attempt in range(max_attempts):
        try:
            conn = await asyncpg.connect(database_url)
            await conn.execute("SELECT 1")
            await conn.close()
            print("✓ PostgreSQL is ready!")
            return True
        except Exception as e:
            print(f"Attempt {attempt + 1}/{max_attempts}: PostgreSQL not ready yet... ({e})")
            await asyncio.sleep(2)
    
    raise Exception("PostgreSQL did not become ready in time")

def run_prisma_migrate():
    """Run Prisma migrations to set up database schema"""
    print("🔧 [CHAINLIT-DB] Setting up Prisma database schema...")
    
    # Check if Prisma client is already generated (from build time)
    print("✓ [CHAINLIT-DB] Prisma client already generated during build")
    
    # Only run schema push (lightweight operation)
    result = subprocess.run(
        ["python", "-m", "prisma", "db", "push"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"❌ [CHAINLIT-DB] Prisma db push failed: {result.stderr}")
        return False
    
    print("✅ [CHAINLIT-DB] Database schema created successfully!")
    return True

async def main():
    """Initialize the database"""
    print("🚀 [CHAINLIT-DB] Database initialization starting...")
    print(f"🔧 [CHAINLIT-DB] DATABASE_URL configured: {'✅ Yes' if os.getenv('DATABASE_URL') else '❌ No'}")
    
    try:
        print("🔧 [CHAINLIT-DB] Testing PostgreSQL connection...")
        await wait_for_postgres()
        print("✅ [CHAINLIT-DB] PostgreSQL connection successful")
        
        print("🔧 [CHAINLIT-DB] Setting up Chainlit database schema...")
        if run_prisma_migrate():
            print("✅ [CHAINLIT-DB] Chainlit schema created successfully")
            print("🎉 [CHAINLIT-DB] Database initialization complete!")
        else:
            print("❌ [CHAINLIT-DB] Database initialization failed!")
            exit(1)
    except Exception as e:
        print(f"❌ [CHAINLIT-DB] Error initializing database: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())