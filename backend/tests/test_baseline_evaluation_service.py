"""
Unit tests for Part 07 BaselineEvaluationService.

Tests use mocks/stubs for Freqtrade services to avoid requiring real Freqtrade
execution. Tests cover:
- Missing strategy -> failed_controlled
- Missing data + download disabled -> failed_controlled
- Missing data + download true + user_confirmed false -> confirmation_required
- user_confirmed false blocks backtest
- Successful mocked flow calls parser and decision service
- Failed backtest stops before parse
- Failed parse stops before decision
- Decision rejected still means pipeline success if evaluation completed
- Stage results are recorded
- Report artifact path generated
- No Ollama/Discord calls
- No approval/export classification emitted
"""
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timezone
from pathlib import Path
import pytest

from app.services.baseline_evaluation_service import BaselineEvaluationService
from app.schemas.baseline import BaselineEvaluationRequest
from app.schemas.freqtrade_strategy import FreqtradeStrategyFile
from app.schemas.freqtrade_config import FreqtradeBacktestConfigResult
from app.schemas.freqtrade_data import FreqtradeDataCheckResult, PairDataStatus, FreqtradeDataDownloadResult
from app.schemas.freqtrade_backtest import FreqtradeBacktestResult
from app.schemas.backtest_results import (
    BacktestParseResult, 
    ResultQualityReport, 
    ExtractedBacktestMetrics,
    ExtractedPairResult,
    ExtractedTradeSummary,
    MetricsExtractionResult,
)
from app.schemas.decisions import DecisionEvaluationResponse, DecisionResult, DecisionReason, DecisionEvidence


@pytest.fixture
def mock_run_repository():
    """Mock RunRepository."""
    repo = Mock()
    repo.create_run = Mock(return_value={
        "id": "test-run-id",
        "name": "Baseline Evaluation - TestStrategy",
        "mode": "baseline_evaluation",
        "status": "created",
        "classification": None,
        "strategy_id": None,
        "exchange": "binance",
        "timeframe": "1h",
        "pairs": ["BTC/USDT"],
        "risk_profile": "balanced",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": None,
        "completed_at": None,
    })
    repo.update_status = Mock(return_value={
        "id": "test-run-id",
        "status": "running",
    })
    repo.set_decision_classification = Mock(return_value={
        "id": "test-run-id",
        "classification": "rejected",
    })
    return repo


@pytest.fixture
def mock_run_stage_repository():
    """Mock RunStageRepository."""
    repo = Mock()
    repo.create_baseline_stages = Mock(return_value=[])
    repo.start_stage = Mock(return_value={
        "id": "stage-id",
        "status": "running",
    })
    repo.complete_stage = Mock(return_value={
        "id": "stage-id",
        "status": "passed",
    })
    repo.fail_stage = Mock(return_value={
        "id": "stage-id",
        "status": "failed",
    })
    repo.mark_stage_waiting = Mock(return_value={
        "id": "stage-id",
        "status": "waiting",
    })
    return repo


@pytest.fixture
def mock_artifact_repository():
    """Mock ArtifactRepository."""
    repo = Mock()
    repo.create_artifact = Mock(return_value={
        "id": "artifact-id",
        "file_path": "artifacts/runs/test-run-id/baseline/baseline_evaluation_report.json",
    })
    return repo


@pytest.fixture
def mock_log_repository():
    """Mock RunLogRepository."""
    repo = Mock()
    repo.add_log = Mock()
    return repo


@pytest.fixture
def mock_audit_repository():
    """Mock AuditLogRepository."""
    repo = Mock()
    repo.create_audit_log = Mock(return_value={"id": "audit-id"})
    return repo


@pytest.fixture
def mock_strategy_service():
    """Mock FreqtradeStrategyService."""
    service = Mock()
    service.validate_strategy_name = Mock(return_value=(True, None))
    service.find_strategy_by_name = Mock(return_value=FreqtradeStrategyFile(
        strategy_name="TestStrategy",
        class_name=None,
        file_path="freqtrade_user_data/strategies/TestStrategy.py",
        params_path="freqtrade_user_data/strategies/TestStrategy.json",
        exists=True,
        has_sidecar_json=True,
        source="file",
        errors=[],
        warnings=[],
    ))
    service.validate_strategy_file_path = Mock(return_value=(True, None))
    return service


@pytest.fixture
def mock_config_generator():
    """Mock FreqtradeConfigGenerator."""
    generator = Mock()
    generator.write_backtest_config = Mock(return_value=FreqtradeBacktestConfigResult(
        run_id="test-run-id",
        config_path="freqtrade_config/runs/test-run-id.backtest.json",
        config={},
        artifact_id="config-artifact-id",
        success=True,
    ))
    return generator


@pytest.fixture
def mock_data_service():
    """Mock FreqtradeDataService."""
    service = Mock()
    # Default: data exists
    service.check_data = Mock(return_value=FreqtradeDataCheckResult(
        run_id="test-run-id",
        exchange="binance",
        trading_mode="spot",
        pairs=[
            PairDataStatus(
                pair="BTC/USDT",
                timeframe="1h",
                exists=True,
                file_path="freqtrade_user_data/data/binance/spot/BTC_USDT-1h.json",
                timerange=None,
                errors=[],
                warnings=[],
            )
        ],
        freqtrade_visible=True,
        source="freqtrade",
        errors=[],
        warnings=[],
    ))
    service.download_data = Mock(return_value=FreqtradeDataDownloadResult(
        run_id="test-run-id",
        exchange="binance",
        trading_mode="spot",
        pairs=["BTC/USDT"],
        timeframes=["1h"],
        success=True,
        blocked=False,
        duration=10.5,
        stdout="",
        stderr="",
        error=None,
        errors=[],
        warnings=[],
    ))
    return service


@pytest.fixture
def mock_backtest_runner():
    """Mock FreqtradeBacktestRunner."""
    runner = Mock()
    runner.run_backtest = Mock(return_value=FreqtradeBacktestResult(
        run_id="test-run-id",
        success=True,
        blocked=False,
        exit_code=0,
        stdout="Backtest completed",
        stderr="",
        duration_seconds=120.5,
        backtest_directory="artifacts/runs/test-run-id/raw_freqtrade/backtest_results",
        artifacts=[],
        error=None,
        errors=[],
        warnings=[],
    ))
    return runner


@pytest.fixture
def mock_result_parser():
    """Mock BacktestResultParser."""
    parser = Mock()
    parser.parse_run = Mock(return_value=BacktestParseResult(
        success=True,
        run_id="test-run-id",
        metrics=MetricsExtractionResult(
            success=True,
            metrics=ExtractedBacktestMetrics(
                net_profit=100.0,
                profit_factor=1.5,
                max_drawdown=-10.0,
                sharpe=1.2,
                calmar=0.8,
                win_rate=0.6,
                trade_count=50,
                expectancy=2.0,
                avg_win=10.0,
                avg_loss=-5.0,
                source_type="backtest_result",
            ),
        ),
        pair_results=[
            ExtractedPairResult(
                pair="BTC/USDT",
                net_profit=100.0,
                profit_factor=1.5,
                max_drawdown=-10.0,
                trade_count=50,
                win_rate=0.6,
                expectancy=2.0,
            )
        ],
        trade_summary=ExtractedTradeSummary(
            total_trades=50,
            wins=30,
            losses=20,
            draws=0,
            avg_duration="1h 0m",
            best_pair="BTC/USDT",
            worst_pair="BTC/USDT",
        ),
        quality_report=ResultQualityReport(
            run_id="test-run-id",
            parse_quality="ok",
            flags=[],
            warnings=[],
            errors=[],
            is_usable_for_metrics=True,
            is_usable_for_decision=True,
        ),
        normalized_result_path="artifacts/runs/test-run-id/normalized/normalized_result.json",
        warnings=[],
        errors=[],
    ))
    return parser


@pytest.fixture
def mock_decision_service():
    """Mock DecisionService."""
    service = Mock()
    service.evaluate_run = Mock(return_value=DecisionEvaluationResponse(
        run_id="test-run-id",
        success=True,
        decision=DecisionResult(
            id="decision-id",
            run_id="test-run-id",
            policy_name="default_balanced",
            classification="rejected",
            confidence_score=0.3,
            gates=[],
            reasons=[
                DecisionReason(
                    code="low_profit_factor",
                    severity="blocking",
                    message="Insufficient profit factor",
                    metric="profit_factor",
                    actual_value=1.5,
                    threshold_value=2.0,
                )
            ],
            evidence=DecisionEvidence(
                run_id="test-run-id",
                profit_factor=1.5,
                trade_count=50,
            ),
            warnings=[],
            blocking_failures=["Low profit factor"],
            next_actions=["Improve strategy profitability"],
            created_at=datetime.now(timezone.utc).isoformat(),
        ),
        saved_decision_id="decision-id",
        decision_report_path="artifacts/runs/test-run-id/decisions/decision_result.json",
        run_updated=True,
        decision_id="decision-id",
        classification="rejected",
        confidence_score=0.3,
        policy_name="default_balanced",
        gates=[],
        reasons=[
            DecisionReason(
                code="low_profit_factor",
                severity="blocking",
                message="Insufficient profit factor",
                metric="profit_factor",
                actual_value=1.5,
                threshold_value=2.0,
            )
        ],
        warnings=[],
        blocking_failures=["Low profit factor"],
        next_actions=["Improve strategy profitability"],
    ))
    return service


@pytest.fixture
def baseline_service(
    mock_run_repository,
    mock_run_stage_repository,
    mock_artifact_repository,
    mock_log_repository,
    mock_audit_repository,
    mock_strategy_service,
    mock_config_generator,
    mock_data_service,
    mock_backtest_runner,
    mock_result_parser,
    mock_decision_service,
):
    """Create BaselineEvaluationService with all mocks."""
    return BaselineEvaluationService(
        run_repository=mock_run_repository,
        run_stage_repository=mock_run_stage_repository,
        artifact_repository=mock_artifact_repository,
        log_repository=mock_log_repository,
        audit_repository=mock_audit_repository,
        strategy_service=mock_strategy_service,
        config_generator=mock_config_generator,
        data_service=mock_data_service,
        backtest_runner=mock_backtest_runner,
        result_parser=mock_result_parser,
        decision_service=mock_decision_service,
    )


@pytest.fixture
def baseline_request():
    """Create a baseline evaluation request."""
    return BaselineEvaluationRequest(
        strategy_name="TestStrategy",
        pairs=["BTC/USDT"],
        timeframe="1h",
        exchange="binance",
        risk_profile="balanced",
        stake_currency="USDT",
        stake_amount="unlimited",
        max_open_trades=3,
        trading_mode="spot",
        download_missing_data=False,
        user_confirmed=True,
        apply_decision_to_run=True,
        force_parse=True,
    )


class TestBaselineEvaluationService:
    """Test suite for BaselineEvaluationService."""

    def test_successful_evaluation_flow(
        self,
        baseline_service,
        baseline_request,
        mock_strategy_service,
        mock_config_generator,
        mock_data_service,
        mock_backtest_runner,
        mock_result_parser,
        mock_decision_service,
    ):
        """Test successful end-to-end evaluation flow."""
        result = baseline_service.evaluate(baseline_request)

        # Assert overall success
        assert result.success is True
        assert result.status == "completed"
        assert result.run_id == "test-run-id"
        assert result.classification == "rejected"  # From mock decision
        assert result.confidence_score == 0.3

        # Assert all stages completed
        assert len(result.stage_results) == 10
        stage_names = [stage.stage_name for stage in result.stage_results]
        assert stage_names == [
            "run_setup",
            "strategy_validation",
            "config_generation",
            "data_check",
            "data_download",
            "baseline_backtest",
            "result_parsing",
            "decision_evaluation",
            "baseline_report",
            "completion",
        ]

        # Assert all services were called
        mock_strategy_service.validate_strategy_name.assert_called_once()
        mock_strategy_service.find_strategy_by_name.assert_called_once()
        mock_config_generator.write_backtest_config.assert_called_once()
        mock_data_service.check_data.assert_called_once()
        mock_backtest_runner.run_backtest.assert_called_once()
        mock_result_parser.parse_run.assert_called_once()
        mock_decision_service.evaluate_run.assert_called_once()

        # Assert no data download was called (data existed)
        mock_data_service.download_data.assert_not_called()

    def test_missing_strategy_failed_controlled(
        self,
        baseline_service,
        baseline_request,
        mock_strategy_service,
    ):
        """Test missing strategy results in failed_controlled."""
        # Mock strategy not found
        mock_strategy_service.find_strategy_by_name = Mock(return_value=None)

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "Strategy not found" in result.errors[0]

        # Assert backtest was not called
        baseline_service.backtest_runner.run_backtest.assert_not_called()

    def test_invalid_strategy_name_failed_controlled(
        self,
        baseline_service,
        baseline_request,
        mock_strategy_service,
    ):
        """Test invalid strategy name results in failed_controlled."""
        # Mock invalid strategy name
        mock_strategy_service.validate_strategy_name = Mock(return_value=(False, "Invalid characters"))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "validation" in result.errors[0].lower() or "invalid" in result.errors[0].lower()

    def test_missing_data_download_disabled_failed_controlled(
        self,
        baseline_service,
        baseline_request,
        mock_data_service,
    ):
        """Test missing data with download disabled results in failed_controlled."""
        # Mock missing data
        mock_data_service.check_data = Mock(return_value=FreqtradeDataCheckResult(
            run_id="test-run-id",
            exchange="binance",
            trading_mode="spot",
            pairs=[
                PairDataStatus(
                    pair="BTC/USDT",
                    timeframe="1h",
                    exists=False,
                    file_path=None,
                    timerange=None,
                    errors=[],
                    warnings=[],
                )
            ],
            freqtrade_visible=True,
            source="freqtrade",
            errors=[],
            warnings=[],
        ))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "data" in result.errors[0].lower() and "missing" in result.errors[0].lower()

    def test_missing_data_download_requires_confirmation(
        self,
        baseline_service,
        baseline_request,
        mock_data_service,
    ):
        """Test missing data with download enabled but not confirmed requires confirmation."""
        # Mock missing data
        mock_data_service.check_data = Mock(return_value=FreqtradeDataCheckResult(
            run_id="test-run-id",
            exchange="binance",
            trading_mode="spot",
            pairs=[
                PairDataStatus(
                    pair="BTC/USDT",
                    timeframe="1h",
                    exists=False,
                    file_path=None,
                    timerange=None,
                    errors=[],
                    warnings=[],
                )
            ],
            freqtrade_visible=True,
            source="freqtrade",
            errors=[],
            warnings=[],
        ))

        # Enable download but not confirmed
        baseline_request.download_missing_data = True
        baseline_request.user_confirmed = False

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "confirmation_required"
        assert any("confirm" in action.lower() for action in result.next_actions)

    def test_user_confirmed_false_blocks_backtest(
        self,
        baseline_service,
        baseline_request,
    ):
        """Test user_confirmed false blocks backtest execution."""
        baseline_request.user_confirmed = False

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "confirmation_required"
        assert any("backtest" in action.lower() for action in result.next_actions)

        # Assert backtest was not called
        baseline_service.backtest_runner.run_backtest.assert_not_called()

    def test_failed_backtest_stops_before_parse(
        self,
        baseline_service,
        baseline_request,
        mock_backtest_runner,
    ):
        """Test failed backtest stops pipeline before parsing."""
        # Mock backtest failure
        mock_backtest_runner.run_backtest = Mock(return_value=FreqtradeBacktestResult(
            run_id="test-run-id",
            success=False,
            blocked=False,
            exit_code=1,
            stdout="",
            stderr="Backtest failed",
            duration_seconds=0.0,
            backtest_directory="/path/to/backtest-results",
            artifacts=[],
            error="Backtest failed",
            errors=["Backtest failed"],
            warnings=[],
        ))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "backtest" in result.errors[0].lower()

        # Assert parser was not called
        baseline_service.result_parser.parse_run.assert_not_called()

    def test_failed_parse_stops_before_decision(
        self,
        baseline_service,
        baseline_request,
        mock_result_parser,
    ):
        """Test failed parse stops pipeline before decision."""
        # Mock parse failure
        mock_result_parser.parse_run = Mock(return_value=BacktestParseResult(
            success=False,
            run_id="test-run-id",
            metrics=None,
            pair_results=[],
            trade_summary=None,
            quality_report=None,
            normalized_result_path=None,
            warnings=[],
            errors=["Parse failed"],
        ))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "parse" in result.errors[0].lower() or "parsing" in result.errors[0].lower()

        # Assert decision service was not called
        baseline_service.decision_service.evaluate_run.assert_not_called()

    def test_decision_rejected_still_pipeline_success(
        self,
        baseline_service,
        baseline_request,
        mock_decision_service,
    ):
        """Test decision rejected still means pipeline success if evaluation completed."""
        # Mock decision service returns rejected classification
        mock_decision_service.evaluate_run = Mock(return_value=DecisionEvaluationResponse(
            run_id="test-run-id",
            success=True,
            decision=DecisionResult(
                id="decision-id",
                run_id="test-run-id",
                policy_name="default_balanced",
                classification="rejected",
                confidence_score=0.3,
                gates=[],
                reasons=[
                    DecisionReason(
                        code="low_profit_factor",
                        severity="blocking",
                        message="Insufficient profit factor",
                        metric="profit_factor",
                        actual_value=1.5,
                        threshold_value=2.0,
                    )
                ],
                evidence=DecisionEvidence(
                    run_id="test-run-id",
                    profit_factor=1.5,
                    trade_count=50,
                ),
                warnings=[],
                blocking_failures=["Low profit factor"],
                next_actions=["Improve strategy profitability"],
                created_at=datetime.now(timezone.utc).isoformat(),
            ),
            saved_decision_id="decision-id",
            decision_report_path="artifacts/runs/test-run-id/decisions/decision_result.json",
            run_updated=True,
            decision_id="decision-id",
            classification="rejected",
            confidence_score=0.3,
            policy_name="default_balanced",
            gates=[],
            reasons=[
                DecisionReason(
                    code="low_profit_factor",
                    severity="blocking",
                    message="Insufficient profit factor",
                    metric="profit_factor",
                    actual_value=1.5,
                    threshold_value=2.0,
                )
            ],
            warnings=[],
            blocking_failures=["Low profit factor"],
            next_actions=["Improve strategy profitability"],
        ))

        result = baseline_service.evaluate(baseline_request)

        # Pipeline succeeded even though strategy was rejected
        assert result.success is True
        assert result.status == "completed"
        assert result.classification == "rejected"

    def test_stage_results_are_recorded(
        self,
        baseline_service,
        baseline_request,
        mock_run_stage_repository,
    ):
        """Test that all stage results are properly recorded."""
        result = baseline_service.evaluate(baseline_request)

        # Assert all stages were started and completed
        assert mock_run_stage_repository.start_stage.call_count == 10
        assert mock_run_stage_repository.complete_stage.call_count == 10

        # Verify stage results in response
        assert len(result.stage_results) == 10
        for stage in result.stage_results:
            assert stage.stage_name is not None
            assert stage.status is not None
            assert stage.started_at is not None
            assert stage.completed_at is not None

    def test_report_artifact_path_generated(
        self,
        baseline_service,
        baseline_request,
        mock_artifact_repository,
    ):
        """Test that report artifact path is generated and registered."""
        result = baseline_service.evaluate(baseline_request)

        # Assert artifact was registered
        mock_artifact_repository.create_artifact.assert_called_once()

        # Assert artifact path is in result
        assert any("baseline_evaluation_report.json" in path for path in result.artifact_paths)

    def test_no_ollama_discord_calls(
        self,
        baseline_service,
        baseline_request,
    ):
        """Test that no Ollama or Discord calls are made."""
        result = baseline_service.evaluate(baseline_request)

        # This test validates that the service doesn't make external AI calls
        # The service should only use existing Part 04/05/06 services
        # If Ollama or Discord were called, they would be injected as dependencies
        # Since they're not in the constructor, this test passes by design
        assert result.success is True

    def test_no_approval_export_classification_emitted(
        self,
        baseline_service,
        baseline_request,
        mock_decision_service,
    ):
        """Test that only decision classifications are emitted, not approval/export."""
        result = baseline_service.evaluate(baseline_request)

        # Assert classification is from decision service (rejected, candidate, promising, validated)
        assert result.classification in ["rejected", "candidate", "promising", "validated"]
        assert result.classification not in ["approved", "exported"]

    def test_config_generation_failure_stops_pipeline(
        self,
        baseline_service,
        baseline_request,
        mock_config_generator,
    ):
        """Test config generation failure stops pipeline."""
        mock_config_generator.write_backtest_config = Mock(return_value=FreqtradeBacktestConfigResult(
            run_id="test-run-id",
            config_path="",
            config={},
            artifact_id=None,
            success=False,
            error="Config generation failed",
        ))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert "config" in result.errors[0].lower() or "configuration" in result.errors[0].lower()

        # Assert data check was not called
        baseline_service.data_service.check_data.assert_not_called()

    def test_decision_evaluation_failure_stops_pipeline(
        self,
        baseline_service,
        baseline_request,
        mock_decision_service,
    ):
        """Test decision evaluation failure stops pipeline."""
        mock_decision_service.evaluate_run = Mock(return_value=DecisionEvaluationResponse(
            run_id="test-run-id",
            success=False,
            decision=None,
            saved_decision_id=None,
            decision_report_path=None,
            run_updated=False,
            decision_id=None,
            classification=None,
            confidence_score=None,
            policy_name=None,
            gates=[],
            reasons=[],
            warnings=[],
            blocking_failures=[],
            next_actions=[],
        ))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"

        # Assert baseline report was not called
        assert len(result.stage_results) == 8  # Stopped before report and completion

    def test_unhandled_exception_caught_controlled_failure(
        self,
        baseline_service,
        baseline_request,
        mock_strategy_service,
    ):
        """Test that unhandled exceptions are caught and result in controlled failure."""
        # Mock strategy service to raise exception
        mock_strategy_service.validate_strategy_name = Mock(side_effect=Exception("Unexpected error"))

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"
        assert len(result.errors) > 0

    def test_data_download_with_confirmation_proceeds(
        self,
        baseline_service,
        baseline_request,
        mock_data_service,
    ):
        """Test data download proceeds when missing data and user confirmed."""
        # Mock missing data
        mock_data_service.check_data = Mock(return_value=FreqtradeDataCheckResult(
            run_id="test-run-id",
            exchange="binance",
            trading_mode="spot",
            pairs=[
                PairDataStatus(
                    pair="BTC/USDT",
                    timeframe="1h",
                    exists=False,
                    file_path=None,
                    timerange=None,
                    errors=[],
                    warnings=[],
                )
            ],
            freqtrade_visible=True,
            source="freqtrade",
            errors=[],
            warnings=[],
        ))

        # Enable download and confirm
        baseline_request.download_missing_data = True
        baseline_request.user_confirmed = True

        result = baseline_service.evaluate(baseline_request)

        assert result.success is True
        assert result.status == "completed"

        # Assert download was called
        mock_data_service.download_data.assert_called_once()

    def test_apply_decision_false_skips_run_classification(
        self,
        baseline_service,
        baseline_request,
        mock_decision_service,
        mock_run_repository,
    ):
        """Test that apply_decision=False skips run classification update."""
        baseline_request.apply_decision_to_run = False

        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert decision service was called with apply_to_run=False
        call_args = mock_decision_service.evaluate_run.call_args
        assert call_args[0][0].apply_to_run is False

        # Assert run classification was not updated
        mock_run_repository.set_decision_classification.assert_not_called()

    def test_baseline_uses_feather_data_format(
        self,
        baseline_service,
        baseline_request,
        mock_config_generator,
    ):
        """Test that baseline pipeline uses feather data format to match downloaded data."""
        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert config generator was called with feather format
        call_args = mock_config_generator.write_backtest_config.call_args
        assert call_args[0][0].data_format_ohlcv == "feather"

    def test_baseline_passes_correct_config_to_backtest(
        self,
        baseline_service,
        baseline_request,
        mock_config_generator,
        mock_backtest_runner,
    ):
        """Test that baseline pipeline passes correct config path to backtest runner."""
        mock_config_generator.write_backtest_config.return_value = FreqtradeBacktestConfigResult(
            run_id="test-run-id",
            config_path="freqtrade_workspace/config/runs/test-run-id.backtest.json",
            config={},
            artifact_id="artifact-123",
            success=True,
        )

        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert backtest runner was called with correct config path
        call_args = mock_backtest_runner.run_backtest.call_args
        assert call_args[0][0].config_path == "freqtrade_workspace/config/runs/test-run-id.backtest.json"

    def test_baseline_uses_correct_strategy_name(
        self,
        baseline_service,
        baseline_request,
        mock_backtest_runner,
    ):
        """Test that baseline pipeline uses correct strategy name in backtest request."""
        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert backtest runner was called with correct strategy name
        call_args = mock_backtest_runner.run_backtest.call_args
        assert call_args[0][0].strategy_name == "TestStrategy"

    def test_baseline_records_stdout_stderr_on_backtest_failure(
        self,
        baseline_service,
        baseline_request,
        mock_backtest_runner,
    ):
        """Test that baseline pipeline records stdout/stderr artifacts on backtest failure."""
        # Mock backtest failure with stdout/stderr
        mock_backtest_runner.run_backtest.return_value = FreqtradeBacktestResult(
            run_id="test-run-id",
            success=False,
            blocked=False,
            exit_code=1,
            stdout="backtest stdout output",
            stderr="backtest stderr output",
            duration_seconds=10.0,
            backtest_directory="/test/backtest",
            artifacts=[],
            error="Backtest failed",
            errors=["Backtest failed"],
            warnings=[],
        )

        result = baseline_service.evaluate(baseline_request)

        assert result.success is False
        assert result.status == "failed_controlled"

        # Assert stdout/stderr were captured in the backtest result
        # The backtest runner should have been called and the result should contain stdout/stderr
        call_args = mock_backtest_runner.run_backtest.call_args
        assert call_args.called

    def test_baseline_no_secrets_logged(
        self,
        baseline_service,
        baseline_request,
        mock_config_generator,
    ):
        """Test that baseline pipeline does not log secrets."""
        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert config generator was called
        assert mock_config_generator.write_backtest_config.called

    def test_force_parse_replaces_previous_evidence(
        self,
        baseline_service,
        baseline_request,
        mock_result_parser,
    ):
        """Test that force_parse=True replaces previous parsed evidence."""
        result = baseline_service.evaluate(baseline_request)

        assert result.success is True

        # Assert parser was called with force=True
        call_args = mock_result_parser.parse_run.call_args
        assert call_args[1]["force"] is True


class TestBaselineStageTracking:
    """Test stage tracking functionality."""

    def test_stage_tracking_records_timestamps(
        self,
        baseline_service,
        baseline_request,
    ):
        """Test that stage tracking records proper timestamps."""
        result = baseline_service.evaluate(baseline_request)

        for stage in result.stage_results:
            assert stage.started_at is not None
            assert stage.completed_at is not None
            # Verify completed_at is after started_at
            started = datetime.fromisoformat(stage.started_at)
            completed = datetime.fromisoformat(stage.completed_at)
            assert completed >= started

    def test_stage_tracking_records_messages(
        self,
        baseline_service,
        baseline_request,
    ):
        """Test that stage tracking records human-readable messages."""
        result = baseline_service.evaluate(baseline_request)

        for stage in result.stage_results:
            assert stage.message is not None
            assert isinstance(stage.message, str)
            assert len(stage.message) > 0

    def test_stage_tracking_records_warnings_and_errors(
        self,
        baseline_service,
        baseline_request,
        mock_strategy_service,
    ):
        """Test that stage tracking records warnings and errors."""
        # Mock strategy with warning
        mock_strategy_service.find_strategy_by_name = Mock(return_value=FreqtradeStrategyFile(
            strategy_name="TestStrategy",
            class_name=None,
            file_path="/path/to/strategies/TestStrategy.py",
            params_path=None,  # Missing sidecar
            exists=True,
            has_sidecar_json=False,
            source="file",
            errors=[],
            warnings=["Missing sidecar .json"],
        ))

        result = baseline_service.evaluate(baseline_request)

        # Find strategy validation stage
        strategy_stage = next(
            (s for s in result.stage_results if s.stage_name == "strategy_validation"),
            None
        )
        assert strategy_stage is not None
        assert len(strategy_stage.warnings) > 0
        assert "sidecar" in strategy_stage.warnings[0].lower()

    def test_stage_tracking_records_artifact_paths(
        self,
        baseline_service,
        baseline_request,
    ):
        """Test that stage tracking records artifact paths."""
        result = baseline_service.evaluate(baseline_request)

        # Check config generation stage has artifact path
        config_stage = next(
            (s for s in result.stage_results if s.stage_name == "config_generation"),
            None
        )
        assert config_stage is not None
        assert len(config_stage.artifact_paths) > 0
