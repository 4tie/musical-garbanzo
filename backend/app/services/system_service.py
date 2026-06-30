"""
System service for managing system status, events, and settings.
"""
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.db.sqlite import database_exists, get_database_path
from app.db.migrations import (
    upsert_app_meta,
    get_app_meta,
    insert_system_event,
    get_recent_system_events,
    get_public_local_settings,
)


def get_system_status() -> dict:
    """
    Get comprehensive system status.
    
    Returns:
        Dict containing system status information
    """
    # Check database status
    db_exists = database_exists()
    db_status = "healthy" if db_exists else "missing"
    
    # Check Freqtrade status
    freqtrade_status = "configured" if settings.freqtrade_configured else "missing"
    
    # Check Ollama status
    ollama_status = "configured" if settings.ollama_configured else "missing"
    
    # Check Discord status
    if settings.discord_enabled:
        discord_status = "configured" if settings.discord_channel_configured else "missing"
    else:
        discord_status = "disabled"
    
    # Check docs foundation
    docs_path = settings.project_root / "docs"
    docs_exist = docs_path.exists() and docs_path.is_dir()
    
    # Get project version from app_meta
    project_version = get_app_meta("project_version") or "unknown"
    
    return {
        "backend": "healthy",
        "database": db_status,
        "database_path": str(get_database_path()),
        "freqtrade": freqtrade_status,
        "ollama": ollama_status,
        "discord": discord_status,
        "docs_foundation_detected": docs_exist,
        "project_version": project_version,
        "project_root": str(settings.project_root),
        "freqtrade_user_data_dir": str(settings.freqtrade_user_data_dir_path),
        "frontend_port": settings.FRONTEND_PORT,
        "backend_port": settings.BACKEND_PORT,
    }


def record_system_event(level: str, source: str, message: str, details: Optional[dict] = None) -> str:
    """
    Record a system event.
    
    Args:
        level: Event level (info, warning, error, etc.)
        source: Event source (backend, frontend, etc.)
        message: Event message
        details: Optional details as dict
    
    Returns:
        The event ID
    """
    return insert_system_event(level, source, message, details)


def get_recent_events(limit: int = 50) -> list:
    """
    Get recent system events.
    
    Args:
        limit: Maximum number of events to return
    
    Returns:
        List of system event dicts
    """
    return get_recent_system_events(limit)


def get_public_settings_status() -> dict:
    """
    Get public settings status without exposing secret values.
    
    Returns:
        Dict containing public-safe settings information
    """
    # Mask database URL
    db_url = settings.DATABASE_URL
    if "://" in db_url:
        parts = db_url.split("://")
        masked_url = f"{parts[0]}://***masked***"
    else:
        masked_url = "***masked***"
    
    # Get any public local settings from database
    public_local_settings = get_public_local_settings()
    
    return {
        "app_name": settings.APP_NAME,
        "app_env": settings.APP_ENV,
        "backend_port": settings.BACKEND_PORT,
        "frontend_port": settings.FRONTEND_PORT,
        "freqtrade_user_data_dir": str(settings.freqtrade_user_data_dir_path),
        "freqtrade_config_dir": str(settings.freqtrade_config_dir_path),
        "ollama_base_url": settings.OLLAMA_BASE_URL,
        "ollama_model_configured": settings.ollama_configured,
        "discord_enabled": settings.discord_enabled,
        "discord_channel_configured": settings.discord_channel_configured,
        "database_url": masked_url,
        "local_settings_count": len(public_local_settings),
    }


def initialize_backend() -> None:
    """
    Initialize backend on startup.
    Sets up database, app_meta, and records startup event.
    """
    from app.db.sqlite import initialize_database
    
    # Initialize database
    initialize_database()
    
    # Set app_meta
    upsert_app_meta("app_name", settings.APP_NAME)
    upsert_app_meta("project_version", "0.3.0")
    upsert_app_meta("schema_version", "0.3.0")
    upsert_app_meta("setup_part", "Part 03")
    upsert_app_meta("database_layer", "sqlite3_repositories")
    
    # Record startup event
    record_system_event(
        level="info",
        source="backend",
        message="Backend started"
    )
