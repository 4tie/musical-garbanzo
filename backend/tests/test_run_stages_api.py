"""
Tests for Run Stages API endpoints.
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
    """Clean the runs and run_stages tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM run_stages")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM run_stages")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()


class TestRunStagesAPI:
    """Test Run Stages API endpoints."""
    
    async def test_create_run_and_list_stages(self, client, clean_db):
        """Test creating a run and listing its stages."""
        # Create a run (which creates default stages)
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # List stages
        response = await client.get(f"/api/v1/runs/{run_id}/stages")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 13  # DEFAULT_RUN_STAGES has 13 stages
        assert data[0]["stage_key"] == "run_setup"
    
    async def test_list_stages_missing_run(self, client, clean_db):
        """Test listing stages for a non-existent run."""
        response = await client.get("/api/v1/runs/non-existent-id/stages")
        
        assert response.status_code == 404
    
    async def test_get_stage(self, client, clean_db):
        """Test getting a specific stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Get a specific stage
        response = await client.get(f"/api/v1/runs/{run_id}/stages/run_setup")
        
        assert response.status_code == 200
        data = response.json()
        assert data["stage_key"] == "run_setup"
        assert data["status"] == "pending"
    
    async def test_get_stage_missing_run(self, client, clean_db):
        """Test getting a stage for a non-existent run."""
        response = await client.get("/api/v1/runs/non-existent-id/stages/run_setup")
        
        assert response.status_code == 404
    
    async def test_get_stage_missing_stage(self, client, clean_db):
        """Test getting a non-existent stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Get a non-existent stage
        response = await client.get(f"/api/v1/runs/{run_id}/stages/non_existent")
        
        assert response.status_code == 404
    
    async def test_start_stage_via_api(self, client, clean_db):
        """Test starting a stage via API."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Start a stage - send input data directly, not wrapped
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/run_setup/start",
            json={"key": "value"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["started_at"] is not None
        assert data["input"] == {"key": "value"}
    
    async def test_start_stage_missing_run(self, client, clean_db):
        """Test starting a stage for a non-existent run."""
        response = await client.post("/api/v1/runs/non-existent-id/stages/run_setup/start")
        
        assert response.status_code == 404
    
    async def test_start_stage_missing_stage(self, client, clean_db):
        """Test starting a non-existent stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        response = await client.post(f"/api/v1/runs/{run_id}/stages/non_existent/start")
        
        assert response.status_code == 404
    
    async def test_complete_stage_via_api(self, client, clean_db):
        """Test completing a stage via API."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Start the stage first
        await client.post(f"/api/v1/runs/{run_id}/stages/run_setup/start")
        
        # Complete the stage
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/run_setup/complete",
            json={
                "output_data": {"result": "success"},
                "logs_summary": "Completed successfully"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "passed"
        assert data["completed_at"] is not None
        assert data["duration_ms"] is not None
        assert data["output"] == {"result": "success"}
        assert data["logs_summary"] == "Completed successfully"
    
    async def test_complete_stage_missing_run(self, client, clean_db):
        """Test completing a stage for a non-existent run."""
        response = await client.post(
            "/api/v1/runs/non-existent-id/stages/run_setup/complete",
            json={}
        )
        
        assert response.status_code == 404
    
    async def test_complete_stage_missing_stage(self, client, clean_db):
        """Test completing a non-existent stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/non_existent/complete",
            json={}
        )
        
        assert response.status_code == 404
    
    async def test_fail_stage_via_api(self, client, clean_db):
        """Test failing a stage via API."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Start the stage first
        await client.post(f"/api/v1/runs/{run_id}/stages/run_setup/start")
        
        # Fail the stage
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/run_setup/fail",
            json={
                "error_data": {"error": "test error"},
                "logs_summary": "Failed due to error"
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "failed"
        assert data["completed_at"] is not None
        assert data["duration_ms"] is not None
        assert data["error"] == {"error": "test error"}
        assert data["logs_summary"] == "Failed due to error"
    
    async def test_fail_stage_missing_run(self, client, clean_db):
        """Test failing a stage for a non-existent run."""
        response = await client.post(
            "/api/v1/runs/non-existent-id/stages/run_setup/fail",
            json={}
        )
        
        assert response.status_code == 404
    
    async def test_fail_stage_missing_stage(self, client, clean_db):
        """Test failing a non-existent stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/non_existent/fail",
            json={}
        )
        
        assert response.status_code == 404
    
    async def test_skip_stage_via_api(self, client, clean_db):
        """Test skipping a stage via API."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Skip a stage
        response = await client.post(
            f"/api/v1/runs/{run_id}/stages/run_setup/skip",
            params={"reason": "Not needed"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "skipped"
        assert data["completed_at"] is not None
        assert data["logs_summary"] == "Not needed"
    
    async def test_skip_stage_missing_run(self, client, clean_db):
        """Test skipping a stage for a non-existent run."""
        response = await client.post("/api/v1/runs/non-existent-id/stages/run_setup/skip")
        
        assert response.status_code == 404
    
    async def test_skip_stage_missing_stage(self, client, clean_db):
        """Test skipping a non-existent stage."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        response = await client.post(f"/api/v1/runs/{run_id}/stages/non_existent/skip")
        
        assert response.status_code == 404
    
    async def test_reset_stages_via_api(self, client, clean_db):
        """Test resetting stages via API."""
        # Create a run
        response = await client.post(
            "/api/v1/runs",
            json={"name": "Test Run", "mode": "generate_strategy"}
        )
        run_id = response.json()["id"]
        
        # Start and complete a stage
        await client.post(f"/api/v1/runs/{run_id}/stages/run_setup/start")
        await client.post(f"/api/v1/runs/{run_id}/stages/run_setup/complete", json={})
        
        # Reset stages
        response = await client.post(f"/api/v1/runs/{run_id}/stages/reset")
        
        assert response.status_code == 200
        data = response.json()
        assert "count" in data
        assert data["count"] == 13
        
        # Verify stages are reset
        response = await client.get(f"/api/v1/runs/{run_id}/stages")
        stages = response.json()
        for stage in stages:
            assert stage["status"] == "pending"
            assert stage["started_at"] is None
            assert stage["completed_at"] is None
    
    async def test_reset_stages_missing_run(self, client, clean_db):
        """Test resetting stages for a non-existent run."""
        response = await client.post("/api/v1/runs/non-existent-id/stages/reset")
        
        assert response.status_code == 404
