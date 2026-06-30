"""
SQLite connection management for HER backend.
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings


def get_database_path() -> Path:
    """Get the absolute path to the SQLite database.
    
    HER always uses SQLite.  If DATABASE_URL is not a SQLite URL (e.g. because
    the host environment injects a PostgreSQL URL), fall back to the default
    SQLite path so the runtime always uses the correct file.
    """
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite:///"):
        db_path = db_url.replace("sqlite:///", "")
    else:
        # Non-SQLite URL in environment (e.g. Replit injects a PostgreSQL URL).
        # HER is SQLite-only; use the default path.
        db_path = "./data/her.db"

    # Convert to absolute path if relative
    if not Path(db_path).is_absolute():
        db_path = str(settings.project_root / db_path)

    return Path(db_path)


def ensure_database_directory() -> None:
    """Ensure the database directory exists."""
    db_path = get_database_path()
    db_path.parent.mkdir(parents=True, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    """
    Get a SQLite connection with row factory for dict-like access.
    
    Returns:
        SQLite connection with row factory configured
    """
    ensure_database_directory()
    db_path = get_database_path()
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row  # Enable dict-like access
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database() -> bool:
    """
    Initialize the database schema.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        from app.db.migrations import run_migrations
        run_migrations()
        return True
    except Exception as e:
        print(f"Failed to initialize database: {e}")
        return False


def database_exists() -> bool:
    """Check if the database file exists."""
    return get_database_path().exists()


def dict_from_row(row: sqlite3.Row) -> Dict[str, Any]:
    """
    Convert a sqlite3.Row to a dictionary.
    
    Args:
        row: SQLite row object
    
    Returns:
        Dictionary representation of the row
    """
    return dict(row)


def execute(query: str, params: Tuple = ()) -> sqlite3.Cursor:
    """
    Execute a SQL query with parameters.
    
    Args:
        query: SQL query string
        params: Query parameters tuple
    
    Returns:
        SQLite cursor
    
    Raises:
        Exception: If query execution fails
    """
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        conn.commit()
        return cursor
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def execute_many(query: str, params_list: List[Tuple]) -> sqlite3.Cursor:
    """
    Execute a SQL query multiple times with different parameters.
    
    Args:
        query: SQL query string
        params_list: List of parameter tuples
    
    Returns:
        SQLite cursor
    
    Raises:
        Exception: If query execution fails
    """
    conn = get_connection()
    try:
        cursor = conn.executemany(query, params_list)
        conn.commit()
        return cursor
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_one(query: str, params: Tuple = ()) -> Optional[Dict[str, Any]]:
    """
    Execute a query and fetch a single row.
    
    Args:
        query: SQL query string
        params: Query parameters tuple
    
    Returns:
        Dictionary representing the row, or None if no row found
    """
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        row = cursor.fetchone()
        return dict_from_row(row) if row else None
    finally:
        conn.close()


def fetch_all(query: str, params: Tuple = ()) -> List[Dict[str, Any]]:
    """
    Execute a query and fetch all rows.
    
    Args:
        query: SQL query string
        params: Query parameters tuple
    
    Returns:
        List of dictionaries representing rows
    """
    conn = get_connection()
    try:
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        return [dict_from_row(row) for row in rows]
    finally:
        conn.close()


@contextmanager
def transaction():
    """
    Context manager for database transactions.
    
    Yields a connection that will be committed on success
    or rolled back on failure.
    
    Usage:
        with transaction() as conn:
            conn.execute("INSERT INTO ...")
            conn.execute("UPDATE ...")
            # Changes committed automatically on exit
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
