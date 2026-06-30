"""
Tests for Part 08 hyperopt result parser.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.constants import HER_ARTIFACTS_RUNS
from app.schemas.optimization import HyperoptPolicy, OptimizationTrialStatus
from app.services.hyperopt_result_parser import HyperoptResultParser


@pytest.fixture
def mock_repository():
    """Create a mock optimization repository."""
    repo = MagicMock()
    repo._uuid = MagicMock(side_effect=lambda: f"trial-{id(repo)}")
    repo._now = MagicMock(return_value="2024-01-01T00:00:00Z")
    return repo


@pytest.fixture
def parser(mock_repository):
    """Create a HyperoptResultParser with mocked repository."""
    return HyperoptResultParser(repository=mock_repository)


@pytest.fixture
def sample_policy():
    """Sample hyperopt policy."""
    return HyperoptPolicy(
        max_epochs=200,
        default_epochs=50,
        min_trades=30,
        stop_on_zero_trades=True,
    )


class TestHyperoptResultParser:
    """Test HyperoptResultParser methods."""

    def test_init_with_defaults(self):
        """Test initialization with default repository."""
        with patch(
            "app.services.hyperopt_result_parser.OptimizationRepository"
        ) as mock_repo_init:
            mock_repo = MagicMock()
            mock_repo_init.return_value = mock_repo

            parser = HyperoptResultParser()

            assert parser.repository == mock_repo

    def test_discover_hyperopt_outputs_with_files(self, parser):
        """Test discovering outputs when files are provided."""
        result_files = ["/path/to/result1.json", "/path/to/result2.json"]
        discovered = parser.discover_hyperopt_outputs("test-run-123", result_files)

        assert discovered == result_files

    def test_discover_hyperopt_outputs_from_run_hyperopt_dir(self, parser, tmp_path):
        """Test discovering outputs from run-specific hyperopt directory."""
        run_id = "test-run-123"
        run_hyperopt_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "hyperopt"
        run_hyperopt_dir.mkdir(parents=True, exist_ok=True)

        # Create test JSON files
        (run_hyperopt_dir / "result1.json").write_text('{"loss": 0.5}')
        (run_hyperopt_dir / "result2.json").write_text('{"loss": 0.3}')

        discovered = parser.discover_hyperopt_outputs(run_id, None)

        assert len(discovered) == 2
        assert any("result1.json" in f for f in discovered)
        assert any("result2.json" in f for f in discovered)

        # Cleanup
        import shutil
        shutil.rmtree(Path(HER_ARTIFACTS_RUNS) / run_id)

    def test_discover_hyperopt_outputs_from_run_artifacts_dir(self, parser, tmp_path):
        """Test discovering outputs from run-specific artifacts directory."""
        run_id = "test-run-456"
        run_artifacts_dir = Path(HER_ARTIFACTS_RUNS) / run_id
        run_artifacts_dir.mkdir(parents=True, exist_ok=True)

        # Create test JSON files
        (run_artifacts_dir / "result1.json").write_text('{"loss": 0.5}')
        (run_artifacts_dir / "result2.json").write_text('{"loss": 0.3}')

        discovered = parser.discover_hyperopt_outputs(run_id, None)

        assert len(discovered) == 2
        assert any("result1.json" in f for f in discovered)
        assert any("result2.json" in f for f in discovered)

        # Cleanup
        import shutil
        shutil.rmtree(Path(HER_ARTIFACTS_RUNS) / run_id)

    def test_discover_hyperopt_outputs_no_files_raises_error(self, parser):
        """Test that discovery raises error when no files are found."""
        run_id = "nonexistent-run-789"

        with pytest.raises(ValueError, match="No hyperopt result files discovered"):
            parser.discover_hyperopt_outputs(run_id, None)

    def test_discover_hyperopt_outputs_deduplicates_files(self, parser, tmp_path):
        """Test that discovery deduplicates files from the same location."""
        import uuid
        run_id = f"test-run-dedupe-{uuid.uuid4()}"
        run_hyperopt_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "hyperopt"
        run_hyperopt_dir.mkdir(parents=True, exist_ok=True)

        # Create test files
        (run_hyperopt_dir / "result1.json").write_text('{"loss": 0.5}')
        (run_hyperopt_dir / "result2.json").write_text('{"loss": 0.3}')

        discovered = parser.discover_hyperopt_outputs(run_id, None)

        # Should return both files (no duplicates from same location)
        assert len(discovered) == 2

        # Cleanup
        import shutil
        shutil.rmtree(Path(HER_ARTIFACTS_RUNS) / run_id)

    def test_load_hyperopt_result(self, parser, tmp_path):
        """Test loading a hyperopt result file."""
        result_file = tmp_path / "result.json"
        result_file.write_text('{"loss": 0.5, "params": {}}')

        result = parser.load_hyperopt_result(str(result_file))

        assert result == {"loss": 0.5, "params": {}}

    def test_load_hyperopt_result_fthypt_ndjson(self, parser, tmp_path):
        """Freqtrade .fthypt files are newline-delimited JSON trials."""
        result_file = tmp_path / "strategy_TestStrategy_2026-06-30.fthypt"
        result_file.write_text(
            '{"loss": 0.5, "current_epoch": 1}\n'
            '{"loss": 0.3, "current_epoch": 2, "is_best": true}\n'
        )

        result = parser.load_hyperopt_result(str(result_file))

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[1]["is_best"] is True

    def test_load_hyperopt_result_invalid_json(self, parser, tmp_path):
        """Test loading invalid JSON file."""
        result_file = tmp_path / "result.json"
        result_file.write_text("invalid json")

        with pytest.raises(ValueError, match="Failed to load"):
            parser.load_hyperopt_result(str(result_file))

    def test_parse_trials_list_shape(self, parser):
        """Test parsing trials from list shape."""
        raw_result = [
            {"loss": 0.5, "buy_rsi": 30},
            {"loss": 0.3, "buy_rsi": 35},
        ]

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].trial_number == 1
        assert trials[1].trial_number == 2
        assert trials[0].loss_score == 0.5
        assert trials[1].loss_score == 0.3

    def test_parse_trials_object_with_results(self, parser):
        """Test parsing trials from object with results key."""
        raw_result = {
            "results": [
                {"loss": 0.5, "buy_rsi": 30},
                {"loss": 0.3, "buy_rsi": 35},
            ]
        }

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].trial_number == 1
        assert trials[1].trial_number == 2

    def test_parse_trials_object_with_trials(self, parser):
        """Test parsing trials from object with trials key."""
        raw_result = {
            "trials": [
                {"loss": 0.5, "buy_rsi": 30},
                {"loss": 0.3, "buy_rsi": 35},
            ]
        }

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].trial_number == 1
        assert trials[1].trial_number == 2

    def test_parse_trials_single_trial(self, parser):
        """Test parsing a single trial object."""
        raw_result = {"loss": 0.5, "buy_rsi": 30}

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 1
        assert trials[0].trial_number == 1
        assert trials[0].loss_score == 0.5

    def test_parse_best_trial_explicit_best_result(self, parser):
        """Test parsing best trial from explicit best_result."""
        raw_result = {
            "best_result": {"loss": 0.3, "buy_rsi": 35},
            "results": [
                {"loss": 0.5, "buy_rsi": 30},
                {"loss": 0.3, "buy_rsi": 35},
            ],
        }

        trials = parser.parse_trials(raw_result)
        best_trial = parser.parse_best_trial(raw_result, trials)

        assert best_trial is not None
        assert best_trial.is_best is True
        assert best_trial.loss_score == 0.3

    def test_parse_best_trial_lowest_loss(self, parser):
        """Test parsing best trial by lowest loss score."""
        raw_result = [
            {"loss": 0.5, "buy_rsi": 30},
            {"loss": 0.3, "buy_rsi": 35},
            {"loss": 0.7, "buy_rsi": 25},
        ]

        trials = parser.parse_trials(raw_result)
        best_trial = parser.parse_best_trial(raw_result, trials)

        assert best_trial is not None
        assert best_trial.is_best is True
        assert best_trial.loss_score == 0.3

    def test_parse_best_trial_prefers_fthypt_is_best_marker(self, parser):
        """Current Freqtrade marks the best .fthypt trial with is_best."""
        raw_result = [
            {"loss": -1.0, "current_epoch": 1, "is_best": True},
            {"loss": 0.2, "current_epoch": 2, "is_best": False},
        ]

        trials = parser.parse_trials(raw_result)
        best_trial = parser.parse_best_trial(raw_result, trials)

        assert best_trial is not None
        assert best_trial.trial_number == 1
        assert best_trial.is_best is True

    def test_parse_best_trial_no_trials(self, parser):
        """Test parsing best trial when no trials exist."""
        trials = []
        best_trial = parser.parse_best_trial({}, trials)

        assert best_trial is None

    def test_normalize_trial(self, parser):
        """Test normalizing a raw trial."""
        raw_trial = {
            "loss": 0.5,
            "buy_rsi": 30,
            "sell_rsi": 70,
            "metrics": {"profit_total": 100.0, "trade_count": 50},
        }

        trial = parser.normalize_trial(raw_trial, 1)

        assert trial.trial_number == 1
        assert trial.loss_score == 0.5
        # Params are separated by space
        assert trial.params["buy"]["rsi"] == 30
        assert trial.params["sell"]["rsi"] == 70
        assert trial.profit_total == 100.0
        assert trial.trade_count == 50

    def test_normalize_current_freqtrade_fthypt_trial_shape(self, parser):
        """Normalize params and metrics from Freqtrade 2026.5 .fthypt rows."""
        raw_trial = {
            "loss": -0.29757,
            "current_epoch": 10,
            "params_details": {
                "buy": {"buy_rsi": 28},
                "sell": {"sell_rsi": 77},
            },
            "results_metrics": {
                "profit_total": 0.0844,
                "profit_factor": 1.2,
                "expectancy": 12.3,
                "total_trades": 66,
                "winrate": 0.561,
                "max_drawdown_account": 0.0994,
            },
        }

        trial = parser.normalize_trial(raw_trial, raw_trial["current_epoch"])

        assert trial.trial_number == 10
        assert trial.loss_score == -0.29757
        assert trial.buy_params == {"buy_rsi": 28}
        assert trial.sell_params == {"sell_rsi": 77}
        assert trial.profit_total == 0.0844
        assert trial.profit_factor == 1.2
        assert trial.expectancy == 12.3
        assert trial.trade_count == 66
        assert trial.win_rate == 0.561
        assert trial.max_drawdown == 0.0994

    def test_extract_params(self, parser):
        """Test extracting parameters from raw trial."""
        raw_trial = {
            "params": {
                "buy_rsi": 30,
                "sell_rsi": 70,
                "roi_t1": 0.02,
                "stoploss_value": -0.05,
            }
        }

        params = parser.extract_params(raw_trial)

        # Params with prefixes should be separated
        assert "buy" in params
        assert "sell" in params
        assert "roi" in params
        assert "stoploss" in params
        assert params["buy"]["rsi"] == 30
        assert params["sell"]["rsi"] == 70

    def test_extract_params_separated_by_space(self, parser):
        """Test extracting parameters separated by space."""
        raw_trial = {
            "buy_rsi": 30,
            "sell_rsi": 70,
            "roi_t1": 0.02,
        }

        params = parser.extract_params(raw_trial)

        assert params["buy"]["rsi"] == 30
        assert params["sell"]["rsi"] == 70
        # ROI should be extracted if key is roi_t1
        assert "roi" in params

    def test_extract_metrics(self, parser):
        """Test extracting metrics from raw trial."""
        raw_trial = {
            "metrics": {
                "profit_total": 100.0,
                "profit_factor": 1.5,
                "trade_count": 50,
                "win_rate": 0.6,
            }
        }

        metrics = parser.extract_metrics(raw_trial)

        assert metrics["profit_total"] == 100.0
        assert metrics["profit_factor"] == 1.5
        assert metrics["trade_count"] == 50
        assert metrics["win_rate"] == 0.6

    def test_extract_metrics_flat_structure(self, parser):
        """Test extracting metrics from flat structure."""
        raw_trial = {
            "profit_total": 100.0,
            "profit_factor": 1.5,
            "trade_count": 50,
        }

        metrics = parser.extract_metrics(raw_trial)

        assert metrics["profit_total"] == 100.0
        assert metrics["profit_factor"] == 1.5
        assert metrics["trade_count"] == 50

    def test_extract_rejection_reason_below_min_trades(self, parser, sample_policy):
        """Test extracting rejection reason for below minimum trades."""
        raw_trial = {"metrics": {"trade_count": 10}}

        reason = parser.extract_rejection_reason(raw_trial, sample_policy)

        assert reason is not None
        assert "below minimum" in reason

    def test_extract_rejection_reason_zero_trades(self, parser, sample_policy):
        """Test extracting rejection reason for zero trades."""
        raw_trial = {"metrics": {"trade_count": 0}}

        reason = parser.extract_rejection_reason(raw_trial, sample_policy)

        assert reason is not None
        # Zero trades triggers the below minimum check first
        assert "below minimum" in reason or "Zero trades" in reason

    def test_extract_rejection_reason_valid(self, parser, sample_policy):
        """Test extracting rejection reason for valid trial."""
        raw_trial = {"metrics": {"trade_count": 50}}

        reason = parser.extract_rejection_reason(raw_trial, sample_policy)

        assert reason is None

    def test_classify_trial_status_completed(self, parser):
        """Test classifying trial as completed."""
        raw_trial = {"loss": 0.5}
        metrics = {}

        status = parser._classify_trial_status(raw_trial, metrics)

        assert status == OptimizationTrialStatus.COMPLETED

    def test_classify_trial_status_failed(self, parser):
        """Test classifying trial as failed."""
        raw_trial = {"error": "Strategy failed"}
        metrics = {}

        status = parser._classify_trial_status(raw_trial, metrics)

        assert status == OptimizationTrialStatus.FAILED

    def test_classify_trial_status_ignored(self, parser):
        """Test classifying trial as ignored."""
        raw_trial = {}
        metrics = {}

        status = parser._classify_trial_status(raw_trial, metrics)

        assert status == OptimizationTrialStatus.IGNORED

    def test_parse_and_persist_trials_success(self, parser, mock_repository, sample_policy, tmp_path):
        """Test parsing and persisting trials successfully."""
        result_file = tmp_path / "result.json"
        result_file.write_text(
            json.dumps([
                {"loss": 0.5, "buy_rsi": 30, "metrics": {"trade_count": 50}},
                {"loss": 0.3, "buy_rsi": 35, "metrics": {"trade_count": 52}},
            ])
        )

        results = parser.parse_and_persist_trials(
            "opt-run-123", [str(result_file)], sample_policy
        )

        assert results["trials_count"] == 2
        assert results["persisted_trials_count"] == 2
        assert results["partial_trial_history"] is False
        assert results["best_trial_id"] is not None
        assert results["best_trial_number"] is not None

    def test_parse_and_persist_trials_with_failed_trial(self, parser, mock_repository, tmp_path):
        """Test parsing and persisting trials including failed trial."""
        result_file = tmp_path / "result.json"
        result_file.write_text(
            json.dumps([
                {"loss": 0.5, "buy_rsi": 30, "metrics": {"trade_count": 50}},
                {"error": "Strategy failed", "buy_rsi": 35, "metrics": {"trade_count": 0}},
            ])
        )

        results = parser.parse_and_persist_trials("opt-run-123", [str(result_file)])

        assert results["trials_count"] == 2
        assert results["persisted_trials_count"] == 2

    def test_parse_and_persist_trials_with_rejected_trial(self, parser, mock_repository, sample_policy, tmp_path):
        """Test parsing and persisting trials including rejected trial."""
        result_file = tmp_path / "result.json"
        result_file.write_text(
            json.dumps([
                {"loss": 0.5, "buy_rsi": 30, "metrics": {"trade_count": 50}},
                {"loss": 0.3, "buy_rsi": 35, "metrics": {"trade_count": 10}},  # Below min_trades
            ])
        )

        results = parser.parse_and_persist_trials(
            "opt-run-123", [str(result_file)], sample_policy
        )

        assert results["trials_count"] == 2
        assert results["persisted_trials_count"] == 2

    def test_parse_and_persist_trials_no_trials(self, parser, mock_repository, tmp_path):
        """Test parsing when no trials are found."""
        result_file = tmp_path / "result.json"
        result_file.write_text("{}")

        results = parser.parse_and_persist_trials("opt-run-123", [str(result_file)])

        assert results["trials_count"] == 0
        assert results["persisted_trials_count"] == 0
        assert results["partial_trial_history"] is True
        assert len(results["warnings"]) > 0

    def test_parse_and_persist_trials_parse_error(self, parser, mock_repository, tmp_path):
        """Test parsing when result file is invalid."""
        result_file = tmp_path / "result.json"
        result_file.write_text("invalid json")

        results = parser.parse_and_persist_trials("opt-run-123", [str(result_file)])

        assert results["trials_count"] == 0
        assert len(results["errors"]) > 0

    def test_parse_list_of_trials_fixture(self, parser):
        """Test parsing list-of-trials fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "hyperopt" / "list_of_trials.json"
        raw_result = parser.load_hyperopt_result(str(fixture_path))

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 3
        assert trials[0].loss_score == 0.5
        assert trials[1].loss_score == 0.3
        assert trials[2].loss_score == 0.7

    def test_parse_object_with_results_fixture(self, parser):
        """Test parsing object-with-results fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "hyperopt" / "object_with_results.json"
        raw_result = parser.load_hyperopt_result(str(fixture_path))

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].loss_score == 0.5
        assert trials[1].loss_score == 0.3

    def test_parse_object_with_trials_fixture(self, parser):
        """Test parsing object-with-trials fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "hyperopt" / "object_with_trials.json"
        raw_result = parser.load_hyperopt_result(str(fixture_path))

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].loss_score == 0.5
        assert trials[1].loss_score == 0.3

    def test_parse_failed_trial_fixture(self, parser):
        """Test parsing failed-trial fixture."""
        fixture_path = Path(__file__).parent / "fixtures" / "hyperopt" / "failed_trial.json"
        raw_result = parser.load_hyperopt_result(str(fixture_path))

        trials = parser.parse_trials(raw_result)

        assert len(trials) == 2
        assert trials[0].status == OptimizationTrialStatus.COMPLETED
        assert trials[1].status == OptimizationTrialStatus.FAILED

    def test_full_params_json_round_trip(self, parser):
        """Test that full params JSON round-trips correctly."""
        raw_trial = {
            "loss": 0.5,
            "params": {
                "buy_rsi": 30,
                "sell_rsi": 70,
                "roi_t1": 0.02,
                "roi_t2": 0.04,
                "roi_t3": 0.06,
                "stoploss_value": -0.05,
                "trailing_stop": -0.02,
            },
            "metrics": {"profit_total": 100.0},
        }

        trial = parser.normalize_trial(raw_trial, 1)

        assert trial.params is not None
        # Params are separated by space
        assert "buy" in trial.params
        assert "sell" in trial.params
        assert "roi" in trial.params
        assert "stoploss" in trial.params
        assert "trailing" in trial.params

    def test_buy_sell_params_extraction(self, parser):
        """Test buy/sell params extraction."""
        raw_trial = {
            "buy_rsi": 30,
            "buy_ema": 20,
            "sell_rsi": 70,
            "sell_ema": 80,
        }

        params = parser.extract_params(raw_trial)

        assert params["buy"]["rsi"] == 30
        assert params["buy"]["ema"] == 20
        assert params["sell"]["rsi"] == 70
        assert params["sell"]["ema"] == 80

    def test_roi_stoploss_trailing_extraction(self, parser):
        """Test ROI/stoploss/trailing params extraction."""
        raw_trial = {
            "roi_t1": 0.02,
            "roi_t2": 0.04,
            "stoploss_value": -0.05,
            "trailing_stop": -0.02,
        }

        params = parser.extract_params(raw_trial)

        assert params["roi"]["t1"] == 0.02
        assert params["roi"]["t2"] == 0.04
        assert params["stoploss"]["value"] == -0.05
        assert params["trailing"]["stop"] == -0.02

    def test_no_trial_discarded_silently(self, parser, mock_repository, tmp_path):
        """Test that no trial is discarded silently."""
        result_file = tmp_path / "result.json"
        result_file.write_text(
            json.dumps([
                {"loss": 0.5, "params": {"buy_rsi": 30}, "metrics": {"trade_count": 50}},
                {"error": "Failed", "params": {"buy_rsi": 35}, "metrics": {"trade_count": 0}},
                {"loss": 0.7, "params": {"buy_rsi": 25}, "metrics": {"trade_count": 45}},
            ])
        )

        results = parser.parse_and_persist_trials("opt-run-123", [str(result_file)])

        # All trials should be counted
        assert results["trials_count"] == 3
        # All trials should be persisted (or have errors logged)
        assert results["persisted_trials_count"] + len(results["errors"]) == 3

    def test_frontend_ready_trial_output(self, parser):
        """Test that trial output is frontend-ready."""
        raw_trial = {
            "loss": 0.5,
            "params": {"buy_rsi": 30, "sell_rsi": 70},
            "metrics": {"profit_total": 100.0, "trade_count": 50, "win_rate": 0.6},
        }

        trial = parser.normalize_trial(raw_trial, 1)

        # Trial should be serializable
        trial_dict = trial.model_dump()

        assert trial_dict["trial_number"] == 1
        assert trial_dict["loss_score"] == 0.5
        assert trial_dict["profit_total"] == 100.0
        assert trial_dict["trade_count"] == 50
        assert trial_dict["win_rate"] == 0.6
        assert trial_dict["is_best"] is False
