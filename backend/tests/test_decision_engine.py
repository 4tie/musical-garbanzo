"""
Tests for Part 06 in-memory decision engine.
"""
import json

from app.schemas.backtest_results import (
    ExtractedBacktestMetrics,
    ExtractedPairResult,
    ExtractedTradeSummary,
    ResultQualityFlag,
    ResultQualityReport,
)
from app.services.decision_engine import DecisionEngine
from app.services.decision_policy import DecisionPolicyService


def make_metrics(**overrides) -> ExtractedBacktestMetrics:
    """Build complete parsed metrics with optional overrides."""
    data = {
        "net_profit": 100.0,
        "profit_factor": 1.12,
        "max_drawdown_pct": 28.0,
        "win_rate": 0.45,
        "trade_count": 80,
        "wins": 36,
        "losses": 44,
        "expectancy": 0.01,
        "source_type": "json",
    }
    data.update(overrides)
    return ExtractedBacktestMetrics(**data)


def make_pairs(*profits) -> list[ExtractedPairResult]:
    """Build pair results from net profit values."""
    if not profits:
        profits = (60.0, 40.0)
    return [
        ExtractedPairResult(
            pair=f"PAIR{index}/USDT",
            trade_count=40,
            net_profit=profit,
        )
        for index, profit in enumerate(profits, start=1)
    ]


def make_summary(**overrides) -> ExtractedTradeSummary:
    """Build complete trade summary with optional overrides."""
    data = {
        "total_trades": 80,
        "wins": 36,
        "losses": 44,
        "draws": 0,
    }
    data.update(overrides)
    return ExtractedTradeSummary(**data)


def quality_report(*flag_codes, usable=True) -> ResultQualityReport:
    """Build a parser quality report."""
    return ResultQualityReport(
        parse_quality="warning" if flag_codes else "ok",
        flags=[
            ResultQualityFlag(
                code=code,
                severity="error" if code == "parse_error" else "warning",
                message=f"{code} flag",
            )
            for code in flag_codes
        ],
        is_usable_for_metrics=usable,
        is_usable_for_decision=usable,
    )


def evaluate(metrics=None, pairs=None, summary=None, quality=None):
    """Evaluate with the default balanced 1h policy."""
    policy = DecisionPolicyService().get_default_policy(
        risk_profile="balanced",
        timeframe="1h",
    )
    return DecisionEngine().evaluate(
        metrics if metrics is not None else make_metrics(),
        pairs if pairs is not None else make_pairs(),
        summary if summary is not None else make_summary(),
        quality_report=quality if quality is not None else quality_report(),
        policy=policy,
        run_id="run-123",
    )


def reason_codes(result):
    """Return decision reason codes."""
    return {reason.code for reason in result.reasons}


def gate_by_name(result, gate_name):
    """Find a gate by name."""
    return next(gate for gate in result.gates if gate.gate_name == gate_name)


def test_negative_expectancy_rejected():
    """Negative expectancy is a blocking rejection."""
    result = evaluate(make_metrics(expectancy=-0.2, profit_factor=1.4))

    assert result.classification == "rejected"
    assert "negative_expectancy" in reason_codes(result)
    assert gate_by_name(result, "expectancy_gate").severity == "blocking"


def test_profit_factor_below_one_rejected():
    """Profit factor below 1.0 is blocking."""
    result = evaluate(make_metrics(profit_factor=0.99, expectancy=0.1))

    assert result.classification == "rejected"
    assert "profit_factor_below_one" in reason_codes(result)


def test_high_drawdown_rejected():
    """Drawdown above the block threshold is blocking."""
    result = evaluate(make_metrics(max_drawdown_pct=60.0, profit_factor=1.5, expectancy=0.1))

    assert result.classification == "rejected"
    assert "drawdown_above_limit" in reason_codes(result)


def test_too_few_trades_rejected():
    """Trade count below the policy minimum is blocking."""
    result = evaluate(make_metrics(trade_count=20), summary=make_summary(total_trades=20))

    assert result.classification == "rejected"
    assert "too_few_trades" in reason_codes(result)


def test_missing_metrics_rejected_insufficient_data():
    """Missing required metrics produce a rejected result."""
    result = evaluate(
        make_metrics(profit_factor=None, expectancy=None, trade_count=None),
        summary=make_summary(total_trades=None),
    )

    assert result.classification == "rejected"
    codes = reason_codes(result)
    assert "missing_profit_factor" in codes
    assert "missing_trade_count" in codes
    assert "missing_expectancy" in codes
    assert any(reason.severity == "blocking" for reason in result.reasons)


def test_single_pair_dependency_warning_not_sole_rejection():
    """Single-pair evidence warns but does not reject by itself."""
    result = evaluate(
        make_metrics(profit_factor=1.3, expectancy=0.04, max_drawdown_pct=22.0),
        pairs=make_pairs(100.0),
    )

    assert result.classification != "rejected"
    assert "single_pair_dependency_warning" in reason_codes(result)
    assert gate_by_name(result, "pair_dependency_gate").status == "warning"


def test_complete_weak_positive_result_candidate():
    """Minimum positive evidence classifies as candidate."""
    result = evaluate(
        make_metrics(profit_factor=1.12, expectancy=0.01, max_drawdown_pct=28.0)
    )

    assert result.classification == "candidate"
    assert result.blocking_failures == []


def test_stronger_result_promising():
    """Stronger baseline evidence classifies as promising."""
    result = evaluate(
        make_metrics(profit_factor=1.30, expectancy=0.04, max_drawdown_pct=22.0)
    )

    assert result.classification == "promising"


def test_strong_result_validated():
    """Strong clean baseline evidence classifies as validated."""
    result = evaluate(
        make_metrics(profit_factor=1.45, expectancy=0.10, max_drawdown_pct=15.0)
    )

    assert result.classification == "validated"
    assert result.confidence_score > 80
    assert result.blocking_failures == []


def test_losing_real_smoke_like_metrics_rejected():
    """Part 05 real smoke-like losing metrics classify as rejected."""
    result = evaluate(
        make_metrics(
            net_profit=-9961.46959422,
            trade_count=8678,
            wins=1718,
            losses=6960,
            profit_factor=0.44620083091599505,
            max_drawdown_pct=99.61469594219984,
            win_rate=0.19797188292233234,
            expectancy=-1.1478992387900437,
        ),
        pairs=make_pairs(-9961.46959422),
        summary=make_summary(total_trades=8678, wins=1718, losses=6960),
        quality=quality_report("negative_expectancy", "high_drawdown"),
    )

    assert result.classification == "rejected"
    codes = reason_codes(result)
    assert "negative_expectancy" in codes
    assert "profit_factor_below_one" in codes
    assert "drawdown_above_limit" in codes


def test_confidence_score_caps_for_rejected():
    """Blocking rejection caps confidence at 40."""
    result = evaluate(make_metrics(profit_factor=0.5, expectancy=-0.2))

    assert result.classification == "rejected"
    assert result.confidence_score <= 40


def test_parse_not_usable_confidence_cap():
    """Parser blocking failures cap confidence at 20."""
    result = evaluate(quality=quality_report("parse_error", usable=False))

    assert result.classification == "rejected"
    assert result.confidence_score <= 20
    assert "parse_quality_blocking" in reason_codes(result)


def test_validated_does_not_contain_approved_exported_live_wording():
    """Validated output avoids approved/exported/live-ready wording."""
    result = evaluate(
        make_metrics(profit_factor=1.45, expectancy=0.10, max_drawdown_pct=15.0)
    )

    output = json.dumps(result.model_dump()).lower()
    assert result.classification == "validated"
    assert "approved" not in output
    assert "exported" not in output
    assert "live-ready" not in output
    assert "live_ready" not in output


def test_next_actions_generated():
    """Decision results include cautious next actions."""
    result = evaluate(make_metrics(profit_factor=0.5, expectancy=-0.2))

    assert result.next_actions
    assert "Do not export this strategy." in result.next_actions
