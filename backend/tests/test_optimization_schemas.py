"""
Tests for Part 08 optimization schemas.
"""
import pytest
from datetime import datetime
from pydantic import ValidationError

from app.schemas.optimization import (
    OptimizationStage,
    OptimizationStatus,
    OptimizationResultStatus,
    OptimizationTrialStatus,
    HyperoptPolicy,
    OptimizationRequest,
    OptimizationStageResult,
    OptimizationTrial,
    OptimizationRun,
    OptimizationComparison,
    OptimizationResult,
    OptimizationStatusResponse,
    OptimizationRunListItem,
    OptimizationRunDetail,
    OptimizationTrialDetail,
)


class TestOptimizationEnums:
    """Test optimization enum values."""

    def test_optimization_stage_values(self):
        """Test OptimizationStage enum values."""
        assert OptimizationStage.OPTIMIZATION_SETUP == "optimization_setup"
        assert OptimizationStage.BASELINE_REFERENCE == "baseline_reference"
        assert OptimizationStage.HYPEROPT_EXECUTION == "hyperopt_execution"
        assert OptimizationStage.COMPLETION == "completion"

    def test_optimization_status_values(self):
        """Test OptimizationStatus enum values."""
        assert OptimizationStatus.PENDING == "pending"
        assert OptimizationStatus.RUNNING == "running"
        assert OptimizationStatus.COMPLETED == "completed"
        assert OptimizationStatus.FAILED_CONTROLLED == "failed_controlled"
        assert OptimizationStatus.CONFIRMATION_REQUIRED == "confirmation_required"

    def test_optimization_result_status_values(self):
        """Test OptimizationResultStatus enum values."""
        assert OptimizationResultStatus.NOT_IMPROVED == "not_improved"
        assert OptimizationResultStatus.IMPROVED == "improved"
        assert OptimizationResultStatus.OPTIMIZATION_CANDIDATE == "optimization_candidate"
        assert OptimizationResultStatus.OPTIMIZATION_PROMISING == "optimization_promising"
        assert OptimizationResultStatus.OPTIMIZATION_REJECTED == "optimization_rejected"
        assert OptimizationResultStatus.OVERFIT_SUSPECTED == "overfit_suspected"
        assert OptimizationResultStatus.INVALID_OPTIMIZATION == "invalid_optimization"

    def test_optimization_trial_status_values(self):
        """Test OptimizationTrialStatus enum values."""
        assert OptimizationTrialStatus.COMPLETED == "completed"
        assert OptimizationTrialStatus.FAILED == "failed"
        assert OptimizationTrialStatus.IGNORED == "ignored"
        assert OptimizationTrialStatus.BEST == "best"
        assert OptimizationTrialStatus.SELECTED_FOR_VALIDATION == "selected_for_validation"
        assert OptimizationTrialStatus.REJECTED == "rejected"


class TestHyperoptPolicy:
    """Test HyperoptPolicy schema."""

    def test_default_policy(self):
        """Test default hyperopt policy values."""
        policy = HyperoptPolicy()

        assert policy.max_epochs == 200
        assert policy.default_epochs == 50
        assert policy.allowed_spaces == ["buy", "sell"]
        assert policy.locked_spaces == ["roi", "stoploss", "trailing", "protection"]
        assert policy.max_optimized_parameters == 6
        assert policy.allow_roi_optimization is False
        assert policy.allow_stoploss_optimization is False
        assert policy.allow_trailing_optimization is False
        assert policy.timeout_seconds == 3600
        assert policy.min_trades == 10
        assert policy.stop_on_zero_trades is True

    def test_custom_policy(self):
        """Test custom hyperopt policy."""
        policy = HyperoptPolicy(
            max_epochs=100,
            default_epochs=25,
            allowed_spaces=["buy", "sell", "roi"],
            allow_roi_optimization=True,
        )

        assert policy.max_epochs == 100
        assert policy.default_epochs == 25
        assert "roi" in policy.allowed_spaces
        assert policy.allow_roi_optimization is True


class TestOptimizationRequest:
    """Test OptimizationRequest schema."""

    def test_valid_request(self):
        """Test valid optimization request."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT", "ETH/USDT"],
            timeframe="5m",
            exchange="binance",
            epochs=50,
            spaces=["buy", "sell"],
            risk_profile="balanced",
        )

        assert request.strategy_name == "TestStrategy"
        assert request.pairs == ["BTC/USDT", "ETH/USDT"]
        assert request.timeframe == "5m"
        assert request.epochs == 50
        assert request.spaces == ["buy", "sell"]
        assert request.risk_profile == "balanced"

    def test_request_with_defaults(self):
        """Test request with default values."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="1h",
        )

        assert request.exchange == "binance"
        assert request.days == 30
        assert request.risk_profile == "balanced"
        assert request.run_baseline_first is True
        assert request.download_missing_data is False
        assert request.user_confirmed is False
        assert request.epochs == 50
        assert request.spaces == ["buy", "sell"]
        assert request.max_open_trades == 3
        assert request.stake_currency == "USDT"
        assert request.apply_decision_to_run is True

    def test_empty_strategy_name_raises_error(self):
        """Test that empty strategy name raises ValidationError."""
        with pytest.raises(ValidationError, match="strategy_name"):
            OptimizationRequest(
                strategy_name="",
                pairs=["BTC/USDT"],
                timeframe="5m",
            )

    def test_whitespace_strategy_name_raises_error(self):
        """Test that whitespace-only strategy name raises ValidationError."""
        with pytest.raises(ValidationError, match="strategy_name"):
            OptimizationRequest(
                strategy_name="   ",
                pairs=["BTC/USDT"],
                timeframe="5m",
            )

    def test_empty_pairs_raises_error(self):
        """Test that empty pairs list raises ValidationError."""
        with pytest.raises(ValidationError, match="pairs"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=[],
                timeframe="5m",
            )

    def test_empty_timeframe_raises_error(self):
        """Test that empty timeframe raises ValidationError."""
        with pytest.raises(ValidationError, match="timeframe"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="",
            )

    def test_epochs_zero_raises_error(self):
        """Test that epochs <= 0 raises ValidationError."""
        with pytest.raises(ValidationError, match="epochs"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                epochs=0,
            )

    def test_epochs_negative_raises_error(self):
        """Test that negative epochs raises ValidationError."""
        with pytest.raises(ValidationError, match="epochs"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                epochs=-10,
            )

    def test_epochs_exceeds_max_raises_error(self):
        """Test that epochs > 200 raises ValidationError."""
        with pytest.raises(ValidationError, match="epochs"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                epochs=250,
            )

    def test_invalid_space_raises_error(self):
        """Test that invalid space raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid space"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                spaces=["invalid_space"],
            )

    def test_invalid_risk_profile_raises_error(self):
        """Test that invalid risk profile raises ValidationError."""
        with pytest.raises(ValidationError, match="Invalid risk_profile"):
            OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                risk_profile="invalid",
            )

    def test_pairs_whitespace_stripped(self):
        """Test that whitespace is stripped from pairs."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["  BTC/USDT  ", "  ETH/USDT  "],
            timeframe="5m",
        )

        assert request.pairs == ["BTC/USDT", "ETH/USDT"]

    def test_strategy_name_whitespace_stripped(self):
        """Test that whitespace is stripped from strategy name."""
        request = OptimizationRequest(
            strategy_name="  TestStrategy  ",
            pairs=["BTC/USDT"],
            timeframe="5m",
        )

        assert request.strategy_name == "TestStrategy"

    def test_valid_spaces(self):
        """Test all valid spaces are accepted."""
        valid_spaces = ["buy", "sell", "roi", "stoploss", "trailing", "protection"]
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
            spaces=valid_spaces,
        )

        assert request.spaces == valid_spaces

    def test_valid_risk_profiles(self):
        """Test all valid risk profiles are accepted."""
        for profile in ["conservative", "balanced", "aggressive"]:
            request = OptimizationRequest(
                strategy_name="TestStrategy",
                pairs=["BTC/USDT"],
                timeframe="5m",
                risk_profile=profile,
            )
            assert request.risk_profile == profile


class TestOptimizationStageResult:
    """Test OptimizationStageResult schema."""

    def test_stage_result(self):
        """Test optimization stage result."""
        result = OptimizationStageResult(
            stage_name=OptimizationStage.HYPEROPT_EXECUTION,
            status=OptimizationStatus.COMPLETED,
            message="Hyperopt completed successfully",
        )

        assert result.stage_name == OptimizationStage.HYPEROPT_EXECUTION
        assert result.status == OptimizationStatus.COMPLETED
        assert result.message == "Hyperopt completed successfully"
        assert result.warnings == []
        assert result.errors == []

    def test_stage_result_with_error(self):
        """Test stage result with error."""
        result = OptimizationStageResult(
            stage_name=OptimizationStage.HYPEROPT_EXECUTION,
            status=OptimizationStatus.FAILED_CONTROLLED,
            error_code="hyperopt_execution_failed",
            message="Hyperopt failed",
            errors=["Strategy error"],
        )

        assert result.status == OptimizationStatus.FAILED_CONTROLLED
        assert result.error_code == "hyperopt_execution_failed"
        assert result.errors == ["Strategy error"]


class TestOptimizationTrial:
    """Test OptimizationTrial schema."""

    def test_trial(self):
        """Test optimization trial."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.COMPLETED,
            params={"buy": {"rsi": 30}},
            profit_total=100.0,
            trade_count=50,
            created_at=datetime.now(),
        )

        assert trial.id == "trial-1"
        assert trial.optimization_run_id == "run-1"
        assert trial.trial_number == 1
        assert trial.status == OptimizationTrialStatus.COMPLETED
        assert trial.is_best is False
        assert trial.profit_total == 100.0

    def test_trial_with_all_params(self):
        """Test trial with all parameter types."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.BEST,
            is_best=True,
            params={"buy": {"rsi": 30}, "sell": {"rsi": 70}},
            buy_params={"rsi": 30},
            sell_params={"rsi": 70},
            roi_params={"0": 0.05, "1": 0.10},
            stoploss_params={"value": -0.10},
            trailing_params={"value": 0.02},
            metrics={"profit_factor": 1.5, "sharpe": 2.0},
            loss_score=0.5,
            profit_total=150.0,
            profit_factor=1.5,
            expectancy=0.02,
            max_drawdown=-0.15,
            trade_count=100,
            win_rate=0.65,
            created_at=datetime.now(),
        )

        assert trial.is_best is True
        assert trial.buy_params["rsi"] == 30
        assert trial.roi_params["1"] == 0.10
        assert trial.stoploss_params["value"] == -0.10
        assert trial.metrics["sharpe"] == 2.0
        assert trial.expectancy == 0.02

    def test_trial_with_rejection(self):
        """Test trial with rejection reason."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.REJECTED,
            rejection_reason="Insufficient trades",
            trade_count=5,
            created_at=datetime.now(),
        )

        assert trial.status == OptimizationTrialStatus.REJECTED
        assert trial.rejection_reason == "Insufficient trades"

    def test_trial_with_failure(self):
        """Test trial with failure reason."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.FAILED,
            failure_reason="Strategy error",
            trade_count=0,
            created_at=datetime.now(),
        )

        assert trial.status == OptimizationTrialStatus.FAILED
        assert trial.failure_reason == "Strategy error"


class TestOptimizationRun:
    """Test OptimizationRun schema."""

    def test_run(self):
        """Test optimization run."""
        run = OptimizationRun(
            id="run-1",
            strategy_name="TestStrategy",
            timeframe="5m",
            pairs=["BTC/USDT"],
            exchange="binance",
            status=OptimizationStatus.RUNNING,
            epochs_requested=50,
            epochs_completed=25,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert run.id == "run-1"
        assert run.strategy_name == "TestStrategy"
        assert run.status == OptimizationStatus.RUNNING
        assert run.epochs_requested == 50
        assert run.epochs_completed == 25

    def test_run_with_result_status(self):
        """Test run with result status."""
        run = OptimizationRun(
            id="run-1",
            strategy_name="TestStrategy",
            timeframe="5m",
            pairs=["BTC/USDT"],
            exchange="binance",
            status=OptimizationStatus.COMPLETED,
            result_status=OptimizationResultStatus.IMPROVED,
            best_trial_id="trial-1",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert run.result_status == OptimizationResultStatus.IMPROVED
        assert run.best_trial_id == "trial-1"


class TestOptimizationComparison:
    """Test OptimizationComparison schema."""

    def test_comparison(self):
        """Test baseline vs optimized comparison."""
        comparison = OptimizationComparison(
            optimization_run_id="run-1",
            baseline_run_id="baseline-1",
            optimized_run_id="optimized-1",
            best_trial_id="trial-1",
            baseline_metrics={"profit_total": 100.0, "profit_factor": 1.5},
            optimized_metrics={"profit_total": 150.0, "profit_factor": 1.8},
            delta_profit_factor=0.3,
            delta_expectancy=0.05,
            delta_drawdown=-2.0,
            delta_trade_count=10,
            baseline_classification="rejected",
            optimized_classification="candidate",
            result_status="improved",
            improvement_summary="Optimized strategy shows improvement",
        )

        assert comparison.optimization_run_id == "run-1"
        assert comparison.delta_profit_factor == 0.3
        assert comparison.delta_expectancy == 0.05
        assert comparison.result_status == "improved"


class TestOptimizationResult:
    """Test OptimizationResult schema."""

    def test_result(self):
        """Test optimization pipeline result."""
        result = OptimizationResult(
            run_id="run-1",
            status=OptimizationStatus.COMPLETED,
            result_status=OptimizationResultStatus.IMPROVED,
            message="Optimization completed successfully",
            created_at=datetime.now(),
        )

        assert result.run_id == "run-1"
        assert result.status == OptimizationStatus.COMPLETED
        assert result.result_status == OptimizationResultStatus.IMPROVED
        assert result.stages == []
        assert result.best_trial is None


class TestOptimizationStatusResponse:
    """Test OptimizationStatusResponse schema."""

    def test_status_response(self):
        """Test optimization status response."""
        response = OptimizationStatusResponse(
            run_id="run-1",
            status=OptimizationStatus.RUNNING,
            current_stage=OptimizationStage.HYPEROPT_EXECUTION,
            epochs_completed=25,
            epochs_total=50,
            trials_completed=25,
            trials_total=50,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert response.run_id == "run-1"
        assert response.current_stage == OptimizationStage.HYPEROPT_EXECUTION
        assert response.epochs_completed == 25
        assert response.epochs_total == 50


class TestOptimizationRunListItem:
    """Test OptimizationRunListItem schema."""

    def test_list_item(self):
        """Test optimization run list item."""
        item = OptimizationRunListItem(
            id="run-1",
            strategy_name="TestStrategy",
            timeframe="5m",
            pairs=["BTC/USDT"],
            exchange="binance",
            status=OptimizationStatus.COMPLETED,
            result_status=OptimizationResultStatus.IMPROVED,
            epochs_requested=50,
            epochs_completed=50,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        assert item.id == "run-1"
        assert item.strategy_name == "TestStrategy"
        assert item.result_status == OptimizationResultStatus.IMPROVED


class TestOptimizationRunDetail:
    """Test OptimizationRunDetail schema."""

    def test_run_detail(self):
        """Test optimization run detail."""
        run = OptimizationRun(
            id="run-1",
            strategy_name="TestStrategy",
            timeframe="5m",
            pairs=["BTC/USDT"],
            exchange="binance",
            status=OptimizationStatus.COMPLETED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        detail = OptimizationRunDetail(
            run=run,
            stages=[],
            best_trial=None,
            comparison=None,
            artifact_paths=[],
        )

        assert detail.run.id == "run-1"
        assert detail.stages == []
        assert detail.best_trial is None


class TestOptimizationTrialDetail:
    """Test OptimizationTrialDetail schema."""

    def test_trial_detail(self):
        """Test optimization trial detail."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.COMPLETED,
            params={},
            trade_count=50,
            created_at=datetime.now(),
        )

        detail = OptimizationTrialDetail(
            trial=trial,
            artifact_paths=[],
        )

        assert detail.trial.id == "trial-1"
        assert detail.artifact_paths == []


class TestSchemasFrontendReady:
    """Test that schemas are frontend-ready."""

    def test_request_serializable(self):
        """Test that OptimizationRequest is serializable."""
        request = OptimizationRequest(
            strategy_name="TestStrategy",
            pairs=["BTC/USDT"],
            timeframe="5m",
        )

        # Should be able to convert to dict
        data = request.model_dump()
        assert isinstance(data, dict)
        assert data["strategy_name"] == "TestStrategy"

    def test_trial_serializable(self):
        """Test that OptimizationTrial is serializable."""
        trial = OptimizationTrial(
            id="trial-1",
            optimization_run_id="run-1",
            trial_number=1,
            status=OptimizationTrialStatus.COMPLETED,
            params={"buy": {"rsi": 30}},
            trade_count=50,
            created_at=datetime.now(),
        )

        data = trial.model_dump()
        assert isinstance(data, dict)
        assert data["params"]["buy"]["rsi"] == 30

    def test_run_serializable(self):
        """Test that OptimizationRun is serializable."""
        run = OptimizationRun(
            id="run-1",
            strategy_name="TestStrategy",
            timeframe="5m",
            pairs=["BTC/USDT"],
            exchange="binance",
            status=OptimizationStatus.COMPLETED,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        data = run.model_dump()
        assert isinstance(data, dict)
        assert data["pairs"] == ["BTC/USDT"]

    def test_comparison_serializable(self):
        """Test that OptimizationComparison is serializable."""
        comparison = OptimizationComparison(
            optimization_run_id="run-1",
            baseline_run_id="baseline-1",
            optimized_run_id="optimized-1",
            best_trial_id="trial-1",
            baseline_metrics={"profit_total": 100.0, "profit_factor": 1.5},
            optimized_metrics={"profit_total": 150.0, "profit_factor": 1.8},
            delta_profit_factor=0.3,
            delta_expectancy=0.05,
            delta_drawdown=-2.0,
            delta_trade_count=10,
        )

        data = comparison.model_dump()
        assert isinstance(data, dict)
        assert data["delta_profit_factor"] == 0.3
        assert data["delta_expectancy"] == 0.05
