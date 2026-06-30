"""
Tests for Strategies API endpoints.
"""
import pytest
import httpx
from httpx import ASGITransport

from app.main import app
from app.db.sqlite import get_connection


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def clean_db():
    """Clean the strategies and strategy_versions tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM strategy_versions")
    conn.execute("DELETE FROM strategies")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM strategy_versions")
    conn.execute("DELETE FROM strategies")
    conn.commit()
    conn.close()


class TestStrategiesAPI:
    """Test Strategies API endpoints."""
    
    async def test_create_strategy_via_api(self, client, clean_db):
        """Test creating a strategy via API."""
        response = await client.post(
            "/api/v1/strategies",
            json={
                "name": "Test Strategy",
                "source_type": "generated",
                "timeframe": "1h",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Strategy"
        assert data["source_type"] == "generated"
        assert data["status"] == "draft"
        assert data["timeframe"] == "1h"
        assert "id" in data
    
    async def test_create_strategy_invalid_source_type(self, client, clean_db):
        """Test creating a strategy with invalid source_type."""
        response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "invalid_type"}
        )
        
        assert response.status_code == 400
    
    async def test_list_strategies_via_api(self, client, clean_db):
        """Test listing strategies via API."""
        await client.post("/api/v1/strategies", json={"name": "Strategy 1", "source_type": "generated"})
        await client.post("/api/v1/strategies", json={"name": "Strategy 2", "source_type": "uploaded"})
        
        response = await client.get("/api/v1/strategies")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    async def test_list_strategies_with_filter(self, client, clean_db):
        """Test listing strategies with status filter."""
        await client.post("/api/v1/strategies", json={"name": "Strategy 1", "source_type": "generated"})
        await client.post("/api/v1/strategies", json={"name": "Strategy 2", "source_type": "uploaded", "status": "active"})
        
        response = await client.get("/api/v1/strategies?status=draft")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
    
    async def test_get_strategy_via_api(self, client, clean_db):
        """Test getting a strategy via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/strategies/{strategy_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == strategy_id
        assert data["name"] == "Test Strategy"
    
    async def test_get_strategy_not_found(self, client, clean_db):
        """Test getting a non-existent strategy."""
        response = await client.get("/api/v1/strategies/non-existent-id")
        
        assert response.status_code == 404
    
    async def test_update_strategy_via_api(self, client, clean_db):
        """Test updating a strategy via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.patch(
            f"/api/v1/strategies/{strategy_id}",
            json={"name": "Updated Strategy", "timeframe": "4h"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Strategy"
        assert data["timeframe"] == "4h"
    
    async def test_update_strategy_not_found(self, client, clean_db):
        """Test updating a non-existent strategy."""
        response = await client.patch(
            "/api/v1/strategies/non-existent-id",
            json={"name": "Updated Strategy"}
        )
        
        assert response.status_code == 404
    
    async def test_archive_strategy_via_api(self, client, clean_db):
        """Test archiving a strategy via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/strategies/{strategy_id}/archive")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"
    
    async def test_archive_strategy_not_found(self, client, clean_db):
        """Test archiving a non-existent strategy."""
        response = await client.post("/api/v1/strategies/non-existent-id/archive")
        
        assert response.status_code == 404
    
    async def test_list_versions_via_api(self, client, clean_db):
        """Test listing versions via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        # Create versions
        await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 1, "spec": {"indicators": ["RSI"]}}
        )
        await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 2, "spec": {"indicators": ["MACD"]}}
        )
        
        response = await client.get(f"/api/v1/strategies/{strategy_id}/versions")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    async def test_list_versions_missing_strategy(self, client, clean_db):
        """Test listing versions for non-existent strategy."""
        response = await client.get("/api/v1/strategies/non-existent-id/versions")
        
        assert response.status_code == 404
    
    async def test_create_version_via_api(self, client, clean_db):
        """Test creating a version via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={
                "version_number": 1,
                "spec": {"indicators": ["RSI"]},
                "params": {"stoploss": -0.1},
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["strategy_id"] == strategy_id
        assert data["version_number"] == 1
        assert data["spec"] == {"indicators": ["RSI"]}
        assert data["params"] == {"stoploss": -0.1}
    
    async def test_create_version_auto_increment_via_api(self, client, clean_db):
        """Test auto-incrementing version number via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        # Create version 1
        await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 1}
        )
        
        # Create version without number - should auto-increment
        response = await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["version_number"] == 2
    
    async def test_create_version_missing_strategy(self, client, clean_db):
        """Test creating a version for non-existent strategy."""
        response = await client.post(
            "/api/v1/strategies/non-existent-id/versions",
            json={"version_number": 1}
        )
        
        assert response.status_code == 404
    
    async def test_get_current_version_via_api(self, client, clean_db):
        """Test getting current version via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        # Create version (version 1 becomes current automatically)
        await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 1}
        )
        
        response = await client.get(f"/api/v1/strategies/{strategy_id}/current-version")
        
        assert response.status_code == 200
        data = response.json()
        assert data["version_number"] == 1
        assert data["is_current"] is True
    
    async def test_get_current_version_missing_strategy(self, client, clean_db):
        """Test getting current version for non-existent strategy."""
        response = await client.get("/api/v1/strategies/non-existent-id/current-version")
        
        assert response.status_code == 404
    
    async def test_get_current_version_none_set(self, client, clean_db):
        """Test getting current version when none is set."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/strategies/{strategy_id}/current-version")
        
        assert response.status_code == 404
    
    async def test_set_current_version_via_api(self, client, clean_db):
        """Test setting current version via API."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        # Create versions
        v1_response = await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 1}
        )
        v1_id = v1_response.json()["id"]
        
        v2_response = await client.post(
            f"/api/v1/strategies/{strategy_id}/versions",
            json={"version_number": 2}
        )
        v2_id = v2_response.json()["id"]
        
        # Set v2 as current
        response = await client.post(f"/api/v1/strategies/{strategy_id}/current-version/{v2_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["current_version_id"] == v2_id
    
    async def test_set_current_version_missing_strategy(self, client, clean_db):
        """Test setting current version for non-existent strategy."""
        response = await client.post("/api/v1/strategies/non-existent-id/current-version/version-id")
        
        assert response.status_code == 404
    
    async def test_set_current_version_missing_version(self, client, clean_db):
        """Test setting current version with non-existent version."""
        create_response = await client.post(
            "/api/v1/strategies",
            json={"name": "Test Strategy", "source_type": "generated"}
        )
        strategy_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/strategies/{strategy_id}/current-version/non-existent-version-id")
        
        assert response.status_code == 404
