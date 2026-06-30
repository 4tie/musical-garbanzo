"""
Tests for health and system endpoints.
"""
import pytest
import httpx
from httpx import ASGITransport
from app.main import app


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


async def test_health_returns_200(client):
    """Test that /health returns 200 status code."""
    response = await client.get("/health")
    assert response.status_code == 200


async def test_health_returns_her_app(client):
    """Test that /health returns app name HER."""
    response = await client.get("/health")
    data = response.json()
    assert data["app"] == "HER"


async def test_system_status_no_discord_token(client):
    """Test that /api/system/status does not include DISCORD_BOT_TOKEN."""
    response = await client.get("/api/system/status")
    data = response.json()
    assert "DISCORD_BOT_TOKEN" not in data
    assert "discord_bot_token" not in data


async def test_public_settings_no_secrets(client):
    """Test that /api/settings/public does not include secret values."""
    response = await client.get("/api/settings/public")
    data = response.json()
    
    # Ensure secret fields are not present
    assert "DISCORD_BOT_TOKEN" not in data
    assert "discord_bot_token" not in data
    assert "APP_SECRET_KEY" not in data
    assert "app_secret_key" not in data
    
    # Ensure database URL is masked
    assert data["database_url"] == "***masked***" or "***masked***" in data["database_url"]


async def test_system_status_structure(client):
    """Test that /api/system/status returns expected structure."""
    response = await client.get("/api/system/status")
    data = response.json()
    
    assert "backend" in data
    assert "database" in data
    assert "freqtrade" in data
    assert "ollama" in data
    assert "discord" in data
    assert "project_root" in data
    assert "freqtrade_user_data_dir" in data
    assert "frontend_port" in data
    assert "backend_port" in data


async def test_public_settings_structure(client):
    """Test that /api/settings/public returns expected structure."""
    response = await client.get("/api/settings/public")
    data = response.json()
    
    assert "app_name" in data
    assert "app_env" in data
    assert "backend_port" in data
    assert "frontend_port" in data
    assert "freqtrade_user_data_dir" in data
    assert "freqtrade_config_dir" in data
    assert "ollama_base_url" in data
    assert "ollama_model_configured" in data
    assert "discord_enabled" in data
    assert "discord_channel_configured" in data
    assert "database_url" in data
