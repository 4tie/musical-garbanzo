"""
Controlled-failure tests for Part 13 validation execution service.
"""
from __future__ import annotations

from types import SimpleNamespace

from fastapi import HTTPException

from app.repositories.validation import ValidationRepository
from app.schemas.validation import ValidationRunRequest
from app.services.validation_policy_service import ValidationPolicyService
from app.services.validation_execution_service import ValidationExecutionService

from tests.test_validation_execution_service import (
    FakeBacktestRunner,
    FakeConfigGenerator,
    FakeDecisionService,
    FakeParser,
    RecordingReadinessGate,
    passing_metrics,
)


def make_request(**overrides) -> ValidationRunRequest:
    data = {
        "source_type": "strategy",
        "strategy_name": "SampleStrategy",
        "pairs": ["BTC/USDT", "ETH/USDT"],
        "timeframe": "15m",
        "exchange": "binance",
        "risk_profile": "balanced",
        "timerange": "20240101-20240601",
        "wfo_train_days": 45,
        "wfo_test_days": 15,
        "wfo_step_days": 15,
        "wfo_max_windows": 2,
        "user_confirmed": True,
    }
    data.update(overrides)
    return ValidationRunRequest(**data)


def service(tmp_path, readiness_gate=None, runner=None, parser=None):
    return ValidationExecutionService(
        validation_repository=ValidationRepository(),
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=runner or FakeBacktestRunner(),
        result_parser=parser or FakeParser([passing_metrics(), passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=readiness_gate or RecordingReadinessGate(),
        project_root=tmp_path,
    )


def test_blocked_strategy_does_not_run_anything(tmp_path):
    runner = FakeBacktestRunner()

    def blocked_gate(strategy_name, run_type="validation"):
        raise HTTPException(
            status_code=400,
            detail={"message": "Strategy is blocked by readiness gate."},
        )

    result = service(tmp_path, readiness_gate=blocked_gate, runner=runner).run_validation(
        make_request()
    )

    assert result.status == "failed_controlled"
    assert result.decision_status == "validation_error"
    assert any("strategy_not_ready" in error for error in result.errors)
    assert runner.calls == []


def test_candidate_reference_missing_is_controlled(tmp_path):
    result = service(tmp_path).run_validation(
        make_request(source_type="baseline_run", source_run_id="missing-run")
    )

    assert result.status == "failed_controlled"
    assert result.decision_status == "validation_error"
    assert any("candidate_reference_missing" in error for error in result.errors)


def test_oos_timerange_invalid_is_controlled(tmp_path):
    result = service(tmp_path).run_validation(
        make_request(timerange="20240101-20240115")
    )

    assert result.status == "failed_controlled"
    assert result.decision_status == "validation_error"
    assert any("oos_timerange_invalid" in error for error in result.errors)


def test_oos_failure_is_controlled(tmp_path):
    result = service(tmp_path, runner=FakeBacktestRunner(fail_at_call=1)).run_validation(
        make_request()
    )

    assert result.status == "failed_controlled"
    assert result.decision_status == "validation_error"
    assert any("oos_backtest_failed" in error for error in result.errors)


def test_wfo_failure_is_controlled(tmp_path):
    result = service(tmp_path, runner=FakeBacktestRunner(fail_at_call=2)).run_validation(
        make_request()
    )

    assert result.status == "failed_controlled"
    assert result.decision_status == "validation_error"
    assert any("wfo_backtest_failed" in error for error in result.errors)


def test_parse_failure_is_controlled_without_stack_trace(tmp_path):
    class FailingParser:
        def parse_run(self, run_id, force=False):
            return SimpleNamespace(
                success=False,
                metrics=None,
                errors=["parse failure without traceback"],
                warnings=[],
            )

    result = service(tmp_path, parser=FailingParser()).run_validation(make_request())

    assert result.status == "failed_controlled"
    assert any("oos_parse_failed" in error for error in result.errors)
    assert "traceback" not in " ".join(result.errors).lower()


def test_no_secrets_in_controlled_failure_response(tmp_path):
    result = service(tmp_path, runner=FakeBacktestRunner(fail_at_call=1)).run_validation(
        make_request(notes="api_key=SHOULD_NOT_LEAK secret=NOPE")
    )

    encoded = " ".join(result.errors + result.warnings + result.next_actions).lower()
    assert "should_not_leak" not in encoded
    assert "api_key" not in encoded
    assert "secret" not in encoded


def test_robustness_failure_is_controlled(tmp_path):
    class FailingRobustness:
        def evaluate_metric_stability(self, baseline_metrics, oos_metrics, wfo_metrics=None):
            raise RuntimeError("robustness exploded")

    result = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=FakeBacktestRunner(),
        result_parser=FakeParser([passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=RecordingReadinessGate(),
        robustness_evaluator=FailingRobustness(),
        project_root=tmp_path,
    ).run_validation(make_request(wfo_enabled=False))

    assert result.status == "failed_controlled"
    assert any("robustness_failed" in error for error in result.errors)


def test_validation_decision_failure_is_controlled(tmp_path):
    class FailingPolicy(ValidationPolicyService):
        def make_final_decision(self, oos_result, wfo_result, robustness_results, policy):
            raise RuntimeError("decision exploded")

    result = ValidationExecutionService(
        validation_repository=ValidationRepository(),
        config_generator=FakeConfigGenerator(tmp_path),
        backtest_runner=FakeBacktestRunner(),
        result_parser=FakeParser([passing_metrics()]),
        decision_service=FakeDecisionService(),
        readiness_gate=RecordingReadinessGate(),
        policy_service=FailingPolicy(),
        project_root=tmp_path,
    ).run_validation(make_request(wfo_enabled=False, robustness_enabled=False))

    assert result.status == "failed_controlled"
    assert any("validation_decision_failed" in error for error in result.errors)
