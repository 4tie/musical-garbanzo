"""
Tests for Part 13 validation evidence schemas and constants.
"""
import json

import pytest
from pydantic import ValidationError

from app.core.constants import (
    VALIDATION_DECISION_STATUSES,
    VALIDATION_STAGES,
    VALIDATION_STATUSES,
)
from app.schemas.validation import (
    OOSValidationResult,
    RobustnessCheckResult,
    ValidationDecision,
    ValidationEvidence,
    ValidationIssue,
    ValidationPolicy,
    ValidationRunDetail,
    ValidationRunListItem,
    ValidationRunRequest,
    ValidationRunResponse,
    ValidationStatusResponse,
    ValidationSummary,
    WFOValidationResult,
    WFOWindowResult,
)


def make_valid_request(**overrides):
    data = {
        "source_type": "strategy",
        "strategy_name": "SmokeTestStrategy",
        "pairs": ["BTC/USDT"],
        "timeframe": "5m",
    }
    data.update(overrides)
    return ValidationRunRequest(**data)


def test_validation_constants_contain_expected_values():
    assert VALIDATION_STAGES == [
        "validation_setup",
        "candidate_reference",
        "readiness_gate",
        "oos_timerange_split",
        "oos_backtest",
        "oos_result_parsing",
        "oos_decision",
        "wfo_window_generation",
        "wfo_window_execution",
        "wfo_result_parsing",
        "wfo_decision",
        "robustness_checks",
        "sensitivity_checks",
        "validation_decision",
        "validation_report",
        "completion",
    ]
    assert VALIDATION_STATUSES == [
        "pending",
        "running",
        "completed",
        "failed_controlled",
        "confirmation_required",
    ]
    assert VALIDATION_DECISION_STATUSES == [
        "not_validated",
        "oos_failed",
        "oos_passed",
        "wfo_failed",
        "wfo_passed",
        "robustness_failed",
        "robustness_passed",
        "validated",
        "rejected",
        "validation_error",
    ]


def test_valid_request_defaults():
    request = make_valid_request()

    assert request.source_type == "strategy"
    assert request.source_run_id is None
    assert request.strategy_name == "SmokeTestStrategy"
    assert request.pairs == ["BTC/USDT"]
    assert request.timeframe == "5m"
    assert request.exchange == "binance"
    assert request.risk_profile == "balanced"
    assert request.timerange is None
    assert request.days == 90
    assert request.oos_ratio == 0.30
    assert request.wfo_enabled is True
    assert request.wfo_train_days == 60
    assert request.wfo_test_days == 15
    assert request.wfo_step_days == 15
    assert request.wfo_max_windows == 5
    assert request.robustness_enabled is True
    assert request.sensitivity_enabled is False
    assert request.download_missing_data is False
    assert request.user_confirmed is False


@pytest.mark.parametrize(
    "source_type",
    ["strategy", "baseline_run", "optimization_run", "optimized_run"],
)
def test_allowed_source_types(source_type):
    request = make_valid_request(source_type=source_type)

    assert request.source_type == source_type


def test_invalid_source_type_rejected():
    with pytest.raises(ValidationError, match="source_type must be one of"):
        make_valid_request(source_type="fake_source")


def test_empty_pairs_rejected():
    with pytest.raises(ValidationError, match="pairs must be non-empty"):
        make_valid_request(pairs=[])


def test_missing_strategy_rejected():
    with pytest.raises(ValidationError, match="strategy_name is required"):
        make_valid_request(strategy_name=" ")


def test_missing_timeframe_rejected():
    with pytest.raises(ValidationError, match="timeframe is required"):
        make_valid_request(timeframe=" ")


def test_invalid_risk_profile_rejected():
    with pytest.raises(ValidationError, match="risk_profile must be one of"):
        make_valid_request(risk_profile="reckless")


@pytest.mark.parametrize("oos_ratio", [0.09, 0.51])
def test_invalid_oos_ratio_rejected(oos_ratio):
    with pytest.raises(ValidationError, match="oos_ratio must be between"):
        make_valid_request(oos_ratio=oos_ratio)


@pytest.mark.parametrize(
    "field",
    ["wfo_train_days", "wfo_test_days", "wfo_step_days", "wfo_max_windows"],
)
def test_invalid_wfo_values_rejected(field):
    with pytest.raises(ValidationError, match="WFO values must be positive"):
        make_valid_request(**{field: 0})


def test_user_confirmed_false_request_can_be_created():
    request = make_valid_request(download_missing_data=True, user_confirmed=False)

    assert request.download_missing_data is True
    assert request.user_confirmed is False


def test_evidence_schema_supports_oos_wfo_and_robustness():
    oos = ValidationEvidence(
        validation_run_id="validation-run-1",
        evidence_type="oos",
        status="completed",
        timerange="20250301-20250331",
        metrics={"profit_factor": 1.4},
        decision={"classification": "candidate"},
        warnings=["low_trade_count_warning"],
        artifact_paths=["artifacts/runs/validation-run/oos/result.json"],
    )
    wfo = ValidationEvidence(
        validation_run_id="validation-run-1",
        evidence_type="wfo_window",
        status="wfo_passed",
        window_index=0,
        timerange="20250201-20250215",
    )
    robustness = ValidationEvidence(
        validation_run_id="validation-run-1",
        evidence_type="robustness",
        status="robustness_passed",
        issues=[ValidationIssue(code="pair_subset_ok", message="Pair subset passed")],
    )

    assert oos.evidence_type == "oos"
    assert wfo.window_index == 0
    assert robustness.issues[0].code == "pair_subset_ok"


def test_absolute_artifact_path_rejected():
    with pytest.raises(ValidationError, match="project-relative"):
        ValidationEvidence(
            validation_run_id="validation-run-1",
            evidence_type="oos",
            status="completed",
            artifact_paths=["/home/mohs/Desktop/her/artifacts/runs/result.json"],
        )


def test_policy_and_decision_validation():
    policy = ValidationPolicy(risk_profile="conservative", min_wfo_pass_rate=0.75)
    decision = ValidationDecision(
        decision_status="validated",
        confidence_score=81.5,
        policy_name=policy.policy_name,
        reasons=["OOS, WFO, and robustness passed"],
    )

    assert policy.risk_profile == "conservative"
    assert decision.decision_status == "validated"
    assert decision.confidence_score == 81.5


def test_invalid_decision_status_rejected():
    with pytest.raises(ValidationError, match="decision_status must be"):
        ValidationDecision(decision_status="approved")


def test_frontend_ready_detail_shape_serializes_cleanly():
    run = ValidationRunListItem(
        id="validation-run-1",
        source_type="strategy",
        strategy_name="SmokeTestStrategy",
        timeframe="5m",
        pairs=["BTC/USDT"],
        exchange="binance",
        risk_profile="balanced",
        status="completed",
        decision_status="validated",
        created_at="2026-06-30T10:00:00+00:00",
        updated_at="2026-06-30T10:05:00+00:00",
    )
    evidence = ValidationEvidence(
        id="evidence-1",
        validation_run_id="validation-run-1",
        evidence_type="oos",
        status="completed",
        metrics={"profit_factor": 1.4},
    )
    detail = ValidationRunDetail(
        run=run,
        evidence=[evidence],
        oos=OOSValidationResult(status="oos_passed", metrics={"profit_factor": 1.4}),
        wfo=WFOValidationResult(
            status="wfo_passed",
            windows=[
                WFOWindowResult(
                    window_index=0,
                    timerange="20250201-20250215",
                    status="wfo_passed",
                )
            ],
            pass_count=1,
        ),
        robustness=[
            RobustnessCheckResult(
                check_name="pair_subset",
                status="robustness_passed",
            )
        ],
        decision=ValidationDecision(decision_status="validated"),
        summary=ValidationSummary(decision_status="validated", evidence_count=3),
        artifact_paths=["artifacts/runs/validation-run/validation/report.json"],
    )
    response = ValidationRunResponse(
        validation_run_id=run.id,
        status="completed",
        decision_status="validated",
        strategy_name=run.strategy_name,
        pairs=run.pairs,
        timeframe=run.timeframe,
        exchange=run.exchange,
        risk_profile=run.risk_profile,
    )
    status = ValidationStatusResponse(
        validation_run_id=run.id,
        status="completed",
        decision_status="validated",
        evidence_count=3,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )

    payload = {
        "detail": detail.model_dump(mode="json"),
        "response": response.model_dump(mode="json"),
        "status": status.model_dump(mode="json"),
    }
    encoded = json.dumps(payload)

    assert payload["detail"]["run"]["id"] == "validation-run-1"
    assert payload["detail"]["summary"]["evidence_count"] == 3
    assert payload["response"]["decision_status"] == "validated"
    assert payload["status"]["evidence_count"] == 3
    assert "stdout" not in encoded.lower()
    assert "stderr" not in encoded.lower()
    assert "approval" not in encoded.lower()
    assert "export" not in encoded.lower()


def test_no_fake_evidence_fields_are_accepted():
    with pytest.raises(ValidationError):
        ValidationEvidence(
            validation_run_id="validation-run-1",
            evidence_type="oos",
            status="completed",
            fake_evidence=True,
        )
