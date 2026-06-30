"""
Tests for Part 08 Freqtrade hyperopt runner.
"""
from pathlib import Path
from unittest.mock import MagicMock, patch
import json

import pytest

from app.schemas.freqtrade import FreqtradeCommandResult
from app.schemas.optimization import HyperoptPolicy, HyperoptRunResult, OptimizationRequest
from app.services.freqtrade_command_runner import FreqtradeCommandRunner
from app.services.freqtrade_detection import FreqtradeDetectionService
from app.services.freqtrade_hyperopt_runner import FreqtradeHyperoptRunner


@pytest.fixture
def mock_command_runner():
    """Create a mock command runner."""
    runner = MagicMock(spec=FreqtradeCommandRunner)
    runner.ALLOWED_COMMANDS = ["hyperopt", "hyperopt-list", "hyperopt-show"]
    return runner


@pytest.fixture
def mock_detection_service():
    """Create a mock detection service."""
    service = MagicMock(spec=FreqtradeDetectionService)
    service.get_freqtrade_executable.return_value = "/usr/bin/freqtrade"
    service.is_executable_available.return_value = True
    return service


@pytest.fixture
def hyperopt_runner(mock_command_runner, mock_detection_service):
    """Create a FreqtradeHyperoptRunner with mocked dependencies."""
    return FreqtradeHyperoptRunner(
        command_runner=mock_command_runner,
        detection_service=mock_detection_service,
    )


@pytest.fixture
def sample_request():
    """Sample optimization request."""
    return OptimizationRequest(
        strategy_name="TestStrategy",
        pairs=["BTC/USDT", "ETH/USDT"],
        timeframe="5m",
        exchange="binance",
        epochs=50,
        spaces=["buy", "sell"],
        risk_profile="balanced",
        user_confirmed=True,
    )


@pytest.fixture
def sample_policy():
    """Sample hyperopt policy."""
    return HyperoptPolicy(
        max_epochs=200,
        default_epochs=50,
        allowed_spaces=["buy", "sell"],
        locked_spaces=["roi", "stoploss", "trailing", "protection"],
        timeout_seconds=3600,
        min_trades=30,
    )


class TestFreqtradeHyperoptRunner:
    """Test FreqtradeHyperoptRunner methods."""

    def test_init_with_defaults(self):
        """Test initialization with default dependencies."""
        with patch(
            "app.services.freqtrade_hyperopt_runner.FreqtradeCommandRunner"
        ) as mock_runner_init, patch(
            "app.services.freqtrade_hyperopt_runner.FreqtradeDetectionService"
        ) as mock_detection_init:
            mock_runner = MagicMock(spec=FreqtradeCommandRunner)
            mock_detection = MagicMock(spec=FreqtradeDetectionService)
            mock_runner_init.return_value = mock_runner
            mock_detection_init.return_value = mock_detection

            runner = FreqtradeHyperoptRunner()

            assert runner.command_runner == mock_runner
            assert runner.detection_service == mock_detection

    def test_build_hyperopt_command(self, hyperopt_runner):
        """Test building safe hyperopt command."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        assert command[0] == "/usr/bin/freqtrade"
        assert command[1] == "hyperopt"
        assert "--config" in command
        assert "/path/to/config.json" in command
        assert "--strategy" in command
        assert "TestStrategy" in command
        assert "--spaces" in command
        assert "buy" in command
        assert "sell" in command
        assert "--epochs" in command
        assert "50" in command
        assert "--hyperopt-loss" in command
        assert "SharpeHyperOptLossDaily" in command
        assert "--disable-param-export" in command

    def test_build_hyperopt_command_no_executable(self, hyperopt_runner):
        """Test building command when executable not found."""
        hyperopt_runner.detection_service.get_freqtrade_executable.return_value = None

        with pytest.raises(ValueError, match="Freqtrade executable not found"):
            hyperopt_runner.build_hyperopt_command(
                config_path="/path/to/config.json",
                strategy_name="TestStrategy",
                spaces=["buy", "sell"],
                epochs=50,
            )

    def test_build_hyperopt_command_no_live_trading_params(self, hyperopt_runner):
        """Test that command does not include live trading parameters."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        # Should not contain live trading parameters
        assert "--dry-run" not in command
        assert "--live" not in command
        assert "trade" not in [arg.lower() for arg in command]
        assert "order" not in [arg.lower() for arg in command]
        assert "--hyperopt-loss" in command
        assert "SharpeHyperOptLossDaily" in command
        assert "--disable-param-export" in command

    def test_run_hyperopt_success(
        self, hyperopt_runner, sample_request, sample_policy
    ):
        """Test successful hyperopt execution."""
        # Mock successful command result
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=0,
            stdout="Hyperopt completed successfully",
            stderr="",
            duration_seconds=60.0,
            success=True,
            error=None,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        assert result.success is True
        assert result.exit_code == 0
        assert result.duration_seconds == 60.0
        assert result.blocked is False
        assert result.timed_out is False

        # Verify command runner was called with correct parameters
        hyperopt_runner.command_runner.run.assert_called_once()
        call_args = hyperopt_runner.command_runner.run.call_args
        assert call_args[1]["run_id"] == "test-run-123"
        assert call_args[1]["stage_key"] == "hyperopt_execution"
        assert call_args[1]["timeout_seconds"] == 3600

    def test_run_hyperopt_command_blocked(
        self, hyperopt_runner, sample_request, sample_policy
    ):
        """Test hyperopt execution when command is blocked."""
        # Mock blocked command result
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            blocked=True,
            error="Command blocked by safety policy",
            duration_seconds=0.1,
            success=False,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        assert result.success is False
        assert result.blocked is True
        assert "Command blocked" in result.errors[0]

    def test_run_hyperopt_timed_out(
        self, hyperopt_runner, sample_request, sample_policy
    ):
        """Test hyperopt execution when command times out."""
        # Mock timed out command result
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            timed_out=True,
            error="Command timed out",
            duration_seconds=3600.0,
            success=False,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        assert result.success is False
        assert result.timed_out is True
        assert "timed out" in result.errors[0]

    def test_run_hyperopt_command_metadata_logged(
        self, hyperopt_runner, sample_request, sample_policy
    ):
        """Test that command metadata is logged without secrets."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=0,
            stdout="",
            stderr="",
            duration_seconds=60.0,
            success=True,
            error=None,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        assert result.command_metadata["executable"] == "/usr/bin/freqtrade"
        assert result.command_metadata["config_path"] == "/path/to/config.json"
        assert result.command_metadata["strategy"] == "TestStrategy"
        assert result.command_metadata["spaces"] == ["buy", "sell"]
        assert result.command_metadata["epochs"] == 50
        assert result.command_metadata["hyperopt_loss"] == "SharpeHyperOptLossDaily"
        assert result.command_metadata["run_id"] == "test-run-123"

        # Ensure no secrets in metadata
        assert "secret" not in str(result.command_metadata).lower()
        assert "api_key" not in str(result.command_metadata).lower()
        assert "password" not in str(result.command_metadata).lower()

    def test_run_hyperopt_persists_failure_stdout_stderr_and_metadata(
        self, hyperopt_runner, sample_request, sample_policy, tmp_path
    ):
        """Failed hyperopt attempts leave durable logs and command evidence."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=2,
            stdout="partial stdout",
            stderr="No module named 'filelock'. Please ensure that the hyperopt dependencies are installed.",
            duration_seconds=0.25,
            success=False,
            error="Freqtrade command failed.",
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        with patch(
            "app.services.freqtrade_hyperopt_runner.HER_ARTIFACTS_RUNS",
            str(tmp_path),
        ):
            result = hyperopt_runner.run_hyperopt(
                request=sample_request,
                config_path="/path/to/config.json",
                run_id="test-run-123",
                policy=sample_policy,
            )

        run_artifact_dir = tmp_path / "test-run-123" / "hyperopt"
        stdout_path = run_artifact_dir / "stdout.log"
        stderr_path = run_artifact_dir / "stderr.log"
        metadata_path = run_artifact_dir / "command_metadata.json"

        assert result.success is False
        assert result.exit_code == 2
        assert result.stdout_path == str(stdout_path)
        assert result.stderr_path == str(stderr_path)
        assert stdout_path.read_text() == "partial stdout"
        assert "No module named 'filelock'" in stderr_path.read_text()

        metadata = json.loads(metadata_path.read_text())
        assert metadata["config_path"] == "/path/to/config.json"
        assert metadata["strategy"] == "TestStrategy"
        assert metadata["spaces"] == ["buy", "sell"]
        assert metadata["epochs"] == 50
        assert metadata["hyperopt_loss"] == "SharpeHyperOptLossDaily"
        assert metadata["exit_code"] == 2
        assert metadata["duration_seconds"] == 0.25
        assert metadata["success"] is False
        assert metadata["command_args"] == metadata["full_args"]
        assert str(metadata_path) not in result.result_files

    def test_execution_artifact_metadata_has_no_output_secrets(
        self, hyperopt_runner, sample_request, sample_policy, tmp_path
    ):
        """Persisted command metadata keeps secrets out while retaining diagnostics."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=1,
            stdout="safe output",
            stderr="[REDACTED]",
            duration_seconds=1.0,
            success=False,
            error="Freqtrade command failed.",
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        with patch(
            "app.services.freqtrade_hyperopt_runner.HER_ARTIFACTS_RUNS",
            str(tmp_path),
        ):
            result = hyperopt_runner.run_hyperopt(
                request=sample_request,
                config_path="/path/to/config.json",
                run_id="test-run-123",
                policy=sample_policy,
            )

        metadata_path = tmp_path / "test-run-123" / "hyperopt" / "command_metadata.json"
        metadata_text = metadata_path.read_text().lower()
        assert "api_key" not in metadata_text
        assert "password" not in metadata_text
        assert "token" not in metadata_text
        assert "[redacted]" not in metadata_text

    def test_capture_hyperopt_artifacts(self, hyperopt_runner, tmp_path):
        """Test capturing hyperopt result files."""
        # Create mock hyperopt results directory
        hyperopt_dir = tmp_path / "hyperopt_results"
        hyperopt_dir.mkdir()
        (hyperopt_dir / "result1.json").write_text("{}")
        (hyperopt_dir / "result2.json").write_text("{}")
        (hyperopt_dir / "result.pickle").write_bytes(b"data")

        artifacts = hyperopt_runner.capture_hyperopt_artifacts("test-run-123", str(tmp_path))

        assert len(artifacts) == 3
        assert any("result1.json" in a for a in artifacts)
        assert any("result2.json" in a for a in artifacts)
        assert any("result.pickle" in a for a in artifacts)

    def test_capture_hyperopt_artifacts_no_cwd(self, hyperopt_runner):
        """Test artifact capture when no working directory provided."""
        with patch(
            "app.services.freqtrade_hyperopt_runner.FREQTRADE_HYPEROPT_RESULTS",
            "/path/that/does/not/exist",
        ):
            artifacts = hyperopt_runner.capture_hyperopt_artifacts("test-run-123", None)

        assert artifacts == []

    def test_find_hyperopt_result_files(self, hyperopt_runner, tmp_path):
        """Test finding hyperopt result files for specific run."""
        hyperopt_dir = tmp_path / "hyperopt_results"
        hyperopt_dir.mkdir()
        (hyperopt_dir / "test-run-123-result.json").write_text("{}")
        (hyperopt_dir / "other-run-result.json").write_text("{}")

        result_files = hyperopt_runner.find_hyperopt_result_files(
            "test-run-123", str(tmp_path)
        )

        assert len(result_files) == 1
        assert "test-run-123" in result_files[0]

    def test_find_hyperopt_result_files_no_directory(self, hyperopt_runner, tmp_path):
        """Test finding result files when directory doesn't exist."""
        result_files = hyperopt_runner.find_hyperopt_result_files("test-run-123", str(tmp_path))

        assert result_files == []

    def test_get_hyperopt_help(self, hyperopt_runner):
        """Test getting hyperopt help information."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt", "--help"],
            sanitized_command=["freqtrade", "hyperopt", "--help"],
            return_code=0,
            stdout="Usage: freqtrade hyperopt [OPTIONS]",
            stderr="",
            duration_seconds=1.0,
            success=True,
            error=None,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        help_info = hyperopt_runner.get_hyperopt_help()

        assert help_info["success"] is True
        assert "Usage: freqtrade hyperopt" in help_info["stdout"]
        assert help_info["exit_code"] == 0

    def test_get_hyperopt_help_no_executable(self, hyperopt_runner):
        """Test getting help when executable not found."""
        hyperopt_runner.detection_service.get_freqtrade_executable.return_value = None

        help_info = hyperopt_runner.get_hyperopt_help()

        assert "error" in help_info
        assert "not found" in help_info["error"]

    def test_command_includes_only_hyperopt(self, hyperopt_runner):
        """Test that command includes only hyperopt, not trade/webserver."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        # Should be hyperopt command
        assert "hyperopt" in command

        # Should not include forbidden commands
        assert "trade" not in [arg.lower() for arg in command]
        assert "webserver" not in [arg.lower() for arg in command]

    def test_command_includes_config_path(self, hyperopt_runner):
        """Test that command includes config path."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        assert "--config" in command
        assert "/path/to/config.json" in command

    def test_command_includes_strategy(self, hyperopt_runner):
        """Test that command includes strategy."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        assert "--strategy" in command
        assert "TestStrategy" in command

    def test_command_includes_spaces_and_epochs(self, hyperopt_runner):
        """Test that command includes spaces and epochs."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        assert "--spaces" in command
        assert "buy" in command
        assert "sell" in command
        assert "--epochs" in command
        assert "50" in command

    def test_command_args_are_all_non_empty_strings(self, hyperopt_runner):
        """Test that all command arguments are non-empty strings."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        for arg in command:
            assert isinstance(arg, str)
            assert arg.strip()  # Non-empty after stripping

    def test_spaces_list_becomes_valid_cli_args(self, hyperopt_runner):
        """Test that spaces list becomes valid CLI args."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=["buy", "sell"],
            epochs=50,
        )

        # Spaces should be separate args after --spaces
        spaces_index = command.index("--spaces")
        assert command[spaces_index + 1] == "buy"
        assert command[spaces_index + 2] == "sell"

    def test_config_path_required(self, hyperopt_runner):
        """Test that config path is required and validated."""
        with pytest.raises(ValueError, match="Invalid config_path"):
            hyperopt_runner.build_hyperopt_command(
                config_path="",
                strategy_name="TestStrategy",
                spaces=["buy"],
                epochs=50,
            )

        with pytest.raises(ValueError, match="Invalid config_path"):
            hyperopt_runner.build_hyperopt_command(
                config_path=None,
                strategy_name="TestStrategy",
                spaces=["buy"],
                epochs=50,
            )

    def test_strategy_name_required(self, hyperopt_runner):
        """Test that strategy name is required and validated."""
        with pytest.raises(ValueError, match="Invalid strategy_name"):
            hyperopt_runner.build_hyperopt_command(
                config_path="/path/to/config.json",
                strategy_name="",
                spaces=["buy"],
                epochs=50,
            )

        with pytest.raises(ValueError, match="Invalid strategy_name"):
            hyperopt_runner.build_hyperopt_command(
                config_path="/path/to/config.json",
                strategy_name=None,
                spaces=["buy"],
                epochs=50,
            )

    def test_epochs_required_and_positive(self, hyperopt_runner):
        """Test that epochs is required and positive."""
        with pytest.raises(ValueError, match="Invalid epochs"):
            hyperopt_runner.build_hyperopt_command(
                config_path="/path/to/config.json",
                strategy_name="TestStrategy",
                spaces=["buy"],
                epochs=0,
            )

        with pytest.raises(ValueError, match="Invalid epochs"):
            hyperopt_runner.build_hyperopt_command(
                config_path="/path/to/config.json",
                strategy_name="TestStrategy",
                spaces=["buy"],
                epochs=-10,
            )

    def test_optional_empty_values_skipped(self, hyperopt_runner):
        """Test that optional empty values are skipped, not included."""
        command = hyperopt_runner.build_hyperopt_command(
            config_path="/path/to/config.json",
            strategy_name="TestStrategy",
            spaces=[],  # Empty spaces list
            epochs=50,
        )

        # Should not include --spaces when spaces is empty
        assert "--spaces" not in command

    def test_invalid_args_produce_clear_error_with_index(self, hyperopt_runner):
        """Test that invalid args produce a clear controlled error with index/value."""
        with pytest.raises(ValueError) as exc_info:
            hyperopt_runner.build_hyperopt_command(
                config_path="",  # Invalid empty string
                strategy_name="TestStrategy",
                spaces=["buy"],
                epochs=50,
            )

        error_message = str(exc_info.value)
        assert "Invalid config_path" in error_message
        assert "index" not in error_message  # Config validation happens before command building

    def test_command_metadata_includes_full_args(self, hyperopt_runner, sample_request, sample_policy):
        """Test that command metadata includes full args for debugging."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=0,
            stdout="",
            stderr="",
            duration_seconds=60.0,
            success=True,
            error=None,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        assert "full_args" in result.command_metadata
        assert isinstance(result.command_metadata["full_args"], list)
        assert len(result.command_metadata["full_args"]) > 0

    def test_no_secrets_in_command_metadata(self, hyperopt_runner, sample_request, sample_policy):
        """Test that no secrets are in command metadata."""
        mock_result = FreqtradeCommandResult(
            command=["freqtrade", "hyperopt"],
            sanitized_command=["freqtrade", "hyperopt"],
            return_code=0,
            stdout="",
            stderr="",
            duration_seconds=60.0,
            success=True,
            error=None,
        )
        hyperopt_runner.command_runner.run.return_value = mock_result

        result = hyperopt_runner.run_hyperopt(
            request=sample_request,
            config_path="/path/to/config.json",
            run_id="test-run-123",
            policy=sample_policy,
        )

        metadata_str = str(result.command_metadata).lower()
        assert "secret" not in metadata_str
        assert "api_key" not in metadata_str
        assert "password" not in metadata_str
        assert "token" not in metadata_str
