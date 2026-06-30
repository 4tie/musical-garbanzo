"""
Tests for RunRepository.
"""
import pytest
import sqlite3

from app.repositories.runs import RunRepository, RunNotFoundError
from app.schemas.runs import RunCreate, RunUpdate
from app.db.sqlite import get_connection


@pytest.fixture
def run_repo():
    """Create a RunRepository instance."""
    return RunRepository()


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


class TestRunRepository:
    """Test RunRepository operations."""
    
    def test_create_run(self, run_repo, clean_db):
        """Test creating a run."""
        data = RunCreate(
            name="Test Run",
            mode="generate_strategy",
            pairs=["BTC/USDT", "ETH/USDT"],
            timeframe="1h",
        )
        
        run = run_repo.create_run(data)
        
        assert run is not None
        assert run["name"] == "Test Run"
        assert run["mode"] == "generate_strategy"
        assert run["status"] == "created"
        assert run["pairs"] == ["BTC/USDT", "ETH/USDT"]
        assert run["timeframe"] == "1h"
        assert run["id"] is not None
        assert run["created_at"] is not None
        assert run["updated_at"] is not None
    
    def test_create_run_with_parent(self, run_repo, clean_db):
        """Test creating a run with parent_run_id."""
        parent_data = RunCreate(name="Parent Run", mode="upload_strategy")
        parent = run_repo.create_run(parent_data)
        
        child_data = RunCreate(
            name="Child Run",
            mode="repair_strategy",
            parent_run_id=parent["id"],
        )
        child = run_repo.create_run(child_data)
        
        assert child["parent_run_id"] == parent["id"]
    
    def test_get_run(self, run_repo, clean_db):
        """Test getting a run by ID."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        created = run_repo.create_run(data)
        
        retrieved = run_repo.get_run(created["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["name"] == "Test Run"
    
    def test_get_run_not_found(self, run_repo, clean_db):
        """Test getting a non-existent run."""
        result = run_repo.get_run("non-existent-id")
        assert result is None
    
    def test_list_runs(self, run_repo, clean_db):
        """Test listing runs."""
        # Create multiple runs
        run_repo.create_run(RunCreate(name="Run 1", mode="generate_strategy"))
        run_repo.create_run(RunCreate(name="Run 2", mode="upload_strategy"))
        run_repo.create_run(RunCreate(name="Run 3", mode="repair_strategy"))
        
        runs = run_repo.list_runs()
        
        assert len(runs) == 3
        assert all("name" in run for run in runs)
    
    def test_list_runs_with_status_filter(self, run_repo, clean_db):
        """Test listing runs with status filter."""
        run1 = run_repo.create_run(RunCreate(name="Run 1", mode="generate_strategy"))
        run2 = run_repo.create_run(RunCreate(name="Run 2", mode="upload_strategy"))
        
        run_repo.update_status(run2["id"], "running")
        
        runs = run_repo.list_runs(status="created")
        
        assert len(runs) == 1
        assert runs[0]["id"] == run1["id"]
    
    def test_list_runs_with_limit(self, run_repo, clean_db):
        """Test listing runs with limit."""
        for i in range(10):
            run_repo.create_run(RunCreate(name=f"Run {i}", mode="generate_strategy"))
        
        runs = run_repo.list_runs(limit=5)
        
        assert len(runs) == 5
    
    def test_update_run(self, run_repo, clean_db):
        """Test updating a run."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        update_data = RunUpdate(
            name="Updated Run",
            timeframe="4h",
            pairs=["BTC/USDT"],
        )
        updated = run_repo.update_run(run["id"], update_data)
        
        assert updated["name"] == "Updated Run"
        assert updated["timeframe"] == "4h"
        assert updated["pairs"] == ["BTC/USDT"]
    
    def test_update_run_not_found(self, run_repo, clean_db):
        """Test updating a non-existent run."""
        with pytest.raises(RunNotFoundError):
            run_repo.update_run("non-existent-id", RunUpdate(name="Test"))
    
    def test_update_status(self, run_repo, clean_db):
        """Test updating run status."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.update_status(run["id"], "running")
        
        assert updated["status"] == "running"
        assert updated["started_at"] is not None
    
    def test_update_status_with_failure_reason(self, run_repo, clean_db):
        """Test updating status with failure reason."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.update_status(
            run["id"],
            "failed_controlled",
            failure_reason="Test failure"
        )
        
        assert updated["status"] == "failed_controlled"
        assert updated["failure_reason"] == "Test failure"
        assert updated["completed_at"] is not None
    
    def test_update_status_invalid(self, run_repo, clean_db):
        """Test updating with invalid status."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        with pytest.raises(ValueError):
            run_repo.update_status(run["id"], "invalid_status")
    
    def test_set_classification(self, run_repo, clean_db):
        """Test setting run classification."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.set_classification(run["id"], "candidate")
        
        assert updated["classification"] == "candidate"
    
    def test_set_classification_invalid(self, run_repo, clean_db):
        """Test setting invalid classification."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        with pytest.raises(ValueError):
            run_repo.set_classification(run["id"], "invalid_classification")
    
    def test_mark_started(self, run_repo, clean_db):
        """Test marking a run as started."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.mark_started(run["id"])
        
        assert updated["status"] == "running"
        assert updated["started_at"] is not None
    
    def test_mark_completed(self, run_repo, clean_db):
        """Test marking a run as completed."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.mark_completed(run["id"], classification="promising")
        
        assert updated["status"] == "candidate"
        assert updated["classification"] == "promising"
        assert updated["completed_at"] is not None
    
    def test_mark_failed_controlled(self, run_repo, clean_db):
        """Test marking a run as failed (controlled)."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.mark_failed(run["id"], "controlled", "Test failure")
        
        assert updated["status"] == "failed_controlled"
        assert updated["failure_reason"] == "Test failure"
        assert updated["completed_at"] is not None
    
    def test_mark_failed_system(self, run_repo, clean_db):
        """Test marking a run as failed (system)."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        updated = run_repo.mark_failed(run["id"], "system", "System error")
        
        assert updated["status"] == "failed_system"
        assert updated["failure_reason"] == "System error"
        assert updated["completed_at"] is not None
    
    def test_mark_failed_invalid_type(self, run_repo, clean_db):
        """Test marking failed with invalid type."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data)
        
        with pytest.raises(ValueError):
            run_repo.mark_failed(run["id"], "invalid_type", "Test")
    
    def test_invalid_mode_rejected(self, run_repo, clean_db):
        """Test that invalid mode is rejected."""
        data = RunCreate(name="Test Run", mode="invalid_mode")
        
        with pytest.raises(ValueError):
            run_repo.create_run(data)
    
    def test_pairs_json_roundtrip(self, run_repo, clean_db):
        """Test that pairs serialize/deserialize correctly."""
        pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]
        data = RunCreate(name="Test Run", mode="generate_strategy", pairs=pairs)
        
        run = run_repo.create_run(data)
        
        assert run["pairs"] == pairs
        assert isinstance(run["pairs"], list)
    
    def test_delete_demo_runs(self, run_repo, clean_db):
        """Test deleting demo runs."""
        # Create demo and non-demo runs
        run_repo.create_run(RunCreate(name="Demo Run", mode="generate_strategy", is_demo=True))
        run_repo.create_run(RunCreate(name="Real Run", mode="generate_strategy", is_demo=False))
        run_repo.create_run(RunCreate(name="Demo Run 2", mode="upload_strategy", is_demo=True))
        
        deleted_count = run_repo.delete_demo_runs()
        
        assert deleted_count == 2
        
        runs = run_repo.list_runs()
        assert len(runs) == 1
        assert runs[0]["name"] == "Real Run"
