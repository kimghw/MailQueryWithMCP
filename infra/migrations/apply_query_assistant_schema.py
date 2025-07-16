#!/usr/bin/env python3
"""
Query Assistant Schema Migration Script
Applies the query_assistant_schema.sql to the database
"""

import sqlite3
import os
import sys
from datetime import datetime
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from infra.core.config import Config


def apply_migration():
    """Apply the query assistant schema migration"""
    
    # Get database path from config
    config = Config()
    db_path = config.database_path
    
    print(f"Applying query assistant schema to database: {db_path}")
    
    # Read the migration SQL
    migration_file = Path(__file__).parent / "query_assistant_schema.sql"
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Connect to database and apply migration
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Execute the migration
        cursor.executescript(migration_sql)
        conn.commit()
        print("✓ Query assistant schema applied successfully")
        
        # Verify tables were created
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name IN ('fallback_queries', 'preprocessing_dataset')
        """)
        created_tables = cursor.fetchall()
        print(f"✓ Created tables: {[t[0] for t in created_tables]}")
        
        # Verify initial data
        cursor.execute("SELECT COUNT(*) FROM preprocessing_dataset")
        row_count = cursor.fetchone()[0]
        print(f"✓ Inserted {row_count} preprocessing rules")
        
    except Exception as e:
        conn.rollback()
        print(f"✗ Error applying migration: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    apply_migration()