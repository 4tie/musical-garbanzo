"""
Tests for Part 06 decision policy thresholds.
"""
import json

import pytest

from app.services.decision_policy import DecisionPolicyService


def test_default_balanced_policy():
    """Default policy uses balanced thresholds."""
    policy = DecisionPolicyService().get_policy(timeframe="1h")

    assert policy.policy_name == "default_balanced"
    assert policy.risk_profile == "balanced"
    assert policy.timeframe == "1h"
    assert policy.thresholds.min_trades == 60
    assert policy.thresholds.candidate_profit_factor == 1.10
    assert policy.thresholds.validated_profit_factor == 1.40
    assert policy.thresholds.max_drawdown_candidate == 30.0


def test_conservative_thresholds_stricter_than_balanced():
    """Conservative policy requires stronger PF and lower drawdown."""
    service = DecisionPolicyService()
    conservative = service.get_thresholds("conservative", "1h")
    balanced = service.get_thresholds("balanced", "1h")

    assert conservative.min_trades > balanced.min_trades
    assert conservative.candidate_profit_factor > balanced.candidate_profit_factor
    assert conservative.promising_profit_factor > balanced.promising_profit_factor
    assert conservative.validated_profit_factor > balanced.validated_profit_factor
    assert conservative.max_drawdown_candidate < balanced.max_drawdown_candidate
    assert conservative.max_drawdown_validated < balanced.max_drawdown_validated
    assert conservative.min_expectancy_validated > balanced.min_expectancy_validated


def test_aggressive_thresholds_looser_than_balanced():
    """Aggressive policy allows lower PF and higher drawdown."""
    service = DecisionPolicyService()
    aggressive = service.get_thresholds("aggressive", "1h")
    balanced = service.get_thresholds("balanced", "1h")

    assert aggressive.min_trades < balanced.min_trades
    assert aggressive.candidate_profit_factor < balanced.candidate_profit_factor
    assert aggressive.promising_profit_factor < balanced.promising_profit_factor
    assert aggressive.validated_profit_factor < balanced.validated_profit_factor
    assert aggressive.max_drawdown_candidate > balanced.max_drawdown_candidate
    assert aggressive.max_drawdown_validated > balanced.max_drawdown_validated
    assert aggressive.min_expectancy_validated < balanced.min_expectancy_validated


@pytest.mark.parametrize(
    ("timeframe", "expected"),
    [
        ("1m", 500),
        ("3m", 400),
        ("5m", 300),
        ("15m", 150),
        ("30m", 100),
        ("1h", 60),
        ("2h", 40),
        ("4h", 30),
        ("1d", 20),
    ],
)
def test_min_trades_by_timeframe(timeframe, expected):
    """Balanced profile uses the base minimum-trade table."""
    assert (
        DecisionPolicyService().get_min_trades_for_timeframe(
            timeframe,
            risk_profile="balanced",
        )
        == expected
    )


def test_risk_profile_modifiers():
    """Risk profiles scale minimum trades."""
    service = DecisionPolicyService()

    assert service.get_min_trades_for_timeframe("15m", "conservative") == 188
    assert service.get_min_trades_for_timeframe("15m", "balanced") == 150
    assert service.get_min_trades_for_timeframe("15m", "aggressive") == 120


def test_unknown_timeframe_fallback():
    """Unknown timeframes fall back to the default 1h minimum."""
    service = DecisionPolicyService()

    policy = service.get_default_policy(timeframe="unsupported")

    assert policy.timeframe == "1h"
    assert policy.thresholds.min_trades == 60


def test_unknown_risk_profile_controlled_error():
    """Unknown risk profiles fail with a clear error."""
    with pytest.raises(ValueError, match="Unknown risk profile"):
        DecisionPolicyService().get_default_policy(risk_profile="reckless")


def test_moderate_alias_maps_to_balanced():
    """Older moderate risk-profile values map to balanced."""
    policy = DecisionPolicyService().get_default_policy(
        risk_profile="moderate",
        timeframe="1h",
    )

    assert policy.risk_profile == "balanced"
    assert policy.policy_name == "default_balanced"
    assert policy.thresholds.min_trades == 60


def test_policy_name_mismatch_controlled_error():
    """Policy names and explicit risk profiles must agree."""
    with pytest.raises(ValueError, match="different risk profiles"):
        DecisionPolicyService().get_policy(
            policy_name="default_conservative",
            risk_profile="aggressive",
        )


def test_policy_summary_output():
    """Policy summary includes thresholds and gate names."""
    service = DecisionPolicyService()
    policy = service.get_policy(policy_name="default_conservative", timeframe="4h")
    summary = service.summarize_policy(policy)

    assert summary.policy_name == "default_conservative"
    assert summary.risk_profile == "conservative"
    assert summary.timeframe == "4h"
    assert summary.thresholds.min_trades == 38
    assert "rejected" in summary.allowed_classifications
    assert "validated" in summary.allowed_classifications
    assert "trade_count_minimum" in summary.gate_names


def test_no_profitability_guarantee_wording_in_policy_output():
    """Policy objects avoid guarantee-style output language."""
    service = DecisionPolicyService()
    policy = service.get_default_policy()
    summary = service.summarize_policy(policy)

    output = json.dumps(
        {
            "policy": policy.model_dump(),
            "summary": summary.model_dump(),
        }
    ).lower()

    assert "guarantee" not in output
    assert "guaranteed" not in output
    assert "profitable" not in output
