"""
Robustness and sensitivity evaluator for Part 13 validation.

This service evaluates already-collected metrics. It does not run Freqtrade,
add frontend behavior, approve strategies, export strategies, or make profit
guarantees.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.validation import (
    RobustnessCheckResult,
    SensitivityCheckResult,
    ValidationIssue,
    ValidationPolicy,
)


class RobustnessEvaluator:
    """Evaluate metric stability, WFO stability, and sensitivity variants."""

    WARNING_RATIO = 0.75
    FAILURE_RATIO = 0.60
    MIN_ABSOLUTE_TRADES = 10
    DRAWDOWN_WARNING_MULTIPLIER = 1.25
    DRAWDOWN_FAILURE_MULTIPLIER = 1.50

    def evaluate_metric_stability(
        self,
        baseline_metrics,
        oos_metrics,
        wfo_metrics=None,
    ) -> list[RobustnessCheckResult]:
        """Run all standard robustness metric stability checks."""
        return [
            self.evaluate_trade_count_stability(baseline_metrics, oos_metrics, wfo_metrics),
            self.evaluate_profit_factor_stability(baseline_metrics, oos_metrics, wfo_metrics),
            self.evaluate_expectancy_stability(baseline_metrics, oos_metrics, wfo_metrics),
            self.evaluate_drawdown_stability(baseline_metrics, oos_metrics, wfo_metrics),
        ]

    def evaluate_trade_count_stability(
        self,
        baseline_metrics,
        oos_metrics,
        wfo_metrics=None,
    ) -> RobustnessCheckResult:
        """Evaluate trade count collapse and WFO trade-count stability."""
        baseline_trade_count = self._integer(baseline_metrics, "trade_count")
        oos_trade_count = self._integer(oos_metrics, "trade_count")
        issues = []

        if baseline_trade_count is None or oos_trade_count is None:
            issues.append(
                self._issue(
                    "missing_trade_count",
                    "critical",
                    "Trade count is missing from baseline or OOS metrics.",
                    "trade_count",
                    {"baseline": baseline_trade_count, "oos": oos_trade_count},
                    "present",
                    "Re-parse baseline and OOS metrics before robustness evaluation.",
                )
            )
        elif oos_trade_count == 0:
            issues.append(
                self._issue(
                    "oos_zero_trades",
                    "critical",
                    "OOS trade count collapsed to zero.",
                    "trade_count",
                    oos_trade_count,
                    "> 0",
                    "Reject this candidate; zero-trade OOS evidence is unusable.",
                )
            )
        else:
            if oos_trade_count < self.MIN_ABSOLUTE_TRADES:
                issues.append(
                    self._issue(
                        "oos_too_few_trades",
                        "error",
                        "OOS trade count is too low for robust evidence.",
                        "trade_count",
                        oos_trade_count,
                        self.MIN_ABSOLUTE_TRADES,
                        "Collect more evidence before continuing.",
                    )
                )
            ratio = self._ratio(oos_trade_count, baseline_trade_count)
            if ratio is not None and ratio < self.FAILURE_RATIO:
                issues.append(
                    self._issue(
                        "trade_count_collapse",
                        "error",
                        "OOS trade count is materially lower than baseline.",
                        "trade_count_ratio",
                        ratio,
                        self.FAILURE_RATIO,
                        "Collect more evidence or reject this candidate.",
                    )
                )
            elif ratio is not None and ratio < self.WARNING_RATIO:
                issues.append(
                    self._issue(
                        "trade_count_decline_warning",
                        "warning",
                        "OOS trade count declined materially from baseline.",
                        "trade_count_ratio",
                        ratio,
                        self.WARNING_RATIO,
                        "Review whether the OOS sample is large enough.",
                    )
                )

        issues.extend(self._wfo_pass_rate_issues(wfo_metrics))
        issues.extend(self._wfo_trade_count_issues(wfo_metrics))
        return self._result(
            "trade_count_stability",
            {
                "baseline_trade_count": baseline_trade_count,
                "oos_trade_count": oos_trade_count,
                "wfo_window_count": len(self._coerce_wfo_metrics(wfo_metrics)),
            },
            issues,
        )

    def evaluate_drawdown_stability(
        self,
        baseline_metrics,
        oos_metrics,
        wfo_metrics=None,
    ) -> RobustnessCheckResult:
        """Evaluate drawdown expansion from baseline to OOS and WFO."""
        baseline_drawdown = self._drawdown_pct(baseline_metrics)
        oos_drawdown = self._drawdown_pct(oos_metrics)
        issues = []

        if baseline_drawdown is None or oos_drawdown is None:
            issues.append(
                self._issue(
                    "missing_drawdown",
                    "critical",
                    "Drawdown is missing from baseline or OOS metrics.",
                    "max_drawdown",
                    {"baseline": baseline_drawdown, "oos": oos_drawdown},
                    "present",
                    "Re-parse baseline and OOS metrics before robustness evaluation.",
                )
            )
        elif baseline_drawdown > 0:
            expansion = oos_drawdown / baseline_drawdown
            if expansion >= self.DRAWDOWN_FAILURE_MULTIPLIER:
                issues.append(
                    self._issue(
                        "drawdown_expansion_failed",
                        "error",
                        "OOS drawdown expanded materially from baseline.",
                        "drawdown_expansion_ratio",
                        expansion,
                        self.DRAWDOWN_FAILURE_MULTIPLIER,
                        "Reject this candidate or reduce drawdown risk.",
                    )
                )
            elif expansion >= self.DRAWDOWN_WARNING_MULTIPLIER:
                issues.append(
                    self._issue(
                        "drawdown_expansion_warning",
                        "warning",
                        "OOS drawdown expanded from baseline.",
                        "drawdown_expansion_ratio",
                        expansion,
                        self.DRAWDOWN_WARNING_MULTIPLIER,
                        "Review drawdown stability before continuing.",
                    )
                )

        issues.extend(self._wfo_drawdown_issues(wfo_metrics))
        return self._result(
            "drawdown_stability",
            {
                "baseline_drawdown_pct": baseline_drawdown,
                "oos_drawdown_pct": oos_drawdown,
            },
            issues,
        )

    def evaluate_expectancy_stability(
        self,
        baseline_metrics,
        oos_metrics,
        wfo_metrics=None,
    ) -> RobustnessCheckResult:
        """Evaluate OOS expectancy and WFO expectancy stability."""
        baseline_expectancy = self._number(baseline_metrics, "expectancy")
        oos_expectancy = self._number(oos_metrics, "expectancy")
        issues = []

        if baseline_expectancy is None or oos_expectancy is None:
            issues.append(
                self._issue(
                    "missing_expectancy",
                    "critical",
                    "Expectancy is missing from baseline or OOS metrics.",
                    "expectancy",
                    {"baseline": baseline_expectancy, "oos": oos_expectancy},
                    "present",
                    "Re-parse baseline and OOS metrics before robustness evaluation.",
                )
            )
        elif oos_expectancy <= 0:
            issues.append(
                self._issue(
                    "expectancy_flipped_negative",
                    "critical",
                    "OOS expectancy is not positive.",
                    "expectancy",
                    oos_expectancy,
                    "> 0",
                    "Reject this candidate until OOS expectancy is positive.",
                )
            )
        elif baseline_expectancy > 0:
            ratio = oos_expectancy / baseline_expectancy
            if ratio < self.FAILURE_RATIO:
                issues.append(
                    self._issue(
                        "expectancy_collapse",
                        "error",
                        "OOS expectancy is materially lower than baseline.",
                        "expectancy_ratio",
                        ratio,
                        self.FAILURE_RATIO,
                        "Review the OOS degradation before continuing.",
                    )
                )
            elif ratio < self.WARNING_RATIO:
                issues.append(
                    self._issue(
                        "expectancy_decline_warning",
                        "warning",
                        "OOS expectancy declined from baseline.",
                        "expectancy_ratio",
                        ratio,
                        self.WARNING_RATIO,
                        "Review expectancy stability before continuing.",
                    )
                )

        issues.extend(self._wfo_expectancy_issues(wfo_metrics))
        return self._result(
            "expectancy_stability",
            {
                "baseline_expectancy": baseline_expectancy,
                "oos_expectancy": oos_expectancy,
            },
            issues,
        )

    def evaluate_profit_factor_stability(
        self,
        baseline_metrics,
        oos_metrics,
        wfo_metrics=None,
    ) -> RobustnessCheckResult:
        """Evaluate OOS profit factor collapse and WFO profit-factor stability."""
        baseline_pf = self._number(baseline_metrics, "profit_factor")
        oos_pf = self._number(oos_metrics, "profit_factor")
        issues = []

        if baseline_pf is None or oos_pf is None:
            issues.append(
                self._issue(
                    "missing_profit_factor",
                    "critical",
                    "Profit factor is missing from baseline or OOS metrics.",
                    "profit_factor",
                    {"baseline": baseline_pf, "oos": oos_pf},
                    "present",
                    "Re-parse baseline and OOS metrics before robustness evaluation.",
                )
            )
        elif oos_pf <= 1:
            issues.append(
                self._issue(
                    "profit_factor_not_profitable",
                    "critical",
                    "OOS profit factor is not above 1.",
                    "profit_factor",
                    oos_pf,
                    "> 1",
                    "Reject this candidate until OOS profit factor improves.",
                )
            )
        elif baseline_pf > 0:
            ratio = oos_pf / baseline_pf
            if ratio < self.FAILURE_RATIO:
                issues.append(
                    self._issue(
                        "profit_factor_collapse",
                        "error",
                        "OOS profit factor collapsed relative to baseline.",
                        "profit_factor_ratio",
                        ratio,
                        self.FAILURE_RATIO,
                        "Review OOS degradation before continuing.",
                    )
                )
            elif ratio < self.WARNING_RATIO:
                issues.append(
                    self._issue(
                        "profit_factor_decline_warning",
                        "warning",
                        "OOS profit factor declined materially from baseline.",
                        "profit_factor_ratio",
                        ratio,
                        self.WARNING_RATIO,
                        "Review profit factor stability before continuing.",
                    )
                )

        issues.extend(self._wfo_profit_factor_issues(wfo_metrics))
        return self._result(
            "profit_factor_stability",
            {
                "baseline_profit_factor": baseline_pf,
                "oos_profit_factor": oos_pf,
            },
            issues,
        )

    def evaluate_sensitivity_variants(
        self,
        variant_results,
        policy: ValidationPolicy,
    ) -> list[SensitivityCheckResult]:
        """Evaluate sensitivity variant result metrics against validation policy."""
        variants = variant_results or []
        if not variants:
            return [
                SensitivityCheckResult(
                    check_name="sensitivity_variants_missing",
                    status="failed",
                    issues=[
                        self._issue(
                            "sensitivity_variants_missing",
                            "critical",
                            "Sensitivity variants are missing.",
                            "variant_count",
                            0,
                            1,
                            "Run or explicitly disable sensitivity checks.",
                        )
                    ],
                )
            ]

        checks = []
        for index, variant in enumerate(variants, start=1):
            metrics = variant.get("metrics", variant) if isinstance(variant, dict) else {}
            variant_name = (
                variant.get("variant_name")
                or variant.get("name")
                or f"variant_{index}"
                if isinstance(variant, dict)
                else f"variant_{index}"
            )
            issues = self._critical_metric_issues(metrics, prefix="sensitivity")
            issues.extend(self._policy_metric_issues(metrics, policy, prefix="sensitivity"))
            checks.append(
                SensitivityCheckResult(
                    check_name=str(variant_name),
                    status=self._status_from_issues(issues),
                    metrics=metrics,
                    issues=issues,
                )
            )
        return checks

    def summarize_robustness(self, checks) -> dict:
        """Summarize robustness or sensitivity check outcomes."""
        summary = {
            "total": 0,
            "passed": 0,
            "warning": 0,
            "failed": 0,
            "critical": 0,
            "critical_failure_count": 0,
            "status": "passed",
            "failed_checks": [],
            "warning_checks": [],
            "critical_checks": [],
        }
        for check in checks or []:
            summary["total"] += 1
            issue_severities = {issue.severity for issue in check.issues}
            has_critical = "critical" in issue_severities
            has_failure = check.status == "failed" or bool(issue_severities & {"error", "critical"})
            has_warning = check.status == "warning" or "warning" in issue_severities
            if has_critical:
                summary["critical"] += 1
                summary["critical_failure_count"] += sum(
                    1 for issue in check.issues if issue.severity == "critical"
                )
                summary["critical_checks"].append(check.check_name)
            elif has_failure:
                summary["failed"] += 1
                summary["failed_checks"].append(check.check_name)
            elif has_warning:
                summary["warning"] += 1
                summary["warning_checks"].append(check.check_name)
            else:
                summary["passed"] += 1

        if summary["critical"] > 0:
            summary["status"] = "critical"
        elif summary["failed"] > 0:
            summary["status"] = "failed"
        elif summary["warning"] > 0:
            summary["status"] = "warning"
        return summary

    def _critical_metric_issues(self, metrics: dict[str, Any], prefix: str = "robustness") -> list[ValidationIssue]:
        issues = []
        required_metrics = ["trade_count", "profit_factor", "expectancy", "max_drawdown"]
        for metric_name in required_metrics:
            value = self._value(metrics, metric_name)
            if value is None and metric_name == "max_drawdown":
                value = self._value(metrics, "max_drawdown_pct")
            if value is None:
                issues.append(
                    self._issue(
                        f"{prefix}_missing_{metric_name}",
                        "critical",
                        f"{metric_name} is missing.",
                        metric_name,
                        None,
                        "present",
                        "Re-parse metrics before robustness evaluation.",
                    )
                )
        return issues

    def _policy_metric_issues(
        self,
        metrics: dict[str, Any],
        policy: ValidationPolicy,
        prefix: str,
    ) -> list[ValidationIssue]:
        issues = []
        trade_count = self._integer(metrics, "trade_count")
        profit_factor = self._number(metrics, "profit_factor")
        expectancy = self._number(metrics, "expectancy")
        drawdown = self._drawdown_pct(metrics)

        if trade_count is not None and trade_count == 0:
            issues.append(
                self._issue(
                    f"{prefix}_zero_trades",
                    "critical",
                    "Variant produced zero trades.",
                    "trade_count",
                    trade_count,
                    "> 0",
                    "Reject this variant evidence.",
                )
            )
        if trade_count is not None and 0 < trade_count < policy.min_oos_trades:
            issues.append(
                self._issue(
                    f"{prefix}_too_few_trades",
                    "error",
                    "Variant trade count is below policy minimum.",
                    "trade_count",
                    trade_count,
                    policy.min_oos_trades,
                    "Collect more evidence or reject this variant.",
                )
            )
        if profit_factor is not None and profit_factor <= 1:
            issues.append(
                self._issue(
                    f"{prefix}_profit_factor_not_profitable",
                    "critical",
                    "Variant profit factor is not above 1.",
                    "profit_factor",
                    profit_factor,
                    "> 1",
                    "Reject this variant evidence.",
                )
            )
        if expectancy is not None and expectancy <= 0:
            issues.append(
                self._issue(
                    f"{prefix}_expectancy_not_positive",
                    "critical",
                    "Variant expectancy is not positive.",
                    "expectancy",
                    expectancy,
                    "> 0",
                    "Reject this variant evidence.",
                )
            )
        if drawdown is not None and drawdown > policy.max_oos_drawdown_pct:
            issues.append(
                self._issue(
                    f"{prefix}_drawdown_exceeds_policy",
                    "error",
                    "Variant drawdown exceeds policy maximum.",
                    "max_drawdown",
                    drawdown,
                    policy.max_oos_drawdown_pct,
                    "Reject this variant or reduce risk.",
                )
            )
        return issues

    def _wfo_trade_count_issues(self, wfo_metrics) -> list[ValidationIssue]:
        issues = []
        windows = self._coerce_wfo_metrics(wfo_metrics)
        if not windows:
            return issues
        zero_trade_windows = [
            index for index, metrics in enumerate(windows, start=1)
            if self._integer(metrics, "trade_count") == 0
        ]
        if zero_trade_windows:
            issues.append(
                self._issue(
                    "wfo_zero_trade_windows",
                    "critical",
                    "One or more WFO windows produced zero trades.",
                    "trade_count",
                    zero_trade_windows,
                    "> 0",
                    "Reject this candidate or inspect WFO data sufficiency.",
                )
        )
        return issues

    def _wfo_pass_rate_issues(self, wfo_metrics) -> list[ValidationIssue]:
        if not isinstance(wfo_metrics, dict):
            return []
        pass_rate = self._number(wfo_metrics, "pass_rate")
        threshold = (
            self._number(wfo_metrics, "min_wfo_pass_rate")
            or self._number(wfo_metrics, "min_pass_rate")
            or self._policy_min_wfo_pass_rate(wfo_metrics.get("policy"))
        )
        if pass_rate is None:
            windows = wfo_metrics.get("windows")
            if isinstance(windows, list) and windows:
                statuses = [
                    str(item.get("status", "")).lower()
                    for item in windows
                    if isinstance(item, dict)
                ]
                if statuses:
                    passing = {
                        "passed",
                        "validated",
                        "wfo_passed",
                        "robustness_passed",
                    }
                    pass_rate = sum(status in passing for status in statuses) / len(statuses)
        if pass_rate is None or threshold is None:
            return []
        if pass_rate < threshold:
            return [
                self._issue(
                    "wfo_pass_rate_below_policy",
                    "critical",
                    "WFO pass rate is below the supplied policy threshold.",
                    "wfo_pass_rate",
                    pass_rate,
                    threshold,
                    "Reject this candidate or collect stronger WFO evidence.",
                )
            ]
        return []

    def _wfo_drawdown_issues(self, wfo_metrics) -> list[ValidationIssue]:
        windows = self._coerce_wfo_metrics(wfo_metrics)
        drawdowns = [self._drawdown_pct(metrics) for metrics in windows]
        drawdowns = [value for value in drawdowns if value is not None]
        if len(drawdowns) < 2:
            return []
        if max(drawdowns) >= min(drawdowns) * self.DRAWDOWN_FAILURE_MULTIPLIER and min(drawdowns) > 0:
            return [
                self._issue(
                    "wfo_drawdown_unstable",
                    "error",
                    "WFO drawdown is unstable across windows.",
                    "max_drawdown",
                    {"min": min(drawdowns), "max": max(drawdowns)},
                    self.DRAWDOWN_FAILURE_MULTIPLIER,
                    "Review unstable WFO windows before continuing.",
                )
            ]
        return []

    def _wfo_expectancy_issues(self, wfo_metrics) -> list[ValidationIssue]:
        issues = []
        windows = self._coerce_wfo_metrics(wfo_metrics)
        negative_windows = [
            index for index, metrics in enumerate(windows, start=1)
            if (self._number(metrics, "expectancy") is not None and self._number(metrics, "expectancy") <= 0)
        ]
        if negative_windows:
            issues.append(
                self._issue(
                    "wfo_negative_expectancy_windows",
                    "critical",
                    "One or more WFO windows have non-positive expectancy.",
                    "expectancy",
                    negative_windows,
                    "> 0",
                    "Reject this candidate or inspect unstable WFO windows.",
                )
            )
        return issues

    def _wfo_profit_factor_issues(self, wfo_metrics) -> list[ValidationIssue]:
        issues = []
        windows = self._coerce_wfo_metrics(wfo_metrics)
        weak_windows = [
            index for index, metrics in enumerate(windows, start=1)
            if (self._number(metrics, "profit_factor") is not None and self._number(metrics, "profit_factor") <= 1)
        ]
        if weak_windows:
            issues.append(
                self._issue(
                    "wfo_profit_factor_weak_windows",
                    "critical",
                    "One or more WFO windows have profit factor at or below 1.",
                    "profit_factor",
                    weak_windows,
                    "> 1",
                    "Reject this candidate or inspect unstable WFO windows.",
                )
            )
        return issues

    def _coerce_wfo_metrics(self, wfo_metrics) -> list[dict[str, Any]]:
        if not wfo_metrics:
            return []
        if isinstance(wfo_metrics, dict):
            if "windows" in wfo_metrics and isinstance(wfo_metrics["windows"], list):
                return [self._metrics_from_item(item) for item in wfo_metrics["windows"]]
            return [wfo_metrics]
        return [self._metrics_from_item(item) for item in wfo_metrics]

    def _metrics_from_item(self, item) -> dict[str, Any]:
        if hasattr(item, "metrics"):
            return item.metrics or {}
        if isinstance(item, dict):
            return item.get("metrics", item)
        return {}

    def _result(
        self,
        check_name: str,
        metrics: dict[str, Any],
        issues: list[ValidationIssue],
    ) -> RobustnessCheckResult:
        return RobustnessCheckResult(
            check_name=check_name,
            status=self._status_from_issues(issues),
            metrics=metrics,
            issues=issues,
            warnings=[issue.code for issue in issues if issue.severity == "warning"],
        )

    def _status_from_issues(self, issues: list[ValidationIssue]) -> str:
        severities = {issue.severity for issue in issues}
        if severities & {"critical", "error"}:
            return "failed"
        if "warning" in severities:
            return "warning"
        return "passed"

    def _issue(
        self,
        code: str,
        severity: str,
        message: str,
        metric_name: str,
        actual_value: Any,
        threshold: Any,
        next_action: str,
    ) -> ValidationIssue:
        return ValidationIssue(
            code=code,
            severity=severity,
            message=message,
            details={
                "metric_name": metric_name,
                "actual_value": actual_value,
                "threshold": threshold,
                "next_action": next_action,
            },
        )

    def _number(self, metrics: dict[str, Any], key: str) -> Optional[float]:
        value = self._value(metrics, key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _integer(self, metrics: dict[str, Any], key: str) -> Optional[int]:
        value = self._number(metrics, key)
        if value is None:
            return None
        return int(value)

    def _drawdown_pct(self, metrics: dict[str, Any]) -> Optional[float]:
        value = (
            self._number(metrics, "max_drawdown")
            if self._value(metrics, "max_drawdown") is not None
            else self._number(metrics, "max_drawdown_pct")
        )
        if value is None:
            return None
        absolute = abs(value)
        return absolute * 100 if absolute <= 1 else absolute

    def _value(self, metrics: dict[str, Any], key: str) -> Any:
        if not isinstance(metrics, dict):
            return None
        if key in metrics:
            return metrics[key]
        raw = metrics.get("raw_json")
        if isinstance(raw, dict):
            nested_metrics = raw.get("metrics")
            if isinstance(nested_metrics, dict) and key in nested_metrics:
                return nested_metrics[key]
        return None

    def _policy_min_wfo_pass_rate(self, policy: Any) -> Optional[float]:
        if isinstance(policy, ValidationPolicy):
            return policy.min_wfo_pass_rate
        if isinstance(policy, dict):
            value = policy.get("min_wfo_pass_rate") or policy.get("min_pass_rate")
            if value is not None:
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None
        return None

    def _ratio(self, numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
        if numerator is None or denominator in (None, 0):
            return None
        return numerator / denominator
