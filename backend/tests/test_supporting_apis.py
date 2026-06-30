"""
Tests for Supporting APIs (Artifacts, Metrics, Logs, Retry History, Audit Logs).
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
    """Clean all supporting tables before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM retry_history")
    conn.execute("DELETE FROM run_logs")
    conn.execute("DELETE FROM trade_summaries")
    conn.execute("DELETE FROM pair_results")
    conn.execute("DELETE FROM metrics_snapshots")
    conn.execute("DELETE FROM artifacts")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM audit_logs")
    conn.execute("DELETE FROM retry_history")
    conn.execute("DELETE FROM run_logs")
    conn.execute("DELETE FROM trade_summaries")
    conn.execute("DELETE FROM pair_results")
    conn.execute("DELETE FROM metrics_snapshots")
    conn.execute("DELETE FROM artifacts")
    conn.execute("DELETE FROM runs")
    conn.commit()
    conn.close()


class TestSupportingAPIs:
    """Test supporting API endpoints integration."""
    
    async def test_create_run_and_attach_artifact(self, client, clean_db):
        """Test creating a run and attaching an artifact."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Attach artifact
        artifact_response = await client.post(
            "/api/v1/artifacts",
            json={
                "run_id": run_id,
                "artifact_type": "strategy_py",
                "file_path": "/-path/to/strategy.py",
            },
        )
        
        assert artifact_response.status_code == 201
        assert artifact_response.json()["run_id"] == run_id
    
    async def test_add_metrics_to_run(self, client, clean_db):
        """Test adding metrics to a run."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add metric snapshot
        metrics_response = await client.post(
            f"/api/v1/runs/{run_id}/metrics",
            json={"raw_json": {"profit": 100}},
        )
        
        assert metrics_response.status_code == 201
        assert metrics_response.json()["run_id"] == run_id
    
    async def test_add_log_to_run(self, client, clean_db):
        """Test adding a log to a run."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add log
        log_response = await client.post(
            f"/api/v1/runs/{run_id}/logs",
            json={
                "run_id": run_id,
                "level": "info",
                "source": "system",
                "message": "Test message",
            },
        )
        
        assert log_response.status_code == 201
        assert log_response.json()["run_id"] == run_id
    
    async def test_add_retry_history_to_run(self, client, clean_db):
        """Test adding retry history to a run."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add retry entry
        retry_response = await client.post(
            f"/api/v1/runs/{run_id}/retry-history",
            json={
                "run_id": run_id,
                "status": "proposed",
                "error_message": "Test error",
            },
        )
        
        assert retry_response.status_code == 201
        assert retry_response.json()["run_id"] == run_id
    
    async def test_add_audit_log(self, client, clean_db):
        """Test adding an audit log."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add audit log
        audit_response = await client.post(
            "/api/v1/audit-logs",
            json={
                "run_id": run_id,
                "actor": "ai_assistant",
                "action_type": "create",
                "target_type": "strategy",
            },
        )
        
        assert audit_response.status_code == 201
        assert audit_response.json()["run_id"] == run_id
    
    async def test_fetch_all_by_run_id(self, client, clean_db):
        """Test fetching all supporting data by run ID."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add artifact
        await client.post(
            "/api/v1/artifacts",
            json={"run_id": run_id, "artifact_type": "strategy_py", "file_path": "/path.py"},
        )
        
        # Add metrics
        await client.post(
            f"/api/v1/runs/{run_id}/metrics",
            json={"raw_json": {"profit": 100}},
        )
        
        # Add log
        await client.post(
            f"/api/v1/runs/{run_id}/logs",
            json={"run_id": run_id, "level": "info", "source": "system", "message": "Test"},
        )
        
        # Add retry history
        await client.post(
            f"/api/v1/runs/{run_id}/retry-history",
            json={"run_id": run_id, "status": "proposed", "error_message": "Error"},
        )
        
        # Fetch all
        artifacts_response = await client.get(f"/api/v1/runs/{run_id}/artifacts")
        artifacts = artifacts_response.json()
        metrics_response = await client.get(f"/api/v1/runs/{run_id}/metrics")
        metrics = metrics_response.json()
        logs_response = await client.get(f"/api/v1/runs/{run_id}/logs")
        logs = logs_response.json()
        retry_history_response = await client.get(f"/api/v1/runs/{run_id}/retry-history")
        retry_history = retry_history_response.json()
        
        assert len(artifacts) == 1
        assert len(metrics) == 1
        assert len(logs) == 1
        assert len(retry_history) == 1
    
    async def test_artifact_list_endpoint(self, client, clean_db):
        """Test the artifacts list endpoint."""
        response = await client.get("/api/v1/artifacts")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    async def test_artifact_get_endpoint(self, client, clean_db):
        """Test getting a specific artifact."""
        # Create artifact
        artifact_response = await client.post(
            "/api/v1/artifacts",
            json={"artifact_type": "strategy_py", "file_path": "/path.py"},
        )
        artifact_id = artifact_response.json()["id"]
        
        # Get artifact
        response = await client.get(f"/api/v1/artifacts/{artifact_id}")
        assert response.status_code == 200
        assert response.json()["id"] == artifact_id
    
    async def test_artifact_get_not_found(self, client, clean_db):
        """Test getting a non-existent artifact."""
        response = await client.get("/api/v1/artifacts/non-existent-id")
        assert response.status_code == 404
    
    async def test_metrics_latest_endpoint(self, client, clean_db):
        """Test getting latest metrics."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add metrics
        await client.post(
            f"/api/v1/runs/{run_id}/metrics",
            json={"raw_json": {"profit": 100}},
        )
        
        # Get latest
        response = await client.get(f"/api/v1/runs/{run_id}/metrics/latest")
        assert response.status_code == 200
        assert response.json()["raw_json"]["profit"] == 100
    
    async def test_metrics_latest_not_found(self, client, clean_db):
        """Test getting latest metrics when none exist."""
        response = await client.get("/api/v1/runs/non-existent-id/metrics/latest")
        assert response.status_code == 404
    
    async def test_pair_results_endpoints(self, client, clean_db):
        """Test pair results endpoints."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add pair result
        await client.post(
            f"/api/v1/runs/{run_id}/pair-results",
            json={"pair": "BTC/USDT", "raw_json": {"profit": 50}},
        )
        
        # List pair results
        response = await client.get(f"/api/v1/runs/{run_id}/pair-results")
        assert response.status_code == 200
        assert len(response.json()) == 1
    
    async def test_trade_summary_endpoints(self, client, clean_db):
        """Test trade summary endpoints."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add trade summary
        await client.post(
            f"/api/v1/runs/{run_id}/trade-summary",
            json={"total_trades": 50, "wins": 30, "losses": 20},
        )
        
        # Get trade summary
        response = await client.get(f"/api/v1/runs/{run_id}/trade-summary")
        assert response.status_code == 200
        assert response.json()["total_trades"] == 50
        assert response.json()["wins"] == 30
    
    async def test_trade_summary_not_found(self, client, clean_db):
        """Test getting trade summary when none exists."""
        response = await client.get("/api/v1/runs/non-existent-id/trade-summary")
        assert response.status_code == 404
    
    async def test_logs_with_filters(self, client, clean_db):
        """Test logs endpoint with filters."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add logs
        await client.post(
            f"/api/v1/runs/{run_id}/logs",
            json={"run_id": run_id, "level": "info", "source": "system", "message": "Info"},
        )
        await client.post(
            f"/api/v1/runs/{run_id}/logs",
            json={"run_id": run_id, "level": "error", "source": "system", "message": "Error"},
        )
        
        # Filter by level
        response = await client.get(f"/api/v1/runs/{run_id}/logs?level=error")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["level"] == "error"
    
    async def test_retry_complete_endpoint(self, client, clean_db):
        """Test completing a retry entry."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add retry entry
        retry_response = await client.post(
            f"/api/v1/runs/{run_id}/retry-history",
            json={"run_id": run_id, "status": "proposed", "error_message": "Error"},
        )
        retry_id = retry_response.json()["id"]
        
        # Complete retry
        response = await client.post(
            f"/api/v1/retry-history/{retry_id}/complete",
            json={"status": "applied", "applied_fix": {"fix": "applied"}},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "applied"
    
    async def test_retry_complete_not_found(self, client, clean_db):
        """Test completing a non-existent retry entry."""
        response = await client.post(
            "/api/v1/retry-history/non-existent-id/complete",
            json={"status": "applied"},
        )
        assert response.status_code == 404
    
    async def test_audit_logs_with_filters(self, client, clean_db):
        """Test audit logs endpoint with filters."""
        # Create a run
        run_response = await client.post(
            "/api/v1/runs",
            json={"name": "Supporting API Run", "mode": "generate_strategy", "pairs": ["BTC/USDT"]},
        )
        run_id = run_response.json()["id"]
        
        # Add audit logs
        await client.post(
            "/api/v1/audit-logs",
            json={"run_id": run_id, "actor": "ai_assistant", "action_type": "create"},
        )
        await client.post(
            "/api/v1/audit-logs",
            json={"run_id": run_id, "actor": "user", "action_type": "update"},
        )
        
        # Filter by action type
        response = await client.get("/api/v1/audit-logs?action_type=create")
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["action_type"] == "create"
