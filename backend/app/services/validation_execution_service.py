"""
Part 13 validation execution service.

This service orchestrates validation evidence collection by reusing existing
readiness, Freqtrade, parser, policy, and robustness services. It does not call
AI services, approve strategies, export strategies, or run live trading.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

from fastapi import HTTPException

from app.core.config import settings
from app.repositories.metrics import MetricsRepository
from app.repositories.optimization import OptimizationRepository
from app.repositories.runs import RunRepository
from app.repositories.validation import ValidationRepository
from app.schemas.decisions import DecisionEvaluationRequest
from app.schemas.freqtrade_backtest import FreqtradeBacktestRequest
from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
from app.schemas.runs import RunCreate
from app.schemas.validation import (
    OOSValidationResult,
    RobustnessCheckResult,
    ValidationDecision,
    ValidationIssue,
    ValidationPolicy,
    ValidationRunRequest,
    ValidationRunResponse,
    WFOValidationResult,
    WFOWindowResult,
)
from app.services.backtest_result_parser import BacktestResultParser
from app.services.decision_service import DecisionService
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator
from app.services.oos_timerange_service import OOSTimerangeService
from app.services.robustness_evaluator import RobustnessEvaluator
from app.services.strategy_readiness_gate import assert_strategy_ready_for_run
from app.services.validation_policy_service import ValidationPolicyService
from app.services.wfo_window_service import WFOWindowService


class ValidationExecutionService:
    """Run the backend validation evidence workflow."""

    REPORT_RELATIVE_PATH = "artifacts/runs/{validation_run_id}/validation/validation_report.json"
    NO_GUARANTEE_STATEMENT = (
        "Validation is evidence only. It is not strategy approval, export, "
        "live-trading authorization, or a guarantee of future performance."
    )

    def __init__(
        self,
        validation_repository: Optional[ValidationRepository] = None,
        run_repository: Optional[RunRepository] = None,
        metrics_repository: Optional[MetricsRepository] = None,
        optimization_repository: Optional[OptimizationRepository] = None,
        config_generator: Optional[FreqtradeConfigGenerator] = None,
        backtest_runner: Optional[FreqtradeBacktestRunner] = None,
        result_parser: Optional[BacktestResultParser] = None,
        decision_service: Optional[DecisionService] = None,
        policy_service: Optional[ValidationPolicyService] = None,
        oos_timerange_service: Optional[OOSTimerangeService] = None,
        wfo_window_service: Optional[WFOWindowService] = None,
        robustness_evaluator: Optional[RobustnessEvaluator] = None,
        readiness_gate: Optional[Callable[..., Any]] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.project_root = (project_root or settings.project_root).resolve()
        self.validation_repository = validation_repository or ValidationRepository()
        self.run_repository = run_repository or RunRepository()
        self.metrics_repository = metrics_repository or MetricsRepository()
        self.optimization_repository = optimization_repository or OptimizationRepository()
        self.config_generator = config_generator or FreqtradeConfigGenerator()
        self.backtest_runner = backtest_runner or FreqtradeBacktestRunner()
        self.result_parser = result_parser or BacktestResultParser(project_root=self.project_root)
        self.decision_service = decision_service or DecisionService(project_root=self.project_root)
        self.policy_service = policy_service or ValidationPolicyService()
        self.oos_timerange_service = oos_timerange_service or OOSTimerangeService()
        self.wfo_window_service = wfo_window_service or WFOWindowService()
        self.robustness_evaluator = robustness_evaluator or RobustnessEvaluator()
        self.readiness_gate = readiness_gate or assert_strategy_ready_for_run

    def run_validation(self, request: ValidationRunRequest) -> ValidationRunResponse:
        """Run validation evidence collection and return a frontend-safe response."""
        validation_run_id: Optional[str] = None
        evidence_ids: list[str] = []
        artifact_paths: list[str] = []
        warnings: list[str] = []
        errors: list[str] = []
        candidate: dict[str, Any] = {}
        policy: Optional[ValidationPolicy] = None

        try:
            policy = self.policy_service.get_default_policy(
                request.risk_profile,
                timeframe=request.timeframe,
            )
            candidate = self._build_candidate_reference(request)
            validation_run = self._create_validation_run(request, candidate, policy)
            validation_run_id = validation_run["id"]

            try:
                self.readiness_gate(candidate["strategy_name"], run_type="validation")
            except HTTPException as exc:
                return self._controlled_failure(
                    validation_run_id,
                    request,
                    candidate,
                    "strategy_not_ready",
                    self._http_exception_message(exc),
                    next_actions=[
                        "Open Strategy Workspace.",
                        "Fix strategy readiness issues.",
                        "Re-run validation after readiness passes.",
                    ],
                )

            if not request.user_confirmed:
                return self._confirmation_required(validation_run_id, request, candidate)

            split = self._split_oos_timerange(request)
            self.validation_repository.update_validation_run(
                validation_run_id,
                {
                    "timerange": split["full_timerange"],
                    "oos_timerange": split["out_of_sample_timerange"],
                    "wfo_config": self._wfo_config_from_request(request),
                    "status": "running",
                },
            )

            oos_run = self._execute_backtest_stage(
                stage_prefix="oos",
                validation_run_id=validation_run_id,
                candidate=candidate,
                timerange=split["out_of_sample_timerange"],
                request=request,
            )
            oos_metrics = oos_run["metrics"]
            oos_result = self.policy_service.evaluate_oos(oos_metrics, policy)
            oos_result.timerange = split["out_of_sample_timerange"]
            oos_result.decision = {
                **oos_result.decision,
                "backtest_decision": oos_run.get("decision"),
            }
            oos_result.artifact_paths = oos_run["artifact_paths"]
            oos_evidence = self._save_evidence(
                validation_run_id,
                "oos",
                oos_result.status,
                split["out_of_sample_timerange"],
                oos_metrics,
                oos_result.decision,
                oos_result.issues,
                oos_result.warnings,
                oos_result.artifact_paths,
            )
            oos_result.evidence_id = oos_evidence["id"]
            evidence_ids.append(oos_evidence["id"])

            if oos_result.status != "oos_passed":
                final_decision = self._make_final_decision(
                    oos_result,
                    None,
                    [],
                    policy,
                )
                return self._complete_validation(
                    validation_run_id,
                    request,
                    candidate,
                    policy,
                    split,
                    oos_result,
                    None,
                    [],
                    [],
                    final_decision,
                    evidence_ids,
                    artifact_paths,
                    warnings,
                    errors,
                )

            wfo_result = None
            wfo_window_metrics: list[dict[str, Any]] = []
            if request.wfo_enabled:
                wfo_result = self._run_wfo(
                    validation_run_id,
                    request,
                    candidate,
                    split["full_timerange"],
                    policy,
                    evidence_ids,
                )
                wfo_window_metrics = [window.metrics for window in wfo_result.windows]

            baseline_metrics = candidate.get("metrics") or {}
            robustness_results: list[RobustnessCheckResult] = []
            if request.robustness_enabled:
                try:
                    raw_robustness = self.robustness_evaluator.evaluate_metric_stability(
                        baseline_metrics,
                        oos_metrics,
                        wfo_window_metrics,
                    )
                    robustness_results = self.policy_service.evaluate_robustness(
                        raw_robustness,
                        policy,
                    )
                except Exception as exc:
                    raise ValueError(
                        f"robustness_failed: {self._safe_exception_message(exc)}"
                    ) from exc
                for check in robustness_results:
                    evidence = self._save_evidence(
                        validation_run_id,
                        "robustness",
                        check.status,
                        None,
                        check.metrics,
                        check.decision,
                        check.issues,
                        check.warnings,
                        check.artifact_paths,
                    )
                    evidence_ids.append(evidence["id"])

            sensitivity_results = []
            if request.sensitivity_enabled:
                try:
                    sensitivity_results = self.robustness_evaluator.evaluate_sensitivity_variants(
                        [],
                        policy,
                    )
                except Exception as exc:
                    raise ValueError(
                        f"robustness_failed: {self._safe_exception_message(exc)}"
                    ) from exc
                for check in sensitivity_results:
                    evidence = self._save_evidence(
                        validation_run_id,
                        "sensitivity",
                        check.status,
                        None,
                        check.metrics,
                        check.decision,
                        check.issues,
                        check.warnings,
                        check.artifact_paths,
                    )
                    evidence_ids.append(evidence["id"])

            final_decision = self._make_final_decision(
                oos_result,
                wfo_result,
                robustness_results,
                policy,
            )
            final_decision = self._apply_sensitivity_to_final_decision(
                final_decision,
                sensitivity_results,
                policy,
            )
            return self._complete_validation(
                validation_run_id,
                request,
                candidate,
                policy,
                split,
                oos_result,
                wfo_result,
                robustness_results,
                sensitivity_results,
                final_decision,
                evidence_ids,
                artifact_paths,
                warnings,
                errors,
            )
        except ValueError as exc:
            code = self._controlled_code_for_value_error(str(exc))
            if validation_run_id:
                return self._controlled_failure(
                    validation_run_id,
                    request,
                    candidate or self._request_candidate(request),
                    code,
                    str(exc),
                )
            return self._response(
                "validation-run-not-created",
                request,
                candidate or self._request_candidate(request),
                "failed_controlled",
                "validation_error",
                errors=[self._safe_error(code, str(exc))],
                next_actions=["Review validation request inputs and retry."],
            )
        except Exception as exc:
            if validation_run_id:
                return self._controlled_failure(
                    validation_run_id,
                    request,
                    candidate or self._request_candidate(request),
                    "unexpected_validation_error",
                    self._safe_exception_message(exc),
                )
            return self._response(
                "validation-run-not-created",
                request,
                candidate or self._request_candidate(request),
                "failed_controlled",
                "validation_error",
                errors=[
                    self._safe_error(
                        "unexpected_validation_error",
                        self._safe_exception_message(exc),
                    )
                ],
                next_actions=["Review service logs and retry validation."],
            )

    def _build_candidate_reference(self, request: ValidationRunRequest) -> dict[str, Any]:
        candidate = self._request_candidate(request)
        if not request.source_run_id:
            return candidate

        # Handle optimization_run source type
        if request.source_type == "optimization_run":
            optimization_run = self.optimization_repository.get_optimization_run(request.source_run_id)
            if not optimization_run:
                raise ValueError("optimization_run_not_found: optimization run was not found")

            optimized_run_id = optimization_run.get("optimized_run_id")
            if not optimized_run_id:
                raise ValueError("optimized_run_missing: optimization run has no optimized_run_id")

            # Load the optimized run as the actual candidate
            optimized_run = self.run_repository.get_run(optimized_run_id)
            if not optimized_run:
                raise ValueError("candidate_reference_missing: optimized run was not found")

            # Keep optimization metadata in candidate
            candidate.update(
                {
                    "optimization_run_id": request.source_run_id,
                    "baseline_run_id": optimization_run.get("baseline_run_id"),
                    "best_trial_id": optimization_run.get("best_trial_id"),
                    "optimized_run_id": optimized_run_id,
                    "source_run_id": optimized_run_id,
                    "source_run": self._sanitize_payload(optimized_run),
                    "strategy_name": optimized_run.get("strategy_id") or candidate["strategy_name"],
                    "pairs": optimized_run.get("pairs") or candidate["pairs"],
                    "timeframe": optimized_run.get("timeframe") or candidate["timeframe"],
                    "exchange": optimized_run.get("exchange") or candidate["exchange"],
                    "risk_profile": optimized_run.get("risk_profile") or candidate["risk_profile"],
                    "timerange": optimized_run.get("timerange") or candidate.get("timerange"),
                }
            )

            source_metrics = self.metrics_repository.get_latest_metric_snapshot(optimized_run_id)
            if source_metrics:
                candidate["metrics"] = self._metrics_from_snapshot(source_metrics)
                candidate["metrics_snapshot_id"] = source_metrics.get("id")
            else:
                candidate["warnings"] = candidate.get("warnings", [])
                candidate["warnings"].append("optimized_source_metrics_missing: optimized run has no metrics")
            return candidate

        # Handle baseline_run, optimized_run, and other source types
        source_run = self.run_repository.get_run(request.source_run_id)
        if not source_run:
            raise ValueError("candidate_reference_missing: source run was not found")

        source_pairs = source_run.get("pairs") or candidate["pairs"]
        candidate.update(
            {
                "source_run_id": request.source_run_id,
                "source_run": self._sanitize_payload(source_run),
                "strategy_name": source_run.get("strategy_id") or candidate["strategy_name"],
                "pairs": source_pairs,
                "timeframe": source_run.get("timeframe") or candidate["timeframe"],
                "exchange": source_run.get("exchange") or candidate["exchange"],
                "risk_profile": source_run.get("risk_profile") or candidate["risk_profile"],
                "timerange": source_run.get("timerange") or candidate.get("timerange"),
            }
        )
        source_metrics = self.metrics_repository.get_latest_metric_snapshot(request.source_run_id)
        if source_metrics:
            candidate["metrics"] = self._metrics_from_snapshot(source_metrics)
            candidate["metrics_snapshot_id"] = source_metrics.get("id")
        return candidate

    def _request_candidate(self, request: ValidationRunRequest) -> dict[str, Any]:
        return {
            "source_type": request.source_type,
            "source_run_id": request.source_run_id,
            "strategy_name": request.strategy_name,
            "pairs": request.pairs,
            "timeframe": request.timeframe,
            "exchange": request.exchange,
            "risk_profile": request.risk_profile,
            "timerange": request.timerange,
            "metrics": {},
        }

    def _create_validation_run(
        self,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        policy: ValidationPolicy,
    ) -> dict[str, Any]:
        return self.validation_repository.create_validation_run(
            {
                "source_type": request.source_type,
                "source_run_id": request.source_run_id,
                "strategy_name": candidate["strategy_name"],
                "timeframe": candidate["timeframe"],
                "pairs": candidate["pairs"],
                "exchange": candidate["exchange"],
                "risk_profile": request.risk_profile,
                "status": "pending",
                "decision_status": "not_validated",
                "timerange": request.timerange,
                "wfo_config": self._wfo_config_from_request(request),
                "policy": self.policy_service.build_policy_summary(policy),
                "request": self._sanitize_payload(request.model_dump(mode="json")),
            }
        )

    def _split_oos_timerange(self, request: ValidationRunRequest) -> dict[str, Any]:
        try:
            if request.timerange:
                return self.oos_timerange_service.split_timerange(
                    request.timerange,
                    request.oos_ratio,
                )
            return self.oos_timerange_service.build_from_days(
                request.days or 90,
                request.oos_ratio,
            )
        except ValueError as exc:
            raise ValueError(f"oos_timerange_invalid: {exc}") from exc

    def _run_wfo(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        full_timerange: str,
        policy: ValidationPolicy,
        evidence_ids: list[str],
    ) -> WFOValidationResult:
        try:
            windows = self.wfo_window_service.build_windows(
                full_timerange,
                request.wfo_train_days,
                request.wfo_test_days,
                request.wfo_step_days,
                request.wfo_max_windows,
            )
        except ValueError as exc:
            raise ValueError(f"wfo_window_generation_failed: {exc}") from exc

        executed_windows = []
        for window in windows:
            result = self._execute_backtest_stage(
                stage_prefix=f"wfo_window_{window.window_index}",
                validation_run_id=validation_run_id,
                candidate=candidate,
                timerange=window.test_timerange or window.timerange,
                request=request,
            )
            window_oos = self.policy_service.evaluate_oos(result["metrics"], policy)
            status = "wfo_passed" if window_oos.status == "oos_passed" else "wfo_failed"
            executed = WFOWindowResult(
                window_index=window.window_index,
                timerange=window.timerange,
                train_timerange=window.train_timerange,
                test_timerange=window.test_timerange,
                train_start=window.train_start,
                train_end=window.train_end,
                test_start=window.test_start,
                test_end=window.test_end,
                status=status,
                metrics=result["metrics"],
                decision={
                    "policy_decision": window_oos.decision,
                    "backtest_decision": result.get("decision"),
                },
                issues=window_oos.issues,
                warnings=window_oos.warnings,
                artifact_paths=result["artifact_paths"],
            )
            evidence = self._save_evidence(
                validation_run_id,
                "wfo_window",
                status,
                executed.test_timerange or executed.timerange,
                executed.metrics,
                executed.decision,
                executed.issues,
                executed.warnings,
                executed.artifact_paths,
                window_index=executed.window_index,
            )
            executed.evidence_id = evidence["id"]
            evidence_ids.append(evidence["id"])
            executed_windows.append(executed)

        aggregate = self.policy_service.evaluate_wfo(executed_windows, policy)
        summary_evidence = self._save_evidence(
            validation_run_id,
            "wfo_summary",
            aggregate.status,
            full_timerange,
            aggregate.summary,
            {"decision_status": aggregate.status},
            aggregate.issues,
            aggregate.warnings,
            [],
        )
        evidence_ids.append(summary_evidence["id"])
        return aggregate

    def _make_final_decision(
        self,
        oos_result: OOSValidationResult,
        wfo_result: Optional[WFOValidationResult],
        robustness_results: list[RobustnessCheckResult],
        policy: ValidationPolicy,
    ) -> ValidationDecision:
        try:
            return self.policy_service.make_final_decision(
                oos_result,
                wfo_result,
                robustness_results,
                policy,
            )
        except Exception as exc:
            raise ValueError(
                f"validation_decision_failed: {self._safe_exception_message(exc)}"
            ) from exc

    def _execute_backtest_stage(
        self,
        stage_prefix: str,
        validation_run_id: str,
        candidate: dict[str, Any],
        timerange: str,
        request: ValidationRunRequest,
    ) -> dict[str, Any]:
        run = self._create_child_backtest_run(validation_run_id, stage_prefix, candidate, timerange)
        run_id = run["id"]

        config_result = self.config_generator.write_backtest_config(
            FreqtradeBacktestConfigRequest(
                run_id=run_id,
                exchange=candidate["exchange"],
                pairs=candidate["pairs"],
                timeframe=candidate["timeframe"],
                timerange=timerange,
                strategy_name=candidate["strategy_name"],
            )
        )
        if not getattr(config_result, "success", False):
            raise ValueError(f"{stage_prefix}_backtest_failed: config generation failed")

        try:
            backtest_result = self.backtest_runner.run_backtest(
                FreqtradeBacktestRequest(
                    run_id=run_id,
                    config_path=config_result.config_path,
                    strategy_name=candidate["strategy_name"],
                    timeframe=candidate["timeframe"],
                    timerange=timerange,
                    pairs=candidate["pairs"],
                    user_confirmed=request.user_confirmed,
                )
            )
        except ValueError as exc:
            raise ValueError(f"{stage_prefix}_backtest_failed: {exc}") from exc

        if not getattr(backtest_result, "success", False):
            error = getattr(backtest_result, "error", None) or "backtest failed"
            raise ValueError(f"{stage_prefix}_backtest_failed: {error}")

        try:
            parse_result = self.result_parser.parse_run(run_id, force=True)
        except Exception as exc:
            raise ValueError(f"{stage_prefix}_parse_failed: {self._safe_exception_message(exc)}") from exc

        if not getattr(parse_result, "success", False):
            parse_errors = getattr(parse_result, "errors", None) or ["parse failed"]
            raise ValueError(f"{stage_prefix}_parse_failed: {'; '.join(map(str, parse_errors))}")

        metrics = self._metrics_from_parse_result(parse_result)

        decision_payload = self._evaluate_backtest_decision(run_id, request)
        artifact_paths = self._artifact_paths(backtest_result, parse_result, config_result)
        return {
            "run_id": run_id,
            "metrics": metrics,
            "decision": decision_payload,
            "artifact_paths": artifact_paths,
        }

    def _create_child_backtest_run(
        self,
        validation_run_id: str,
        stage_prefix: str,
        candidate: dict[str, Any],
        timerange: str,
    ) -> dict[str, Any]:
        return self.run_repository.create_run(
            RunCreate(
                name=f"Validation {stage_prefix} for {candidate['strategy_name']}",
                mode="manual_test",
                parent_run_id=validation_run_id,
                exchange=candidate["exchange"],
                quote_currency="USDT",
                trading_mode="spot",
                timeframe=candidate["timeframe"],
                pairs=candidate["pairs"],
                timerange=timerange,
                risk_profile=candidate.get("risk_profile"),
                analysis_depth="validation",
            ),
            create_default_stages=False,
        )

    def _evaluate_backtest_decision(
        self,
        run_id: str,
        request: ValidationRunRequest,
    ) -> dict[str, Any]:
        result = self.decision_service.evaluate_run(
            DecisionEvaluationRequest(
                run_id=run_id,
                risk_profile=request.risk_profile,
                timeframe=request.timeframe,
                apply_to_run=False,
                force=True,
            )
        )
        if hasattr(result, "model_dump"):
            return result.model_dump(mode="json", exclude={"decision"})
        return self._sanitize_payload(result)

    def _complete_validation(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        policy: ValidationPolicy,
        split: dict[str, Any],
        oos_result: OOSValidationResult,
        wfo_result: Optional[WFOValidationResult],
        robustness_results: list[RobustnessCheckResult],
        sensitivity_results: list[RobustnessCheckResult],
        final_decision: ValidationDecision,
        evidence_ids: list[str],
        artifact_paths: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> ValidationRunResponse:
        decision_evidence = self._save_evidence(
            validation_run_id,
            "validation_decision",
            final_decision.decision_status,
            None,
            {},
            final_decision.model_dump(mode="json"),
            [],
            final_decision.warnings,
            [],
        )
        evidence_ids.append(decision_evidence["id"])
        self.validation_repository.save_decision(
            validation_run_id,
            final_decision.model_dump(mode="json"),
            final_decision.decision_status,
        )
        report_path = self._write_report(
            validation_run_id,
            request,
            candidate,
            policy,
            split,
            oos_result,
            wfo_result,
            robustness_results,
            sensitivity_results,
            final_decision,
            evidence_ids,
            artifact_paths,
            warnings,
            errors,
        )
        self.validation_repository.update_validation_run(
            validation_run_id,
            {
                "status": "completed",
                "summary": {
                    "decision_status": final_decision.decision_status,
                    "evidence_count": len(evidence_ids),
                    "oos_status": oos_result.status,
                    "wfo_status": wfo_result.status if wfo_result else None,
                    "robustness_count": len(robustness_results),
                    "sensitivity_count": len(sensitivity_results),
                },
                "report_artifact_path": report_path,
            },
        )
        return self._response(
            validation_run_id,
            request,
            candidate,
            "completed",
            final_decision.decision_status,
            warnings=final_decision.warnings + warnings,
            errors=errors,
            next_actions=final_decision.next_actions,
        )

    def _write_report(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        policy: ValidationPolicy,
        split: dict[str, Any],
        oos_result: OOSValidationResult,
        wfo_result: Optional[WFOValidationResult],
        robustness_results: list[RobustnessCheckResult],
        sensitivity_results: list[RobustnessCheckResult],
        final_decision: ValidationDecision,
        evidence_ids: list[str],
        artifact_paths: list[str],
        warnings: list[str],
        errors: list[str],
    ) -> str:
        relative_path = self.REPORT_RELATIVE_PATH.format(validation_run_id=validation_run_id)
        report_path = self.project_root / relative_path
        try:
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report = {
                "request": self._sanitize_payload(request.model_dump(mode="json")),
                "candidate_reference": self._sanitize_payload(candidate),
                "policy": self.policy_service.build_policy_summary(policy),
                "oos_result": oos_result.model_dump(mode="json"),
                "wfo_result": wfo_result.model_dump(mode="json") if wfo_result else None,
                "robustness_checks": [
                    check.model_dump(mode="json") for check in robustness_results
                ],
                "sensitivity_checks": [
                    check.model_dump(mode="json") for check in sensitivity_results
                ],
                "final_decision": final_decision.model_dump(mode="json"),
                "evidence_ids": evidence_ids,
                "artifact_paths": artifact_paths,
                "warnings": warnings,
                "errors": errors,
                "next_actions": final_decision.next_actions,
                "no_guarantee_statement": self.NO_GUARANTEE_STATEMENT,
            }
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        except Exception as exc:
            raise ValueError(f"validation_report_failed: {self._safe_exception_message(exc)}") from exc
        return relative_path

    def _controlled_failure(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        code: str,
        message: str,
        next_actions: Optional[list[str]] = None,
    ) -> ValidationRunResponse:
        safe_message = self._safe_error(code, message)
        self.validation_repository.update_validation_run(
            validation_run_id,
            {
                "status": "failed_controlled",
                "decision_status": "validation_error",
                "summary": {
                    "error_code": code,
                    "errors": [safe_message],
                    "next_actions": next_actions or ["Review validation evidence and retry."],
                },
            },
        )
        return self._response(
            validation_run_id,
            request,
            candidate,
            "failed_controlled",
            "validation_error",
            errors=[safe_message],
            next_actions=next_actions or ["Review validation evidence and retry."],
        )

    def _confirmation_required(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
    ) -> ValidationRunResponse:
        message = "confirmation_required: user confirmation is required before running validation backtests"
        self.validation_repository.update_validation_run(
            validation_run_id,
            {
                "status": "confirmation_required",
                "decision_status": "not_validated",
                "summary": {
                    "error_code": "confirmation_required",
                    "warnings": [message],
                    "next_actions": ["Confirm validation execution before running Freqtrade backtests."],
                },
            },
        )
        return self._response(
            validation_run_id,
            request,
            candidate,
            "confirmation_required",
            "not_validated",
            warnings=[message],
            next_actions=["Confirm validation execution before running Freqtrade backtests."],
        )

    def _save_evidence(
        self,
        validation_run_id: str,
        evidence_type: str,
        status: str,
        timerange: Optional[str],
        metrics: dict[str, Any],
        decision: dict[str, Any],
        issues: list[ValidationIssue],
        warnings: list[str],
        artifact_paths: list[str],
        window_index: Optional[int] = None,
    ) -> dict[str, Any]:
        return self.validation_repository.create_evidence(
            {
                "validation_run_id": validation_run_id,
                "evidence_type": evidence_type,
                "status": self._evidence_status(status),
                "window_index": window_index,
                "timerange": timerange,
                "metrics": self._sanitize_payload(metrics),
                "decision": self._sanitize_payload(decision),
                "issues": [issue.model_dump(mode="json") for issue in issues],
                "warnings": warnings,
                "artifact_paths": artifact_paths,
            }
        )

    def _apply_sensitivity_to_final_decision(
        self,
        final_decision: ValidationDecision,
        sensitivity_results: list[RobustnessCheckResult],
        policy: ValidationPolicy,
    ) -> ValidationDecision:
        if not sensitivity_results:
            return final_decision

        failed_checks = []
        blocking_failures = list(final_decision.blocking_failures)
        for check in sensitivity_results:
            severities = {issue.severity for issue in check.issues}
            if check.status != "passed" or severities & {"error", "critical", "blocking"}:
                failed_checks.append(check.check_name)
                blocking_failures.append(f"sensitivity_failed:{check.check_name}")
                blocking_failures.extend(issue.code for issue in check.issues)

        if not failed_checks:
            return final_decision

        return ValidationDecision(
            decision_status="rejected",
            confidence_score=0.0,
            policy_name=policy.policy_name,
            reasons=self._unique(
                final_decision.reasons
                + [f"Sensitivity check failed: {name}." for name in failed_checks]
            ),
            blocking_failures=self._unique(blocking_failures),
            warnings=final_decision.warnings,
            next_actions=self._unique(
                final_decision.next_actions
                + ["Review failed sensitivity evidence before continuing."]
            ),
        )

    def _evidence_status(self, status: str) -> str:
        if status == "passed":
            return "completed"
        if status == "warning":
            return "completed"
        if status == "failed":
            return "rejected"
        return status

    def _response(
        self,
        validation_run_id: str,
        request: ValidationRunRequest,
        candidate: dict[str, Any],
        status: str,
        decision_status: str,
        warnings: Optional[list[str]] = None,
        errors: Optional[list[str]] = None,
        next_actions: Optional[list[str]] = None,
    ) -> ValidationRunResponse:
        return ValidationRunResponse(
            validation_run_id=validation_run_id,
            status=status,
            decision_status=decision_status,
            strategy_name=candidate.get("strategy_name") or request.strategy_name,
            pairs=candidate.get("pairs") or request.pairs,
            timeframe=candidate.get("timeframe") or request.timeframe,
            exchange=candidate.get("exchange") or request.exchange,
            risk_profile=request.risk_profile,
            warnings=warnings or [],
            errors=errors or [],
            next_actions=next_actions or [],
        )

    def _wfo_config_from_request(self, request: ValidationRunRequest) -> dict[str, Any]:
        return {
            "enabled": request.wfo_enabled,
            "train_days": request.wfo_train_days,
            "test_days": request.wfo_test_days,
            "step_days": request.wfo_step_days,
            "max_windows": request.wfo_max_windows,
        }

    def _metrics_from_snapshot(self, snapshot: dict[str, Any]) -> dict[str, Any]:
        return {
            "net_profit": snapshot.get("net_profit"),
            "profit_factor": snapshot.get("profit_factor"),
            "max_drawdown": snapshot.get("max_drawdown"),
            "sharpe": snapshot.get("sharpe"),
            "calmar": snapshot.get("calmar"),
            "win_rate": snapshot.get("win_rate"),
            "trade_count": snapshot.get("trade_count"),
            "expectancy": snapshot.get("expectancy"),
            "avg_win": snapshot.get("avg_win"),
            "avg_loss": snapshot.get("avg_loss"),
        }

    def _metrics_from_parse_result(self, parse_result: Any) -> dict[str, Any]:
        metrics = getattr(parse_result, "metrics", None)
        if metrics is None and isinstance(parse_result, dict):
            metrics = parse_result.get("metrics")
        if metrics is None:
            return {}
        if hasattr(metrics, "metrics") and isinstance(metrics.metrics, dict):
            return dict(metrics.metrics)
        if hasattr(metrics, "model_dump"):
            return metrics.model_dump(mode="json")
        if isinstance(metrics, dict):
            return dict(metrics)
        return {}

    def _artifact_paths(self, backtest_result: Any, parse_result: Any, config_result: Any) -> list[str]:
        paths = []
        config_path = getattr(config_result, "config_path", None)
        if config_path:
            paths.append(self._project_relative_path(config_path))
        for artifact in getattr(backtest_result, "artifacts", []) or []:
            path = getattr(artifact, "path", None)
            if path:
                paths.append(self._project_relative_path(path))
        normalized = getattr(parse_result, "normalized_result_path", None)
        if normalized:
            paths.append(self._project_relative_path(normalized))
        return self._unique([path for path in paths if path])

    def _project_relative_path(self, path: str | Path) -> str:
        raw_path = Path(path)
        try:
            return raw_path.resolve().relative_to(self.project_root).as_posix()
        except Exception:
            return raw_path.as_posix().lstrip("/")

    def _controlled_code_for_value_error(self, message: str) -> str:
        prefix = message.split(":", 1)[0].strip()
        allowed = {
            "candidate_reference_missing",
            "optimization_run_not_found",
            "optimized_run_missing",
            "oos_timerange_invalid",
            "oos_backtest_failed",
            "oos_parse_failed",
            "wfo_window_generation_failed",
            "wfo_backtest_failed",
            "wfo_parse_failed",
            "robustness_failed",
            "validation_decision_failed",
            "validation_report_failed",
        }
        if prefix in allowed:
            return prefix
        if prefix.endswith("_backtest_failed"):
            return "wfo_backtest_failed" if prefix.startswith("wfo") else "oos_backtest_failed"
        if prefix.endswith("_parse_failed"):
            return "wfo_parse_failed" if prefix.startswith("wfo") else "oos_parse_failed"
        return "unexpected_validation_error"

    def _safe_error(self, code: str, message: str) -> str:
        cleaned = self._safe_exception_message(message)
        if cleaned.startswith(f"{code}:"):
            return cleaned
        return f"{code}: {cleaned}"

    def _safe_exception_message(self, exc: Any) -> str:
        message = str(exc).replace("\n", " ").strip()
        if not message:
            return "validation failed"
        blocked_terms = ["traceback", "api_key", "apikey", "secret", "password", "token"]
        lower = message.lower()
        if any(term in lower for term in blocked_terms):
            return "validation failed with sanitized error details"
        return message[:500]

    def _http_exception_message(self, exc: HTTPException) -> str:
        detail = exc.detail
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("error") or "strategy is not ready")
        return str(detail or "strategy is not ready")

    def _sanitize_payload(self, payload: Any) -> Any:
        if hasattr(payload, "model_dump"):
            payload = payload.model_dump(mode="json")
        if isinstance(payload, dict):
            sanitized = {}
            for key, value in payload.items():
                lower = str(key).lower()
                if any(term in lower for term in ("api_key", "apikey", "secret", "password", "token")):
                    sanitized[key] = "[redacted]"
                elif lower in {"stdout", "stderr"}:
                    continue
                else:
                    sanitized[key] = self._sanitize_payload(value)
            return sanitized
        if isinstance(payload, list):
            return [self._sanitize_payload(item) for item in payload]
        return payload

    def _unique(self, values: list[str]) -> list[str]:
        seen = set()
        result = []
        for value in values:
            if value and value not in seen:
                seen.add(value)
                result.append(value)
        return result
