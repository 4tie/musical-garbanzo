"""
Part 06 decision service.

Connects parsed Part 05 evidence to the in-memory decision engine, decision
persistence, optional safe run classification updates, logs, audit entries, and
decision report artifacts.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.decisions import DecisionRepository
from app.repositories.logs import RunLogRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.runs import RunRepository
from app.schemas.artifacts import ArtifactCreate
from app.schemas.backtest_results import ResultQualityReport
from app.schemas.decisions import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionResult,
)
from app.services.decision_engine import DecisionEngine
from app.services.decision_policy import DecisionPolicyService
from app.services.result_quality_service import ResultQualityService


class DecisionService:
    """Evaluate a run's parsed evidence and persist the decision result."""

    STAGE_KEY = "decision_engine"
    REPORT_RELATIVE_PATH = "artifacts/runs/{run_id}/decisions/decision_result.json"

    def __init__(
        self,
        run_repository: Optional[RunRepository] = None,
        metrics_repository: Optional[MetricsRepository] = None,
        artifact_repository: Optional[ArtifactRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
        log_repository: Optional[RunLogRepository] = None,
        decision_repository: Optional[DecisionRepository] = None,
        policy_service: Optional[DecisionPolicyService] = None,
        decision_engine: Optional[DecisionEngine] = None,
        quality_service: Optional[ResultQualityService] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.project_root = (project_root or settings.project_root).resolve()
        self.run_repository = run_repository or RunRepository()
        self.metrics_repository = metrics_repository or MetricsRepository()
        self.artifact_repository = artifact_repository or ArtifactRepository()
        self.audit_repository = audit_repository or AuditLogRepository()
        self.log_repository = log_repository or RunLogRepository()
        self.decision_repository = decision_repository or DecisionRepository()
        self.policy_service = policy_service or DecisionPolicyService()
        self.decision_engine = decision_engine or DecisionEngine(self.policy_service)
        self.quality_service = quality_service or ResultQualityService()

    def evaluate_run(
        self,
        request: DecisionEvaluationRequest,
    ) -> DecisionEvaluationResponse:
        """Evaluate parsed evidence for a run and persist the decision."""
        run = self.run_repository.get_run(request.run_id)
        if not run:
            return self._failure_response(
                request.run_id,
                "run_not_found",
                ["Run was not found."],
            )

        evidence = self.load_latest_parsed_evidence(request.run_id)
        if evidence.get("error"):
            return self._failure_response(
                request.run_id,
                evidence["error"],
                evidence.get("errors", []),
                warnings=evidence.get("warnings", []),
            )

        if request.force:
            self.decision_repository.delete_decisions_for_run(request.run_id)

        self.log_repository.add_log(
            run_id=request.run_id,
            level="info",
            source="decision_service",
            message="decision_evaluation_started",
            stage_key=self.STAGE_KEY,
            details={
                "policy_name": request.policy_name,
                "risk_profile": request.risk_profile or run.get("risk_profile"),
                "timeframe": request.timeframe or run.get("timeframe"),
                "force": request.force,
            },
        )

        policy = self.policy_service.get_policy(
            policy_name=request.policy_name,
            risk_profile=request.risk_profile or run.get("risk_profile"),
            timeframe=request.timeframe or run.get("timeframe"),
        )
        decision = self.decision_engine.evaluate(
            evidence["metrics"],
            evidence["pair_results"],
            evidence["trade_summary"],
            quality_report=evidence["quality_report"],
            policy=policy,
            run_id=request.run_id,
        )

        saved = self.save_decision(decision)
        saved_decision_id = saved["id"]
        decision.id = saved_decision_id

        artifact = self.write_decision_report_artifact(request.run_id, decision)
        run_updated = False
        if request.apply_to_run:
            self.apply_decision_to_run(request.run_id, decision.classification)
            run_updated = True

        self.add_decision_logs(request.run_id, decision)
        self.add_decision_audit(request.run_id, decision)

        report_path = artifact["file_path"]
        return DecisionEvaluationResponse(
            run_id=request.run_id,
            success=True,
            decision=decision,
            saved_decision_id=saved_decision_id,
            decision_report_path=report_path,
            run_updated=run_updated,
            decision_id=saved_decision_id,
            classification=decision.classification,
            confidence_score=decision.confidence_score,
            policy_name=decision.policy_name,
            gates=decision.gates,
            reasons=decision.reasons,
            warnings=decision.warnings,
            blocking_failures=decision.blocking_failures,
            next_actions=decision.next_actions,
        )

    def load_latest_parsed_evidence(self, run_id) -> dict:
        """Load latest Part 05 parsed evidence for a run."""
        run = self.run_repository.get_run(run_id)
        if not run:
            return {
                "error": "run_not_found",
                "errors": ["Run was not found."],
                "warnings": [],
            }

        metrics = self.metrics_repository.get_latest_metric_snapshot(run_id)
        if not metrics:
            return {
                "error": "parsed_metrics_missing",
                "errors": [
                    "Parsed metrics are missing. Run the Part 05 parse endpoint or script first."
                ],
                "warnings": [],
            }

        pair_results = self.metrics_repository.list_pair_results(run_id)
        trade_summary = self.metrics_repository.get_trade_summary(run_id)
        quality_report = self.load_quality_report(run_id)
        if quality_report is None:
            quality_report = ResultQualityReport(
                run_id=run_id,
                parse_quality="ok",
                flags=[],
                warnings=[],
                errors=[],
                is_usable_for_metrics=True,
                is_usable_for_decision=True,
            )

        normalized_artifact = self._get_normalized_artifact(run_id)
        normalized_path = normalized_artifact["file_path"] if normalized_artifact else None
        if normalized_path:
            metrics["normalized_result_artifact_path"] = normalized_path

        return {
            "run": run,
            "metrics": metrics,
            "pair_results": pair_results,
            "trade_summary": trade_summary,
            "quality_report": quality_report,
            "normalized_result_artifact_path": normalized_path,
            "warnings": [],
            "errors": [],
        }

    def load_quality_report(self, run_id):
        """Load the latest Part 05 quality report from audit evidence or artifact."""
        audits = self.audit_repository.list_audit_logs(
            run_id=run_id,
            action_type="backtest_result_quality",
            limit=1,
        )
        if audits and audits[0].get("after"):
            return ResultQualityReport.model_validate(audits[0]["after"])

        normalized_artifact = self._get_normalized_artifact(run_id)
        if normalized_artifact:
            artifact_path = self.project_root / normalized_artifact["file_path"]
            if artifact_path.exists():
                payload = json.loads(artifact_path.read_text(encoding="utf-8"))
                if "quality_report" in payload:
                    return ResultQualityReport.model_validate(payload["quality_report"])
                if "quality_flags" in payload:
                    return ResultQualityReport(
                        run_id=run_id,
                        parse_quality="warning" if payload["quality_flags"] else "ok",
                        flags=payload["quality_flags"],
                        is_usable_for_metrics=True,
                        is_usable_for_decision=True,
                    )
        return None

    def save_decision(self, result: DecisionResult) -> dict:
        """Persist a decision result."""
        return self.decision_repository.create_decision_result(result)

    def apply_decision_to_run(self, run_id, classification) -> dict:
        """Apply a safe Part 06 classification to a run."""
        return self.run_repository.set_decision_classification(run_id, classification)

    def write_decision_report_artifact(self, run_id, result) -> dict:
        """Write and register the decision report artifact."""
        artifact_path = self.project_root / self.REPORT_RELATIVE_PATH.format(run_id=run_id)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
        artifact_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload_bytes = artifact_path.read_bytes()
        sha256 = hashlib.sha256(payload_bytes).hexdigest()
        return self.artifact_repository.create_or_update_artifact(
            ArtifactCreate(
                run_id=run_id,
                artifact_type="metrics_json",
                file_path=str(artifact_path),
                description="Decision engine result",
                sha256=sha256,
                size_bytes=len(payload_bytes),
            )
        )

    def add_decision_logs(self, run_id, result) -> None:
        """Add decision completion logs."""
        self.log_repository.add_log(
            run_id=run_id,
            level="info",
            source="decision_service",
            message="decision_evaluation_completed",
            stage_key=self.STAGE_KEY,
            details={
                "classification": result.classification,
                "confidence_score": result.confidence_score,
                "blocking_failures_count": len(result.blocking_failures),
            },
        )
        if result.classification == "rejected":
            self.log_repository.add_log(
                run_id=run_id,
                level="warning",
                source="decision_service",
                message=(
                    "Run classification was set from strategy decision evidence; "
                    "integration validation status is separate."
                ),
                stage_key=self.STAGE_KEY,
                details={"classification": result.classification},
            )

    def add_decision_audit(self, run_id, result) -> dict:
        """Add audit evidence for a decision evaluation."""
        payload = result.model_dump(mode="json") if hasattr(result, "model_dump") else result.dict()
        return self.audit_repository.create_audit_log(
            {
                "run_id": run_id,
                "actor": "system",
                "action_type": "decision_evaluation",
                "target_type": "run",
                "target_id": run_id,
                "after": payload,
                "approved": False,
                "description": "Decision engine evaluation completed",
            }
        )

    def _get_normalized_artifact(self, run_id: str) -> Optional[dict]:
        """Return the normalized Part 05 artifact row if present."""
        artifacts = self.artifact_repository.list_artifacts(
            run_id=run_id,
            artifact_type="metrics_json",
            limit=100,
        )
        for artifact in artifacts:
            if artifact["file_path"].endswith("normalized/backtest_result.normalized.json"):
                return artifact
        return None

    def _failure_response(
        self,
        run_id: str,
        error_code: str,
        errors: list[str],
        warnings: Optional[list[str]] = None,
    ) -> DecisionEvaluationResponse:
        """Return a controlled failure response."""
        return DecisionEvaluationResponse(
            run_id=run_id,
            success=False,
            run_updated=False,
            warnings=warnings or [],
            errors=[error_code, *errors],
            next_actions=["Run the Part 05 parse endpoint or script first."],
        )
