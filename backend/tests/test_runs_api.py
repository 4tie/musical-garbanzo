"""
Tests for Runs API endpoints.
"""
import pytest
import httpx
from httpx import ASGITransport

from app.main import app
from app.repositories.runs import RunRepository
from app.schemas.runs import RunCreate
from app.db.sqlite import get_connection


@pytest.fixture
async def client():
    """Create a test client using httpx with ASGI transport."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def clean_db():
    """Clean the runs table before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()


class TestRunsAPI:
    """Test Runs API endpoints."""
    
    async def test_create_run_via_api(self, client, clean_db):
        """Test creating a run via API."""
        response = await client.post(
            "/api/v1/runs",
            json={
                "name": "Test Run",
                "mode": "generate_strategy",
                "pairs": ["BTC/USDT"],
                "timeframe": "1h",
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Run"
        assert data["mode"] == "generate_strategy"
        assert data["status"] == "created"
        assert data["pairs"] == ["BTC/USDT"]
        assert "id" in data
    
    async def test_create_run_invalid_mode(self, client, clean_db):
        """Test creating a run with invalid mode."""
        response = await client.post(
            "/api/v1/runs",
            json={
                "name": "Test Run",
                "mode": "invalid_mode",
            }
        )
        
        assert response.status_code == 400
    
    async def test_list_runs_via_api(self, client, clean_db):
        """Test listing runs via API."""
        # Create some runs
        await client.post("/api/v1/runs", json={"name": "Run 1", "mode": "generate_strategy"})
        await client.post("/api/v1/runs", json={"name": "Run 2", "mode": "upload_strategy"})
        
        response = await client.get("/api/v1/runs")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
    
    async def test_list_runs_with_filter(self, client, clean_db):
        """Test listing runs with status filter."""
        run_repo = RunRepository()
        run1 = run_repo.create_run(RunCreate(name="Run 1", mode="generate_strategy"))
        run2 = run_repo.create_run(RunCreate(name="Run 2", mode="upload_strategy"))
        run_repo.update_status(run2["id"], "running")
        
        response = await client.get("/api/v1/runs?status=created")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == run1["id"]
    
    async def test_get_run_via_api(self, client, clean_db):
        """Test getting a run via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.get(f"/api/v1/runs/{run_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == run_id
        assert data["name"] == "Test Run"
    
    async def test_get_run_not_found(self, client, clean_db):
        """Test getting a non-existent run."""
        response = await client.get("/api/v1/runs/non-existent-id")
        
        assert response.status_code == 404
    
    async def test_update_run_via_api(self, client, clean_db):
        """Test updating a run via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.patch(
            f"/api/v1/runs/{run_id}",
            json={"name": "Updated Run", "timeframe": "4h"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Run"
        assert data["timeframe"] == "4h"
    
    async def test_update_run_not_found(self, client, clean_db):
        """Test updating a non-existent run."""
        response = await client.patch(
            "/api/v1/runs/non-existent-id",
            json={"name": "Updated Run"}
        )
        
        assert response.status_code == 404
    
    async def test_update_status_via_api(self, client, clean_db):
        """Test updating run status via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/status",
            json={"status": "running"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None
    
    async def test_update_status_invalid(self, client, clean_db):
        """Test updating with invalid status."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/status",
            json={"status": "invalid_status"}
        )
        
        assert response.status_code == 400
    
    async def test_update_status_not_found(self, client, clean_db):
        """Test updating status of non-existent run."""
        response = await client.post(
            "/api/v1/runs/non-existent-id/status",
            json={"status": "running"}
        )
        
        assert response.status_code == 404
    
    async def test_update_classification_via_api(self, client, clean_db):
        """Test updating classification via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/classification",
            json={"classification": "candidate"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["classification"] == "candidate"
    
    async def test_update_classification_invalid(self, client, clean_db):
        """Test updating with invalid classification."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/classification",
            json={"classification": "invalid_classification"}
        )
        
        assert response.status_code == 400
    
    async def test_start_run_via_api(self, client, clean_db):
        """Test starting a run via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(f"/api/v1/runs/{run_id}/start")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None
    
    async def test_complete_run_via_api(self, client, clean_db):
        """Test completing a run via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/complete",
            params={"classification": "promising"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "candidate"
        assert data["classification"] == "promising"
        assert data["completed_at"] is not None
    
    async def test_fail_run_via_api(self, client, clean_db):
        """Test failing a run via API."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/fail",
            json={"failure_type": "controlled", "reason": "Test failure"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed_controlled"
        assert data["failure_reason"] == "Test failure"
        assert data["completed_at"] is not None
    
    async def test_fail_run_invalid_type(self, client, clean_db):
        """Test failing a run with invalid type."""
        create_response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = create_response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/fail",
            json={"failure_type": "invalid", "reason": "Test"}
        )
        
        assert response.status_code == 400
