"""
Pair-level result and trade summary parser.

This parser extracts pair evidence and aggregate trade summaries. It does not
approve, reject, classify, or make profitability claims about strategies.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Optional

from app.schemas.backtest_results import (
    ExtractedPairResult,
    ExtractedTradeSummary,
    PairTradeParseResult,
    RawBacktestPayload,
)
from app.services.backtest_metrics_extractor import BacktestMetricsExtractor


class BacktestPairTradeParser:
    """Parse pair-level results and trade summaries from raw backtest payloads."""

    PAIR_KEYS = ("pair", "key", "pair_name", "symbol")
    PAIR_LIST_KEYS = (
        "results_per_pair",
        "pair_results",
        "pair_summary",
        "pairs",
        "results_by_pair",
    )
    TRADE_LIST_KEYS = ("trades", "closed_trades", "trade_list")
    PROFIT_KEYS = (
        "profit_abs",
        "profit_amount",
        "close_profit_abs",
        "profit",
        "profit_total_abs",
        "total_profit_abs",
        "net_profit",
    )
    PROFIT_PCT_KEYS = (
        "profit_pct",
        "profit_ratio",
        "profit_total",
        "profit_total_pct",
        "net_profit_pct",
    )
    PROFIT_FACTOR_KEYS = ("profit_factor", "profitfactor")
    DRAWDOWN_KEYS = ("max_drawdown_abs", "max_drawdown", "drawdown")
    TRADE_COUNT_KEYS = ("total_trades", "trade_count", "trades", "total_count")
    WINS_KEYS = ("wins", "winning_trades", "wins_count")
    LOSSES_KEYS = ("losses", "losing_trades", "losses_count")
    DRAWS_KEYS = ("draws", "draw_trades", "draws_count")
    WIN_RATE_KEYS = ("win_rate", "winrate", "wins_percent", "winning_percent")
    AVG_DURATION_KEYS = ("avg_duration", "average_duration", "holding_avg", "duration_avg")
    AVG_WIN_KEYS = ("avg_win", "average_win", "winning_avg", "avg_profit_win")
    AVG_LOSS_KEYS = ("avg_loss", "average_loss", "losing_avg", "avg_profit_loss")

    def __init__(self) -> None:
        self.metrics = BacktestMetricsExtractor()

    def parse(self, payload: RawBacktestPayload) -> PairTradeParseResult:
        """Parse pair results and trade summary from one raw payload."""
        warnings = list(payload.warnings)
        errors = list(payload.errors)

        if payload.raw_data is not None:
            try:
                pair_results = self.parse_pair_results_from_json(payload.raw_data)
                trade_summary = self.parse_trade_summary_from_json(payload.raw_data)
                warnings.extend(self._collect_pair_warnings(pair_results))
                warnings.extend(trade_summary.warnings)
                if self._summary_trade_count(trade_summary, pair_results) == 0:
                    warnings.append("no_trades_detected")
                return PairTradeParseResult(
                    success=bool(pair_results) or self._summary_has_data(trade_summary),
                    pair_results=pair_results,
                    trade_summary=trade_summary,
                    warnings=self._unique_strings(warnings),
                    errors=self._unique_strings(errors),
                )
            except Exception as exc:
                errors.append(f"pair_trade_parse_error: {exc}")

        if payload.raw_text is not None and payload.parser_type == "stdout_table_fallback":
            try:
                pair_results = self.parse_pair_results_from_stdout(payload.raw_text)
                trade_summary = self.parse_trade_summary_from_stdout(payload.raw_text)
                warnings.extend(["stdout_fallback_lower_quality"])
                warnings.extend(self._collect_pair_warnings(pair_results))
                warnings.extend(trade_summary.warnings)
                if self._summary_trade_count(trade_summary, pair_results) == 0:
                    warnings.append("no_trades_detected")
                return PairTradeParseResult(
                    success=bool(pair_results) or self._summary_has_data(trade_summary),
                    pair_results=pair_results,
                    trade_summary=trade_summary,
                    warnings=self._unique_strings(warnings),
                    errors=self._unique_strings(errors),
                )
            except Exception as exc:
                errors.append(f"stdout_pair_trade_parse_error: {exc}")

        if payload.raw_data is None and payload.raw_text is None:
            warnings.append("payload_has_no_raw_data")

        return PairTradeParseResult(
            success=False,
            pair_results=[],
            trade_summary=ExtractedTradeSummary(warnings=["no_trade_summary_data"]),
            warnings=self._unique_strings(warnings + ["no_pair_results_found"]),
            errors=self._unique_strings(errors),
        )

    def parse_pair_results_from_json(self, raw_data: dict) -> list[ExtractedPairResult]:
        """Parse pair results from structured Freqtrade JSON."""
        if not isinstance(raw_data, dict):
            return []

        pair_rows = self._find_pair_summary_rows(raw_data)
        if pair_rows:
            results = [self._pair_result_from_summary(row) for row in pair_rows]
            return [result for result in results if result.pair.upper() != "TOTAL"]

        trades = self._find_trade_list(raw_data)
        if trades:
            return self._pair_results_from_trades(trades)

        return []

    def parse_trade_summary_from_json(self, raw_data: dict) -> ExtractedTradeSummary:
        """Parse aggregate trade summary from structured Freqtrade JSON."""
        if not isinstance(raw_data, dict):
            return ExtractedTradeSummary(warnings=["raw_data_must_be_object"])

        summary = self._select_summary_container(raw_data)
        trades = self._find_trade_list(raw_data)
        pair_results = self.parse_pair_results_from_json(raw_data)

        if trades:
            counts = self._count_trade_outcomes(trades)
            total_trades = counts["wins"] + counts["losses"] + counts["draws"]
        else:
            total_trades = self.metrics.safe_int(self.metrics.find_possible_keys(summary, self.TRADE_COUNT_KEYS))
            counts = {
                "wins": self.metrics.safe_int(self.metrics.find_possible_keys(summary, self.WINS_KEYS)),
                "losses": self.metrics.safe_int(self.metrics.find_possible_keys(summary, self.LOSSES_KEYS)),
                "draws": self.metrics.safe_int(self.metrics.find_possible_keys(summary, self.DRAWS_KEYS)),
            }

        best_pair, worst_pair = self.find_best_worst_pair(pair_results)
        warnings: list[str] = []
        if total_trades == 0:
            warnings.append("no_trades_detected")
        if not pair_results:
            warnings.append("no_pair_results_found")

        return ExtractedTradeSummary(
            total_trades=total_trades,
            wins=counts["wins"],
            losses=counts["losses"],
            draws=counts["draws"],
            avg_duration=self._safe_str(self.metrics.find_possible_keys(summary, self.AVG_DURATION_KEYS)),
            best_pair=best_pair,
            worst_pair=worst_pair,
            raw_json=summary if isinstance(summary, dict) else {},
            warnings=self._unique_strings(warnings),
        )

    def parse_pair_results_from_stdout(self, raw_text: str) -> list[ExtractedPairResult]:
        """Parse a simple Freqtrade stdout BACKTESTING REPORT table."""
        rows = self._parse_stdout_table_rows(raw_text)
        results: list[ExtractedPairResult] = []
        for row in rows:
            pair = row.get("pair") or row.get("Pair")
            if not pair or pair.upper() == "TOTAL":
                continue

            result = ExtractedPairResult(
                pair=pair,
                trade_count=self.metrics.safe_int(row.get("trades") or row.get("Trades")),
                net_profit=self.metrics.safe_float(
                    row.get("profit abs")
                    or row.get("profit")
                    or row.get("tot profit")
                    or row.get("total profit")
                ),
                net_profit_pct=self._normalize_percent(
                    self.metrics.safe_float(
                        row.get("profit %")
                        or row.get("profit pct")
                        or row.get("profit pct %")
                    )
                ),
                wins=self.metrics.safe_int(row.get("wins") or row.get("Wins")),
                draws=self.metrics.safe_int(row.get("draws") or row.get("Draws")),
                losses=self.metrics.safe_int(row.get("losses") or row.get("Losses")),
                avg_duration=row.get("avg duration") or row.get("Avg Duration"),
                raw_json=dict(row),
                warnings=["stdout_pair_fallback"],
            )
            result.expectancy = self.calculate_pair_expectancy(result.model_dump())
            result.win_rate = self._win_rate(result.wins, result.losses, result.draws)
            results.append(result)
        return results

    def parse_trade_summary_from_stdout(self, raw_text: str) -> ExtractedTradeSummary:
        """Parse aggregate trade summary from stdout fallback text."""
        rows = self._parse_stdout_table_rows(raw_text)
        pair_results = self.parse_pair_results_from_stdout(raw_text)
        total_row = next((row for row in rows if str(row.get("pair", "")).upper() == "TOTAL"), {})

        if total_row:
            total_trades = self.metrics.safe_int(total_row.get("trades"))
            wins = self.metrics.safe_int(total_row.get("wins"))
            losses = self.metrics.safe_int(total_row.get("losses"))
            draws = self.metrics.safe_int(total_row.get("draws"))
            avg_duration = total_row.get("avg duration")
        else:
            total_trades = sum(result.trade_count or 0 for result in pair_results) if pair_results else None
            wins = sum(result.wins or 0 for result in pair_results) if pair_results else None
            losses = sum(result.losses or 0 for result in pair_results) if pair_results else None
            draws = sum(result.draws or 0 for result in pair_results) if pair_results else None
            avg_duration = None

        best_pair, worst_pair = self.find_best_worst_pair(pair_results)
        warnings = ["stdout_summary_fallback"]
        if total_trades == 0:
            warnings.append("no_trades_detected")
        if not pair_results:
            warnings.append("no_pair_results_found")

        return ExtractedTradeSummary(
            total_trades=total_trades,
            wins=wins,
            losses=losses,
            draws=draws,
            avg_duration=avg_duration,
            best_pair=best_pair,
            worst_pair=worst_pair,
            raw_json=total_row,
            warnings=self._unique_strings(warnings),
        )

    def calculate_pair_expectancy(self, pair_trades_or_summary: Any) -> Optional[float]:
        """Calculate pair expectancy from trade rows or summary data."""
        if isinstance(pair_trades_or_summary, list):
            profits = [
                self.metrics.safe_float(self.metrics.find_possible_keys(trade, self.PROFIT_KEYS))
                for trade in pair_trades_or_summary
                if isinstance(trade, dict)
            ]
            profits = [profit for profit in profits if profit is not None]
            if profits:
                return sum(profits) / len(profits)
            return None

        if isinstance(pair_trades_or_summary, dict):
            net_profit = self.metrics.safe_float(
                self.metrics.find_possible_keys(pair_trades_or_summary, self.PROFIT_KEYS + ("net_profit",))
            )
            trade_count = self.metrics.safe_int(
                self.metrics.find_possible_keys(pair_trades_or_summary, self.TRADE_COUNT_KEYS)
            )
            if net_profit is not None and trade_count and trade_count > 0:
                return net_profit / trade_count

            wins = self.metrics.safe_int(self.metrics.find_possible_keys(pair_trades_or_summary, self.WINS_KEYS))
            losses = self.metrics.safe_int(self.metrics.find_possible_keys(pair_trades_or_summary, self.LOSSES_KEYS))
            avg_win = self.metrics.safe_float(self.metrics.find_possible_keys(pair_trades_or_summary, self.AVG_WIN_KEYS))
            avg_loss = self.metrics.safe_float(self.metrics.find_possible_keys(pair_trades_or_summary, self.AVG_LOSS_KEYS))
            breakdown = self.metrics.calculate_expectancy_from_summary(wins, losses, avg_win, avg_loss)
            return breakdown.expectancy

        return None

    def find_best_worst_pair(
        self,
        pair_results: list[ExtractedPairResult],
    ) -> tuple[Optional[str], Optional[str]]:
        """Return best/worst pair by net profit, falling back to percent profit."""
        if not pair_results:
            return None, None

        profit_pairs = [pair for pair in pair_results if pair.net_profit is not None]
        if profit_pairs:
            best = max(profit_pairs, key=lambda pair: pair.net_profit)
            worst = min(profit_pairs, key=lambda pair: pair.net_profit)
            return best.pair, worst.pair

        pct_pairs = [pair for pair in pair_results if pair.net_profit_pct is not None]
        if pct_pairs:
            best = max(pct_pairs, key=lambda pair: pair.net_profit_pct)
            worst = min(pct_pairs, key=lambda pair: pair.net_profit_pct)
            return best.pair, worst.pair

        return None, None

    def _pair_result_from_summary(self, row: dict) -> ExtractedPairResult:
        """Build a pair result from a pair summary row."""
        pair = self._safe_str(self.metrics.find_possible_keys(row, self.PAIR_KEYS)) or "unknown"
        trade_count = self.metrics.safe_int(self.metrics.find_possible_keys(row, self.TRADE_COUNT_KEYS))
        wins = self.metrics.safe_int(self.metrics.find_possible_keys(row, self.WINS_KEYS))
        losses = self.metrics.safe_int(self.metrics.find_possible_keys(row, self.LOSSES_KEYS))
        draws = self.metrics.safe_int(self.metrics.find_possible_keys(row, self.DRAWS_KEYS))
        warnings: list[str] = []
        if trade_count == 0:
            warnings.append("no_trades_detected")

        return ExtractedPairResult(
            pair=pair,
            trade_count=trade_count,
            net_profit=self.metrics.safe_float(self.metrics.find_possible_keys(row, self.PROFIT_KEYS)),
            net_profit_pct=self._normalize_percent(self.metrics.safe_float(self.metrics.find_possible_keys(row, self.PROFIT_PCT_KEYS))),
            profit_factor=self.metrics.safe_float(self.metrics.find_possible_keys(row, self.PROFIT_FACTOR_KEYS)),
            max_drawdown=self.metrics.safe_float(self.metrics.find_possible_keys(row, self.DRAWDOWN_KEYS)),
            win_rate=self._normalize_rate(
                self.metrics.safe_float(self.metrics.find_possible_keys(row, self.WIN_RATE_KEYS))
            ) or self._win_rate(wins, losses, draws),
            wins=wins,
            losses=losses,
            draws=draws,
            expectancy=self.calculate_pair_expectancy(row),
            avg_duration=self._safe_str(self.metrics.find_possible_keys(row, self.AVG_DURATION_KEYS)),
            raw_json=row,
            warnings=warnings,
        )

    def _pair_results_from_trades(self, trades: list[dict]) -> list[ExtractedPairResult]:
        """Build pair results by grouping trade rows by pair."""
        grouped: dict[str, list[dict]] = defaultdict(list)
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            pair = self._safe_str(self.metrics.find_possible_keys(trade, self.PAIR_KEYS))
            if pair:
                grouped[pair].append(trade)

        results: list[ExtractedPairResult] = []
        for pair, pair_trades in grouped.items():
            profits = [
                self.metrics.safe_float(self.metrics.find_possible_keys(trade, self.PROFIT_KEYS))
                for trade in pair_trades
            ]
            profits = [profit for profit in profits if profit is not None]
            wins = len([profit for profit in profits if profit > 0])
            losses = len([profit for profit in profits if profit < 0])
            draws = len([profit for profit in profits if profit == 0])
            trade_count = len(profits)
            warnings = []
            if trade_count == 0:
                warnings.append("no_trades_detected")

            results.append(
                ExtractedPairResult(
                    pair=pair,
                    trade_count=trade_count,
                    net_profit=sum(profits) if profits else None,
                    wins=wins,
                    losses=losses,
                    draws=draws,
                    win_rate=self._win_rate(wins, losses, draws),
                    expectancy=(sum(profits) / trade_count) if trade_count else None,
                    raw_json={"trades": pair_trades},
                    warnings=warnings,
                )
            )

        return results

    def _find_pair_summary_rows(self, raw_data: dict) -> list[dict]:
        """Find pair summary row dictionaries in common Freqtrade shapes."""
        rows: list[dict] = []
        for value in self._find_values_for_keys(raw_data, self.PAIR_LIST_KEYS):
            if isinstance(value, list):
                rows.extend([item for item in value if isinstance(item, dict) and self._has_pair_key(item)])
            elif isinstance(value, dict):
                for key, item in value.items():
                    if isinstance(item, dict):
                        row = {"pair": key, **item}
                        if self._has_pair_key(row):
                            rows.append(row)
        return rows

    def _find_trade_list(self, raw_data: dict) -> Optional[list]:
        """Find a likely trade-level result list."""
        for value in self._find_values_for_keys(raw_data, self.TRADE_LIST_KEYS):
            if isinstance(value, list) and any(isinstance(item, dict) and self._has_pair_key(item) for item in value):
                return value
        return None

    def _select_summary_container(self, raw_data: dict) -> dict:
        """Select likely strategy summary container."""
        return self.metrics._select_summary_container(raw_data)

    def _parse_stdout_table_rows(self, raw_text: str) -> list[dict[str, str]]:
        """Parse pipe-delimited rows from stdout tables."""
        table_lines = [
            line.strip()
            for line in raw_text.splitlines()
            if "|" in line and not re.match(r"^[+\-|=\s]+$", line.strip())
        ]
        if len(table_lines) < 2:
            return []

        header = [cell.strip().lower() for cell in table_lines[0].strip("|").split("|")]
        rows: list[dict[str, str]] = []
        for line in table_lines[1:]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != len(header):
                continue
            row = dict(zip(header, cells))
            if row.get("pair") and row["pair"].lower() != "pair":
                rows.append(row)
        return rows

    def _count_trade_outcomes(self, trades: list[dict]) -> dict[str, int]:
        """Count wins/losses/draws from trade-level profits."""
        counts = {"wins": 0, "losses": 0, "draws": 0}
        for trade in trades:
            profit = self.metrics.safe_float(self.metrics.find_possible_keys(trade, self.PROFIT_KEYS))
            if profit is None:
                continue
            if profit > 0:
                counts["wins"] += 1
            elif profit < 0:
                counts["losses"] += 1
            else:
                counts["draws"] += 1
        return counts

    def _find_values_for_keys(self, raw_data: Any, candidates: tuple[str, ...]) -> list[Any]:
        """Find all values matching candidate keys in nested data."""
        values: list[Any] = []
        candidate_set = {candidate.lower() for candidate in candidates}
        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                if str(key).lower() in candidate_set:
                    values.append(value)
                values.extend(self._find_values_for_keys(value, candidates))
        elif isinstance(raw_data, list):
            for value in raw_data:
                values.extend(self._find_values_for_keys(value, candidates))
        return values

    def _has_pair_key(self, row: dict) -> bool:
        """Return whether a row contains a non-total pair identifier."""
        pair = self._safe_str(self.metrics.find_possible_keys(row, self.PAIR_KEYS))
        return bool(pair)

    def _summary_trade_count(
        self,
        trade_summary: ExtractedTradeSummary,
        pair_results: list[ExtractedPairResult],
    ) -> Optional[int]:
        """Return best known trade count for no-trade detection."""
        if trade_summary.total_trades is not None:
            return trade_summary.total_trades
        if pair_results:
            return sum(pair.trade_count or 0 for pair in pair_results)
        return None

    @staticmethod
    def _summary_has_data(summary: ExtractedTradeSummary) -> bool:
        """Return whether a trade summary has any extracted data."""
        return any(
            value is not None
            for value in (
                summary.total_trades,
                summary.wins,
                summary.losses,
                summary.draws,
                summary.avg_duration,
                summary.best_pair,
                summary.worst_pair,
            )
        )

    @staticmethod
    def _collect_pair_warnings(pair_results: list[ExtractedPairResult]) -> list[str]:
        """Collect warnings from pair results."""
        warnings: list[str] = []
        for result in pair_results:
            warnings.extend(result.warnings)
        if not pair_results:
            warnings.append("no_pair_results_found")
        return warnings

    @staticmethod
    def _normalize_rate(value: Optional[float]) -> Optional[float]:
        """Normalize percentage-like rates to fractions."""
        if value is None:
            return None
        if abs(value) > 1:
            return value / 100
        return value

    @staticmethod
    def _normalize_percent(value: Optional[float]) -> Optional[float]:
        """Normalize tiny ratio percentages to percent values."""
        if value is None:
            return None
        if -1 < value < 1 and value != 0:
            return value * 100
        return value

    @staticmethod
    def _win_rate(wins: Optional[int], losses: Optional[int], draws: Optional[int]) -> Optional[float]:
        """Calculate win rate from counts."""
        if wins is None:
            return None
        total = wins + (losses or 0) + (draws or 0)
        if total <= 0:
            return None
        return wins / total

    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        """Convert a scalar value to a non-empty string."""
        if value is None or isinstance(value, (dict, list)):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
