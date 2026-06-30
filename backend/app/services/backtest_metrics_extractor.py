"""
Backtest metrics extractor.

This module extracts normalized metrics from raw Freqtrade payloads. It does not
approve, reject, classify, or make profitability claims about strategies.
"""
from __future__ import annotations

import re
from typing import Any, Optional

from app.schemas.backtest_results import (
    ExpectancyBreakdown,
    ExtractedBacktestMetrics,
    MetricsExtractionResult,
    RawBacktestPayload,
)


class BacktestMetricsExtractor:
    """Extract normalized metrics and expectancy from raw backtest payloads."""

    TOTAL_PROFIT_KEYS = (
        "profit_total_abs",
        "total_profit_abs",
        "total_profit",
        "profit_total",
        "net_profit",
        "absolute_profit",
    )
    TOTAL_PROFIT_PCT_KEYS = (
        "profit_total",
        "profit_total_pct",
        "total_profit_pct",
        "profit_total_percent",
        "net_profit_pct",
        "profit_ratio",
    )
    PROFIT_FACTOR_KEYS = ("profit_factor", "profitfactor")
    MAX_DRAWDOWN_KEYS = (
        "max_drawdown_abs",
        "max_drawdown",
        "max_drawdown_account",
        "drawdown",
    )
    MAX_DRAWDOWN_PCT_KEYS = (
        "max_drawdown_pct",
        "max_drawdown_percent",
        "max_relative_drawdown",
        "drawdown_pct",
    )
    SHARPE_KEYS = ("sharpe", "sharpe_ratio")
    CALMAR_KEYS = ("calmar", "calmar_ratio")
    WIN_RATE_KEYS = ("win_rate", "winrate", "wins_percent", "winning_percent")
    TRADE_COUNT_KEYS = ("total_trades", "trade_count", "trades", "total_count")
    WINS_KEYS = ("wins", "winning_trades", "wins_count")
    LOSSES_KEYS = ("losses", "losing_trades", "losses_count")
    DRAWS_KEYS = ("draws", "draw_trades", "draws_count")
    AVG_WIN_KEYS = ("avg_win", "average_win", "winning_avg", "avg_profit_win")
    AVG_LOSS_KEYS = ("avg_loss", "average_loss", "losing_avg", "avg_profit_loss")
    AVG_DURATION_KEYS = ("avg_duration", "average_duration", "holding_avg")
    BEST_PAIR_KEYS = ("best_pair", "best_pair_name")
    WORST_PAIR_KEYS = ("worst_pair", "worst_pair_name")
    TRADE_LIST_KEYS = ("trades", "closed_trades", "trade_list")
    TRADE_PROFIT_KEYS = (
        "profit_abs",
        "profit_amount",
        "close_profit_abs",
        "profit",
        "profit_ratio",
        "profit_pct",
    )

    def extract(self, payload: RawBacktestPayload) -> MetricsExtractionResult:
        """Extract metrics from one raw payload."""
        warnings = list(payload.warnings)
        errors = list(payload.errors)

        if payload.raw_data is not None:
            try:
                metrics = self.extract_from_freqtrade_json(payload.raw_data)
                metrics.source_type = payload.source_type
                warnings.extend(metrics.warnings)
                errors.extend(metrics.errors)
                expectancy = self._breakdown_from_metrics(metrics)
                return MetricsExtractionResult(
                    success=not errors and self._has_any_metric(metrics),
                    metrics=metrics,
                    expectancy=expectancy,
                    warnings=self._unique_strings(warnings),
                    errors=self._unique_strings(errors),
                )
            except Exception as exc:
                errors.append(f"metrics_extraction_error: {exc}")

        if payload.raw_text is not None and payload.parser_type == "stdout_table_fallback":
            try:
                metrics = self.extract_from_stdout_text(payload.raw_text)
                metrics.source_type = payload.source_type
                warnings.extend(metrics.warnings)
                errors.extend(metrics.errors)
                expectancy = self._breakdown_from_metrics(metrics)
                return MetricsExtractionResult(
                    success=not errors and self._has_any_metric(metrics),
                    metrics=metrics,
                    expectancy=expectancy,
                    warnings=self._unique_strings(warnings),
                    errors=self._unique_strings(errors),
                )
            except Exception as exc:
                errors.append(f"stdout_metrics_extraction_error: {exc}")

        if payload.raw_data is None and payload.raw_text is None:
            warnings.append("payload_has_no_raw_data")

        metrics = ExtractedBacktestMetrics(
            source_type=payload.source_type,
            raw_metrics={},
            expectancy_source="not_available",
            warnings=["no_metrics_extracted"],
            errors=errors,
        )
        return MetricsExtractionResult(
            success=False,
            metrics=metrics,
            expectancy=None,
            warnings=self._unique_strings(warnings + metrics.warnings),
            errors=self._unique_strings(errors),
        )

    def extract_from_freqtrade_json(self, raw_data: dict) -> ExtractedBacktestMetrics:
        """Extract normalized metrics from a Freqtrade JSON object."""
        warnings: list[str] = []
        if not isinstance(raw_data, dict):
            return ExtractedBacktestMetrics(
                source_type="json",
                raw_metrics={},
                expectancy_source="not_available",
                errors=["raw_data_must_be_object"],
            )

        summary = self._select_summary_container(raw_data)
        trades = self._find_trade_list(raw_data)
        expectancy_breakdown = self.calculate_expectancy_from_trades(trades)

        wins = expectancy_breakdown.trade_count and self._count_trade_outcomes(trades)["wins"]
        losses = expectancy_breakdown.trade_count and self._count_trade_outcomes(trades)["losses"]
        draws = expectancy_breakdown.trade_count and self._count_trade_outcomes(trades)["draws"]

        if expectancy_breakdown.expectancy is None:
            wins = self.safe_int(self.find_possible_keys(summary, self.WINS_KEYS))
            losses = self.safe_int(self.find_possible_keys(summary, self.LOSSES_KEYS))
            draws = self.safe_int(self.find_possible_keys(summary, self.DRAWS_KEYS))
            avg_win = self.safe_float(self.find_possible_keys(summary, self.AVG_WIN_KEYS))
            avg_loss = self.safe_float(self.find_possible_keys(summary, self.AVG_LOSS_KEYS))
            summary_breakdown = self.calculate_expectancy_from_summary(wins, losses, avg_win, avg_loss)
            expectancy_breakdown = summary_breakdown
        else:
            avg_win = expectancy_breakdown.avg_win
            avg_loss = expectancy_breakdown.avg_loss

        trade_count = (
            expectancy_breakdown.trade_count
            or self.safe_int(self.find_possible_keys(summary, self.TRADE_COUNT_KEYS))
        )
        win_rate = (
            expectancy_breakdown.win_rate
            if expectancy_breakdown.win_rate is not None
            else self._normalize_rate(self.safe_float(self.find_possible_keys(summary, self.WIN_RATE_KEYS)))
        )

        if trade_count is None:
            warnings.append("trade_count_missing")
        if expectancy_breakdown.expectancy is None:
            warnings.extend(expectancy_breakdown.warnings)

        metrics = ExtractedBacktestMetrics(
            net_profit=self.safe_float(self.find_possible_keys(summary, self.TOTAL_PROFIT_KEYS)),
            net_profit_pct=self._normalize_percent_value(
                self.safe_float(self.find_possible_keys(summary, self.TOTAL_PROFIT_PCT_KEYS))
            ),
            profit_factor=self.safe_float(self.find_possible_keys(summary, self.PROFIT_FACTOR_KEYS)),
            max_drawdown=self.safe_float(self.find_possible_keys(summary, self.MAX_DRAWDOWN_KEYS)),
            max_drawdown_pct=self._normalize_percent_value(
                self.safe_float(self.find_possible_keys(summary, self.MAX_DRAWDOWN_PCT_KEYS))
            ),
            sharpe=self.safe_float(self.find_possible_keys(summary, self.SHARPE_KEYS)),
            calmar=self.safe_float(self.find_possible_keys(summary, self.CALMAR_KEYS)),
            win_rate=win_rate,
            trade_count=trade_count,
            wins=wins if isinstance(wins, int) else self.safe_int(self.find_possible_keys(summary, self.WINS_KEYS)),
            losses=losses if isinstance(losses, int) else self.safe_int(self.find_possible_keys(summary, self.LOSSES_KEYS)),
            draws=draws if isinstance(draws, int) else self.safe_int(self.find_possible_keys(summary, self.DRAWS_KEYS)),
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=expectancy_breakdown.expectancy,
            expectancy_source=expectancy_breakdown.method,
            avg_duration=self._safe_str(self.find_possible_keys(summary, self.AVG_DURATION_KEYS)),
            best_pair=self._safe_str(self.find_possible_keys(summary, self.BEST_PAIR_KEYS)),
            worst_pair=self._safe_str(self.find_possible_keys(summary, self.WORST_PAIR_KEYS)),
            source_type="json",
            raw_metrics=summary if isinstance(summary, dict) else raw_data,
            warnings=self._unique_strings(warnings),
        )

        if metrics.profit_factor is None:
            metrics.warnings.append("profit_factor_missing")
        if metrics.expectancy is None:
            metrics.expectancy_source = "not_available"
        return metrics

    def extract_from_stdout_text(self, raw_text: str) -> ExtractedBacktestMetrics:
        """Extract a limited metric set from stdout fallback text."""
        warnings = ["stdout_fallback_lower_quality"]
        lines = raw_text.splitlines()
        parsed: dict[str, Any] = {}

        patterns = {
            "net_profit": r"(?:total\s+profit|net\s+profit)\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "profit_factor": r"profit\s+factor\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "max_drawdown": r"max\s+drawdown\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "sharpe": r"sharpe\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "calmar": r"calmar\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "win_rate": r"(?:win\s*rate|win%)\s*[:|]\s*([-+]?\d+(?:\.\d+)?)\s*%?",
            "trade_count": r"(?:total\s+trades|trades)\s*[:|]\s*(\d+)",
            "wins": r"wins\s*[:|]\s*(\d+)",
            "losses": r"losses\s*[:|]\s*(\d+)",
            "draws": r"draws\s*[:|]\s*(\d+)",
            "avg_win": r"(?:avg\s+win|average\s+win)\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
            "avg_loss": r"(?:avg\s+loss|average\s+loss)\s*[:|]\s*([-+]?\d+(?:\.\d+)?)",
        }

        text = "\n".join(lines)
        for key, pattern in patterns.items():
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                parsed[key] = match.group(1)

        wins = self.safe_int(parsed.get("wins"))
        losses = self.safe_int(parsed.get("losses"))
        avg_win = self.safe_float(parsed.get("avg_win"))
        avg_loss = self.safe_float(parsed.get("avg_loss"))
        breakdown = self.calculate_expectancy_from_summary(wins, losses, avg_win, avg_loss)
        warnings.extend(breakdown.warnings)

        return ExtractedBacktestMetrics(
            net_profit=self.safe_float(parsed.get("net_profit")),
            profit_factor=self.safe_float(parsed.get("profit_factor")),
            max_drawdown=self.safe_float(parsed.get("max_drawdown")),
            sharpe=self.safe_float(parsed.get("sharpe")),
            calmar=self.safe_float(parsed.get("calmar")),
            win_rate=self._normalize_rate(self.safe_float(parsed.get("win_rate"))),
            trade_count=self.safe_int(parsed.get("trade_count")) or breakdown.trade_count,
            wins=wins,
            losses=losses,
            draws=self.safe_int(parsed.get("draws")),
            avg_win=avg_win,
            avg_loss=avg_loss,
            expectancy=breakdown.expectancy,
            expectancy_source="stdout_fallback" if breakdown.expectancy is not None else "not_available",
            source_type="stdout_log",
            raw_metrics=parsed,
            warnings=self._unique_strings(warnings),
        )

    def calculate_expectancy_from_trades(self, trades: Any) -> ExpectancyBreakdown:
        """Calculate expectancy as average trade profit from trade-level data."""
        if not isinstance(trades, list) or not trades:
            return ExpectancyBreakdown(
                method="not_available",
                warnings=["trade_level_data_missing"],
            )

        profits = []
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            profit = self.safe_float(self.find_possible_keys(trade, self.TRADE_PROFIT_KEYS))
            if profit is not None:
                profits.append(profit)

        if not profits:
            return ExpectancyBreakdown(
                method="not_available",
                warnings=["trade_profit_values_missing"],
            )

        wins = [value for value in profits if value > 0]
        losses = [value for value in profits if value < 0]
        trade_count = len(profits)
        total_profit = sum(profits)
        win_rate = len(wins) / trade_count if trade_count else None
        loss_rate = len(losses) / trade_count if trade_count else None
        avg_win = sum(wins) / len(wins) if wins else None
        avg_loss = sum(losses) / len(losses) if losses else None

        return ExpectancyBreakdown(
            expectancy=total_profit / trade_count if trade_count else None,
            method="trade_level",
            trade_count=trade_count,
            win_rate=win_rate,
            loss_rate=loss_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_profit=total_profit,
        )

    def calculate_expectancy_from_summary(
        self,
        wins: Optional[int],
        losses: Optional[int],
        avg_win: Optional[float],
        avg_loss: Optional[float],
    ) -> ExpectancyBreakdown:
        """Calculate expectancy from summary-level win/loss data."""
        warnings: list[str] = []
        if wins is None or losses is None:
            warnings.append("summary_win_loss_counts_missing")
        if avg_win is None or avg_loss is None:
            warnings.append("summary_average_win_loss_missing")
        if warnings:
            return ExpectancyBreakdown(method="not_available", warnings=warnings)

        trade_count = wins + losses
        if trade_count <= 0:
            return ExpectancyBreakdown(
                method="not_available",
                trade_count=trade_count,
                warnings=["summary_trade_count_zero"],
            )

        win_rate = wins / trade_count
        loss_rate = losses / trade_count
        expectancy = (win_rate * avg_win) - (loss_rate * abs(avg_loss))

        return ExpectancyBreakdown(
            expectancy=expectancy,
            method="summary_level",
            trade_count=trade_count,
            win_rate=win_rate,
            loss_rate=loss_rate,
            avg_win=avg_win,
            avg_loss=avg_loss,
            total_profit=expectancy * trade_count,
        )

    def safe_float(self, value: Any) -> Optional[float]:
        """Convert a value to float safely."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            cleaned = cleaned.rstrip("%")
            if not cleaned:
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    def safe_int(self, value: Any) -> Optional[int]:
        """Convert a value to int safely."""
        if value is None or isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            cleaned = value.strip().replace(",", "")
            if not cleaned:
                return None
            try:
                return int(float(cleaned))
            except ValueError:
                return None
        return None

    def find_possible_keys(self, raw_data: Any, candidates: tuple[str, ...] | list[str]) -> Any:
        """Find the first value matching candidate keys in nested data."""
        if isinstance(raw_data, dict):
            lower_map = {str(key).lower(): value for key, value in raw_data.items()}
            for candidate in candidates:
                if candidate.lower() in lower_map:
                    return lower_map[candidate.lower()]
            for value in raw_data.values():
                found = self.find_possible_keys(value, candidates)
                if found is not None:
                    return found
        elif isinstance(raw_data, list):
            for value in raw_data:
                found = self.find_possible_keys(value, candidates)
                if found is not None:
                    return found
        return None

    def _select_summary_container(self, raw_data: dict) -> dict:
        """Select the most likely aggregate strategy summary object."""
        strategy = raw_data.get("strategy")
        if isinstance(strategy, dict):
            if any(key in {str(item).lower() for item in strategy.keys()} for key in self.PROFIT_FACTOR_KEYS):
                return strategy
            for value in strategy.values():
                if isinstance(value, dict):
                    return value
        if isinstance(raw_data.get("strategy_comparison"), list) and raw_data["strategy_comparison"]:
            first = raw_data["strategy_comparison"][0]
            if isinstance(first, dict):
                return first
        return raw_data

    def _find_trade_list(self, raw_data: dict) -> Optional[list]:
        """Find a likely trade-level result list."""
        for value in self._find_values_for_keys(raw_data, self.TRADE_LIST_KEYS):
            if isinstance(value, list) and self._looks_like_trade_list(value):
                return value
        return None

    def _find_values_for_keys(self, raw_data: Any, candidates: tuple[str, ...] | list[str]) -> list[Any]:
        """Find all values matching candidate keys in nested data."""
        values: list[Any] = []
        if isinstance(raw_data, dict):
            for key, value in raw_data.items():
                if str(key).lower() in {candidate.lower() for candidate in candidates}:
                    values.append(value)
                values.extend(self._find_values_for_keys(value, candidates))
        elif isinstance(raw_data, list):
            for value in raw_data:
                values.extend(self._find_values_for_keys(value, candidates))
        return values

    def _looks_like_trade_list(self, values: list) -> bool:
        """Return whether a list appears to contain trade dictionaries."""
        return any(
            isinstance(item, dict)
            and self.find_possible_keys(item, self.TRADE_PROFIT_KEYS) is not None
            for item in values
        )

    def _count_trade_outcomes(self, trades: Optional[list]) -> dict[str, int]:
        """Count wins, losses, and draws from trade-level profits."""
        counts = {"wins": 0, "losses": 0, "draws": 0}
        if not trades:
            return counts
        for trade in trades:
            if not isinstance(trade, dict):
                continue
            profit = self.safe_float(self.find_possible_keys(trade, self.TRADE_PROFIT_KEYS))
            if profit is None:
                continue
            if profit > 0:
                counts["wins"] += 1
            elif profit < 0:
                counts["losses"] += 1
            else:
                counts["draws"] += 1
        return counts

    def _breakdown_from_metrics(self, metrics: ExtractedBacktestMetrics) -> Optional[ExpectancyBreakdown]:
        """Build an expectancy breakdown from extracted metric fields."""
        if metrics.expectancy is None:
            return None
        trade_count = metrics.trade_count
        total_profit = metrics.expectancy * trade_count if trade_count else metrics.net_profit
        return ExpectancyBreakdown(
            expectancy=metrics.expectancy,
            method=metrics.expectancy_source or "not_available",
            trade_count=trade_count,
            win_rate=metrics.win_rate,
            loss_rate=(1 - metrics.win_rate) if metrics.win_rate is not None else None,
            avg_win=metrics.avg_win,
            avg_loss=metrics.avg_loss,
            total_profit=total_profit,
        )

    @staticmethod
    def _normalize_rate(value: Optional[float]) -> Optional[float]:
        """Normalize percentage-like win rates to fractions."""
        if value is None:
            return None
        if abs(value) > 1:
            return value / 100
        return value

    @staticmethod
    def _normalize_percent_value(value: Optional[float]) -> Optional[float]:
        """Return percent fields as provided, converting tiny ratios to percent."""
        if value is None:
            return None
        if -1 < value < 1 and value != 0:
            return value * 100
        return value

    @staticmethod
    def _safe_str(value: Any) -> Optional[str]:
        """Convert a scalar value to a non-empty string."""
        if value is None or isinstance(value, (dict, list)):
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _has_any_metric(metrics: ExtractedBacktestMetrics) -> bool:
        """Return whether any normalized metric was extracted."""
        fields = (
            metrics.net_profit,
            metrics.net_profit_pct,
            metrics.profit_factor,
            metrics.max_drawdown,
            metrics.max_drawdown_pct,
            metrics.sharpe,
            metrics.calmar,
            metrics.win_rate,
            metrics.trade_count,
            metrics.expectancy,
        )
        return any(value is not None for value in fields)

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
