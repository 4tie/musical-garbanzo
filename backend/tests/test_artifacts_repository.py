"""
Tests for ArtifactRepository.
"""
import pytest

from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifacts import ArtifactCreate
from app.db.sqlite import get_connection


@pytest.fixture
def artifact_repo():
    """Create an ArtifactRepository instance."""
    return ArtifactRepository()


@pytest.fixture
def clean_db():
    """Clean the artifacts table before each test."""
    conn = get_connection()
    conn.execute("DELETE FROM artifacts")
    conn.commit()
    conn.close()
    yield
    # Clean up after test
    conn = get_connection()
    conn.execute("DELETE FROM artifacts")
    conn.commit()
    conn.close()


class TestArtifactRepository:
    """Test ArtifactRepository operations."""
    
    def test_create_artifact(self, artifact_repo, clean_db):
        """Test creating an artifact."""
        data = ArtifactCreate(
            run_id="run-123",
            artifact_type="strategy_py",
            file_path="/path/to/strategy.py",
            description="Generated strategy",
            sha256="abc123",
            size_bytes=1024,
        )
        
        artifact = artifact_repo.create_artifact(data)
        
        assert artifact is not None
        assert artifact["run_id"] == "run-123"
        assert artifact["artifact_type"] == "strategy_py"
        assert artifact["file_path"] == "/path/to/strategy.py"
        assert artifact["description"] == "Generated strategy"
        assert artifact["sha256"] == "abc123"
        assert artifact["size_bytes"] == 1024
        assert artifact["id"] is not None

    def test_create_optimized_params_artifact(self, artifact_repo, clean_db):
        """Optimized params are first-class run artifacts."""
        data = ArtifactCreate(
            run_id="opt-run-123",
            artifact_type="optimized_params",
            file_path="/path/to/optimized_params/MyStrategy.json",
            description="Optimized params for MyStrategy",
        )

        artifact = artifact_repo.create_artifact(data)

        assert artifact["run_id"] == "opt-run-123"
        assert artifact["artifact_type"] == "optimized_params"
    
    def test_get_artifact(self, artifact_repo, clean_db):
        """Test getting an artifact by ID."""
        data = ArtifactCreate(
            run_id="run-123",
            artifact_type="strategy_py",
            file_path="/path/to/strategy.py",
        )
        created = artifact_repo.create_artifact(data)
        
        retrieved = artifact_repo.get_artifact(created["id"])
        
        assert retrieved is not None
        assert retrieved["id"] == created["id"]
        assert retrieved["file_path"] == "/path/to/strategy.py"
    
    def test_get_artifact_not_found(self, artifact_repo, clean_db):
        """Test getting a non-existent artifact."""
        result = artifact_repo.get_artifact("non-existent-id")
        assert result is None
    
    def test_list_artifacts(self, artifact_repo, clean_db):
        """Test listing artifacts."""
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-1", artifact_type="strategy_py", file_path="/path1.py")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-2", artifact_type="strategy_json", file_path="/path2.json")
        )
        
        artifacts = artifact_repo.list_artifacts()
        
        assert len(artifacts) == 2
    
    def test_list_artifacts_with_run_filter(self, artifact_repo, clean_db):
        """Test listing artifacts with run_id filter."""
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-1", artifact_type="strategy_py", file_path="/path1.py")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-2", artifact_type="strategy_json", file_path="/path2.json")
        )
        
        artifacts = artifact_repo.list_artifacts(run_id="run-1")
        
        assert len(artifacts) == 1
        assert artifacts[0]["run_id"] == "run-1"
    
    def test_list_artifacts_with_type_filter(self, artifact_repo, clean_db):
        """Test listing artifacts with artifact_type filter."""
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-1", artifact_type="strategy_py", file_path="/path1.py")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-2", artifact_type="strategy_json", file_path="/path2.json")
        )
        
        artifacts = artifact_repo.list_artifacts(artifact_type="strategy_py")
        
        assert len(artifacts) == 1
        assert artifacts[0]["artifact_type"] == "strategy_py"
    
    def test_list_run_artifacts(self, artifact_repo, clean_db):
        """Test listing artifacts for a specific run."""
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-1", artifact_type="strategy_py", file_path="/path1.py")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-1", artifact_type="strategy_json", file_path="/path2.json")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(run_id="run-2", artifact_type="strategy_py", file_path="/path3.py")
        )
        
        artifacts = artifact_repo.list_run_artifacts("run-1")
        
        assert len(artifacts) == 2
    
    def test_list_strategy_artifacts(self, artifact_repo, clean_db):
        """Test listing artifacts for a specific strategy."""
        artifact_repo.create_artifact(
            ArtifactCreate(strategy_id="strat-1", artifact_type="strategy_py", file_path="/path1.py")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(strategy_id="strat-1", artifact_type="strategy_json", file_path="/path2.json")
        )
        artifact_repo.create_artifact(
            ArtifactCreate(strategy_id="strat-2", artifact_type="strategy_py", file_path="/path3.py")
        )
        
        artifacts = artifact_repo.list_strategy_artifacts("strat-1")
        
        assert len(artifacts) == 2
    
    def test_invalid_artifact_type_rejected(self, artifact_repo, clean_db):
        """Test that invalid artifact_type is rejected."""
        data = ArtifactCreate(
            run_id="run-123",
            artifact_type="invalid_type",
            file_path="/path/to/file.py",
        )
        
        with pytest.raises(ValueError):
            artifact_repo.create_artifact(data)
