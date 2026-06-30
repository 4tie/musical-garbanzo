"""
Tests for Part 13 validation policy service.
"""
from app.schemas.validation import RobustnessCheckResult, ValidationIssue, WFOWindowResult
from app.services.validation_policy_service import ValidationPolicyService


def passing_metrics(**overrides):
    metrics = {
        "profit_factor": 1.35,
        "expectancy": 0.02,
        "trade_count": 60,
        "max_drawdown": 20.0,
    }
    metrics.update(overrides)
    return metrics


def wfo_window(index: int, status: str = "wfo_passed", **overrides):
    data = {
        "window_index": index,
        "timerange": f"202501{index + 1:02d}-202501{index + 10:02d}",
        "status": status,
        "metrics": {"profit_factor": 1.2, "trade_count": 20},
    }
    data.update(overrides)
    return WFOWindowResult(**data)


def robustness_check(status: str = "robustness_passed", **overrides):
    data = {
        "check_name": "pair_subset",
        "status": status,
        "metrics": {"subset_count": 2},
        "issues": [],
    }
    data.update(overrides)
    return RobustnessCheckResult(**data)


def test_conservative_thresholds():
    service = ValidationPolicyService()
    policy = service.get_default_policy("conservative", timeframe="5m")

    assert policy.risk_profile == "conservative"
    assert policy.min_oos_profit_factor == 1.20
    assert policy.max_oos_drawdown_pct == 25.0
    assert policy.min_wfo_pass_rate == 0.70
    assert policy.min_oos_trades > service.get_default_policy("balanced", "5m").min_oos_trades


def test_balanced_thresholds():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    assert policy.risk_profile == "balanced"
    assert policy.min_oos_profit_factor == 1.10
    assert policy.max_oos_drawdown_pct == 35.0
    assert policy.min_wfo_pass_rate == 0.60
    assert policy.min_oos_trades == 20


def test_aggressive_thresholds():
    service = ValidationPolicyService()
    policy = service.get_default_policy("aggressive", timeframe="15m")

    assert policy.risk_profile == "aggressive"
    assert policy.min_oos_profit_factor == 1.05
    assert policy.max_oos_drawdown_pct == 45.0
    assert policy.min_wfo_pass_rate == 0.50
    assert policy.min_oos_trades < service.get_default_policy("balanced", "15m").min_oos_trades


def test_oos_pass():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos(passing_metrics(), policy)

    assert result.status == "oos_passed"
    assert result.issues == []


def test_oos_fail_pf():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos(passing_metrics(profit_factor=1.0), policy)

    assert result.status == "oos_failed"
    assert_issue(result.issues, "oos_profit_factor_below_threshold", "profit_factor", 1.0, 1.10)


def test_oos_fail_expectancy():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos(passing_metrics(expectancy=0.0), policy)

    assert result.status == "oos_failed"
    assert_issue(result.issues, "oos_expectancy_not_positive", "expectancy", 0.0, 0.0)


def test_oos_fail_drawdown():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos(passing_metrics(max_drawdown=36.0), policy)

    assert result.status == "oos_failed"
    assert_issue(result.issues, "oos_drawdown_exceeds_threshold", "max_drawdown", 36.0, 35.0)


def test_oos_fail_zero_trades():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos(passing_metrics(trade_count=0), policy)

    assert result.status == "oos_failed"
    assert_issue(result.issues, "oos_zero_trades", "trade_count", 0, 20)


def test_wfo_pass():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_wfo(
        [wfo_window(0), wfo_window(1), wfo_window(2, "wfo_failed")],
        policy,
    )

    assert result.status == "wfo_passed"
    assert result.pass_count == 2
    assert result.summary["pass_rate"] == 2 / 3


def test_wfo_fail_pass_rate():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_wfo(
        [wfo_window(0), wfo_window(1, "wfo_failed"), wfo_window(2, "wfo_failed")],
        policy,
    )

    assert result.status == "wfo_failed"
    assert_issue(
        result.issues,
        "wfo_pass_rate_below_threshold",
        "wfo_pass_rate",
        1 / 3,
        0.60,
    )


def test_robustness_pass():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_robustness([robustness_check()], policy)

    assert len(result) == 1
    assert result[0].status == "robustness_passed"


def test_robustness_fail_critical():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")
    critical_issue = ValidationIssue(
        code="single_pair_dependency",
        severity="critical",
        message="Performance depends on one pair.",
        details={
            "metric_name": "critical_failure_count",
            "actual_value": 1,
            "threshold": 0,
            "next_action": "Reject this candidate.",
        },
    )

    result = service.evaluate_robustness(
        [robustness_check(issues=[critical_issue])],
        policy,
    )

    assert result[0].status == "robustness_failed"
    assert result[0].decision["critical_failure_count"] == 1


def test_final_validated_decision():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")
    oos = service.evaluate_oos(passing_metrics(), policy)
    wfo = service.evaluate_wfo([wfo_window(0), wfo_window(1)], policy)
    robustness = service.evaluate_robustness([robustness_check()], policy)

    decision = service.make_final_decision(oos, wfo, robustness, policy)

    assert decision.decision_status == "validated"
    assert decision.blocking_failures == []
    assert "guarantee" in " ".join(decision.next_actions).lower()
    assert "approval" in " ".join(decision.next_actions).lower()


def test_final_rejected_decision():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")
    oos = service.evaluate_oos(passing_metrics(profit_factor=1.0), policy)
    wfo = service.evaluate_wfo([wfo_window(0), wfo_window(1)], policy)
    robustness = service.evaluate_robustness([robustness_check()], policy)

    decision = service.make_final_decision(oos, wfo, robustness, policy)

    assert decision.decision_status == "rejected"
    assert "oos_failed" in decision.blocking_failures
    assert "oos_profit_factor_below_threshold" in decision.blocking_failures


def test_missing_metrics_rejected_safely():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")

    result = service.evaluate_oos({}, policy)

    assert result.status == "oos_failed"
    assert_issue(result.issues, "missing_profit_factor", "profit_factor", None, 1.10)
    assert_issue(result.issues, "missing_expectancy", "expectancy", None, 0.0)
    assert_issue(result.issues, "missing_trade_count", "trade_count", None, 20)
    assert_issue(result.issues, "missing_drawdown", "max_drawdown", None, 35.0)


def test_no_profit_guarantee_wording():
    service = ValidationPolicyService()
    policy = service.get_default_policy("balanced", timeframe="15m")
    summary = service.build_policy_summary(policy)
    oos = service.evaluate_oos(passing_metrics(), policy)
    wfo = service.evaluate_wfo([wfo_window(0), wfo_window(1)], policy)
    robustness = service.evaluate_robustness([robustness_check()], policy)
    decision = service.make_final_decision(oos, wfo, robustness, policy)
    payload = " ".join(
        [
            str(summary),
            str(oos.model_dump()),
            str(wfo.model_dump()),
            str([item.model_dump() for item in robustness]),
            str(decision.model_dump()),
        ]
    ).lower()

    forbidden = [
        "profit guarantee",
        "guaranteed profit",
        "risk-free",
        "approved for live trading",
        "safe to trade",
    ]
    assert not any(phrase in payload for phrase in forbidden)


def assert_issue(issues, code, metric_name, actual_value, threshold):
    issue = next(item for item in issues if item.code == code)

    assert issue.severity in {"blocking", "critical"}
    assert issue.message
    assert issue.details["metric_name"] == metric_name
    assert issue.details["actual_value"] == actual_value
    assert issue.details["threshold"] == threshold
    assert issue.details["next_action"]
