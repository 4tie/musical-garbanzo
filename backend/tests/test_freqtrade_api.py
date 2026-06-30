"""
Tests for Freqtrade API endpoints.
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


async def test_status_endpoint_works_when_freqtrade_missing(client):
    """Test that status endpoint works when Freqtrade is missing."""
    response = await client.get("/api/freqtrade/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data
    assert "executable_available" in data
    assert "version" in data
    assert "workspace_valid" in data
    assert "allowed_commands" in data
    assert "forbidden_commands" in data
    assert "real_smoke_enabled" in data
    assert "warnings" in data


async def test_version_endpoint_controlled_when_missing(client):
    """Test that version endpoint returns controlled response when Freqtrade is missing."""
    response = await client.get("/api/freqtrade/version")
    
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "available" in data
    assert "error" in data


async def test_workspace_endpoint_works(client):
    """Test that workspace endpoint works."""
    response = await client.get("/api/freqtrade/workspace")
    
    assert response.status_code == 200
    data = response.json()
    assert "valid" in data
    assert "user_data_dir" in data
    assert "config_dir" in data
    assert "missing_dirs" in data
    assert "created_dirs" in data


async def test_strategies_endpoint_works_with_local_files(client):
    """Test that strategies endpoint works with local files."""
    response = await client.get("/api/freqtrade/strategies")
    
    assert response.status_code == 200
    data = response.json()
    assert "strategies" in data
    assert "source" in data
    assert isinstance(data["strategies"], list)


async def test_strategy_detail_endpoint(client):
    """Test strategy detail endpoint."""
    response = await client.get("/api/freqtrade/strategies/MyStrategy")
    
    assert response.status_code == 200
    data = response.json()
    assert "strategy" in data
    assert "error" in data


async def test_data_overview_endpoint(client):
    """Test data overview endpoint."""
    response = await client.get("/api/freqtrade/data")
    
    assert response.status_code == 200
    data = response.json()
    assert "data_dir" in data
    assert "exists" in data
    assert "pairs_count" in data


async def test_config_generation_endpoint(client):
    """Test config generation endpoint."""
    request = {
        "strategy_name": "MyStrategy",
        "timeframe": "1h",
        "pairs": ["BTC/USDT"],
        "dry_run": True,
    }
    
    response = await client.post("/api/freqtrade/config/backtest", json=request)
    
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "config_path" in data
    assert "error" in data


async def test_data_check_endpoint(client):
    """Test data check endpoint."""
    request = {
        "exchange": "binance",
        "trading_mode": "spot",
        "pairs": ["BTC/USDT"],
        "timeframe": "1h",
    }
    
    response = await client.post("/api/freqtrade/data/check", json=request)
    
    assert response.status_code == 200
    data = response.json()
    assert "pairs" in data
    assert "source" in data
    assert "freqtrade_visible" in data


async def test_data_download_requires_confirmation(client):
    """Test that data download endpoint requires confirmation."""
    request = {
        "exchange": "binance",
        "trading_mode": "spot",
        "pairs": ["BTC/USDT"],
        "timeframes": ["1h"],
        "days": 30,
        "user_confirmed": False,  # Not confirmed
    }
    
    response = await client.post("/api/freqtrade/data/download", json=request)
    
    # Should return 400 due to validation error
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == True
    assert "user_confirmed" in str(data).lower()


async def test_data_download_with_confirmation(client):
    """Test data download with confirmation (will fail without Freqtrade)."""
    request = {
        "exchange": "binance",
        "trading_mode": "spot",
        "pairs": ["BTC/USDT"],
        "timeframes": ["1h"],
        "days": 30,
        "user_confirmed": True,
    }
    
    response = await client.post("/api/freqtrade/data/download", json=request)
    
    # Should return 200 (even if Freqtrade not configured, controlled failure)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "blocked" in data


async def test_backtest_requires_confirmation(client):
    """Test that backtest endpoint requires confirmation."""
    request = {
        "run_id": "test-run-123",
        "config_path": "/path/to/config.json",
        "strategy_name": "MyStrategy",
        "timeframe": "1h",
        "user_confirmed": False,  # Not confirmed
    }
    
    response = await client.post("/api/freqtrade/backtest", json=request)
    
    # Should return 400 due to validation error
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == True
    assert "user_confirmed" in str(data).lower()


async def test_backtest_with_confirmation(client):
    """Test backtest with confirmation (will fail without Freqtrade)."""
    request = {
        "run_id": "test-run-123",
        "config_path": "/path/to/config.json",
        "strategy_name": "MyStrategy",
        "timeframe": "1h",
        "user_confirmed": True,
    }
    
    response = await client.post("/api/freqtrade/backtest", json=request)
    
    # Should return 200 (even if Freqtrade not configured, controlled failure)
    assert response.status_code == 200
    data = response.json()
    assert "success" in data
    assert "blocked" in data


async def test_blocked_command_never_exposed(client):
    """Test that blocked commands are never exposed via API."""
    response = await client.get("/api/freqtrade/status")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that forbidden commands are listed
    assert "forbidden_commands" in data
    assert isinstance(data["forbidden_commands"], list)
    
    # Ensure 'trade' is in forbidden commands
    assert "trade" in data["forbidden_commands"]


async def test_errors_are_clean(client):
    """Test that API errors are clean and don't expose stack traces."""
    # Test with invalid strategy name
    request = {
        "strategy_name": "Invalid-Strategy!",
        "timeframe": "1h",
        "dry_run": True,
    }
    
    response = await client.post("/api/freqtrade/config/backtest", json=request)
    
    assert response.status_code == 200
    data = response.json()
    assert "error" in data
    # Error should be a clean string, not a stack trace
    assert "Traceback" not in str(data["error"])
    assert "File" not in str(data["error"])


async def test_no_secrets_exposed(client):
    """Test that no secrets are exposed in API responses."""
    response = await client.get("/api/freqtrade/status")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that no sensitive data is exposed
    response_str = str(data)
    assert "password" not in response_str.lower()
    assert "secret" not in response_str.lower()
    assert "token" not in response_str.lower()
    assert "key" not in response_str.lower() or "api_key" not in response_str.lower()


async def test_openapi_includes_freqtrade_tag(client):
    """Test that OpenAPI spec includes Freqtrade tag."""
    response = await client.get("/openapi.json")
    
    assert response.status_code == 200
    data = response.json()
    
    # Check that Freqtrade endpoints are included
    assert "/api/freqtrade/status" in data["paths"]
    assert "/api/freqtrade/version" in data["paths"]
    assert "/api/freqtrade/workspace" in data["paths"]
    assert "/api/freqtrade/strategies" in data["paths"]
    assert "/api/freqtrade/data" in data["paths"]
    assert "/api/freqtrade/config/backtest" in data["paths"]
    assert "/api/freqtrade/data/check" in data["paths"]
    assert "/api/freqtrade/data/download" in data["paths"]
    assert "/api/freqtrade/backtest" in data["paths"]
    
    # Check that at least one endpoint has the Freqtrade tag
    status_endpoint = data["paths"]["/api/freqtrade/status"]["get"]
    assert "tags" in status_endpoint
    assert "Freqtrade" in status_endpoint["tags"]


async def test_v1_prefix_mounted(client):
    """Test that endpoints are mounted under /api/v1 as well."""
    response = await client.get("/api/v1/freqtrade/status")
    
    assert response.status_code == 200
    data = response.json()
    assert "configured" in data


async def test_data_download_without_days_or_timerange(client):
    """Test that data download requires days or timerange."""
    request = {
        "exchange": "binance",
        "trading_mode": "spot",
        "pairs": ["BTC/USDT"],
        "timeframes": ["1h"],
        "user_confirmed": True,
        # No days or timerange
    }
    
    response = await client.post("/api/freqtrade/data/download", json=request)
    
    # Should return 400 due to validation error
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == True
    assert "days" in str(data).lower() or "timerange" in str(data).lower()


async def test_backtest_invalid_strategy_name(client):
    """Test that backtest rejects invalid strategy name."""
    request = {
        "run_id": "test-run-123",
        "config_path": "/path/to/config.json",
        "strategy_name": "Invalid-Strategy!",
        "timeframe": "1h",
        "user_confirmed": True,
    }
    
    response = await client.post("/api/freqtrade/backtest", json=request)
    
    # Should return 400 due to validation error
    assert response.status_code == 400
    data = response.json()
    assert data["error"] == True
    assert "strategy" in str(data).lower()


async def test_data_check_with_timerange(client):
    """Test data check with timerange."""
    request = {
        "exchange": "binance",
        "trading_mode": "spot",
        "pairs": ["BTC/USDT"],
        "timeframe": "1h",
        "timerange": "20240101-20240131",
    }
    
    response = await client.post("/api/freqtrade/data/check", json=request)
    
    assert response.status_code == 200
    data = response.json()
    assert "pairs" in data
