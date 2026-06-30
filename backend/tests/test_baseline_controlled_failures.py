"""
Tests for Part 07 baseline evaluation controlled failure behavior.

Tests ensure:
- Every known error code has message and next action
- Confirmation-required download path
- Confirmation-required backtest path
- Rejected decision still returns pipeline success
- Failed backtest stores failed stage
- Failed parse stores failed stage
- Failed decision stores failed stage
- Unexpected exception is converted to controlled failure
- Response contains frontend-ready stage data
- No stack traces in response
- No secrets in errors/details
"""
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone

from app.core.constants import BASELINE_ERROR_CODES, BASELINE_ERROR_MESSAGES
from app.schemas.baseline import BaselineEvaluationRequest, BaselineStageResult
from app.services.baseline_evaluation_service import BaselineEvaluationService


class TestBaselineErrorCodes:
    """Test that all error codes have user-facing messages."""

    def test_all_error_codes_have_messages(self):
        """Every error code should have a message mapping."""
        for error_code in BASELINE_ERROR_CODES:
            assert error_code in BASELINE_ERROR_MESSAGES, f"Error code {error_code} missing from messages"
            msg = BASELINE_ERROR_MESSAGES[error_code]
            assert "short_message" in msg, f"Error code {error_code} missing short_message"
            assert "user_message" in msg, f"Error code {error_code} missing user_message"
            assert "next_actions" in msg, f"Error code {error_code} missing next_actions"
            assert isinstance(msg["next_actions"], list), f"Error code {error_code} next_actions not a list"
            assert len(msg["next_actions"]) > 0, f"Error code {error_code} has empty next_actions"

    def test_error_message_structure(self):
        """Error messages should have required fields."""
        error_msg = BASELINE_ERROR_MESSAGES["strategy_not_found"]
        assert isinstance(error_msg["short_message"], str)
        assert isinstance(error_msg["user_message"], str)
        assert isinstance(error_msg["next_actions"], list)
        assert len(error_msg["next_actions"]) > 0


class TestBaselineStageResult:
    """Test BaselineStageResult includes error_code field."""

    def test_stage_result_has_error_code(self):
        """Stage result should include error_code field."""
        result = BaselineStageResult(
            stage_name="strategy_validation",
            status="failed_controlled",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            message="Test failure",
            error_code="strategy_not_found",
            errors=["Test error"],
        )
        assert result.error_code == "strategy_not_found"
        assert result.status == "failed_controlled"


class TestBaselineControlledFailures:
    """Test controlled failure behavior in baseline evaluation service."""

    @pytest.fixture
    def service(self):
        """Create a baseline evaluation service with mocked dependencies."""
        return BaselineEvaluationService(
            run_repository=MagicMock(),
            run_stage_repository=MagicMock(),
            artifact_repository=MagicMock(),
            log_repository=MagicMock(),
            audit_repository=MagicMock(),
            strategy_service=MagicMock(),
            config_generator=MagicMock(),
            data_service=MagicMock(),
            backtest_runner=MagicMock(),
            result_parser=MagicMock(),
            decision_service=MagicMock(),
            project_root=MagicMock(),
        )

    @pytest.fixture
    def baseline_request(self):
        """Create a baseline evaluation request."""
        return BaselineEvaluationRequest(
            strategy_name="test_strategy",
            pairs=["BTC/USDT"],
            timeframe="1h",
            exchange="binance",
            risk_profile="balanced",
            download_missing_data=False,
            user_confirmed=False,
        )

    def test_strategy_not_found_controlled_failure(self, service, baseline_request):
        """Strategy not found should return controlled failure with error code."""
        # Mock strategy service to return None (not found)
        service.strategy_service.validate_strategy_name.return_value = (True, None)
        service.strategy_service.find_strategy_by_name.return_value = None

        # Mock run setup
        service.run_repository.create_run.return_value = {"id": "test_run_id"}
        service.run_stage_repository.create_baseline_stages.return_value = None
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_strategy_validation("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "strategy_not_found"
        assert result.stage_name == "strategy_validation"
        assert result.message is not None
        assert len(result.errors) > 0
        # No stack traces in errors
        for error in result.errors:
            assert "Traceback" not in error
            assert "File " not in error

    def test_unsafe_strategy_path_controlled_failure(self, service, baseline_request):
        """Unsafe strategy path should return controlled failure with error code."""
        # Mock strategy service to return strategy with unsafe path
        mock_strategy = MagicMock()
        mock_strategy.strategy_name = "test_strategy"
        mock_strategy.file_path = "/etc/passwd"
        mock_strategy.has_sidecar_json = True

        service.strategy_service.validate_strategy_name.return_value = (True, None)
        service.strategy_service.find_strategy_by_name.return_value = mock_strategy
        service.strategy_service.validate_strategy_file_path.return_value = (False, "Path outside workspace")

        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_strategy_validation("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "unsafe_strategy_path"
        assert result.stage_name == "strategy_validation"

    def test_config_generation_failed_controlled_failure(self, service, baseline_request):
        """Config generation failure should return controlled failure with error code."""
        # Mock config generator to fail
        mock_config_result = MagicMock()
        mock_config_result.success = False
        mock_config_result.error = "Invalid parameters"

        service.config_generator.write_backtest_config.return_value = mock_config_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_config_generation("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "config_generation_failed"
        assert result.stage_name == "config_generation"

    def test_data_missing_controlled_failure(self, service, baseline_request):
        """Missing data should return controlled failure with error code."""
        # Mock data service to return missing data
        mock_data_check_result = MagicMock()
        mock_pair = MagicMock()
        mock_pair.pair = "BTC/USDT"
        mock_pair.exists = False
        mock_data_check_result.pairs = [mock_pair]

        service.data_service.check_data.return_value = mock_data_check_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_data_check("test_run_id", baseline_request, None)

        assert result.status == "failed_controlled"
        assert result.error_code == "data_missing"
        assert result.stage_name == "data_check"

    def test_confirmation_required_for_download(self, service, baseline_request):
        """Missing data with download enabled but not confirmed should require confirmation."""
        # Mock data service to return missing data
        mock_data_check_result = MagicMock()
        mock_pair = MagicMock()
        mock_pair.pair = "BTC/USDT"
        mock_pair.exists = False
        mock_data_check_result.pairs = [mock_pair]

        service.data_service.check_data.return_value = mock_data_check_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.mark_stage_waiting.return_value = None

        # Enable download but not confirmed
        baseline_request.download_missing_data = True
        baseline_request.user_confirmed = False

        result = service._stage_data_check("test_run_id", baseline_request, None)

        assert result.status == "confirmation_required"
        assert result.error_code == "confirmation_required_for_download"
        assert result.stage_name == "data_check"

    def test_confirmation_required_for_backtest(self, service, baseline_request):
        """Backtest without user confirmation should require confirmation."""
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.mark_stage_waiting.return_value = None

        # Not confirmed
        baseline_request.user_confirmed = False

        result = service._stage_baseline_backtest("test_run_id", baseline_request, None)

        assert result.status == "confirmation_required"
        assert result.error_code == "confirmation_required_for_backtest"
        assert result.stage_name == "baseline_backtest"

    def test_data_download_failed_controlled_failure(self, service, baseline_request):
        """Data download failure should return controlled failure with error code."""
        # Mock download to fail
        mock_download_result = MagicMock()
        mock_download_result.success = False
        mock_download_result.error = "Network error"

        service.data_service.download_data.return_value = mock_download_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        # Enable download and confirm
        baseline_request.download_missing_data = True
        baseline_request.user_confirmed = True

        result = service._stage_data_download("test_run_id", baseline_request, missing_data=True)

        assert result.status == "failed_controlled"
        assert result.error_code == "data_download_failed"
        assert result.stage_name == "data_download"

    def test_backtest_failed_controlled_failure(self, service, baseline_request):
        """Backtest failure should return controlled failure with error code."""
        # Mock backtest to fail
        mock_backtest_result = MagicMock()
        mock_backtest_result.success = False
        mock_backtest_result.error = "Strategy runtime error"
        mock_backtest_result.exit_code = 1
        mock_backtest_result.artifacts = []
        mock_backtest_result.duration_seconds = 1.0
        mock_backtest_result.backtest_directory = "/tmp/backtest"

        service.backtest_runner.run_backtest.return_value = mock_backtest_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None
        # Mock the path helper to avoid exceptions in artifact collection
        service._make_project_relative = lambda x: x

        baseline_request.user_confirmed = True

        result = service._stage_baseline_backtest("test_run_id", baseline_request, "/tmp/config.json")

        assert result.status == "failed_controlled"
        assert result.error_code == "backtest_failed"
        assert result.stage_name == "baseline_backtest"
        assert result.details.get("exit_code") == 1

    def test_parse_failed_controlled_failure(self, service, baseline_request):
        """Parse failure should return controlled failure with error code."""
        # Mock parser to fail
        mock_parse_result = MagicMock()
        mock_parse_result.success = False
        mock_parse_result.errors = ["Could not parse backtest results"]

        service.result_parser.parse_run.return_value = mock_parse_result
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_result_parsing("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "parse_failed"
        assert result.stage_name == "result_parsing"

    def test_decision_failed_controlled_failure(self, service, baseline_request):
        """Decision failure should return controlled failure with error code."""
        # Mock decision service to fail
        mock_decision_response = MagicMock()
        mock_decision_response.success = False

        service.decision_service.evaluate_run.return_value = mock_decision_response
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_decision_evaluation("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "decision_failed"
        assert result.stage_name == "decision_evaluation"

    def test_baseline_report_failed_controlled_failure(self, service, baseline_request):
        """Report creation failure should return controlled failure with error code."""
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None
        service.artifact_repository.create_artifact.side_effect = Exception("File system error")

        result = service._stage_baseline_report(
            "test_run_id",
            baseline_request,
            [],
            {"classification": "rejected"},
        )

        assert result.status == "failed_controlled"
        assert result.error_code == "baseline_report_failed"
        assert result.stage_name == "baseline_report"

    def test_unexpected_exception_converted_to_controlled_failure(self, service, baseline_request):
        """Unexpected exceptions should be converted to controlled failures."""
        service.run_stage_repository.start_stage.side_effect = Exception("Unexpected error")

        result = service._stage_strategy_validation("test_run_id", baseline_request)

        assert result.status == "failed_controlled"
        assert result.error_code == "unexpected_pipeline_error"
        assert result.stage_name == "strategy_validation"
        # No stack trace in message
        assert "Traceback" not in result.message

    def test_rejected_decision_is_pipeline_success(self, service, baseline_request):
        """Rejected classification should still return pipeline success."""
        # Mock decision service to return rejected
        mock_decision_response = MagicMock()
        mock_decision_response.success = True
        mock_decision_response.classification = "rejected"
        mock_decision_response.confidence_score = 0.5
        mock_decision_response.policy_name = "default_balanced"
        mock_decision_response.next_actions = ["Review strategy"]
        mock_decision_response.run_updated = True
        mock_decision_response.warnings = []
        mock_decision_response.decision_report_path = None

        service.decision_service.evaluate_run.return_value = mock_decision_response
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.complete_stage.return_value = None

        result = service._stage_decision_evaluation("test_run_id", baseline_request)

        assert result.status == "completed"
        assert result.details.get("classification") == "rejected"
        # Pipeline stage completed successfully even though classification is rejected

    def test_stage_result_includes_frontend_ready_data(self, service, baseline_request):
        """Stage results should include all frontend-ready fields."""
        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.complete_stage.return_value = None

        result = service._stage_strategy_validation("test_run_id", baseline_request)

        assert result.stage_name is not None
        assert result.status is not None
        assert result.started_at is not None
        assert result.completed_at is not None
        assert result.duration_seconds is not None
        assert result.message is not None
        assert isinstance(result.warnings, list)
        assert isinstance(result.errors, list)
        assert isinstance(result.artifact_paths, list)
        assert isinstance(result.details, dict)

    def test_no_secrets_in_errors_or_details(self, service, baseline_request):
        """Errors and details should not contain sensitive information."""
        # Mock strategy service to fail with a message that might contain secrets
        service.strategy_service.validate_strategy_name.return_value = (True, None)
        service.strategy_service.find_strategy_by_name.return_value = None

        service.run_stage_repository.start_stage.return_value = None
        service.run_stage_repository.fail_stage.return_value = None

        result = service._stage_strategy_validation("test_run_id", baseline_request)

        # Check that no secrets are leaked
        for error in result.errors:
            assert "password" not in error.lower()
            assert "api_key" not in error.lower()
            assert "secret" not in error.lower()

        for key, value in result.details.items():
            if isinstance(value, str):
                assert "password" not in value.lower()
                assert "api_key" not in value.lower()
                assert "secret" not in value.lower()

    def test_build_result_uses_error_next_actions(self, service, baseline_request):
        """Build result should use next_actions from error messages when available."""
        # Create a failed stage with error code
        failed_stage = BaselineStageResult(
            stage_name="strategy_validation",
            status="failed_controlled",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            message="Strategy not found",
            error_code="strategy_not_found",
            errors=["Strategy not found"],
        )

        result = service._build_result(
            request=baseline_request,
            run_id="test_run_id",
            success=False,
            status="failed_controlled",
            classification=None,
            confidence_score=None,
            stage_results=[failed_stage],
            artifact_paths=[],
            errors=[],
            warnings=[],
            next_actions=[],  # Empty initially
        )

        # Should populate next_actions from error message
        assert len(result.next_actions) > 0
        assert "Verify strategy name spelling" in result.next_actions

    def test_build_result_uses_confirmation_next_actions(self, service, baseline_request):
        """Build result should use next_actions for confirmation_required status."""
        # Create a confirmation-required stage
        waiting_stage = BaselineStageResult(
            stage_name="data_check",
            status="confirmation_required",
            started_at=datetime.now(timezone.utc).isoformat(),
            completed_at=datetime.now(timezone.utc).isoformat(),
            message="Data download requires confirmation",
            error_code="confirmation_required_for_download",
            errors=[],
        )

        result = service._build_result(
            request=baseline_request,
            run_id="test_run_id",
            success=False,
            status="confirmation_required",
            classification=None,
            confidence_score=None,
            stage_results=[waiting_stage],
            artifact_paths=[],
            errors=[],
            warnings=[],
            next_actions=[],  # Empty initially
        )

        # Should populate next_actions from error message
        assert len(result.next_actions) > 0
        assert "Set user_confirmed to True" in " ".join(result.next_actions)


class TestBaselineHelperMethods:
    """Test baseline evaluation service helper methods."""

    @pytest.fixture
    def service(self):
        """Create a baseline evaluation service with mocked dependencies."""
        return BaselineEvaluationService(
            run_repository=MagicMock(),
            run_stage_repository=MagicMock(),
            artifact_repository=MagicMock(),
            log_repository=MagicMock(),
            audit_repository=MagicMock(),
            strategy_service=MagicMock(),
            config_generator=MagicMock(),
            data_service=MagicMock(),
            backtest_runner=MagicMock(),
            result_parser=MagicMock(),
            decision_service=MagicMock(),
            project_root=MagicMock(),
        )

    def test_start_stage(self, service):
        """Test _start_stage helper method."""
        service.run_stage_repository.start_stage.return_value = None

        started_at = service._start_stage("strategy_validation", "test_run_id")

        assert started_at is not None
        service.run_stage_repository.start_stage.assert_called_once_with("test_run_id", "strategy_validation")

    def test_complete_stage(self, service):
        """Test _complete_stage helper method."""
        service.run_stage_repository.complete_stage.return_value = None
        service.log_repository.add_log.return_value = None

        started_at = datetime.now(timezone.utc)
        result = service._complete_stage(
            stage_name="strategy_validation",
            run_id="test_run_id",
            started_at=started_at,
            message="Test completed",
            details={"test": "data"},
        )

        assert result.status == "completed"
        assert result.message == "Test completed"
        assert result.duration_seconds is not None
        assert result.duration_seconds >= 0
        service.run_stage_repository.complete_stage.assert_called_once()
        service.log_repository.add_log.assert_called_once()

    def test_fail_stage(self, service):
        """Test _fail_stage helper method."""
        service.run_stage_repository.fail_stage.return_value = None
        service.log_repository.add_log.return_value = None

        started_at = datetime.now(timezone.utc)
        result = service._fail_stage(
            stage_name="strategy_validation",
            run_id="test_run_id",
            started_at=started_at,
            message="Test failed",
            error_code="strategy_not_found",
            details={"error": "details"},
        )

        assert result.status == "failed_controlled"
        assert result.message == "Test failed"
        assert result.error_code == "strategy_not_found"
        assert result.duration_seconds is not None
        service.run_stage_repository.fail_stage.assert_called_once()
        service.log_repository.add_log.assert_called_once()

    def test_confirmation_required(self, service):
        """Test _confirmation_required helper method."""
        service.run_stage_repository.mark_stage_waiting.return_value = None
        service.log_repository.add_log.return_value = None

        started_at = datetime.now(timezone.utc)
        result = service._confirmation_required(
            stage_name="data_check",
            run_id="test_run_id",
            started_at=started_at,
            message="Confirmation required",
            details={"requires": "confirmation"},
            error_code="confirmation_required_for_download",
        )

        assert result.status == "confirmation_required"
        assert result.message == "Confirmation required"
        assert result.duration_seconds is not None
        service.run_stage_repository.mark_stage_waiting.assert_called_once()
        service.log_repository.add_log.assert_called_once()

    def test_add_run_log(self, service):
        """Test _add_run_log helper method."""
        service.log_repository.add_log.return_value = None

        service._add_run_log(
            run_id="test_run_id",
            level="info",
            message="Test log",
            details={"test": "data"},
        )

        service.log_repository.add_log.assert_called_once()

    def test_add_audit_log(self, service):
        """Test _add_audit_log helper method."""
        service.audit_repository.create_audit_log.return_value = None

        service._add_audit_log(
            run_id="test_run_id",
            action_type="test_action",
            before={"status": "old"},
            after={"status": "new"},
        )

        service.audit_repository.create_audit_log.assert_called_once()

    def test_get_error_message(self, service):
        """Test _get_error_message helper method."""
        msg = service._get_error_message("strategy_not_found")

        assert msg is not None
        assert "short_message" in msg
        assert "user_message" in msg
        assert "next_actions" in msg

    def test_get_error_message_unknown_code(self, service):
        """Test _get_error_message with unknown error code."""
        msg = service._get_error_message("unknown_error_code")

        assert msg is not None
        assert "short_message" in msg
        assert "Unknown error" in msg["short_message"]
