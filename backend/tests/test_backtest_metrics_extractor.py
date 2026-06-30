"""
Tests for backtest metrics extraction.
"""
import pytest

from app.schemas.backtest_results import RawBacktestPayload
from app.services.backtest_metrics_extractor import BacktestMetricsExtractor


def make_json_payload(raw_data):
    """Build a raw JSON payload for extractor tests."""
    return RawBacktestPayload(
        source_path="/tmp/backtest-result.json",
        source_type="json",
        parser_type="freqtrade_json",
        raw_data=raw_data,
    )


def test_trade_level_expectancy_calculation():
    """Trade-level expectancy is average profit per trade."""
    extractor = BacktestMetricsExtractor()
    trades = [
        {"profit_abs": 10.0},
        {"profit_abs": -4.0},
        {"profit_abs": 0.0},
        {"profit_abs": 6.0},
    ]

    result = extractor.calculate_expectancy_from_trades(trades)

    assert result.method == "trade_level"
    assert result.expectancy == 3.0
    assert result.trade_count == 4
    assert result.win_rate == 0.5
    assert result.loss_rate == 0.25
    assert result.avg_win == 8.0
    assert result.avg_loss == -4.0
    assert result.total_profit == 12.0


def test_summary_level_expectancy_calculation():
    """Summary-level expectancy uses win/loss rates and average win/loss."""
    result = BacktestMetricsExtractor().calculate_expectancy_from_summary(
        wins=6,
        losses=4,
        avg_win=10.0,
        avg_loss=-5.0,
    )

    assert result.method == "summary_level"
    assert result.expectancy == 4.0
    assert result.trade_count == 10
    assert result.win_rate == 0.6
    assert result.loss_rate == 0.4
    assert result.total_profit == 40.0


def test_no_trades_returns_warning():
    """Missing trade-level data returns warning and no fabricated expectancy."""
    result = BacktestMetricsExtractor().calculate_expectancy_from_trades([])

    assert result.expectancy is None
    assert result.method == "not_available"
    assert "trade_level_data_missing" in result.warnings


def test_wins_losses_draws_extraction_from_trades():
    """Extractor derives wins/losses/draws from trade-level profits."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "total_trades": 3,
                    "trades": [
                        {"profit_abs": 2.0},
                        {"profit_abs": -1.0},
                        {"profit_abs": 0.0},
                    ],
                }
            }
        }
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.success is True
    assert result.metrics.wins == 1
    assert result.metrics.losses == 1
    assert result.metrics.draws == 1
    assert result.metrics.trade_count == 3
    assert result.metrics.expectancy == 1 / 3
    assert result.metrics.expectancy_source == "trade_level"


def test_profit_factor_extraction_from_multiple_possible_keys():
    """Extractor supports common profit factor key variants."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "profitfactor": "1.42",
                    "total_trades": 10,
                }
            }
        }
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.metrics.profit_factor == 1.42


def test_drawdown_extraction():
    """Extractor supports absolute and percent drawdown fields."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "max_drawdown_abs": "123.45",
                    "max_drawdown_pct": "6.7",
                    "total_trades": 10,
                }
            }
        }
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.metrics.max_drawdown == 123.45
    assert result.metrics.max_drawdown_pct == 6.7


def test_stdout_fallback_simple_table_parse():
    """Stdout fallback extracts a limited lower-quality metric set."""
    payload = RawBacktestPayload(
        source_path="/tmp/stdout.log",
        source_type="stdout_log",
        parser_type="stdout_table_fallback",
        raw_text="""
        Total profit | 42.5
        Profit factor | 1.25
        Max drawdown | 7.5
        Trades | 10
        Win rate | 60%
        Wins | 6
        Losses | 4
        Avg win | 10
        Avg loss | -5
        """,
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.success is True
    assert result.metrics.net_profit == 42.5
    assert result.metrics.profit_factor == 1.25
    assert result.metrics.max_drawdown == 7.5
    assert result.metrics.trade_count == 10
    assert result.metrics.win_rate == 0.6
    assert result.metrics.expectancy == 4.0
    assert result.metrics.expectancy_source == "stdout_fallback"
    assert "stdout_fallback_lower_quality" in result.warnings


def test_malformed_payload_returns_controlled_error():
    """Payload loader errors are preserved and extraction does not crash."""
    payload = RawBacktestPayload(
        source_path="/tmp/backtest-result.json",
        source_type="json",
        parser_type="freqtrade_json",
        errors=["json_load_error: malformed"],
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.success is False
    assert "json_load_error: malformed" in result.errors
    assert "payload_has_no_raw_data" in result.warnings


def test_missing_keys_do_not_crash():
    """Unknown JSON shapes return controlled missing-metric warnings."""
    payload = make_json_payload({"metadata": {"freqtrade_version": "2026.5.1"}})

    result = BacktestMetricsExtractor().extract(payload)

    assert result.success is False
    assert result.metrics is not None
    assert result.metrics.expectancy is None
    assert "trade_count_missing" in result.warnings
    assert "profit_factor_missing" in result.warnings


def test_summary_fields_used_when_trades_missing():
    """Summary data is used when trade-level profits are unavailable."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "wins": 3,
                    "losses": 2,
                    "draws": 1,
                    "avg_win": 8.0,
                    "avg_loss": -4.0,
                    "win_rate": 60,
                    "profit_factor": 1.8,
                    "total_trades": 6,
                }
            }
        }
    )

    result = BacktestMetricsExtractor().extract(payload)

    assert result.success is True
    assert result.metrics.expectancy == pytest.approx(3.2)
    assert result.metrics.expectancy_source == "summary_level"
    assert result.metrics.win_rate == 0.6
    assert result.metrics.draws == 1


def test_no_profitability_claim_is_made_in_output():
    """Extractor output has no approval or profitability classification field."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "profit_factor": 2.5,
                    "total_trades": 1,
                }
            }
        }
    )

    result_text = BacktestMetricsExtractor().extract(payload).model_dump_json()

    assert "profitable" not in result_text.lower()
    assert "approved" not in result_text.lower()
    assert "rejected" not in result_text.lower()
