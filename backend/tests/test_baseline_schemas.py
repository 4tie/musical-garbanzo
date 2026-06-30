"""
Tests for Part 07 baseline evaluation schemas and constants.
"""
import json

import pytest
from pydantic import ValidationError

from app.core.constants import (
    BASELINE_EVALUATION_MODES,
    BASELINE_PIPELINE_STAGES,
    BASELINE_PIPELINE_STATUSES,
)
from app.schemas.baseline import (
    BaselineEvaluationRequest,
    BaselineEvaluationResult,
    BaselineStageResult,
    BaselineStatusResponse,
)


def make_valid_request(**overrides):
    data = {
        "strategy_name": "SmokeTestStrategy",
        "pairs": ["BTC/USDT"],
        "timeframe": "5m",
    }
    data.update(overrides)
    return BaselineEvaluationRequest(**data)


def test_valid_request_defaults():
    request = make_valid_request()

    assert request.strategy_name == "SmokeTestStrategy"
    assert request.pairs == ["BTC/USDT"]
    assert request.timeframe == "5m"
    assert request.exchange == "binance"
    assert request.days == 30
    assert request.timerange is None
    assert request.risk_profile == "balanced"
    assert request.stake_currency == "USDT"
    assert request.stake_amount == "unlimited"
    assert request.max_open_trades == 3
    assert request.trading_mode == "spot"
    assert request.download_missing_data is False
    assert request.user_confirmed is False
    assert request.apply_decision_to_run is True
    assert request.force_parse is True


def test_empty_pairs_rejected():
    with pytest.raises(ValidationError, match="pairs must not be empty"):
        make_valid_request(pairs=[])


def test_missing_strategy_rejected():
    with pytest.raises(ValidationError, match="strategy_name is required"):
        make_valid_request(strategy_name=" ")


def test_invalid_risk_profile_rejected():
    with pytest.raises(ValidationError, match="risk_profile must be one of"):
        make_valid_request(risk_profile="reckless")


@pytest.mark.parametrize("days", [0, -1])
def test_invalid_negative_days_rejected(days):
    with pytest.raises(ValidationError, match="days must be positive"):
        make_valid_request(days=days)


def test_user_confirmed_false_request_can_be_created_with_download_flag():
    request = make_valid_request(
        download_missing_data=True,
        user_confirmed=False,
    )

    assert request.download_missing_data is True
    assert request.user_confirmed is False


def test_response_serializes_cleanly():
    stage = BaselineStageResult(
        stage_name="run_setup",
        status="completed",
        duration_seconds=1.25,
        message="Run created",
        artifact_paths=["artifacts/runs/run-123/setup.json"],
        details={"run_id": "run-123"},
    )
    result = BaselineEvaluationResult(
        success=True,
        run_id="run-123",
        status="completed",
        classification="rejected",
        confidence_score=40.0,
        strategy_name="SmokeTestStrategy",
        pairs=["BTC/USDT"],
        timeframe="5m",
        exchange="binance",
        risk_profile="balanced",
        metrics={"trade_count": 10},
        decision={"classification": "rejected"},
        quality_flags=["negative_expectancy"],
        stage_results=[stage],
        artifact_paths=["artifacts/runs/run-123/decisions/decision_result.json"],
        warnings=["low_win_rate_warning"],
        next_actions=["Review blocking failures"],
    )
    status = BaselineStatusResponse(
        run_id="run-123",
        status="completed",
        classification="rejected",
        current_stage="completion",
        stage_results=[stage],
        metrics={"trade_count": 10},
        decision={"classification": "rejected"},
    )

    payload = result.model_dump()
    status_payload = status.model_dump()
    encoded = json.dumps({"result": payload, "status": status_payload})

    assert "SmokeTestStrategy" in encoded
    assert "stdout" not in encoded.lower()
    assert "stderr" not in encoded.lower()
    assert payload["artifact_paths"] == [
        "artifacts/runs/run-123/decisions/decision_result.json"
    ]
    assert status_payload["current_stage"] == "completion"


def test_absolute_artifact_path_rejected():
    with pytest.raises(ValidationError, match="project-relative"):
        BaselineStageResult(
            stage_name="run_setup",
            status="completed",
            artifact_paths=["/home/mohs/Desktop/her/artifacts/runs/run-123/file.json"],
        )


def test_no_fake_or_mock_evaluation_mode_exists():
    assert BASELINE_EVALUATION_MODES == ["real"]
    assert "fake" not in BASELINE_EVALUATION_MODES
    assert "mock" not in BASELINE_EVALUATION_MODES


def test_stage_constants_contain_expected_stages():
    assert BASELINE_PIPELINE_STAGES == [
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
    assert BASELINE_PIPELINE_STATUSES == [
        "pending",
        "running",
        "completed",
        "failed_controlled",
        "confirmation_required",
    ]
