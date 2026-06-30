"""
Tests for Part 13 robustness evaluator.
"""
from app.schemas.validation import ValidationPolicy
from app.services.robustness_evaluator import RobustnessEvaluator
from app.services.validation_policy_service import ValidationPolicyService


def baseline_metrics(**overrides):
    metrics = {
        "trade_count": 100,
        "profit_factor": 1.8,
        "expectancy": 0.08,
        "max_drawdown": 20.0,
    }
    metrics.update(overrides)
    return metrics


def oos_metrics(**overrides):
    metrics = {
        "trade_count": 85,
        "profit_factor": 1.5,
        "expectancy": 0.06,
        "max_drawdown": 22.0,
    }
    metrics.update(overrides)
    return metrics


def policy() -> ValidationPolicy:
    return ValidationPolicyService().get_default_policy("balanced", timeframe="15m")


def test_stable_metrics_pass():
    evaluator = RobustnessEvaluator()

    checks = evaluator.evaluate_metric_stability(
        baseline_metrics(),
        oos_metrics(),
        wfo_metrics=[
            {"trade_count": 40, "profit_factor": 1.3, "expectancy": 0.04, "max_drawdown": 21.0},
            {"trade_count": 38, "profit_factor": 1.2, "expectancy": 0.03, "max_drawdown": 24.0},
        ],
    )

    assert [check.status for check in checks] == ["passed", "passed", "passed", "passed"]
    assert evaluator.summarize_robustness(checks)["status"] == "passed"


def test_trade_collapse_warning_and_fail():
    evaluator = RobustnessEvaluator()

    warning = evaluator.evaluate_trade_count_stability(
        baseline_metrics(trade_count=100),
        oos_metrics(trade_count=70),
    )
    failed = evaluator.evaluate_trade_count_stability(
        baseline_metrics(trade_count=100),
        oos_metrics(trade_count=40),
    )

    assert warning.status == "warning"
    assert warning.issues[0].code == "trade_count_decline_warning"
    assert failed.status == "failed"
    assert failed.issues[0].code == "trade_count_collapse"


def test_pf_collapse_warning_and_fail():
    evaluator = RobustnessEvaluator()

    warning = evaluator.evaluate_profit_factor_stability(
        baseline_metrics(profit_factor=2.0),
        oos_metrics(profit_factor=1.4),
    )
    failed = evaluator.evaluate_profit_factor_stability(
        baseline_metrics(profit_factor=2.0),
        oos_metrics(profit_factor=1.1),
    )

    assert warning.status == "warning"
    assert warning.issues[0].code == "profit_factor_decline_warning"
    assert failed.status == "failed"
    assert failed.issues[0].code == "profit_factor_collapse"


def test_expectancy_negative_critical():
    evaluator = RobustnessEvaluator()

    result = evaluator.evaluate_expectancy_stability(
        baseline_metrics(),
        oos_metrics(expectancy=-0.01),
    )

    assert result.status == "failed"
    assert result.issues[0].severity == "critical"
    assert result.issues[0].code == "expectancy_flipped_negative"


def test_drawdown_expansion_fail():
    evaluator = RobustnessEvaluator()

    result = evaluator.evaluate_drawdown_stability(
        baseline_metrics(max_drawdown=20.0),
        oos_metrics(max_drawdown=35.0),
    )

    assert result.status == "failed"
    assert result.issues[0].code == "drawdown_expansion_failed"


def test_missing_metrics_critical():
    evaluator = RobustnessEvaluator()

    checks = evaluator.evaluate_metric_stability({}, {})

    assert all(check.status == "failed" for check in checks)
    assert all(check.issues[0].severity == "critical" for check in checks)
    assert {check.issues[0].code for check in checks} == {
        "missing_trade_count",
        "missing_profit_factor",
        "missing_expectancy",
        "missing_drawdown",
    }


def test_wfo_instability_fail():
    evaluator = RobustnessEvaluator()

    pass_rate_result = evaluator.evaluate_trade_count_stability(
        baseline_metrics(),
        oos_metrics(),
        wfo_metrics={
            "pass_rate": 0.40,
            "min_pass_rate": 0.60,
            "windows": [
                {"status": "passed", "metrics": {"trade_count": 20}},
                {"status": "failed", "metrics": {"trade_count": 20}},
            ],
        },
    )
    pf_result = evaluator.evaluate_profit_factor_stability(
        baseline_metrics(),
        oos_metrics(),
        wfo_metrics=[
            {"trade_count": 20, "profit_factor": 1.3, "expectancy": 0.02, "max_drawdown": 20},
            {"trade_count": 20, "profit_factor": 0.9, "expectancy": 0.02, "max_drawdown": 20},
        ],
    )
    expectancy_result = evaluator.evaluate_expectancy_stability(
        baseline_metrics(),
        oos_metrics(),
        wfo_metrics=[
            {"trade_count": 20, "profit_factor": 1.3, "expectancy": 0.02, "max_drawdown": 20},
            {"trade_count": 20, "profit_factor": 1.3, "expectancy": -0.01, "max_drawdown": 20},
        ],
    )

    assert pass_rate_result.status == "failed"
    assert pass_rate_result.issues[0].code == "wfo_pass_rate_below_policy"
    assert pf_result.status == "failed"
    assert pf_result.issues[0].code == "wfo_profit_factor_weak_windows"
    assert expectancy_result.status == "failed"
    assert expectancy_result.issues[0].code == "wfo_negative_expectancy_windows"


def test_sensitivity_variants_pass():
    evaluator = RobustnessEvaluator()

    checks = evaluator.evaluate_sensitivity_variants(
        [
            {
                "variant_name": "fees_plus",
                "metrics": {
                    "trade_count": 25,
                    "profit_factor": 1.2,
                    "expectancy": 0.01,
                    "max_drawdown": 30.0,
                },
            },
            {
                "variant_name": "pair_subset",
                "metrics": {
                    "trade_count": 30,
                    "profit_factor": 1.25,
                    "expectancy": 0.02,
                    "max_drawdown": 28.0,
                },
            },
        ],
        policy(),
    )

    assert [check.status for check in checks] == ["passed", "passed"]


def test_sensitivity_variants_fail():
    evaluator = RobustnessEvaluator()

    checks = evaluator.evaluate_sensitivity_variants(
        [
            {
                "variant_name": "fees_plus",
                "metrics": {
                    "trade_count": 0,
                    "profit_factor": 0.9,
                    "expectancy": -0.01,
                    "max_drawdown": 50.0,
                },
            }
        ],
        policy(),
    )

    assert checks[0].status == "failed"
    assert {issue.code for issue in checks[0].issues} >= {
        "sensitivity_zero_trades",
        "sensitivity_profit_factor_not_profitable",
        "sensitivity_expectancy_not_positive",
        "sensitivity_drawdown_exceeds_policy",
    }


def test_summary_counts_pass_warning_fail_critical():
    evaluator = RobustnessEvaluator()
    pass_check = evaluator.evaluate_trade_count_stability(
        baseline_metrics(),
        oos_metrics(),
    )
    warning_check = evaluator.evaluate_trade_count_stability(
        baseline_metrics(trade_count=100),
        oos_metrics(trade_count=70),
    )
    fail_check = evaluator.evaluate_profit_factor_stability(
        baseline_metrics(profit_factor=2.0),
        oos_metrics(profit_factor=1.1),
    )
    critical_check = evaluator.evaluate_expectancy_stability(
        baseline_metrics(),
        oos_metrics(expectancy=-0.01),
    )

    summary = evaluator.summarize_robustness(
        [pass_check, warning_check, fail_check, critical_check]
    )

    assert summary["total"] == 4
    assert summary["passed"] == 1
    assert summary["warning"] == 1
    assert summary["failed"] == 1
    assert summary["critical"] == 1
    assert summary["critical_failure_count"] == 1
    assert summary["status"] == "critical"


def test_no_profit_guarantee_wording():
    evaluator = RobustnessEvaluator()
    checks = evaluator.evaluate_metric_stability(baseline_metrics(), oos_metrics())
    sensitivity = evaluator.evaluate_sensitivity_variants(
        [
            {
                "variant_name": "normal",
                "metrics": {
                    "trade_count": 25,
                    "profit_factor": 1.2,
                    "expectancy": 0.01,
                    "max_drawdown": 30.0,
                },
            }
        ],
        policy(),
    )
    summary = evaluator.summarize_robustness(checks + sensitivity)
    payload = " ".join(
        [
            str([check.model_dump() for check in checks]),
            str([check.model_dump() for check in sensitivity]),
            str(summary),
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
