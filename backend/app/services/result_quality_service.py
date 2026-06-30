"""
Result quality flag service.

Quality flags describe parser completeness and data quality. They do not
approve, reject, classify, or make trading claims about strategies.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.backtest_results import (
    BacktestOutputDiscoveryResult,
    ExtractedBacktestMetrics,
    ExtractedPairResult,
    ExtractedTradeSummary,
    MetricsExtractionResult,
    PairTradeParseResult,
    RawBacktestLoadResult,
    ResultQualityFlag,
    ResultQualityReport,
)


class ResultQualityService:
    """Build quality reports for parsed backtest results."""

    BLOCKING_DECISION_FLAGS = {
        "no_trades",
        "missing_backtest_file",
        "missing_profit_factor",
        "missing_drawdown",
        "parse_error",
        "partial_parse",
    }

    def build_quality_report(
        self,
        metrics,
        pair_results,
        trade_summary,
        loader_result: Optional[RawBacktestLoadResult] = None,
        discovery_result: Optional[BacktestOutputDiscoveryResult] = None,
    ) -> ResultQualityReport:
        """Build a quality report from parsed metric, pair, and summary data."""
        metric_obj = self._coerce_metrics(metrics)
        pair_list = self._coerce_pair_results(pair_results)
        summary_obj = self._coerce_trade_summary(trade_summary, pair_results)

        warnings: list[str] = []
        errors: list[str] = []
        warnings.extend(self._extract_warnings(metrics))
        warnings.extend(self._extract_warnings(pair_results))
        warnings.extend(self._extract_warnings(trade_summary))
        warnings.extend(self._extract_warnings(loader_result))
        warnings.extend(self._extract_warnings(discovery_result))
        errors.extend(self._extract_errors(metrics))
        errors.extend(self._extract_errors(pair_results))
        errors.extend(self._extract_errors(trade_summary))
        errors.extend(self._extract_errors(loader_result))
        errors.extend(self._extract_errors(discovery_result))

        flags: list[ResultQualityFlag] = []
        for flag in (
            self.flag_missing_backtest_file(discovery_result),
            self.flag_stdout_only_parse(loader_result),
            self.flag_no_trades(metric_obj, summary_obj),
            self.flag_too_few_trades(metric_obj),
            self.flag_partial_parse(metric_obj, pair_list, summary_obj),
            self.flag_negative_expectancy(metric_obj),
            self.flag_high_drawdown(metric_obj),
            self.flag_single_pair_dependency(pair_list),
            self.flag_missing_pair_results(pair_list),
            self.flag_missing_profit_factor(metric_obj),
            self.flag_missing_drawdown(metric_obj),
        ):
            if flag:
                flags.append(flag)

        for warning in self._unique_strings(warnings):
            flags.append(
                ResultQualityFlag(
                    code="parse_warning",
                    severity="warning",
                    message="Parser warning was reported.",
                    details={"warning": warning},
                )
            )
        for error in self._unique_strings(errors):
            flags.append(
                ResultQualityFlag(
                    code="parse_error",
                    severity="error",
                    message="Parser error was reported.",
                    details={"error": error},
                )
            )

        flags = self._dedupe_flags(flags)
        is_usable_for_metrics = self._is_usable_for_metrics(metric_obj, pair_list)
        is_usable_for_decision = (
            is_usable_for_metrics
            and not any(flag.code in self.BLOCKING_DECISION_FLAGS for flag in flags)
        )

        return ResultQualityReport(
            run_id=self._extract_run_id(discovery_result),
            parse_quality=self._parse_quality(flags),
            flags=flags,
            warnings=self._unique_strings(warnings),
            errors=self._unique_strings(errors),
            is_usable_for_metrics=is_usable_for_metrics,
            is_usable_for_decision=is_usable_for_decision,
        )

    def flag_no_trades(self, metrics, trade_summary) -> Optional[ResultQualityFlag]:
        """Flag results with explicit zero trades."""
        trade_count = self._trade_count(metrics, trade_summary)
        if trade_count == 0:
            return ResultQualityFlag(
                code="no_trades",
                severity="error",
                message="No trades were detected in the parsed result.",
                details={"trade_count": 0},
            )
        return None

    def flag_too_few_trades(self, metrics, min_trades: int = 20) -> Optional[ResultQualityFlag]:
        """Flag results with too few trades for robust downstream use."""
        trade_count = self._trade_count(metrics, None)
        if trade_count is not None and 0 < trade_count < min_trades:
            return ResultQualityFlag(
                code="too_few_trades",
                severity="warning",
                message="Parsed result has fewer trades than the configured minimum.",
                details={"trade_count": trade_count, "min_trades": min_trades},
            )
        return None

    def flag_missing_backtest_file(self, discovery_result) -> Optional[ResultQualityFlag]:
        """Flag missing structured backtest files."""
        if discovery_result is None:
            return None
        if not getattr(discovery_result, "success", False) or not getattr(discovery_result, "primary_result_path", None):
            return ResultQualityFlag(
                code="missing_backtest_file",
                severity="error",
                message="No structured backtest result file was discovered.",
                details={"warnings": getattr(discovery_result, "warnings", [])},
            )
        return None

    def flag_stdout_only_parse(self, loader_result) -> Optional[ResultQualityFlag]:
        """Flag results loaded only from stdout fallback text."""
        if loader_result is None:
            return None
        payloads = getattr(loader_result, "payloads", []) or []
        has_structured = any(getattr(payload, "raw_data", None) is not None for payload in payloads)
        has_stdout = any(getattr(payload, "parser_type", None) == "stdout_table_fallback" for payload in payloads)
        if has_stdout and not has_structured:
            return ResultQualityFlag(
                code="stdout_only_parse",
                severity="warning",
                message="Only stdout fallback data was available for parsing.",
            )
        return None

    def flag_partial_parse(self, metrics, pair_results, trade_summary) -> Optional[ResultQualityFlag]:
        """Flag parsed results with missing major sections."""
        missing_sections: list[str] = []
        if metrics is None:
            missing_sections.append("metrics")
        if not pair_results:
            missing_sections.append("pair_results")
        if trade_summary is None or not self._summary_has_data(trade_summary):
            missing_sections.append("trade_summary")

        if missing_sections:
            return ResultQualityFlag(
                code="partial_parse",
                severity="warning",
                message="Parsed result is missing one or more major sections.",
                details={"missing_sections": missing_sections},
            )
        return None

    def flag_negative_expectancy(self, metrics) -> Optional[ResultQualityFlag]:
        """Flag negative expectancy as weak result evidence."""
        if metrics and getattr(metrics, "expectancy", None) is not None and metrics.expectancy < 0:
            return ResultQualityFlag(
                code="negative_expectancy",
                severity="warning",
                message="Parsed expectancy is negative.",
                details={"expectancy": metrics.expectancy},
            )
        return None

    def flag_high_drawdown(self, metrics, threshold: float = 35.0) -> Optional[ResultQualityFlag]:
        """Flag high drawdown values."""
        if metrics is None:
            return None
        drawdown = getattr(metrics, "max_drawdown_pct", None)
        if drawdown is None:
            drawdown = getattr(metrics, "max_drawdown", None)
        if drawdown is not None and abs(drawdown) >= threshold:
            return ResultQualityFlag(
                code="high_drawdown",
                severity="warning",
                message="Parsed drawdown is above the configured threshold.",
                details={"drawdown": drawdown, "threshold": threshold},
            )
        return None

    def flag_single_pair_dependency(
        self,
        pair_results,
        threshold: float = 0.8,
    ) -> Optional[ResultQualityFlag]:
        """Flag results dominated by one pair's absolute net profit."""
        if not pair_results:
            return None
        profit_pairs = [pair for pair in pair_results if pair.net_profit is not None]
        if len(profit_pairs) == 1:
            return ResultQualityFlag(
                code="single_pair_dependency",
                severity="warning",
                message="Parsed result depends on a single pair.",
                details={"pair": profit_pairs[0].pair, "threshold": threshold},
            )
        total_abs = sum(abs(pair.net_profit) for pair in profit_pairs)
        if total_abs <= 0:
            return None
        dominant = max(profit_pairs, key=lambda pair: abs(pair.net_profit))
        ratio = abs(dominant.net_profit) / total_abs
        if ratio >= threshold:
            return ResultQualityFlag(
                code="single_pair_dependency",
                severity="warning",
                message="One pair contributes most of the parsed pair-level result.",
                details={"pair": dominant.pair, "dependency_ratio": ratio, "threshold": threshold},
            )
        return None

    def flag_missing_pair_results(self, pair_results) -> Optional[ResultQualityFlag]:
        """Flag missing pair-level evidence."""
        if not pair_results:
            return ResultQualityFlag(
                code="missing_pair_results",
                severity="warning",
                message="No pair-level results were parsed.",
            )
        return None

    def flag_missing_profit_factor(self, metrics) -> Optional[ResultQualityFlag]:
        """Flag missing profit factor."""
        if metrics is None or getattr(metrics, "profit_factor", None) is None:
            return ResultQualityFlag(
                code="missing_profit_factor",
                severity="error",
                message="Profit factor is missing from parsed metrics.",
            )
        return None

    def flag_missing_drawdown(self, metrics) -> Optional[ResultQualityFlag]:
        """Flag missing drawdown metrics."""
        if metrics is None:
            return ResultQualityFlag(
                code="missing_drawdown",
                severity="error",
                message="Drawdown is missing from parsed metrics.",
            )
        if getattr(metrics, "max_drawdown", None) is None and getattr(metrics, "max_drawdown_pct", None) is None:
            return ResultQualityFlag(
                code="missing_drawdown",
                severity="error",
                message="Drawdown is missing from parsed metrics.",
            )
        return None

    def _coerce_metrics(self, metrics) -> Optional[ExtractedBacktestMetrics]:
        """Accept either metrics object or extraction result envelope."""
        if isinstance(metrics, MetricsExtractionResult):
            return metrics.metrics
        return metrics

    def _coerce_pair_results(self, pair_results) -> list[ExtractedPairResult]:
        """Accept either pair list or parse result envelope."""
        if isinstance(pair_results, PairTradeParseResult):
            return pair_results.pair_results
        return pair_results or []

    def _coerce_trade_summary(self, trade_summary, pair_results) -> Optional[ExtractedTradeSummary]:
        """Accept explicit summary or parse result envelope."""
        if trade_summary is None and isinstance(pair_results, PairTradeParseResult):
            return pair_results.trade_summary
        if isinstance(trade_summary, ExtractedTradeSummary) or trade_summary is None:
            return trade_summary
        return getattr(trade_summary, "trade_summary", None)

    def _trade_count(self, metrics, trade_summary) -> Optional[int]:
        """Return best available total trade count."""
        if metrics is not None and getattr(metrics, "trade_count", None) is not None:
            return metrics.trade_count
        if trade_summary is not None and getattr(trade_summary, "total_trades", None) is not None:
            return trade_summary.total_trades
        return None

    @staticmethod
    def _is_usable_for_metrics(metrics, pair_results) -> bool:
        """Return whether enough data exists for metrics display/storage."""
        return bool(
            (metrics is not None and getattr(metrics, "trade_count", None) is not None)
            or (metrics is not None and getattr(metrics, "net_profit", None) is not None)
            or pair_results
        )

    @staticmethod
    def _summary_has_data(summary) -> bool:
        """Return whether a trade summary has extracted data."""
        if summary is None:
            return False
        return any(
            getattr(summary, field, None) is not None
            for field in ("total_trades", "wins", "losses", "draws", "avg_duration", "best_pair", "worst_pair")
        )

    @staticmethod
    def _parse_quality(flags: list[ResultQualityFlag]) -> str:
        """Return coarse parse quality from flag severities."""
        severities = {flag.severity for flag in flags}
        if "critical" in severities:
            return "critical"
        if "error" in severities:
            return "error"
        if "warning" in severities:
            return "warning"
        return "clean"

    @staticmethod
    def _extract_run_id(discovery_result) -> Optional[str]:
        """Extract run ID from discovery result when available."""
        return getattr(discovery_result, "run_id", None) if discovery_result else None

    @staticmethod
    def _extract_warnings(value: Any) -> list[str]:
        """Collect warnings from result envelopes or parsed objects."""
        if value is None:
            return []
        if isinstance(value, list):
            warnings: list[str] = []
            for item in value:
                warnings.extend(ResultQualityService._extract_warnings(item))
            return warnings
        return list(getattr(value, "warnings", []) or [])

    @staticmethod
    def _extract_errors(value: Any) -> list[str]:
        """Collect errors from result envelopes or parsed objects."""
        if value is None:
            return []
        if isinstance(value, list):
            errors: list[str] = []
            for item in value:
                errors.extend(ResultQualityService._extract_errors(item))
            return errors
        return list(getattr(value, "errors", []) or [])

    @staticmethod
    def _dedupe_flags(flags: list[ResultQualityFlag]) -> list[ResultQualityFlag]:
        """Deduplicate flags by code and detail payload."""
        deduped: list[ResultQualityFlag] = []
        seen: set[tuple[str, str]] = set()
        for flag in flags:
            detail_key = str(flag.details or {})
            key = (flag.code, detail_key)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(flag)
        return deduped

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
