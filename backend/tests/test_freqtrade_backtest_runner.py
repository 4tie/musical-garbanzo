"""
Tests for Freqtrade backtest runner service.
"""
from pathlib import Path
from datetime import datetime
import pytest

from app.schemas.freqtrade_backtest import FreqtradeBacktestRequest
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner


class DummyCommandRunner:
    def __init__(self, success=True, stdout="", stderr="", blocked=False):
        self.success = success
        self.stdout = stdout
        self.stderr = stderr
        self.blocked = blocked

    def run(self, command, **kwargs):
        from app.schemas.freqtrade import FreqtradeCommandResult
        return FreqtradeCommandResult(
            command=command,
            success=self.success,
            stdout=self.stdout,
            stderr=self.stderr,
            return_code=0 if self.success else 1,
            duration_seconds=0.1,
            blocked=self.blocked,
            timed_out=False,
            error=self.stderr if not self.success else None,
        )


class DummyStrategyService:
    def __init__(self, exists=True):
        self.exists = exists

    def get_strategy_status(self, strategy_name):
        from app.schemas.freqtrade_strategy import FreqtradeStrategyStatus
        return FreqtradeStrategyStatus(
            strategy_name=strategy_name,
            exists=self.exists,
            freqtrade_visible=False,
            has_sidecar_json=False,
        )


class FakeArtifactRepository:
    def __init__(self):
        self.artifacts = []

    def create(self, **kwargs):
        artifact = {"id": f"artifact-{len(self.artifacts)}", **kwargs}
        self.artifacts.append(artifact)
        return artifact


class FakeLogRepository:
    def __init__(self):
        self.logs = []

    def add_log(self, **kwargs):
        self.logs.append(kwargs)
        return kwargs


class FakeAuditRepository:
    def __init__(self):
        self.audit_logs = []

    def create_audit_log(self, data):
        self.audit_logs.append(data)
        return data


def make_runner(command_runner=None, strategy_service=None):
    return FreqtradeBacktestRunner(
        command_runner=command_runner or DummyCommandRunner(),
        strategy_service=strategy_service or DummyStrategyService(),
        artifact_repository=FakeArtifactRepository(),
        log_repository=FakeLogRepository(),
        audit_repository=FakeAuditRepository(),
    )


def test_build_backtest_command():
    """Test building backtest command."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "backtesting" in command
    assert "--config" in command
    assert "/path/to/config.json" in command
    assert "--userdir" in command
    assert "--strategy" in command
    assert "MyStrategy" in command
    assert "--timeframe" in command
    assert "1h" in command
    assert "--export" in command
    assert "--backtest-directory" in command


def test_build_backtest_command_with_timerange():
    """Test building backtest command with timerange."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        timerange="20240101-20240131",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "--timerange" in command
    assert "20240101-20240131" in command


def test_build_backtest_command_with_pairs():
    """Test building backtest command with pairs."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        pairs=["BTC/USDT", "ETH/USDT"],
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "--pairs" in command
    assert "BTC/USDT,ETH/USDT" in command


def test_confirmation_required():
    """Test that user confirmation is required."""
    with pytest.raises(ValueError, match="user_confirmed must be true"):
        FreqtradeBacktestRequest(
            run_id="run-123",
            config_path="/path/to/config.json",
            strategy_name="MyStrategy",
            timeframe="1h",
            user_confirmed=False,
        )


def test_invalid_strategy_name_rejected():
    """Test that invalid strategy name is rejected."""
    with pytest.raises(ValueError, match="Strategy name must be valid class-name style"):
        FreqtradeBacktestRequest(
            run_id="run-123",
            config_path="/path/to/config.json",
            strategy_name="Invalid-Strategy!",
            timeframe="1h",
            user_confirmed=True,
        )


def test_invalid_export_rejected():
    """Test that invalid export type is rejected."""
    with pytest.raises(ValueError, match="export must be one of"):
        FreqtradeBacktestRequest(
            run_id="run-123",
            config_path="/path/to/config.json",
            strategy_name="MyStrategy",
            timeframe="1h",
            export="invalid",
            user_confirmed=True,
        )


def test_backtest_directory_created(tmp_path, monkeypatch):
    """Test that backtest directory is created."""
    from app.core.config import settings

    monkeypatch.setenv("PROJECT_ROOT", str(tmp_path))

    runner = make_runner()
    backtest_dir = runner.prepare_backtest_directory("run-123")

    assert backtest_dir.exists()
    assert backtest_dir.name == "backtest_results"
    assert "run-123" in str(backtest_dir)


def test_artifact_registration_with_sample_files(tmp_path, monkeypatch):
    """Test artifact registration with sample files."""
    from app.core.config import settings

    # Create the expected directory structure
    artifacts_dir = tmp_path / "artifacts" / "runs" / "run-123" / "raw_freqtrade" / "backtest_results"
    artifacts_dir.mkdir(parents=True)

    # Set started_at slightly before creating files to account for timing
    started_at = datetime.fromtimestamp(0)  # Use epoch to ensure files are newer

    # Create sample files
    (artifacts_dir / "backtest-result.json").write_text("{}")
    (artifacts_dir / "trades.csv").write_text("")

    runner = make_runner()
    artifacts = runner.discover_backtest_outputs(artifacts_dir, started_at)

    assert len(artifacts) == 2


def test_missing_freqtrade_controlled_failure(tmp_path, monkeypatch):
    """Test controlled failure when Freqtrade is missing."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", None)

    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    result = runner.run_backtest(request)

    assert result.success is False
    assert result.blocked is True
    assert "Freqtrade is not configured" in result.error


def test_missing_strategy_controlled_failure(tmp_path, monkeypatch):
    """Test controlled failure when strategy is missing."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    runner = make_runner(strategy_service=DummyStrategyService(exists=False))
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="NonExistentStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    result = runner.run_backtest(request)

    assert result.success is False
    assert result.blocked is True
    assert "Strategy not found" in result.error


def test_forbidden_command_never_used():
    """Test that forbidden 'trade' command is never used."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "trade" not in command
    assert "backtesting" in command


def test_no_metrics_classification():
    """Test that no metrics classification happens in backtest runner."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    # No classification-related flags
    assert "--analyze" not in command
    assert "--breakdown" not in command
    assert "--export-filename" not in command


def test_write_stdout_stderr_logs(tmp_path, monkeypatch):
    """Test writing stdout and stderr to log files."""
    from app.core.config import settings

    # Create the expected directory structure
    logs_dir = tmp_path / "artifacts" / "runs" / "run-123" / "raw_freqtrade"
    logs_dir.mkdir(parents=True)

    runner = make_runner()
    command_result = DummyCommandRunner().run(["test"])

    # Manually set the artifacts directory for this test
    runner.get_artifacts_dir = lambda: tmp_path

    log_paths = runner.write_stdout_stderr_logs("run-123", command_result)

    assert Path(log_paths["stdout"]).exists()
    assert Path(log_paths["stderr"]).exists()


def test_backtest_success(tmp_path, monkeypatch):
    """Test successful backtest execution."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    freqtrade_output = "Backtest completed successfully"
    command_runner = DummyCommandRunner(success=True, stdout=freqtrade_output)
    runner = make_runner(command_runner=command_runner)

    # Manually set the artifacts directory for this test
    runner.get_artifacts_dir = lambda: tmp_path

    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    result = runner.run_backtest(request)

    assert result.success is True
    assert result.blocked is False
    assert result.stdout == freqtrade_output


def test_backtest_failure(tmp_path, monkeypatch):
    """Test failed backtest execution."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    command_runner = DummyCommandRunner(success=False, stderr="Backtest failed")
    runner = make_runner(command_runner=command_runner)

    # Manually set the artifacts directory for this test
    runner.get_artifacts_dir = lambda: tmp_path

    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    result = runner.run_backtest(request)

    assert result.success is False
    assert result.blocked is False
    assert result.error is not None


def test_logs_and_audit_recorded(tmp_path, monkeypatch):
    """Test that logs and audit entries are recorded."""
    from app.core.config import settings

    monkeypatch.setattr(settings, "FREQTRADE_PATH", "freqtrade")

    command_runner = DummyCommandRunner(success=True, stdout="Success")
    log_repo = FakeLogRepository()
    audit_repo = FakeAuditRepository()
    runner = make_runner(command_runner=command_runner, strategy_service=DummyStrategyService())
    runner.log_repository = log_repo
    runner.audit_repository = audit_repo

    # Manually set the artifacts directory for this test
    runner.get_artifacts_dir = lambda: tmp_path

    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    runner.run_backtest(request)

    assert len(log_repo.logs) >= 2  # Start and completion logs
    assert len(audit_repo.audit_logs) == 1
    assert audit_repo.audit_logs[0]["action"] == "freqtrade_backtest"


def test_custom_backtest_directory(tmp_path):
    """Test using custom backtest directory."""
    custom_dir = tmp_path / "custom_backtest"
    custom_dir.mkdir(parents=True)

    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        backtest_directory=str(custom_dir),
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert str(custom_dir) in command


def test_default_export_trades():
    """Test that default export is trades."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "--export" in command
    assert "trades" in command


def test_export_signals():
    """Test export signals option."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        export="signals",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "--export" in command
    assert "signals" in command


def test_export_none():
    """Test export none option."""
    runner = make_runner()
    request = FreqtradeBacktestRequest(
        run_id="run-123",
        config_path="/path/to/config.json",
        strategy_name="MyStrategy",
        timeframe="1h",
        export="none",
        user_confirmed=True,
    )

    command = runner.build_backtest_command(request)

    assert "--export" in command
    assert "none" in command
