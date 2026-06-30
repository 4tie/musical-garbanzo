"""
Validation evidence API router for Part 13.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query

from app.core.config import settings
from app.repositories.validation import ValidationRepository
from app.schemas.validation import (
    ValidationRunAPIListItem,
    ValidationRunRequest,
    ValidationRunResponse,
    ValidationStatusResponse,
)
from app.services.validation_execution_service import ValidationExecutionService


router = APIRouter(prefix="/validation", tags=["Validation"])


@router.post("/run", response_model=ValidationRunResponse)
def run_validation(request: ValidationRunRequest) -> ValidationRunResponse:
    """
    Run validation evidence collection.

    Requires `user_confirmed=true` before real validation backtests execute.
    Strategy readiness is enforced by `ValidationExecutionService`.
    """
    try:
        return ValidationExecutionService().run_validation(request)
    except Exception as exc:
        return ValidationRunResponse(
            validation_run_id="validation-run-not-created",
            status="failed_controlled",
            decision_status="validation_error",
            strategy_name=request.strategy_name,
            pairs=request.pairs,
            timeframe=request.timeframe,
            exchange=request.exchange,
            risk_profile=request.risk_profile,
            errors=[_safe_error("unexpected_validation_error", str(exc))],
            next_actions=["Review validation request and backend logs before retrying."],
        )


@router.get("/runs", response_model=list[ValidationRunAPIListItem])
def list_validation_runs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    status: Optional[str] = None,
    decision_status: Optional[str] = None,
    source_type: Optional[str] = None,
    strategy_name: Optional[str] = None,
) -> list[ValidationRunAPIListItem]:
    """Return frontend-ready validation run list items."""
    repo = ValidationRepository()
    runs = repo.list_validation_runs(
        strategy_name=strategy_name,
        status=status,
        decision_status=decision_status,
        source_type=source_type,
        limit=limit,
        offset=offset,
    )
    return [_list_item(run) for run in runs]


@router.get("/runs/{validation_run_id}", response_model=dict[str, Any])
def get_validation_run(validation_run_id: str) -> dict[str, Any]:
    """Return full validation run detail."""
    repo = ValidationRepository()
    run = _get_run_or_404(repo, validation_run_id)
    evidence = repo.list_evidence(validation_run_id)
    return _detail_payload(run, evidence)


@router.get("/runs/{validation_run_id}/status", response_model=ValidationStatusResponse)
def get_validation_status(validation_run_id: str) -> ValidationStatusResponse:
    """Return lightweight validation status."""
    repo = ValidationRepository()
    run = _get_run_or_404(repo, validation_run_id)
    evidence = repo.list_evidence(validation_run_id)
    summary = run.get("summary") or {}
    completed_stages = _completed_stages(run, evidence)
    failed_stage = _failed_stage(run, evidence)
    return ValidationStatusResponse(
        validation_run_id=run["id"],
        status=run["status"],
        decision_status=run.get("decision_status"),
        current_stage=_current_stage(run, completed_stages, failed_stage),
        evidence_count=len(evidence),
        message=summary.get("message"),
        completed_stages=completed_stages,
        failed_stage=failed_stage,
        summary=summary,
        warnings=summary.get("warnings", []),
        errors=summary.get("errors", []),
        created_at=run["created_at"],
        updated_at=run["updated_at"],
    )


@router.get("/runs/{validation_run_id}/evidence", response_model=dict[str, Any])
def get_validation_evidence(validation_run_id: str) -> dict[str, Any]:
    """Return all validation evidence grouped by evidence type."""
    repo = ValidationRepository()
    _get_run_or_404(repo, validation_run_id)
    evidence = repo.list_evidence(validation_run_id)
    if not evidence:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "not_found",
                "message": f"Validation evidence not found for run {validation_run_id}",
            },
        )
    return {
        "validation_run_id": validation_run_id,
        "evidence": _sanitize(evidence),
        "oos": [item for item in evidence if item.get("evidence_type") == "oos"],
        "wfo_windows": [
            item for item in evidence if item.get("evidence_type") == "wfo_window"
        ],
        "wfo_summary": [
            item for item in evidence if item.get("evidence_type") == "wfo_summary"
        ],
        "robustness": [
            item for item in evidence if item.get("evidence_type") == "robustness"
        ],
        "sensitivity": [
            item for item in evidence if item.get("evidence_type") == "sensitivity"
        ],
    }


@router.get("/runs/{validation_run_id}/report", response_model=dict[str, Any])
def get_validation_report(validation_run_id: str) -> dict[str, Any]:
    """Return validation report JSON if available."""
    repo = ValidationRepository()
    run = _get_run_or_404(repo, validation_run_id)
    report_path = run.get("report_artifact_path")
    if not report_path:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "not_found",
                "message": f"Validation report not found for run {validation_run_id}",
            },
        )

    path = _safe_project_path(report_path)
    if not path.exists():
        raise HTTPException(
            status_code=404,
            detail={
                "type": "not_found",
                "message": f"Validation report artifact is missing for run {validation_run_id}",
            },
        )
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "type": "system_error",
                "message": _safe_error("report_read_failed", str(exc)),
            },
        ) from exc

    return {
        "validation_run_id": validation_run_id,
        "report_artifact_path": report_path,
        "report": _sanitize(content),
    }


def _get_run_or_404(repo: ValidationRepository, validation_run_id: str) -> dict[str, Any]:
    run = repo.get_validation_run(validation_run_id)
    if not run:
        raise HTTPException(
            status_code=404,
            detail={
                "type": "not_found",
                "message": f"Validation run {validation_run_id} not found",
            },
        )
    return run


def _list_item(run: dict[str, Any]) -> ValidationRunAPIListItem:
    return ValidationRunAPIListItem(
        validation_run_id=run["id"],
        strategy_name=run["strategy_name"],
        source_type=run["source_type"],
        source_run_id=run.get("source_run_id"),
        pairs=run.get("pairs") or [],
        timeframe=run["timeframe"],
        status=run["status"],
        decision_status=run.get("decision_status"),
        created_at=run["created_at"],
        updated_at=run["updated_at"],
        summary=run.get("summary"),
    )


def _detail_payload(run: dict[str, Any], evidence: list[dict[str, Any]]) -> dict[str, Any]:
    grouped = _group_evidence(evidence)
    summary = run.get("summary") or {}
    decision = run.get("decision")
    return _sanitize(
        {
            "run": {
                "validation_run_id": run["id"],
                "source_type": run["source_type"],
                "source_run_id": run.get("source_run_id"),
                "strategy_name": run["strategy_name"],
                "pairs": run.get("pairs") or [],
                "timeframe": run["timeframe"],
                "exchange": run.get("exchange"),
                "risk_profile": run.get("risk_profile"),
                "status": run["status"],
                "decision_status": run.get("decision_status"),
                "timerange": run.get("timerange"),
                "oos_timerange": run.get("oos_timerange"),
                "created_at": run.get("created_at"),
                "updated_at": run.get("updated_at"),
            },
            "request": run.get("request"),
            "candidate_reference": (run.get("request") or {}),
            "oos_summary": grouped["oos"][0] if grouped["oos"] else None,
            "wfo_summary": grouped["wfo_summary"][0] if grouped["wfo_summary"] else None,
            "robustness_summary": {
                "checks": grouped["robustness"],
                "count": len(grouped["robustness"]),
            },
            "sensitivity_summary": {
                "checks": grouped["sensitivity"],
                "count": len(grouped["sensitivity"]),
            },
            "final_decision": decision,
            "report_path": run.get("report_artifact_path"),
            "evidence": evidence,
            "warnings": summary.get("warnings", []),
            "errors": summary.get("errors", []),
            "next_actions": summary.get("next_actions", []),
            "summary": summary,
        }
    )


def _group_evidence(evidence: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    return {
        "oos": [item for item in evidence if item.get("evidence_type") == "oos"],
        "wfo_window": [
            item for item in evidence if item.get("evidence_type") == "wfo_window"
        ],
        "wfo_summary": [
            item for item in evidence if item.get("evidence_type") == "wfo_summary"
        ],
        "robustness": [
            item for item in evidence if item.get("evidence_type") == "robustness"
        ],
        "sensitivity": [
            item for item in evidence if item.get("evidence_type") == "sensitivity"
        ],
        "validation_decision": [
            item for item in evidence if item.get("evidence_type") == "validation_decision"
        ],
    }


def _completed_stages(run: dict[str, Any], evidence: list[dict[str, Any]]) -> list[str]:
    stages = ["validation_setup", "candidate_reference"]
    if run.get("status") != "confirmation_required":
        stages.append("readiness_gate")
    types = {item.get("evidence_type") for item in evidence}
    if "oos" in types:
        stages.extend(["oos_timerange_split", "oos_backtest", "oos_result_parsing", "oos_decision"])
    if "wfo_window" in types:
        stages.extend(["wfo_window_generation", "wfo_window_execution", "wfo_result_parsing"])
    if "wfo_summary" in types:
        stages.append("wfo_decision")
    if "robustness" in types:
        stages.append("robustness_checks")
    if "sensitivity" in types:
        stages.append("sensitivity_checks")
    if "validation_decision" in types or run.get("decision"):
        stages.append("validation_decision")
    if run.get("report_artifact_path"):
        stages.append("validation_report")
    if run.get("status") == "completed":
        stages.append("completion")
    return _unique(stages)


def _failed_stage(run: dict[str, Any], evidence: list[dict[str, Any]]) -> Optional[str]:
    summary = run.get("summary") or {}
    error_code = summary.get("error_code")
    if error_code:
        return _stage_from_error_code(error_code)
    failed = [item for item in evidence if item.get("status") in {"rejected", "validation_error"}]
    if failed:
        return _stage_from_evidence_type(failed[0].get("evidence_type"))
    return None


def _current_stage(
    run: dict[str, Any],
    completed_stages: list[str],
    failed_stage: Optional[str],
) -> Optional[str]:
    if failed_stage:
        return failed_stage
    if run.get("status") in {"completed", "failed_controlled"}:
        return None
    if run.get("status") == "confirmation_required":
        return "confirmation_required"
    return completed_stages[-1] if completed_stages else "validation_setup"


def _stage_from_error_code(error_code: str) -> str:
    if error_code.startswith("oos_timerange"):
        return "oos_timerange_split"
    if error_code.startswith("oos_backtest"):
        return "oos_backtest"
    if error_code.startswith("oos_parse"):
        return "oos_result_parsing"
    if error_code.startswith("wfo_window"):
        return "wfo_window_generation"
    if error_code.startswith("wfo_backtest"):
        return "wfo_window_execution"
    if error_code.startswith("wfo_parse"):
        return "wfo_result_parsing"
    if error_code.startswith("robustness"):
        return "robustness_checks"
    if error_code.startswith("validation_decision"):
        return "validation_decision"
    if error_code.startswith("validation_report"):
        return "validation_report"
    if error_code.startswith("strategy_not_ready"):
        return "readiness_gate"
    return "validation_setup"


def _stage_from_evidence_type(evidence_type: Optional[str]) -> Optional[str]:
    return {
        "oos": "oos_decision",
        "wfo_window": "wfo_window_execution",
        "wfo_summary": "wfo_decision",
        "robustness": "robustness_checks",
        "sensitivity": "sensitivity_checks",
        "validation_decision": "validation_decision",
    }.get(evidence_type or "")


def _safe_project_path(path: str) -> Path:
    project_root = settings.project_root.resolve()
    candidate = (project_root / path).resolve()
    try:
        candidate.relative_to(project_root)
    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "type": "validation_error",
                "message": "Report path must be project-relative.",
            },
        ) from exc
    return candidate


def _safe_error(code: str, message: str) -> str:
    cleaned = str(message).replace("\n", " ").strip()
    lower = cleaned.lower()
    if any(term in lower for term in ("traceback", "api_key", "apikey", "secret", "password", "token")):
        cleaned = "validation API error details were sanitized"
    return f"{code}: {cleaned[:300]}"


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lower = str(key).lower()
            if lower in {"stdout", "stderr"}:
                continue
            if any(term in lower for term in ("api_key", "apikey", "secret", "password", "token")):
                result[key] = "[redacted]"
            else:
                result[key] = _sanitize(item)
        return result
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value


def _unique(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result
