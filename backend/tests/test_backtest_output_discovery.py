"""
Tests for backtest output discovery.
"""
from pathlib import Path

from app.services.backtest_output_discovery import BacktestOutputDiscoveryService


class FakeArtifactRepository:
    """Small artifact repository fake for discovery tests."""

    def __init__(self, artifacts=None):
        self.artifacts = artifacts or []

    def list_run_artifacts(self, run_id):
        return self.artifacts


def make_service(tmp_path: Path, artifacts=None) -> BacktestOutputDiscoveryService:
    """Build a discovery service rooted in a temp project."""
    return BacktestOutputDiscoveryService(
        artifact_repository=FakeArtifactRepository(artifacts),
        project_root=tmp_path,
    )


def raw_dir(tmp_path: Path, run_id: str = "run-123") -> Path:
    """Return the Part 04 raw Freqtrade artifact directory."""
    return tmp_path / "artifacts" / "runs" / run_id / "raw_freqtrade"


def backtest_dir(tmp_path: Path, run_id: str = "run-123") -> Path:
    """Return the Part 04 raw Freqtrade backtest result directory."""
    return raw_dir(tmp_path, run_id) / "backtest_results"


def test_discovers_stdout_stderr_logs(tmp_path):
    """Discovery finds captured stdout and stderr logs."""
    run_raw_dir = raw_dir(tmp_path)
    run_raw_dir.mkdir(parents=True)
    stdout = run_raw_dir / "stdout.log"
    stderr = run_raw_dir / "stderr.log"
    stdout.write_text("freqtrade output")
    stderr.write_text("freqtrade errors")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is False
    assert result.stdout_path == str(stdout.resolve())
    assert result.stderr_path == str(stderr.resolve())
    assert "only_stdout_stderr_available" in result.warnings
    assert {file.file_type for file in result.files} == {"stdout_log", "stderr_log"}


def test_discovers_json_files_in_raw_backtest_results(tmp_path):
    """Discovery finds JSON result files in the Part 04 backtest directory."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    result_file = directory / "backtest-result.json"
    result_file.write_text("{}")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(result_file.resolve())
    assert len(result.files) == 1
    assert result.files[0].file_type == "json"
    assert result.files[0].source == "backtest_results_dir"
    assert result.files[0].is_candidate_result is True


def test_discovers_zip_files(tmp_path):
    """Discovery treats ZIP bundles as structured result candidates."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    result_file = directory / "backtest-result.zip"
    result_file.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(result_file.resolve())
    assert result.files[0].file_type == "zip"
    assert result.files[0].is_candidate_result is True


def test_classifies_meta_json_separately(tmp_path):
    """Metadata JSON is not treated as a primary result candidate."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    meta_file = directory / "backtest-result.meta.json"
    meta_file.write_text("{}")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is False
    assert result.primary_result_path is None
    assert result.files[0].file_type == "meta_json"
    assert result.files[0].is_candidate_result is False
    assert "metadata_file_not_primary_result" in result.files[0].warnings
    assert "no_candidate_result_file_found" in result.warnings


def test_classifies_last_result_json_as_metadata(tmp_path):
    """Freqtrade's .last_result.json pointer is not a primary result candidate."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    last_result = directory / ".last_result.json"
    result_zip = directory / "backtest-result.zip"
    last_result.write_text('{"latest_backtest": "backtest-result.zip"}')
    result_zip.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    result = make_service(tmp_path).discover_outputs("run-123")

    by_name = {file.file_name: file for file in result.files}
    assert by_name[".last_result.json"].file_type == "meta_json"
    assert by_name[".last_result.json"].is_candidate_result is False
    assert result.primary_result_path == str(result_zip.resolve())


def test_chooses_primary_json_before_stdout(tmp_path):
    """Structured JSON is preferred over stdout logs."""
    run_raw_dir = raw_dir(tmp_path)
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    (run_raw_dir / "stdout.log").write_text("human table")
    result_file = directory / "backtest-result.json"
    result_file.write_text("{}")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(result_file.resolve())
    assert result.stdout_path == str((run_raw_dir / "stdout.log").resolve())


def test_chooses_primary_zip_before_stdout_when_json_missing(tmp_path):
    """Structured ZIP is preferred over stdout logs when JSON is missing."""
    run_raw_dir = raw_dir(tmp_path)
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    (run_raw_dir / "stdout.log").write_text("human table")
    result_file = directory / "backtest-result.zip"
    result_file.write_bytes(b"PK\x05\x06" + b"\x00" * 18)

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(result_file.resolve())


def test_returns_controlled_missing_result_if_no_files(tmp_path):
    """Missing run output returns a controlled result instead of raising."""
    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is False
    assert result.primary_result_path is None
    assert result.files == []
    assert "no_backtest_output_files_found" in result.warnings
    assert "raw_freqtrade_dir_missing" in result.warnings


def test_rejects_path_outside_project_root(tmp_path):
    """Artifact paths outside the project root are rejected."""
    outside = tmp_path.parent / "outside-backtest-result.json"
    outside.write_text("{}")
    artifacts = [{"file_path": str(outside)}]

    result = make_service(tmp_path, artifacts=artifacts).discover_outputs("run-123")

    assert result.success is False
    assert result.files == []
    assert "artifact_path_outside_project_root" in result.warnings


def test_does_not_read_env_files(tmp_path):
    """Discovery skips .env files and does not treat them as outputs."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    (directory / ".env").write_text("APP_SECRET_KEY=secret")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is False
    assert all(file.file_name != ".env" for file in result.files)
    assert "env_file_skipped" in result.warnings


def test_handles_empty_directories(tmp_path):
    """Empty expected directories return missing output warnings."""
    backtest_dir(tmp_path).mkdir(parents=True)

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is False
    assert result.files == []
    assert "no_backtest_output_files_found" in result.warnings


def test_uses_artifact_registry_if_artifact_records_exist(tmp_path):
    """Artifact registry paths are discovered and preferred."""
    directory = backtest_dir(tmp_path)
    directory.mkdir(parents=True)
    artifact_file = directory / "artifact-result.json"
    artifact_file.write_text("{}")
    artifacts = [
        {
            "file_path": "artifacts/runs/run-123/raw_freqtrade/backtest_results/artifact-result.json",
            "artifact_type": "backtest_raw",
        }
    ]

    result = make_service(tmp_path, artifacts=artifacts).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(artifact_file.resolve())
    assert result.files[0].source == "artifact_registry"


def test_artifact_registry_skips_non_raw_result_artifacts(tmp_path):
    """Generated configs and normalized metrics are not raw backtest sources."""
    config_dir = tmp_path / "freqtrade_workspace" / "config" / "runs"
    normalized_dir = tmp_path / "artifacts" / "runs" / "run-123" / "normalized"
    config_dir.mkdir(parents=True)
    normalized_dir.mkdir(parents=True)
    config_file = config_dir / "run-123.backtest.json"
    normalized_file = normalized_dir / "backtest_result.normalized.json"
    config_file.write_text("{}")
    normalized_file.write_text("{}")
    artifacts = [
        {
            "file_path": "freqtrade_workspace/config/runs/run-123.backtest.json",
            "artifact_type": "freqtrade_config",
        },
        {
            "file_path": "artifacts/runs/run-123/normalized/backtest_result.normalized.json",
            "artifact_type": "metrics_json",
        },
    ]

    result = make_service(tmp_path, artifacts=artifacts).discover_outputs("run-123")

    assert result.success is False
    assert result.files == []
    assert result.primary_result_path is None


def test_workspace_scan_requires_link_or_run_metadata(tmp_path):
    """Workspace discovery is limited to obvious run-linked files."""
    workspace_dir = tmp_path / "freqtrade_workspace" / "user_data" / "backtest_results"
    workspace_dir.mkdir(parents=True)
    ignored = workspace_dir / "unrelated-result.json"
    linked = workspace_dir / "run-123-result.json"
    ignored.write_text("{}")
    linked.write_text("{}")

    result = make_service(tmp_path).discover_outputs("run-123")

    assert result.success is True
    assert result.primary_result_path == str(linked.resolve())
    assert all(file.path != str(ignored.resolve()) for file in result.files)
