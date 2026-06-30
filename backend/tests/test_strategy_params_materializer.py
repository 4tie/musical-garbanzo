"""
Tests for StrategyParamsMaterializer.
Tests safe materialization of best trial parameters without overwriting originals.
"""
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from app.services.strategy_params_materializer import StrategyParamsMaterializer
from app.repositories.artifacts import ArtifactRepository


@pytest.fixture
def temp_artifacts_dir(tmp_path):
    """Create a temporary artifacts directory."""
    artifacts_dir = tmp_path / "artifacts" / "runs"
    artifacts_dir.mkdir(parents=True)
    return artifacts_dir


@pytest.fixture
def mock_artifact_repository():
    """Create a mock artifact repository."""
    repo = MagicMock()
    repo.create_artifact.return_value = {
        "id": "artifact-123",
        "run_id": "opt-run-123",
        "artifact_type": "optimized_params",
        "file_path": "/path/to/params.json",
    }
    return repo


@pytest.fixture
def sample_params():
    """Sample best trial parameters."""
    return {
        "buy": {
            "buy_rsi": 30,
            "buy_fastd": 20,
        },
        "sell": {
            "sell_rsi": 70,
            "sell_fastd": 80,
        },
        "roi": {
            "0": 0.06,
            "60": 0.04,
            "120": 0.02,
        },
        "stoploss": {
            "stoploss": -0.1,
        },
        "trailing": {
            "trailing_stop": True,
            "trailing_stop_positive": 0.02,
        },
    }


class TestStrategyParamsMaterializer:
    """Test StrategyParamsMaterializer."""

    def test_materialize_params_writes_params_file(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer writes params file to correct location."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            # Check that file was created
            params_path = Path(result["artifact_path"])
            assert params_path.exists()

            # Check file is in optimized_params subdirectory
            assert "optimized_params" in str(params_path)

            # Check file content
            with open(params_path) as f:
                content = json.load(f)
            assert content["strategy_name"] == "MyStrategy"
            assert content["source_trial_id"] == "trial-456"
            assert content["source_trial_number"] == 42
            assert "params" in content

    def test_materialize_params_includes_source_trial_id(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer includes source trial ID."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            params_path = Path(result["artifact_path"])
            with open(params_path) as f:
                content = json.load(f)

            assert content["source_trial_id"] == "trial-456"

    def test_materialize_params_separates_params_sections(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer separates buy/sell/roi/stoploss/trailing params."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            params_path = Path(result["artifact_path"])
            with open(params_path) as f:
                content = json.load(f)

            assert "buy" in content["params"]
            assert "sell" in content["params"]
            assert "roi" in content["params"]
            assert "stoploss" in content["params"]
            assert "trailing" in content["params"]

    def test_materialize_params_validates_required_sections(
        self, temp_artifacts_dir, mock_artifact_repository
    ):
        """Test that materializer validates required params sections."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            # Missing buy section
            invalid_params = {
                "sell": {"sell_rsi": 70},
            }

            with pytest.raises(ValueError, match="Missing required params section: buy"):
                materializer.materialize_params(
                    run_id="opt-run-123",
                    strategy_name="MyStrategy",
                    trial_id="trial-456",
                    trial_number=42,
                    params=invalid_params,
                )

    def test_materialize_params_validates_buy_not_empty(
        self, temp_artifacts_dir, mock_artifact_repository
    ):
        """Test that materializer validates buy params are not empty."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            invalid_params = {
                "buy": {},
                "sell": {"sell_rsi": 70},
            }

            with pytest.raises(ValueError, match="Buy params must be a non-empty dictionary"):
                materializer.materialize_params(
                    run_id="opt-run-123",
                    strategy_name="MyStrategy",
                    trial_id="trial-456",
                    trial_number=42,
                    params=invalid_params,
                )

    def test_materialize_params_registers_artifact(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer registers artifact in repository."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            # Check that artifact was registered
            mock_artifact_repository.create_artifact.assert_called_once()
            call_args = mock_artifact_repository.create_artifact.call_args
            assert call_args[0][0].run_id == "opt-run-123"
            assert call_args[0][0].artifact_type == "optimized_params"

    def test_materialize_params_includes_description(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer includes description in artifact."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            # Check description in artifact registration
            call_args = mock_artifact_repository.create_artifact.call_args
            description = call_args[0][0].description
            assert "MyStrategy" in description
            assert "trial-456" in description

    def test_materialize_params_no_secrets_in_artifact(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that params artifact contains no secrets."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            params_path = Path(result["artifact_path"])
            with open(params_path) as f:
                content = json.load(f)

            # Check for common secret markers
            content_str = json.dumps(content).lower()
            assert "api_key" not in content_str
            assert "secret" not in content_str
            assert "password" not in content_str
            assert "token" not in content_str

    def test_materialize_params_creates_run_owned_directory(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that materializer creates run-owned directory."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            # Check that params file was created in the correct location
            # This implicitly verifies the directory was created
            params_path = Path(result["artifact_path"])
            assert params_path.parent.name == "optimized_params"
            assert params_path.parent.parent.name == "opt-run-123"

    def test_materialize_params_filename_uses_strategy_name(
        self, temp_artifacts_dir, mock_artifact_repository, sample_params
    ):
        """Test that params filename uses strategy name."""
        with patch("app.core.constants.HER_ARTIFACTS_RUNS", str(temp_artifacts_dir)):
            materializer = StrategyParamsMaterializer(artifact_repository=mock_artifact_repository)

            result = materializer.materialize_params(
                run_id="opt-run-123",
                strategy_name="MyStrategy",
                trial_id="trial-456",
                trial_number=42,
                params=sample_params,
            )

            params_path = Path(result["artifact_path"])
            assert params_path.name == "MyStrategy.json"
            assert params_path.suffix == ".json"
