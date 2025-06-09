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
    print("Running Prisma database migrations...")
    
    # Generate Prisma client
    result = subprocess.run(
        ["python", "-m", "prisma", "generate"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Prisma generate failed: {result.stderr}")
        return False
    
    print("✓ Prisma client generated")
    
    # Run migrations
    result = subprocess.run(
        ["python", "-m", "prisma", "db", "push"],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Prisma db push failed: {result.stderr}")
        return False
    
    print("✓ Database schema created successfully!")
    return True

async def main():
    """Initialize the database"""
    try:
        # Wait for PostgreSQL to be ready
        await wait_for_postgres()
        
        # Run Prisma migrations
        if run_prisma_migrate():
            print("🎉 Database initialization complete!")
        else:
            print("❌ Database initialization failed!")
            exit(1)
            
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        exit(1)

if __name__ == "__main__":
    asyncio.run(main())