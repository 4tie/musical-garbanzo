"""
Tests for pair-level result and trade summary parsing.
"""
import pytest

from app.schemas.backtest_results import RawBacktestPayload
from app.services.backtest_pair_trade_parser import BacktestPairTradeParser


def make_json_payload(raw_data):
    """Build a raw JSON payload for parser tests."""
    return RawBacktestPayload(
        source_path="/tmp/backtest-result.json",
        source_type="json",
        parser_type="freqtrade_json",
        raw_data=raw_data,
    )


def make_stdout_payload(raw_text):
    """Build a stdout fallback payload for parser tests."""
    return RawBacktestPayload(
        source_path="/tmp/stdout.log",
        source_type="stdout_log",
        parser_type="stdout_table_fallback",
        raw_text=raw_text,
    )


def test_parse_pair_results_from_json():
    """Parser extracts direct Freqtrade-style pair summary rows."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "results_per_pair": [
                        {
                            "key": "BTC/USDT",
                            "trades": 3,
                            "profit_total_abs": 12.0,
                            "profit_total": 2.4,
                            "profit_factor": 1.8,
                            "wins": 2,
                            "draws": 0,
                            "losses": 1,
                            "avg_duration": "0:35:00",
                        },
                        {
                            "key": "TOTAL",
                            "trades": 3,
                            "profit_total_abs": 12.0,
                        },
                    ],
                    "total_trades": 3,
                    "wins": 2,
                    "losses": 1,
                    "draws": 0,
                }
            }
        }
    )

    result = BacktestPairTradeParser().parse(payload)

    assert result.success is True
    assert len(result.pair_results) == 1
    pair = result.pair_results[0]
    assert pair.pair == "BTC/USDT"
    assert pair.trade_count == 3
    assert pair.net_profit == 12.0
    assert pair.net_profit_pct == 2.4
    assert pair.profit_factor == 1.8
    assert pair.win_rate == pytest.approx(2 / 3)
    assert result.trade_summary.total_trades == 3
    assert result.trade_summary.best_pair == "BTC/USDT"


def test_parse_pair_results_from_trade_list_grouped_by_pair():
    """Parser groups trade-level rows by pair when pair summaries are absent."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "trades": [
                        {"pair": "BTC/USDT", "profit_abs": 10.0},
                        {"pair": "BTC/USDT", "profit_abs": -4.0},
                        {"pair": "ETH/USDT", "profit_abs": 2.0},
                    ]
                }
            }
        }
    )

    result = BacktestPairTradeParser().parse(payload)
    pairs = {pair.pair: pair for pair in result.pair_results}

    assert result.success is True
    assert pairs["BTC/USDT"].trade_count == 2
    assert pairs["BTC/USDT"].net_profit == 6.0
    assert pairs["BTC/USDT"].expectancy == 3.0
    assert pairs["ETH/USDT"].trade_count == 1
    assert pairs["ETH/USDT"].net_profit == 2.0
    assert result.trade_summary.total_trades == 3
    assert result.trade_summary.wins == 2
    assert result.trade_summary.losses == 1
    assert result.trade_summary.draws == 0


def test_parse_stdout_report_table():
    """Parser extracts pair rows from a simple stdout BACKTESTING REPORT table."""
    payload = make_stdout_payload(
        """
        BACKTESTING REPORT
        | Pair | Trades | Profit Abs | Profit % | Wins | Draws | Losses | Avg Duration |
        | BTC/USDT | 2 | 6.0 | 1.2 | 1 | 0 | 1 | 0:30:00 |
        | ETH/USDT | 1 | 2.0 | 0.5 | 1 | 0 | 0 | 0:15:00 |
        | TOTAL | 3 | 8.0 | 1.7 | 2 | 0 | 1 | 0:25:00 |
        """
    )

    result = BacktestPairTradeParser().parse(payload)

    assert result.success is True
    assert len(result.pair_results) == 2
    assert result.pair_results[0].pair == "BTC/USDT"
    assert result.trade_summary.total_trades == 3
    assert result.trade_summary.best_pair == "BTC/USDT"
    assert result.trade_summary.worst_pair == "ETH/USDT"
    assert "stdout_fallback_lower_quality" in result.warnings


def test_extract_best_worst_pair():
    """Best/worst pair selection uses net profit first."""
    parser = BacktestPairTradeParser()
    pair_results = parser.parse_pair_results_from_json(
        {
            "results_per_pair": [
                {"pair": "BTC/USDT", "trades": 2, "profit_total_abs": 4.0},
                {"pair": "ETH/USDT", "trades": 2, "profit_total_abs": -3.0},
                {"pair": "SOL/USDT", "trades": 2, "profit_total_abs": 9.0},
            ]
        }
    )

    best, worst = parser.find_best_worst_pair(pair_results)

    assert best == "SOL/USDT"
    assert worst == "ETH/USDT"


def test_detect_no_trades():
    """No-trade results return warning without acceptance/rejection decision."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "results_per_pair": [
                        {"pair": "BTC/USDT", "trades": 0, "profit_total_abs": 0.0}
                    ],
                    "total_trades": 0,
                    "wins": 0,
                    "losses": 0,
                    "draws": 0,
                }
            }
        }
    )

    result = BacktestPairTradeParser().parse(payload)
    result_text = result.model_dump_json()

    assert result.success is True
    assert "no_trades_detected" in result.warnings
    assert "approved" not in result_text.lower()
    assert "rejected" not in result_text.lower()
    assert "profitable" not in result_text.lower()


def test_trade_summary_totals():
    """Trade summary totals are extracted from structured summary fields."""
    payload = make_json_payload(
        {
            "strategy": {
                "HERSmokeStrategy": {
                    "total_trades": 10,
                    "wins": 6,
                    "losses": 3,
                    "draws": 1,
                    "avg_duration": "1:05:00",
                    "results_per_pair": [
                        {"pair": "BTC/USDT", "trades": 10, "profit_total_abs": 1.0}
                    ],
                }
            }
        }
    )

    summary = BacktestPairTradeParser().parse(payload).trade_summary

    assert summary.total_trades == 10
    assert summary.wins == 6
    assert summary.losses == 3
    assert summary.draws == 1
    assert summary.avg_duration == "1:05:00"


def test_missing_pair_data_does_not_crash():
    """Unknown JSON shapes produce controlled empty results."""
    payload = make_json_payload({"metadata": {"freqtrade_version": "2026.5.1"}})

    result = BacktestPairTradeParser().parse(payload)

    assert result.success is False
    assert result.pair_results == []
    assert result.trade_summary is not None
    assert "no_pair_results_found" in result.warnings


def test_expectancy_per_pair_when_trades_available():
    """Per-pair expectancy is calculated from grouped trade profits."""
    payload = make_json_payload(
        {
            "trades": [
                {"pair": "BTC/USDT", "profit_abs": 8.0},
                {"pair": "BTC/USDT", "profit_abs": -2.0},
                {"pair": "BTC/USDT", "profit_abs": 0.0},
            ]
        }
    )

    result = BacktestPairTradeParser().parse(payload)

    assert result.pair_results[0].pair == "BTC/USDT"
    assert result.pair_results[0].expectancy == 2.0
    assert result.pair_results[0].wins == 1
    assert result.pair_results[0].losses == 1
    assert result.pair_results[0].draws == 1
