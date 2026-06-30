#!/usr/bin/env python3
"""
Initialize HER database.
"""
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.db.sqlite import get_database_path, initialize_database, database_exists
from app.db.migrations import run_migrations


def main():
    """Initialize the database and print status."""
    print("Initializing HER database...")
    
    # Get database path
    db_path = get_database_path()
    print(f"Database path: {db_path}")
    
    # Check if database exists
    exists = database_exists()
    print(f"Database exists: {exists}")
    
    # Initialize database
    success = initialize_database()
    
    if success:
        print("Database initialized successfully")
        
        # Verify tables
        import sqlite3
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        print("Created/verified tables:")
        for table in tables:
            print(f"  - {table}")
    else:
        print("Failed to initialize database")
        sys.exit(1)


if __name__ == "__main__":
    main()
