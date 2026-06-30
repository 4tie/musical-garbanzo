"""
Part 06 in-memory decision engine.

The engine evaluates parsed Part 05 evidence against deterministic gates and
returns an explainable DecisionResult. It does not persist decisions, update
runs, run Freqtrade, call AI services, send notifications, approve, or export.
"""
from __future__ import annotations

from typing import Any, Optional

from app.schemas.decisions import (
    DecisionEvidence,
    DecisionGateResult,
    DecisionPolicy,
    DecisionReason,
    DecisionResult,
)
from app.services.decision_policy import DecisionPolicyService


class DecisionEngine:
    """Evaluate parsed backtest evidence using acceptance gates."""

    CRITICAL_WARNING_CODES = {
        "parse_quality_warning",
        "partial_parse",
        "stdout_only_parse",
        "missing_drawdown",
        "single_pair_dependency_warning",
        "pair_concentration_warning",
        "missing_win_loss",
        "low_win_rate_warning",
    }

    def __init__(self, policy_service: Optional[DecisionPolicyService] = None) -> None:
        self.policy_service = policy_service or DecisionPolicyService()

    def evaluate(
        self,
        metrics,
        pair_results,
        trade_summary,
        quality_report=None,
        policy: Optional[DecisionPolicy] = None,
        run_id: Optional[str] = None,
    ) -> DecisionResult:
        """Evaluate parsed evidence and return an explainable decision result."""
        decision_policy = policy or self.policy_service.get_default_policy()
        resolved_run_id = run_id or self._value(metrics, "run_id") or self._value(quality_report, "run_id") or "unknown"

        gates = [
            self.evaluate_parse_quality_gate(metrics, quality_report),
            self.evaluate_min_trades_gate(metrics, trade_summary, decision_policy),
            self.evaluate_profit_factor_gate(metrics, decision_policy),
            self.evaluate_expectancy_gate(metrics, decision_policy),
            self.evaluate_drawdown_gate(metrics, decision_policy),
            self.evaluate_win_loss_balance_gate(metrics, trade_summary),
            self.evaluate_pair_dependency_gate(pair_results, decision_policy),
        ]

        classification = self.classify_from_gates(gates, metrics, decision_policy)
        reasons = self.build_reasons(gates, metrics, decision_policy)
        warnings = [reason.code for reason in reasons if reason.severity == "warning"]
        blocking_failures = [
            reason.code for reason in reasons if reason.severity == "blocking"
        ]
        return DecisionResult(
            run_id=resolved_run_id,
            classification=classification,
            confidence_score=self.calculate_confidence_score(
                gates,
                metrics,
                pair_results,
                decision_policy,
            ),
            policy_name=decision_policy.policy_name,
            risk_profile=decision_policy.risk_profile,
            timeframe=decision_policy.timeframe,
            gates=gates,
            reasons=reasons,
            evidence=self._build_evidence(
                resolved_run_id,
                metrics,
                pair_results,
                trade_summary,
                quality_report,
            ),
            warnings=warnings,
            blocking_failures=blocking_failures,
            next_actions=self.build_next_actions(
                classification,
                gates,
                metrics,
                quality_report,
            ),
        )

    def evaluate_parse_quality_gate(self, metrics, quality_report=None) -> DecisionGateResult:
        """Evaluate parser quality and evidence usability."""
        flags = self._quality_flag_codes(quality_report)
        if "parse_error" in flags or self._quality_errors(quality_report):
            return self._gate(
                "parse_quality_gate",
                "failed",
                "blocking",
                "Parsed result has parser errors and cannot be evaluated.",
                details={"flags": flags},
            )

        if metrics is None:
            return self._gate(
                "parse_quality_gate",
                "failed",
                "blocking",
                "Parsed metrics are missing.",
                details={"flags": flags},
            )

        warnings = [
            flag for flag in flags if flag in {"stdout_only_parse", "partial_parse"}
        ]
        if warnings:
            return self._gate(
                "parse_quality_gate",
                "warning",
                "warning",
                "Parsed result is usable but has parser quality warnings.",
                details={"flags": flags, "warnings": warnings},
            )

        if quality_report is not None and self._value(quality_report, "is_usable_for_decision") is False:
            return self._gate(
                "parse_quality_gate",
                "failed",
                "blocking",
                "Parsed result is not usable for decision evaluation.",
                details={"flags": flags},
            )

        return self._gate(
            "parse_quality_gate",
            "passed",
            "info",
            "Parsed metrics are usable for gate evaluation.",
            details={"flags": flags},
        )

    def evaluate_min_trades_gate(
        self,
        metrics,
        trade_summary,
        policy: DecisionPolicy,
    ) -> DecisionGateResult:
        """Evaluate timeframe-aware minimum trade count."""
        trade_count = self._trade_count(metrics, trade_summary)
        min_trades = policy.thresholds.min_trades
        if trade_count is None:
            return self._gate(
                "minimum_trades_gate",
                "failed",
                "blocking",
                "Trade count is missing.",
                actual_value=None,
                threshold_value=min_trades,
            )
        if trade_count < min_trades:
            return self._gate(
                "minimum_trades_gate",
                "failed",
                "blocking",
                "Trade count is below the policy minimum.",
                actual_value=trade_count,
                threshold_value=min_trades,
            )
        return self._gate(
            "minimum_trades_gate",
            "passed",
            "info",
            "Trade count meets the policy minimum.",
            actual_value=trade_count,
            threshold_value=min_trades,
        )

    def evaluate_profit_factor_gate(
        self,
        metrics,
        policy: DecisionPolicy,
    ) -> DecisionGateResult:
        """Evaluate profit factor thresholds."""
        profit_factor = self._number(metrics, "profit_factor")
        thresholds = policy.thresholds
        if profit_factor is None:
            return self._gate(
                "profit_factor_gate",
                "failed",
                "blocking",
                "Profit factor is missing.",
                threshold_value=thresholds.candidate_profit_factor,
            )
        if profit_factor < 1.0:
            return self._gate(
                "profit_factor_gate",
                "failed",
                "blocking",
                "Profit factor is below 1.0.",
                actual_value=profit_factor,
                threshold_value=1.0,
            )

        tier = self._profit_factor_tier(profit_factor, policy)
        if tier is None:
            return self._gate(
                "profit_factor_gate",
                "warning",
                "warning",
                "Profit factor is positive but below the candidate threshold.",
                actual_value=profit_factor,
                threshold_value=thresholds.candidate_profit_factor,
            )
        return self._gate(
            "profit_factor_gate",
            "passed",
            "info",
            f"Profit factor meets the {tier} threshold.",
            actual_value=profit_factor,
            threshold_value=self._tier_threshold(policy, "profit_factor", tier),
            details={"tier": tier},
        )

    def evaluate_expectancy_gate(
        self,
        metrics,
        policy: DecisionPolicy,
    ) -> DecisionGateResult:
        """Evaluate expectancy thresholds."""
        expectancy = self._number(metrics, "expectancy")
        thresholds = policy.thresholds
        if expectancy is None:
            return self._gate(
                "expectancy_gate",
                "failed",
                "blocking",
                "Expectancy is missing.",
                threshold_value=thresholds.min_expectancy_candidate,
            )
        if expectancy < 0:
            return self._gate(
                "expectancy_gate",
                "failed",
                "blocking",
                "Expectancy is negative.",
                actual_value=expectancy,
                threshold_value=0,
            )

        tier = self._expectancy_tier(expectancy, policy)
        return self._gate(
            "expectancy_gate",
            "passed",
            "info",
            f"Expectancy meets the {tier} threshold.",
            actual_value=expectancy,
            threshold_value=self._tier_threshold(policy, "expectancy", tier),
            details={"tier": tier},
        )

    def evaluate_drawdown_gate(
        self,
        metrics,
        policy: DecisionPolicy,
    ) -> DecisionGateResult:
        """Evaluate drawdown thresholds."""
        drawdown = self._drawdown(metrics)
        thresholds = policy.thresholds
        if drawdown is None:
            return self._gate(
                "drawdown_gate",
                "warning",
                "warning",
                "Drawdown is missing.",
                threshold_value=thresholds.max_drawdown_candidate,
            )
        if drawdown > thresholds.high_drawdown_block_threshold:
            return self._gate(
                "drawdown_gate",
                "failed",
                "blocking",
                "Drawdown is above the blocking threshold.",
                actual_value=drawdown,
                threshold_value=thresholds.high_drawdown_block_threshold,
            )

        tier = self._drawdown_tier(drawdown, policy)
        if tier is None:
            return self._gate(
                "drawdown_gate",
                "warning",
                "warning",
                "Drawdown is below the blocking threshold but above candidate limits.",
                actual_value=drawdown,
                threshold_value=thresholds.max_drawdown_candidate,
            )
        return self._gate(
            "drawdown_gate",
            "passed",
            "info",
            f"Drawdown meets the {tier} threshold.",
            actual_value=drawdown,
            threshold_value=self._tier_threshold(policy, "drawdown", tier),
            details={"tier": tier},
        )

    def evaluate_win_loss_balance_gate(self, metrics, trade_summary) -> DecisionGateResult:
        """Warn on missing or extremely weak win/loss balance evidence."""
        wins = self._number(metrics, "wins")
        losses = self._number(metrics, "losses")
        if wins is None:
            wins = self._number(trade_summary, "wins")
        if losses is None:
            losses = self._number(trade_summary, "losses")
        win_rate = self._number(metrics, "win_rate")

        if wins is None or losses is None:
            return self._gate(
                "win_loss_balance_gate",
                "warning",
                "warning",
                "Win/loss counts are missing.",
                details={"win_rate": win_rate},
            )

        if win_rate is None and (wins + losses) > 0:
            win_rate = wins / (wins + losses)
        if win_rate is not None and win_rate < 0.20:
            return self._gate(
                "win_loss_balance_gate",
                "warning",
                "warning",
                "Win rate is very low; expectancy and profit factor must justify the result.",
                actual_value=win_rate,
                threshold_value=0.20,
                details={"wins": wins, "losses": losses},
            )

        return self._gate(
            "win_loss_balance_gate",
            "passed",
            "info",
            "Win/loss balance evidence is present.",
            actual_value=win_rate,
            details={"wins": wins, "losses": losses},
        )

    def evaluate_pair_dependency_gate(
        self,
        pair_results,
        policy: DecisionPolicy,
    ) -> DecisionGateResult:
        """Warn on single-pair or concentrated pair evidence."""
        pairs = self._list(pair_results)
        pair_count = len(pairs)
        min_pairs = policy.thresholds.min_pair_count_warning
        if pair_count == 0:
            return self._gate(
                "pair_dependency_gate",
                "warning",
                "warning",
                "Pair-level evidence is missing.",
                actual_value=0,
                threshold_value=min_pairs,
            )
        if pair_count < min_pairs:
            return self._gate(
                "pair_dependency_gate",
                "warning",
                "warning",
                "Decision evidence depends on a single pair.",
                actual_value=pair_count,
                threshold_value=min_pairs,
                details={"dependency_ratio": 1.0},
            )

        profits = [
            abs(value)
            for value in (self._number(pair, "net_profit") for pair in pairs)
            if value is not None
        ]
        total_profit = sum(profits)
        if total_profit > 0:
            dependency_ratio = max(profits) / total_profit
            threshold = policy.thresholds.single_pair_dependency_warning_threshold
            if dependency_ratio > threshold:
                return self._gate(
                    "pair_dependency_gate",
                    "warning",
                    "warning",
                    "One pair dominates the pair-level evidence.",
                    actual_value=dependency_ratio,
                    threshold_value=threshold,
                    details={"pair_count": pair_count},
                )

        return self._gate(
            "pair_dependency_gate",
            "passed",
            "info",
            "Pair-level evidence is not dominated by a single pair.",
            actual_value=pair_count,
            threshold_value=min_pairs,
        )

    def classify_from_gates(
        self,
        gates: list[DecisionGateResult],
        metrics,
        policy: DecisionPolicy,
    ) -> str:
        """Classify parsed evidence from evaluated gates."""
        if any(gate.status == "failed" and gate.severity == "blocking" for gate in gates):
            return "rejected"

        profit_factor = self._number(metrics, "profit_factor")
        expectancy = self._number(metrics, "expectancy")
        drawdown = self._drawdown(metrics)
        min_trades_passed = self._gate_passed(gates, "minimum_trades_gate")
        parse_quality_ok = self._gate_passed_or_warning(gates, "parse_quality_gate")
        critical_warnings = self._critical_warning_count(gates)

        if (
            self._meets_validated(profit_factor, expectancy, drawdown, policy)
            and min_trades_passed
            and parse_quality_ok
            and critical_warnings == 0
        ):
            return "validated"

        if (
            self._meets_promising(profit_factor, expectancy, drawdown, policy)
            and min_trades_passed
        ):
            return "promising"

        if (
            self._meets_candidate(profit_factor, expectancy, drawdown, policy)
            and min_trades_passed
        ):
            return "candidate"

        return "rejected"

    def calculate_confidence_score(
        self,
        gates: list[DecisionGateResult],
        metrics,
        pair_results,
        policy: DecisionPolicy,
    ) -> float:
        """Calculate bounded evidence-strength confidence score."""
        score = 100.0
        warning_count = sum(1 for gate in gates if gate.status == "warning")
        score -= warning_count * 8
        score -= sum(1 for gate in gates if gate.status == "insufficient_data") * 12

        if self._drawdown(metrics) is None:
            score -= 8
        if self._number(metrics, "win_rate") is None:
            score -= 4
        if len(self._list(pair_results)) < policy.thresholds.min_pair_count_warning:
            score -= 10

        drawdown = self._drawdown(metrics)
        if drawdown is not None and drawdown >= policy.thresholds.max_drawdown_candidate * 0.90:
            score -= 8

        trade_count = self._number(metrics, "trade_count")
        if trade_count is not None and trade_count < policy.thresholds.min_trades * 1.25:
            score -= 8

        blocking = any(
            gate.status == "failed" and gate.severity == "blocking" for gate in gates
        )
        if blocking:
            score = min(score, 40.0)
        if not self._gate_passed_or_warning(gates, "parse_quality_gate"):
            score = min(score, 20.0)
        if trade_count == 0:
            score = min(score, 10.0)

        return round(max(0.0, min(100.0, score)), 2)

    def build_reasons(
        self,
        gates: list[DecisionGateResult],
        metrics,
        policy: DecisionPolicy,
    ) -> list[DecisionReason]:
        """Build human-readable reasons from gates."""
        reasons: list[DecisionReason] = []
        for gate in gates:
            if gate.status == "passed":
                continue
            code = self._reason_code_for_gate(gate)
            reasons.append(
                DecisionReason(
                    code=code,
                    severity=gate.severity,
                    message=gate.message,
                    metric=self._metric_for_gate(gate.gate_name),
                    actual_value=gate.actual_value,
                    threshold_value=gate.threshold_value,
                    details=gate.details,
                )
            )

        if not reasons:
            reasons.append(
                DecisionReason(
                    code="baseline_gates_passed",
                    severity="info",
                    message="Baseline evidence passed the configured acceptance gates.",
                    details={"policy_name": policy.policy_name},
                )
            )
        return reasons

    def build_next_actions(
        self,
        classification: str,
        gates: list[DecisionGateResult],
        metrics,
        quality_report,
    ) -> list[str]:
        """Build cautious next actions for the decision result."""
        actions: list[str] = []
        if classification == "rejected":
            actions.extend(
                [
                    "Reject this baseline result and do not optimize yet.",
                    "Inspect data quality and fees.",
                    "Try a different strategy family.",
                    "Do not export this strategy.",
                ]
            )
        else:
            actions.extend(
                [
                    "Run WFO/OOS before promotion.",
                    "Run multi-pair validation before trusting this result.",
                    "Inspect data quality and fees.",
                    "Do not export this strategy.",
                ]
            )
        if any(gate.gate_name == "pair_dependency_gate" and gate.status == "warning" for gate in gates):
            actions.append("Run multi-pair validation before trusting this result.")
        if any(gate.gate_name == "parse_quality_gate" and gate.status != "passed" for gate in gates):
            actions.append("Review parser quality warnings before further validation.")
        return self._dedupe(actions)

    def _build_evidence(
        self,
        run_id: str,
        metrics,
        pair_results,
        trade_summary,
        quality_report,
    ) -> DecisionEvidence:
        """Build DecisionEvidence from parsed inputs."""
        return DecisionEvidence(
            run_id=run_id,
            metrics_snapshot_id=self._value(metrics, "id"),
            trade_summary_id=self._value(trade_summary, "id"),
            pair_count=len(self._list(pair_results)),
            trade_count=self._trade_count(metrics, trade_summary),
            profit_factor=self._number(metrics, "profit_factor"),
            expectancy=self._number(metrics, "expectancy"),
            max_drawdown=self._drawdown(metrics),
            win_rate=self._number(metrics, "win_rate"),
            quality_flags=self._quality_flag_codes(quality_report),
            normalized_result_artifact_path=self._value(
                metrics,
                "normalized_result_artifact_path",
            ),
        )

    def _gate(
        self,
        gate_name: str,
        status: str,
        severity: str,
        message: str,
        actual_value: Any = None,
        threshold_value: Any = None,
        details: Optional[dict[str, Any]] = None,
    ) -> DecisionGateResult:
        """Create a gate result."""
        return DecisionGateResult(
            gate_name=gate_name,
            status=status,
            actual_value=actual_value,
            threshold_value=threshold_value,
            message=message,
            severity=severity,
            details=details or {},
        )

    def _trade_count(self, metrics, trade_summary) -> Optional[int]:
        value = self._number(metrics, "trade_count")
        if value is None:
            value = self._number(trade_summary, "total_trades")
        return int(value) if value is not None else None

    def _drawdown(self, metrics) -> Optional[float]:
        drawdown = self._number(metrics, "max_drawdown_pct")
        if drawdown is None:
            drawdown = self._number(metrics, "max_drawdown")
        return abs(drawdown) if drawdown is not None else None

    def _quality_flag_codes(self, quality_report) -> list[str]:
        flags = self._value(quality_report, "flags") or []
        codes: list[str] = []
        for flag in flags:
            code = self._value(flag, "code")
            if code:
                codes.append(str(code))
        return self._dedupe(codes)

    def _quality_errors(self, quality_report) -> list[str]:
        return self._list(self._value(quality_report, "errors"))

    def _profit_factor_tier(
        self,
        profit_factor: float,
        policy: DecisionPolicy,
    ) -> Optional[str]:
        thresholds = policy.thresholds
        if profit_factor >= thresholds.validated_profit_factor:
            return "validated"
        if profit_factor >= thresholds.promising_profit_factor:
            return "promising"
        if profit_factor >= thresholds.candidate_profit_factor:
            return "candidate"
        return None

    def _expectancy_tier(self, expectancy: float, policy: DecisionPolicy) -> str:
        thresholds = policy.thresholds
        if expectancy >= thresholds.min_expectancy_validated:
            return "validated"
        if expectancy >= thresholds.min_expectancy_promising:
            return "promising"
        return "candidate"

    def _drawdown_tier(self, drawdown: float, policy: DecisionPolicy) -> Optional[str]:
        thresholds = policy.thresholds
        if drawdown <= thresholds.max_drawdown_validated:
            return "validated"
        if drawdown <= thresholds.max_drawdown_promising:
            return "promising"
        if drawdown <= thresholds.max_drawdown_candidate:
            return "candidate"
        return None

    def _tier_threshold(
        self,
        policy: DecisionPolicy,
        metric: str,
        tier: str,
    ) -> Optional[float]:
        thresholds = policy.thresholds
        lookup = {
            ("profit_factor", "candidate"): thresholds.candidate_profit_factor,
            ("profit_factor", "promising"): thresholds.promising_profit_factor,
            ("profit_factor", "validated"): thresholds.validated_profit_factor,
            ("expectancy", "candidate"): thresholds.min_expectancy_candidate,
            ("expectancy", "promising"): thresholds.min_expectancy_promising,
            ("expectancy", "validated"): thresholds.min_expectancy_validated,
            ("drawdown", "candidate"): thresholds.max_drawdown_candidate,
            ("drawdown", "promising"): thresholds.max_drawdown_promising,
            ("drawdown", "validated"): thresholds.max_drawdown_validated,
        }
        return lookup.get((metric, tier))

    def _meets_candidate(self, profit_factor, expectancy, drawdown, policy) -> bool:
        thresholds = policy.thresholds
        return (
            profit_factor is not None
            and expectancy is not None
            and drawdown is not None
            and profit_factor >= thresholds.candidate_profit_factor
            and expectancy >= thresholds.min_expectancy_candidate
            and drawdown <= thresholds.max_drawdown_candidate
        )

    def _meets_promising(self, profit_factor, expectancy, drawdown, policy) -> bool:
        thresholds = policy.thresholds
        return (
            profit_factor is not None
            and expectancy is not None
            and drawdown is not None
            and profit_factor >= thresholds.promising_profit_factor
            and expectancy >= thresholds.min_expectancy_promising
            and drawdown <= thresholds.max_drawdown_promising
        )

    def _meets_validated(self, profit_factor, expectancy, drawdown, policy) -> bool:
        thresholds = policy.thresholds
        return (
            profit_factor is not None
            and expectancy is not None
            and drawdown is not None
            and profit_factor >= thresholds.validated_profit_factor
            and expectancy >= thresholds.min_expectancy_validated
            and drawdown <= thresholds.max_drawdown_validated
        )

    def _gate_passed(self, gates: list[DecisionGateResult], gate_name: str) -> bool:
        return any(gate.gate_name == gate_name and gate.status == "passed" for gate in gates)

    def _gate_passed_or_warning(
        self,
        gates: list[DecisionGateResult],
        gate_name: str,
    ) -> bool:
        return any(
            gate.gate_name == gate_name and gate.status in {"passed", "warning"}
            for gate in gates
        )

    def _critical_warning_count(self, gates: list[DecisionGateResult]) -> int:
        return sum(
            1
            for gate in gates
            if gate.status == "warning"
            and self._reason_code_for_gate(gate) in self.CRITICAL_WARNING_CODES
        )

    def _reason_code_for_gate(self, gate: DecisionGateResult) -> str:
        if gate.gate_name == "expectancy_gate" and gate.actual_value is not None and gate.actual_value < 0:
            return "negative_expectancy"
        if gate.gate_name == "expectancy_gate" and gate.actual_value is None:
            return "missing_expectancy"
        if gate.gate_name == "profit_factor_gate" and gate.actual_value is None:
            return "missing_profit_factor"
        if gate.gate_name == "profit_factor_gate" and gate.actual_value is not None and gate.actual_value < 1:
            return "profit_factor_below_one"
        if gate.gate_name == "drawdown_gate" and gate.status == "failed":
            return "drawdown_above_limit"
        if gate.gate_name == "drawdown_gate" and gate.actual_value is None:
            return "missing_drawdown"
        if gate.gate_name == "minimum_trades_gate" and gate.actual_value is None:
            return "missing_trade_count"
        if gate.gate_name == "minimum_trades_gate":
            return "too_few_trades"
        if gate.gate_name == "parse_quality_gate":
            return "parse_quality_warning" if gate.status == "warning" else "parse_quality_blocking"
        if gate.gate_name == "pair_dependency_gate" and gate.actual_value == 1:
            return "single_pair_dependency_warning"
        if gate.gate_name == "pair_dependency_gate":
            return "pair_concentration_warning"
        if gate.gate_name == "win_loss_balance_gate" and gate.actual_value is None:
            return "missing_win_loss"
        if gate.gate_name == "win_loss_balance_gate":
            return "low_win_rate_warning"
        return f"{gate.gate_name}_{gate.status}"

    def _metric_for_gate(self, gate_name: str) -> Optional[str]:
        return {
            "minimum_trades_gate": "trade_count",
            "profit_factor_gate": "profit_factor",
            "expectancy_gate": "expectancy",
            "drawdown_gate": "max_drawdown",
            "win_loss_balance_gate": "win_rate",
            "pair_dependency_gate": "pair_results",
        }.get(gate_name)

    def _number(self, obj, key: str) -> Optional[float]:
        value = self._value(obj, key)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _value(self, obj, key: str) -> Any:
        if obj is None:
            return None
        if isinstance(obj, dict):
            return obj.get(key)
        return getattr(obj, key, None)

    def _list(self, value) -> list:
        if value is None:
            return []
        if isinstance(value, list):
            return value
        return list(value) if isinstance(value, tuple) else [value]

    def _dedupe(self, values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            if value not in seen:
                result.append(value)
                seen.add(value)
        return result
