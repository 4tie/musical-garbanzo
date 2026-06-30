"""
Tests for database bootstrap and system service.
"""
import os
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.db.sqlite import get_database_path, get_connection, initialize_database, database_exists
from app.db.migrations import (
    upsert_app_meta,
    get_app_meta,
    insert_system_event,
    get_recent_system_events,
    upsert_local_setting,
    get_public_local_settings,
)
from app.services.system_service import (
    get_system_status,
    record_system_event,
    get_recent_events,
    get_public_settings_status,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing."""
    original_db_url = settings.DATABASE_URL
    with tempfile.TemporaryDirectory() as tmpdir:
        temp_db_path = Path(tmpdir) / "test.db"
        settings.DATABASE_URL = f"sqlite:///{temp_db_path}"
        
        # Initialize database
        initialize_database()
        
        yield temp_db_path
        
        # Cleanup
        settings.DATABASE_URL = original_db_url
        if temp_db_path.exists():
            temp_db_path.unlink()


def test_database_initializes(temp_db):
    """Test that database initializes successfully."""
    assert temp_db.exists()
    assert database_exists()


def test_app_meta_table_exists(temp_db):
    """Test that app_meta table exists and works."""
    # Insert test data
    upsert_app_meta("test_key", "test_value")
    
    # Retrieve it
    value = get_app_meta("test_key")
    assert value == "test_value"


def test_system_events_table_exists(temp_db):
    """Test that system_events table exists and works."""
    # Insert test event
    event_id = insert_system_event(
        level="info",
        source="test",
        message="Test message"
    )
    
    assert event_id is not None
    
    # Retrieve recent events
    events = get_recent_system_events(limit=10)
    assert len(events) == 1
    assert events[0]["level"] == "info"
    assert events[0]["source"] == "test"
    assert events[0]["message"] == "Test message"


def test_local_settings_table_exists(temp_db):
    """Test that local_settings table exists and works."""
    # Insert test setting
    upsert_local_setting("test_setting", {"key": "value"}, is_secret=False)
    
    # Retrieve public settings
    public_settings = get_public_local_settings()
    assert "test_setting" in public_settings
    assert public_settings["test_setting"] == {"key": "value"}


def test_can_insert_system_event(temp_db):
    """Test that system events can be inserted."""
    event_id = record_system_event(
        level="warning",
        source="backend",
        message="Test warning",
        details={"test": "data"}
    )
    
    assert event_id is not None
    
    events = get_recent_events(limit=10)
    assert len(events) >= 1
    assert events[0]["level"] == "warning"


def test_public_settings_do_not_expose_secrets(temp_db):
    """Test that public settings do not expose secret values."""
    # Insert a secret setting
    upsert_local_setting("secret_key", {"token": "secret123"}, is_secret=True)
    
    # Insert a public setting
    upsert_local_setting("public_key", {"value": "public123"}, is_secret=False)
    
    # Get public settings
    public_settings = get_public_local_settings()
    
    # Secret should not be present
    assert "secret_key" not in public_settings
    
    # Public setting should be present
    assert "public_key" in public_settings
    assert public_settings["public_key"] == {"value": "public123"}


def test_system_status_includes_database_status(temp_db):
    """Test that system status includes database information."""
    status = get_system_status()
    
    assert "database" in status
    assert "database_path" in status
    assert status["database"] in ["healthy", "missing"]


def test_system_status_does_not_expose_secrets():
    """Test that system status does not expose secret values."""
    status = get_system_status()
    
    # Ensure no secret fields are present
    assert "DISCORD_BOT_TOKEN" not in status
    assert "discord_bot_token" not in status
    assert "APP_SECRET_KEY" not in status
    assert "app_secret_key" not in status


def test_public_settings_status_does_not_expose_secrets():
    """Test that public settings status does not expose secret values."""
    settings_status = get_public_settings_status()
    
    # Ensure no secret fields are present
    assert "DISCORD_BOT_TOKEN" not in settings_status
    assert "discord_bot_token" not in settings_status
    assert "APP_SECRET_KEY" not in settings_status
    assert "app_secret_key" not in settings_status
    
    # Database URL should be masked
    assert "database_url" in settings_status
    assert "***masked***" in settings_status["database_url"]
