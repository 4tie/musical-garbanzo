"""
Part 13 validation policy service.

This service evaluates already-collected validation evidence. It does not run
Freqtrade, call AI services, approve strategies, export strategies, or make
profit guarantees.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.validation import (
    OOSValidationResult,
    RobustnessCheckResult,
    ValidationDecision,
    ValidationIssue,
    ValidationPolicy,
    WFOValidationResult,
    WFOWindowResult,
)


class ValidationPolicyService:
    """Evaluate OOS, WFO, robustness, and aggregate validation evidence."""

    PROFILE_THRESHOLDS = {
        "conservative": {
            "min_oos_profit_factor": 1.20,
            "max_oos_drawdown_pct": 25.0,
            "min_wfo_pass_rate": 0.70,
        },
        "balanced": {
            "min_oos_profit_factor": 1.10,
            "max_oos_drawdown_pct": 35.0,
            "min_wfo_pass_rate": 0.60,
        },
        "aggressive": {
            "min_oos_profit_factor": 1.05,
            "max_oos_drawdown_pct": 45.0,
            "min_wfo_pass_rate": 0.50,
        },
    }

    BASE_MIN_TRADES = {
        "conservative": 30,
        "balanced": 20,
        "aggressive": 10,
    }

    TIMEFRAME_MULTIPLIERS = {
        "1m": 2.0,
        "3m": 1.7,
        "5m": 1.5,
        "15m": 1.0,
        "30m": 0.8,
        "1h": 0.6,
        "2h": 0.5,
        "4h": 0.4,
        "1d": 0.25,
    }

    def get_default_policy(
        self,
        risk_profile: str = "balanced",
        timeframe: Optional[str] = None,
    ) -> ValidationPolicy:
        """Return the default deterministic validation policy."""
        profile = self._normalize_risk_profile(risk_profile)
        thresholds = self.PROFILE_THRESHOLDS[profile]
        return ValidationPolicy(
            policy_name=f"default_validation_{profile}",
            risk_profile=profile,
            timeframe=timeframe,
            min_oos_profit_factor=thresholds["min_oos_profit_factor"],
            min_oos_expectancy=0.0,
            min_oos_trades=self.get_min_trades(timeframe, profile),
            max_oos_drawdown_pct=thresholds["max_oos_drawdown_pct"],
            min_wfo_pass_rate=thresholds["min_wfo_pass_rate"],
            max_robustness_critical_failures=0,
            require_robustness_pass=True,
            notes=(
                "Policy thresholds are deterministic validation gates. "
                "They do not guarantee future performance."
            ),
        )

    def evaluate_oos(
        self,
        metrics: dict[str, Any],
        policy: ValidationPolicy,
    ) -> OOSValidationResult:
        """Evaluate out-of-sample metrics against policy thresholds."""
        issues: list[ValidationIssue] = []
        profit_factor = self._number(metrics, "profit_factor")
        expectancy = self._number(metrics, "expectancy")
        trade_count = self._integer(metrics, "trade_count")
        drawdown_pct = self._drawdown_pct(metrics)

        if profit_factor is None:
            issues.append(
                self._issue(
                    "missing_profit_factor",
                    "critical",
                    "OOS profit factor is missing.",
                    "profit_factor",
                    None,
                    policy.min_oos_profit_factor,
                    "Re-run or re-parse OOS backtest evidence before validation.",
                )
            )
        elif profit_factor < policy.min_oos_profit_factor:
            issues.append(
                self._issue(
                    "oos_profit_factor_below_threshold",
                    "blocking",
                    "OOS profit factor is below the policy threshold.",
                    "profit_factor",
                    profit_factor,
                    policy.min_oos_profit_factor,
                    "Reject this candidate or collect stronger OOS evidence.",
                )
            )

        if expectancy is None:
            issues.append(
                self._issue(
                    "missing_expectancy",
                    "critical",
                    "OOS expectancy is missing.",
                    "expectancy",
                    None,
                    policy.min_oos_expectancy,
                    "Re-run or re-parse OOS backtest evidence before validation.",
                )
            )
        elif expectancy <= policy.min_oos_expectancy:
            issues.append(
                self._issue(
                    "oos_expectancy_not_positive",
                    "blocking",
                    "OOS expectancy must be positive.",
                    "expectancy",
                    expectancy,
                    policy.min_oos_expectancy,
                    "Reject this candidate until OOS expectancy is positive.",
                )
            )

        if trade_count is None:
            issues.append(
                self._issue(
                    "missing_trade_count",
                    "critical",
                    "OOS trade count is missing.",
                    "trade_count",
                    None,
                    policy.min_oos_trades,
                    "Re-run or re-parse OOS backtest evidence before validation.",
                )
            )
        elif trade_count == 0:
            issues.append(
                self._issue(
                    "oos_zero_trades",
                    "critical",
                    "OOS validation produced zero trades.",
                    "trade_count",
                    trade_count,
                    policy.min_oos_trades,
                    "Reject this candidate; zero-trade OOS evidence is unusable.",
                )
            )
        elif trade_count < policy.min_oos_trades:
            issues.append(
                self._issue(
                    "oos_trade_count_below_threshold",
                    "blocking",
                    "OOS trade count is below the policy minimum.",
                    "trade_count",
                    trade_count,
                    policy.min_oos_trades,
                    "Collect a longer OOS sample or reject this candidate.",
                )
            )

        if drawdown_pct is None:
            issues.append(
                self._issue(
                    "missing_drawdown",
                    "critical",
                    "OOS maximum drawdown is missing.",
                    "max_drawdown",
                    None,
                    policy.max_oos_drawdown_pct,
                    "Re-run or re-parse OOS backtest evidence before validation.",
                )
            )
        elif drawdown_pct > policy.max_oos_drawdown_pct:
            issues.append(
                self._issue(
                    "oos_drawdown_exceeds_threshold",
                    "blocking",
                    "OOS maximum drawdown exceeds the policy threshold.",
                    "max_drawdown",
                    drawdown_pct,
                    policy.max_oos_drawdown_pct,
                    "Reject this candidate or reduce risk before validating.",
                )
            )

        status = "oos_failed" if self._has_blocking_or_critical(issues) else "oos_passed"
        warnings = [issue.code for issue in issues if issue.severity == "warning"]
        return OOSValidationResult(
            status=status,
            metrics=metrics,
            decision={
                "decision_status": status,
                "policy_name": policy.policy_name,
            },
            issues=issues,
            warnings=warnings,
        )

    def evaluate_wfo(
        self,
        window_results: list[WFOWindowResult | dict[str, Any]],
        policy: ValidationPolicy,
    ) -> WFOValidationResult:
        """Evaluate walk-forward windows against the pass-rate threshold."""
        windows = [self._coerce_wfo_window(window) for window in window_results]
        if not windows:
            issue = self._issue(
                "wfo_windows_missing",
                "critical",
                "WFO validation has no windows.",
                "window_count",
                0,
                1,
                "Generate WFO windows before making a validation decision.",
            )
            return WFOValidationResult(
                status="wfo_failed",
                windows=[],
                pass_count=0,
                fail_count=0,
                summary={"pass_rate": 0.0, "window_count": 0},
                issues=[issue],
            )

        pass_count = sum(1 for window in windows if window.status == "wfo_passed")
        fail_count = len(windows) - pass_count
        pass_rate = pass_count / len(windows)
        issues: list[ValidationIssue] = []

        if pass_rate < policy.min_wfo_pass_rate:
            issues.append(
                self._issue(
                    "wfo_pass_rate_below_threshold",
                    "blocking",
                    "WFO pass rate is below the policy threshold.",
                    "wfo_pass_rate",
                    pass_rate,
                    policy.min_wfo_pass_rate,
                    "Reject this candidate or collect more stable WFO evidence.",
                )
            )

        for window in windows:
            for issue in window.issues:
                if issue.severity == "critical":
                    issues.append(
                        self._issue(
                            "wfo_window_critical_issue",
                            "critical",
                            "A WFO window contains a critical issue.",
                            "window_index",
                            window.window_index,
                            "no critical issues",
                            "Inspect the failed WFO window evidence.",
                        )
                    )
                    break

        status = "wfo_failed" if self._has_blocking_or_critical(issues) else "wfo_passed"
        return WFOValidationResult(
            status=status,
            windows=windows,
            pass_count=pass_count,
            fail_count=fail_count,
            summary={
                "pass_rate": pass_rate,
                "window_count": len(windows),
                "required_pass_rate": policy.min_wfo_pass_rate,
            },
            issues=issues,
            warnings=[issue.code for issue in issues if issue.severity == "warning"],
        )

    def evaluate_robustness(
        self,
        checks: list[RobustnessCheckResult | dict[str, Any]],
        policy: ValidationPolicy,
    ) -> list[RobustnessCheckResult]:
        """Normalize robustness checks and mark critical failures."""
        if not checks:
            return [
                RobustnessCheckResult(
                    check_name="robustness_checks_missing",
                    status="robustness_failed",
                    issues=[
                        self._issue(
                            "robustness_checks_missing",
                            "critical",
                            "Robustness checks are missing.",
                            "robustness_check_count",
                            0,
                            1,
                            "Run robustness checks before final validation.",
                        )
                    ],
                )
            ]

        evaluated = []
        for raw_check in checks:
            check = self._coerce_robustness_check(raw_check)
            critical_count = sum(
                1 for issue in check.issues if issue.severity == "critical"
            )
            failed_status = check.status in {
                "failed_controlled",
                "robustness_failed",
                "rejected",
                "validation_error",
            }
            status = (
                "robustness_failed"
                if failed_status
                or critical_count > policy.max_robustness_critical_failures
                else "robustness_passed"
            )
            evaluated.append(
                RobustnessCheckResult(
                    check_name=check.check_name,
                    status=status,
                    metrics=check.metrics,
                    decision={
                        **check.decision,
                        "critical_failure_count": critical_count,
                    },
                    issues=check.issues,
                    warnings=check.warnings,
                    artifact_paths=check.artifact_paths,
                )
            )
        return evaluated

    def make_final_decision(
        self,
        oos_result: OOSValidationResult,
        wfo_result: Optional[WFOValidationResult],
        robustness_results: list[RobustnessCheckResult],
        policy: ValidationPolicy,
    ) -> ValidationDecision:
        """Make the aggregate validation decision from validation evidence."""
        reasons: list[str] = []
        warnings: list[str] = []
        blocking_failures: list[str] = []

        if oos_result.status != "oos_passed":
            blocking_failures.append("oos_failed")
            reasons.append("OOS validation failed.")
        if self._has_blocking_or_critical(oos_result.issues):
            blocking_failures.extend(issue.code for issue in oos_result.issues)

        if wfo_result is None:
            warnings.append("wfo_disabled")
            reasons.append("WFO was disabled; validation relies on explicit warning.")
        elif wfo_result.status != "wfo_passed":
            blocking_failures.append("wfo_failed")
            blocking_failures.extend(issue.code for issue in wfo_result.issues)
            reasons.append("WFO validation failed.")

        if not robustness_results:
            blocking_failures.append("robustness_missing")
            reasons.append("Robustness evidence is missing.")
        for check in robustness_results:
            critical_issues = [
                issue.code for issue in check.issues if issue.severity == "critical"
            ]
            if check.status != "robustness_passed" or critical_issues:
                blocking_failures.append(f"robustness_failed:{check.check_name}")
                blocking_failures.extend(critical_issues)
                reasons.append(f"Robustness check failed: {check.check_name}.")

        unique_blocking = self._unique(blocking_failures)
        if unique_blocking:
            return ValidationDecision(
                decision_status="rejected",
                confidence_score=0.0,
                policy_name=policy.policy_name,
                reasons=self._unique(reasons),
                blocking_failures=unique_blocking,
                warnings=self._unique(warnings),
                next_actions=[
                    "Review failed validation evidence.",
                    "Do not approve, export, or trade this strategy from this result.",
                ],
            )

        return ValidationDecision(
            decision_status="validated",
            confidence_score=80.0 if wfo_result is not None else 65.0,
            policy_name=policy.policy_name,
            reasons=[
                "OOS validation passed.",
                "WFO validation passed." if wfo_result else "WFO disabled with explicit warning.",
                "Robustness checks passed.",
            ],
            blocking_failures=[],
            warnings=self._unique(warnings),
            next_actions=[
                "Keep validation evidence attached to the strategy record.",
                "Treat this as validation evidence only, not approval or a guarantee.",
            ],
        )

    def build_policy_summary(self, policy: ValidationPolicy) -> dict[str, Any]:
        """Return a JSON-safe policy summary."""
        return {
            "policy_name": policy.policy_name,
            "risk_profile": policy.risk_profile,
            "timeframe": policy.timeframe,
            "min_oos_profit_factor": policy.min_oos_profit_factor,
            "min_oos_expectancy": policy.min_oos_expectancy,
            "min_oos_trades": policy.min_oos_trades,
            "max_oos_drawdown_pct": policy.max_oos_drawdown_pct,
            "min_wfo_pass_rate": policy.min_wfo_pass_rate,
            "max_robustness_critical_failures": policy.max_robustness_critical_failures,
            "require_robustness_pass": policy.require_robustness_pass,
        }

    def get_min_trades(
        self,
        timeframe: Optional[str],
        risk_profile: str,
    ) -> int:
        """Return timeframe- and risk-profile-adjusted minimum OOS trades."""
        profile = self._normalize_risk_profile(risk_profile)
        base = self.BASE_MIN_TRADES[profile]
        multiplier = self.TIMEFRAME_MULTIPLIERS.get(str(timeframe or "").lower(), 1.0)
        return max(1, round(base * multiplier))

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
        if key in metrics:
            return metrics[key]
        raw = metrics.get("raw_json")
        if isinstance(raw, dict):
            nested_metrics = raw.get("metrics")
            if isinstance(nested_metrics, dict) and key in nested_metrics:
                return nested_metrics[key]
        return None

    def _coerce_wfo_window(self, value: WFOWindowResult | dict[str, Any]) -> WFOWindowResult:
        if isinstance(value, WFOWindowResult):
            return value
        return WFOWindowResult.model_validate(value)

    def _coerce_robustness_check(
        self,
        value: RobustnessCheckResult | dict[str, Any],
    ) -> RobustnessCheckResult:
        if isinstance(value, RobustnessCheckResult):
            return value
        return RobustnessCheckResult.model_validate(value)

    def _has_blocking_or_critical(self, issues: list[ValidationIssue]) -> bool:
        return any(issue.severity in {"blocking", "critical"} for issue in issues)

    def _normalize_risk_profile(self, risk_profile: str) -> str:
        profile = risk_profile.strip().lower()
        if profile not in self.PROFILE_THRESHOLDS:
            raise ValueError(
                "risk_profile must be one of: aggressive, balanced, conservative"
            )
        return profile

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result
