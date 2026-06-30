"""
Tests for RunStageRepository.
"""
import pytest

from app.repositories.run_stages import RunStageRepository, RunStageNotFoundError
from app.repositories.runs import RunRepository
from app.schemas.runs import RunCreate
from app.db.sqlite import get_connection


@pytest.fixture
def stage_repo():
    """Create a RunStageRepository instance."""
    return RunStageRepository()


@pytest.fixture
def run_repo():
    """Create a RunRepository instance."""
    return RunRepository()


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


class TestRunStageRepository:
    """Test RunStageRepository operations."""
    
    def test_create_stage(self, stage_repo, clean_db):
        """Test creating a stage."""
        stage = stage_repo.create_stage(
            run_id="test-run-id",
            stage_key="test_stage",
            stage_name="Test Stage",
            order_index=1,
            input_data={"key": "value"}
        )
        
        assert stage is not None
        assert stage["stage_key"] == "test_stage"
        assert stage["stage_name"] == "Test Stage"
        assert stage["order_index"] == 1
        assert stage["status"] == "pending"
        assert stage["input"] == {"key": "value"}
        assert stage["id"] is not None
        assert stage["created_at"] is not None
    
    def test_create_default_stages(self, stage_repo, clean_db):
        """Test creating default stages for a run."""
        stages = stage_repo.create_default_stages("test-run-id")
        
        assert len(stages) == 13  # DEFAULT_RUN_STAGES has 13 stages
        
        # Check that stages are ordered
        for i, stage in enumerate(stages):
            assert stage["order_index"] == i + 1
        
        # Check first stage
        assert stages[0]["stage_key"] == "run_setup"
        assert stages[0]["status"] == "pending"
        
        # Check last stage
        assert stages[-1]["stage_key"] == "notification"
    
    def test_get_stage(self, stage_repo, clean_db):
        """Test getting a stage by run_id and stage_key."""
        stage_repo.create_stage(
            run_id="test-run-id",
            stage_key="test_stage",
            stage_name="Test Stage",
            order_index=1
        )
        
        retrieved = stage_repo.get_stage("test-run-id", "test_stage")
        
        assert retrieved is not None
        assert retrieved["stage_key"] == "test_stage"
    
    def test_get_stage_not_found(self, stage_repo, clean_db):
        """Test getting a non-existent stage."""
        result = stage_repo.get_stage("test-run-id", "non_existent")
        assert result is None
    
    def test_list_stages(self, stage_repo, clean_db):
        """Test listing stages for a run."""
        stage_repo.create_stage("test-run-id", "stage1", "Stage 1", 1)
        stage_repo.create_stage("test-run-id", "stage2", "Stage 2", 2)
        stage_repo.create_stage("test-run-id", "stage3", "Stage 3", 3)
        
        stages = stage_repo.list_stages("test-run-id")
        
        assert len(stages) == 3
        # Check ordering
        assert stages[0]["order_index"] == 1
        assert stages[1]["order_index"] == 2
        assert stages[2]["order_index"] == 3
    
    def test_list_stages_ordered(self, stage_repo, clean_db):
        """Test that stages are returned in order_index order."""
        # Create stages out of order
        stage_repo.create_stage("test-run-id", "stage3", "Stage 3", 3)
        stage_repo.create_stage("test-run-id", "stage1", "Stage 1", 1)
        stage_repo.create_stage("test-run-id", "stage2", "Stage 2", 2)
        
        stages = stage_repo.list_stages("test-run-id")
        
        assert stages[0]["stage_key"] == "stage1"
        assert stages[1]["stage_key"] == "stage2"
        assert stages[2]["stage_key"] == "stage3"
    
    def test_update_stage(self, stage_repo, clean_db):
        """Test updating a stage."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        
        updated = stage_repo.update_stage(
            "test-run-id",
            "test_stage",
            {
                "stage_name": "Updated Name",
                "output_data": {"result": "success"},
                "logs_summary": "Test logs"
            }
        )
        
        assert updated["stage_name"] == "Updated Name"
        assert updated["output"] == {"result": "success"}
        assert updated["logs_summary"] == "Test logs"
    
    def test_update_stage_not_found(self, stage_repo, clean_db):
        """Test updating a non-existent stage."""
        with pytest.raises(RunStageNotFoundError):
            stage_repo.update_stage("test-run-id", "non_existent", {"stage_name": "Test"})
    
    def test_start_stage(self, stage_repo, clean_db):
        """Test starting a stage."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        
        updated = stage_repo.start_stage(
            "test-run-id",
            "test_stage",
            input_data={"input": "data"}
        )
        
        assert updated["status"] == "running"
        assert updated["started_at"] is not None
        assert updated["input"] == {"input": "data"}
    
    def test_start_stage_not_found(self, stage_repo, clean_db):
        """Test starting a non-existent stage."""
        with pytest.raises(RunStageNotFoundError):
            stage_repo.start_stage("test-run-id", "non_existent")
    
    def test_complete_stage(self, stage_repo, clean_db):
        """Test completing a stage."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        stage_repo.start_stage("test-run-id", "test_stage")
        
        updated = stage_repo.complete_stage(
            "test-run-id",
            "test_stage",
            output_data={"result": "success"},
            logs_summary="Completed successfully"
        )
        
        assert updated["status"] == "passed"
        assert updated["completed_at"] is not None
        assert updated["duration_ms"] is not None
        assert updated["output"] == {"result": "success"}
        assert updated["logs_summary"] == "Completed successfully"
    
    def test_complete_stage_not_found(self, stage_repo, clean_db):
        """Test completing a non-existent stage."""
        with pytest.raises(RunStageNotFoundError):
            stage_repo.complete_stage("test-run-id", "non_existent")
    
    def test_fail_stage(self, stage_repo, clean_db):
        """Test failing a stage."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        stage_repo.start_stage("test-run-id", "test_stage")
        
        updated = stage_repo.fail_stage(
            "test-run-id",
            "test_stage",
            error_data={"error": "test error"},
            logs_summary="Failed due to error"
        )
        
        assert updated["status"] == "failed"
        assert updated["completed_at"] is not None
        assert updated["duration_ms"] is not None
        assert updated["error"] == {"error": "test error"}
        assert updated["logs_summary"] == "Failed due to error"
    
    def test_fail_stage_not_found(self, stage_repo, clean_db):
        """Test failing a non-existent stage."""
        with pytest.raises(RunStageNotFoundError):
            stage_repo.fail_stage("test-run-id", "non_existent")
    
    def test_skip_stage(self, stage_repo, clean_db):
        """Test skipping a stage."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        
        updated = stage_repo.skip_stage("test-run-id", "test_stage", reason="Not needed")
        
        assert updated["status"] == "skipped"
        assert updated["completed_at"] is not None
        assert updated["logs_summary"] == "Not needed"
    
    def test_skip_stage_not_found(self, stage_repo, clean_db):
        """Test skipping a non-existent stage."""
        with pytest.raises(RunStageNotFoundError):
            stage_repo.skip_stage("test-run-id", "non_existent")
    
    def test_reset_stages(self, stage_repo, clean_db):
        """Test resetting all stages for a run."""
        # Create and modify stages
        stage_repo.create_stage("test-run-id", "stage1", "Stage 1", 1)
        stage_repo.create_stage("test-run-id", "stage2", "Stage 2", 2)
        stage_repo.start_stage("test-run-id", "stage1")
        stage_repo.complete_stage("test-run-id", "stage1")
        
        count = stage_repo.reset_stages("test-run-id")
        
        assert count == 2
        
        stages = stage_repo.list_stages("test-run-id")
        for stage in stages:
            assert stage["status"] == "pending"
            assert stage["started_at"] is None
            assert stage["completed_at"] is None
            assert stage["duration_ms"] is None
    
    def test_json_input_output_error_roundtrip(self, stage_repo, clean_db):
        """Test that JSON data serializes/deserializes correctly."""
        input_data = {"pairs": ["BTC/USDT", "ETH/USDT"], "config": {"key": "value"}}
        output_data = {"metrics": {"profit": 100, "loss": 50}}
        error_data = {"exception": "ValueError", "message": "Test error"}
        
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1, input_data=input_data)
        stage_repo.start_stage("test-run-id", "test_stage")
        stage_repo.complete_stage("test-run-id", "test_stage", output_data=output_data)
        
        stage = stage_repo.get_stage("test-run-id", "test_stage")
        
        assert stage["input"] == input_data
        assert stage["output"] == output_data
        assert isinstance(stage["input"], dict)
        assert isinstance(stage["output"], dict)
    
    def test_duration_ms_calculated(self, stage_repo, clean_db):
        """Test that duration_ms is calculated correctly."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        stage_repo.start_stage("test-run-id", "test_stage")
        
        # Complete the stage
        stage_repo.complete_stage("test-run-id", "test_stage")
        
        stage = stage_repo.get_stage("test-run-id", "test_stage")
        
        assert stage["duration_ms"] is not None
        assert stage["duration_ms"] >= 0
    
    def test_duplicate_stage_prevented(self, stage_repo, clean_db):
        """Test that creating a duplicate stage is prevented by UNIQUE constraint."""
        stage_repo.create_stage("test-run-id", "test_stage", "Test Stage", 1)
        
        # Try to create the same stage again - should fail due to UNIQUE constraint
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            stage_repo.create_stage("test-run-id", "test_stage", "Test Stage 2", 2)
        
        stages = stage_repo.list_stages("test-run-id")
        # Only one stage should exist
        assert len(stages) == 1
    
    def test_run_creates_default_stages(self, run_repo, stage_repo, clean_db):
        """Test that creating a run creates default stages."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data, create_default_stages=True)
        
        stages = stage_repo.list_stages(run["id"])
        
        assert len(stages) == 13
        assert stages[0]["stage_key"] == "run_setup"
    
    def test_run_without_default_stages(self, run_repo, stage_repo, clean_db):
        """Test that creating a run can skip default stages."""
        data = RunCreate(name="Test Run", mode="generate_strategy")
        run = run_repo.create_run(data, create_default_stages=False)
        
        stages = stage_repo.list_stages(run["id"])
        
        assert len(stages) == 0
