#!/usr/bin/env python3
"""
Utility to migrate existing file-based history to PostgreSQL database
"""
import asyncio
import os
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from database import db_manager, ensure_db_initialized

API_HISTORY_DIR = "api_history_threads"
TEXT_HISTORY_DIR = "text_history_threads"

async def migrate_api_history():
    """Migrate API history files to database"""
    print("Starting API history migration...")
    
    if not os.path.exists(API_HISTORY_DIR):
        print(f"No {API_HISTORY_DIR} directory found. Skipping API history migration.")
        return
    
    files_migrated = 0
    entries_migrated = 0
    
    for filename in os.listdir(API_HISTORY_DIR):
        if not filename.endswith('.json'):
            continue
            
        thread_id = filename[:-5]  # Remove .json extension
        file_path = os.path.join(API_HISTORY_DIR, filename)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                if not content:
                    print(f"Empty file: {filename}, skipping...")
                    continue
                    
                history = json.loads(content)
                
            # Create thread in database (no user_id for existing data)
            await db_manager.create_thread(thread_id, 'api', user_id=None)
            
            # Migrate each history entry
            for entry in history:
                try:
                    response_id = entry['id']
                    created_at = datetime.fromisoformat(entry['created_at'])
                    expires_at = datetime.fromisoformat(entry['expires_at'])
                    
                    # Ensure timezone info
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    if expires_at.tzinfo is None:
                        expires_at = expires_at.replace(tzinfo=timezone.utc)
                    
                    await db_manager.add_api_history_entry(
                        thread_id, response_id, created_at, expires_at
                    )
                    entries_migrated += 1
                    
                except Exception as e:
                    print(f"Error migrating entry in {filename}: {e}")
                    continue
            
            files_migrated += 1
            print(f"Migrated {filename} with {len(history)} entries")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    print(f"API history migration complete: {files_migrated} files, {entries_migrated} entries")

async def migrate_text_history():
    """Migrate text history files to database"""
    print("\nStarting text history migration...")
    
    if not os.path.exists(TEXT_HISTORY_DIR):
        print(f"No {TEXT_HISTORY_DIR} directory found. Skipping text history migration.")
        return
    
    files_migrated = 0
    conversations_migrated = 0
    
    for filename in os.listdir(TEXT_HISTORY_DIR):
        if not filename.endswith('.txt'):
            continue
            
        thread_id = filename[:-4]  # Remove .txt extension
        file_path = os.path.join(TEXT_HISTORY_DIR, filename)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if not content.strip():
                print(f"Empty file: {filename}, skipping...")
                continue
            
            # Create thread in database (no user_id for existing data)
            await db_manager.create_thread(thread_id, 'text', user_id=None)
            
            # Parse conversations
            lines = content.strip().split('\n')
            i = 0
            conversation_count = 0
            
            while i < len(lines):
                # Look for User: line
                if lines[i].startswith('User: '):
                    user_input = lines[i][6:]  # Remove "User: " prefix
                    
                    # Look for Assistant: line
                    if i + 1 < len(lines) and lines[i + 1].startswith('Assistant: '):
                        assistant_response = lines[i + 1][11:]  # Remove "Assistant: " prefix
                        
                        # Save to database
                        await db_manager.add_text_history_entry(
                            thread_id, user_input, assistant_response
                        )
                        conversation_count += 1
                        conversations_migrated += 1
                        
                        i += 2  # Skip both lines
                    else:
                        print(f"Warning: User message without Assistant response in {filename} at line {i+1}")
                        i += 1
                else:
                    i += 1
            
            files_migrated += 1
            print(f"Migrated {filename} with {conversation_count} conversations")
            
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            continue
    
    print(f"Text history migration complete: {files_migrated} files, {conversations_migrated} conversations")

async def verify_migration():
    """Verify migration by checking some data"""
    print("\nVerifying migration...")
    
    # Check a few threads
    async with db_manager.acquire() as conn:
        # Count threads
        thread_count = await conn.fetchval("SELECT COUNT(*) FROM threads")
        api_history_count = await conn.fetchval("SELECT COUNT(*) FROM api_history")
        text_history_count = await conn.fetchval("SELECT COUNT(*) FROM text_history")
        
        print(f"Total threads: {thread_count}")
        print(f"Total API history entries: {api_history_count}")
        print(f"Total text history entries: {text_history_count}")
        
        # Show sample data
        print("\nSample threads:")
        threads = await conn.fetch("SELECT id, thread_type, created_at FROM threads LIMIT 5")
        for thread in threads:
            print(f"  {thread['id']} ({thread['thread_type']}) - Created: {thread['created_at']}")

async def main():
    """Main migration function"""
    print("Starting history migration to PostgreSQL...")
    
    # Initialize database connection
    await ensure_db_initialized()
    
    try:
        # Run migrations
        await migrate_api_history()
        await migrate_text_history()
        
        # Verify results
        await verify_migration()
        
        print("\nMigration complete!")
        print("You can now safely remove or archive the old history directories.")
        
    finally:
        # Clean up
        await db_manager.close()

if __name__ == "__main__":
    asyncio.run(main())