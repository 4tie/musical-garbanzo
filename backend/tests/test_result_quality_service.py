"""
Tests for result quality flags.
"""
from app.schemas.backtest_results import (
    BacktestOutputDiscoveryResult,
    ExtractedBacktestMetrics,
    ExtractedPairResult,
    ExtractedTradeSummary,
    RawBacktestLoadResult,
    RawBacktestPayload,
)
from app.services.result_quality_service import ResultQualityService


def make_metrics(**kwargs) -> ExtractedBacktestMetrics:
    """Build complete-enough metrics with test overrides."""
    data = {
        "net_profit": 10.0,
        "profit_factor": 1.2,
        "max_drawdown_pct": 10.0,
        "trade_count": 40,
        "expectancy": 0.25,
        "source_type": "json",
    }
    data.update(kwargs)
    return ExtractedBacktestMetrics(**data)


def make_summary(**kwargs) -> ExtractedTradeSummary:
    """Build a trade summary with test overrides."""
    data = {
        "total_trades": 40,
        "wins": 22,
        "losses": 18,
        "draws": 0,
    }
    data.update(kwargs)
    return ExtractedTradeSummary(**data)


def make_pairs() -> list[ExtractedPairResult]:
    """Build balanced pair results."""
    return [
        ExtractedPairResult(pair="BTC/USDT", trade_count=20, net_profit=6.0),
        ExtractedPairResult(pair="ETH/USDT", trade_count=20, net_profit=4.0),
    ]


def codes(report):
    """Return flag codes from a report."""
    return {flag.code for flag in report.flags}


def test_no_trades_flag():
    """Explicit zero trades blocks decision usability."""
    report = ResultQualityService().build_quality_report(
        make_metrics(trade_count=0),
        make_pairs(),
        make_summary(total_trades=0),
    )

    assert "no_trades" in codes(report)
    assert report.is_usable_for_metrics is True
    assert report.is_usable_for_decision is False


def test_too_few_trades_flag():
    """Small trade counts are warned but not by themselves blocking."""
    report = ResultQualityService().build_quality_report(
        make_metrics(trade_count=5),
        make_pairs(),
        make_summary(total_trades=5),
    )

    assert "too_few_trades" in codes(report)
    assert report.is_usable_for_decision is True


def test_stdout_only_parse_flag():
    """Stdout-only loader output is flagged as lower quality."""
    loader_result = RawBacktestLoadResult(
        success=False,
        payloads=[
            RawBacktestPayload(
                source_path="/tmp/stdout.log",
                source_type="stdout_log",
                parser_type="stdout_table_fallback",
                raw_text="BACKTESTING REPORT",
            )
        ],
    )

    report = ResultQualityService().build_quality_report(
        make_metrics(),
        make_pairs(),
        make_summary(),
        loader_result=loader_result,
    )

    assert "stdout_only_parse" in codes(report)


def test_negative_expectancy_flag():
    """Negative expectancy is a warning, not an acceptance decision."""
    report = ResultQualityService().build_quality_report(
        make_metrics(expectancy=-0.2, net_profit=-8.0),
        make_pairs(),
        make_summary(),
    )

    assert "negative_expectancy" in codes(report)
    assert report.is_usable_for_decision is True


def test_high_drawdown_flag():
    """High drawdown is flagged."""
    report = ResultQualityService().build_quality_report(
        make_metrics(max_drawdown_pct=45.0),
        make_pairs(),
        make_summary(),
    )

    assert "high_drawdown" in codes(report)


def test_single_pair_dependency_flag():
    """Dominant pair contribution is flagged."""
    pair_results = [
        ExtractedPairResult(pair="BTC/USDT", trade_count=30, net_profit=90.0),
        ExtractedPairResult(pair="ETH/USDT", trade_count=10, net_profit=10.0),
    ]

    report = ResultQualityService().build_quality_report(
        make_metrics(),
        pair_results,
        make_summary(),
    )

    assert "single_pair_dependency" in codes(report)


def test_missing_pair_results_flag():
    """Missing pair evidence is flagged and blocks future decision usability."""
    report = ResultQualityService().build_quality_report(
        make_metrics(),
        [],
        make_summary(),
    )

    assert "missing_pair_results" in codes(report)
    assert "partial_parse" in codes(report)
    assert report.is_usable_for_decision is False


def test_missing_profit_factor_flag():
    """Missing profit factor is flagged as a missing core metric."""
    report = ResultQualityService().build_quality_report(
        make_metrics(profit_factor=None),
        make_pairs(),
        make_summary(),
    )

    assert "missing_profit_factor" in codes(report)
    assert report.is_usable_for_decision is False


def test_missing_drawdown_flag():
    """Missing drawdown is flagged as a missing core metric."""
    report = ResultQualityService().build_quality_report(
        make_metrics(max_drawdown=None, max_drawdown_pct=None),
        make_pairs(),
        make_summary(),
    )

    assert "missing_drawdown" in codes(report)
    assert report.is_usable_for_decision is False


def test_decision_usability_false_on_parse_error():
    """Parser errors block future decision usability."""
    metrics = make_metrics()
    metrics.errors.append("json_load_error: malformed")

    report = ResultQualityService().build_quality_report(
        metrics,
        make_pairs(),
        make_summary(),
    )

    assert "parse_error" in codes(report)
    assert report.is_usable_for_decision is False


def test_decision_usability_false_on_missing_backtest_file():
    """Missing structured result files block future decision usability."""
    discovery_result = BacktestOutputDiscoveryResult(
        run_id="run-123",
        success=False,
        warnings=["no_backtest_output_files_found"],
    )

    report = ResultQualityService().build_quality_report(
        make_metrics(),
        make_pairs(),
        make_summary(),
        discovery_result=discovery_result,
    )

    assert report.run_id == "run-123"
    assert "missing_backtest_file" in codes(report)
    assert report.is_usable_for_decision is False


def test_decision_usability_true_for_complete_but_losing_result():
    """A complete losing result can still be usable for a future decision engine."""
    report = ResultQualityService().build_quality_report(
        make_metrics(net_profit=-15.0, expectancy=-0.4, profit_factor=0.7),
        make_pairs(),
        make_summary(),
    )

    assert "negative_expectancy" in codes(report)
    assert report.is_usable_for_metrics is True
    assert report.is_usable_for_decision is True


def test_no_profitability_claim():
    """Quality reports do not include acceptance or outcome claims."""
    report = ResultQualityService().build_quality_report(
        make_metrics(),
        make_pairs(),
        make_summary(),
    )
    text = report.model_dump_json()

    assert "approved" not in text.lower()
    assert "rejected" not in text.lower()
    assert "profitable" not in text.lower()
