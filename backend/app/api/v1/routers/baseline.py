"""
API router for Part 07 baseline evaluation.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from app.repositories.artifacts import ArtifactRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.runs import RunRepository
from app.repositories.run_stages import RunStageRepository
from app.schemas.baseline import (
    BaselineEvaluationRequest,
    BaselineEvaluationResult,
    BaselineStatusResponse,
)
from app.services.baseline_evaluation_service import BaselineEvaluationService
from app.services.strategy_readiness_gate import assert_strategy_ready_for_run


router = APIRouter(tags=["Baseline Evaluation"])


@router.post("/baseline/evaluate", response_model=BaselineEvaluationResult)
def evaluate_baseline(request: BaselineEvaluationRequest) -> BaselineEvaluationResult:
    """
    Evaluate an existing strategy baseline.

    This endpoint orchestrates the complete baseline evaluation pipeline:
    - Validates strategy readiness (Part 12)
    - Validates strategy exists and is safe
    - Generates backtest config
    - Checks data availability
    - Downloads data (if allowed and confirmed)
    - Runs backtest (if confirmed)
    - Parses results
    - Evaluates decision gates
    - Generates report

    Confirmation rules:
    - Requires user_confirmed=true before real Freqtrade backtest
    - Requires both download_missing_data=true and user_confirmed=true before data download

    This endpoint may take time because it can run a real Freqtrade backtest.
    Synchronous local execution is used (no background workers in Part 07).
    """
    # Part 12: Check strategy readiness before starting baseline evaluation
    assert_strategy_ready_for_run(request.strategy_name, run_type="baseline")

    service = BaselineEvaluationService(
        run_repository=RunRepository(),
        run_stage_repository=RunStageRepository(),
        artifact_repository=ArtifactRepository(),
        log_repository=None,  # Will be created by service
        audit_log_repository=None,  # Will be created by service
        strategy_service=None,  # Will be created by service
        config_generator=None,  # Will be created by service
        data_service=None,  # Will be created by service
        backtest_runner=None,  # Will be created by service
        result_parser=None,  # Will be created by service
        decision_service=None,  # Will be created by service
        project_root=None,  # Will be created by service
    )

    try:
        result = service.evaluate(request)
        return result
    except Exception as exc:
        # Convert unexpected exceptions to controlled failure
        raise HTTPException(
            status_code=500,
            detail="Baseline evaluation failed. Check run logs for details.",
        ) from exc


@router.get("/baseline/runs/{run_id}", response_model=dict[str, Any])
def get_baseline_run(run_id: str) -> dict[str, Any]:
    """
    Return full baseline run summary.

    Includes:
    - run metadata
    - stages
    - latest metrics
    - latest decision
    - artifacts
    - warnings/errors
    """
    run_repo = RunRepository()
    stage_repo = RunStageRepository()
    metrics_repo = MetricsRepository()
    artifact_repo = ArtifactRepository()

    # Get run
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Get stages
    stages = stage_repo.list_stages(run_id)

    # Get latest metrics
    metrics = metrics_repo.get_latest_metric_snapshot(run_id)
    metrics_data = metrics if metrics else {}

    # Get decision (if exists)
    decision = {}
    if run.classification:
        decision = {
            "classification": run.classification,
            "confidence_score": run.confidence_score,
        }

    # Get artifacts
    artifacts = artifact_repo.list_run_artifacts(run_id)
    artifact_paths = [a.file_path for a in artifacts if a.file_path]

    return {
        "run_id": run.id,
        "status": run.status,
        "classification": run.classification,
        "confidence_score": run.confidence_score,
        "mode": run.mode,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at else None,
        "stages": [
            {
                "stage_name": s.stage_name,
                "status": s.status,
                "started_at": s.started_at.isoformat() if s.started_at else None,
                "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                "duration_ms": s.duration_ms,
                "message": s.logs_summary,
                "error_data": s.error_data,
            }
            for s in stages
        ],
        "metrics": metrics_data,
        "decision": decision,
        "artifacts": artifact_paths,
        "warnings": [],
        "errors": [],
    }


@router.get("/baseline/runs/{run_id}/status", response_model=BaselineStatusResponse)
def get_baseline_status(run_id: str) -> BaselineStatusResponse:
    """
    Return lightweight status for a baseline evaluation run.

    Includes:
    - run_id
    - status
    - classification
    - current_stage
    - stage_results
    - warnings/errors
    """
    run_repo = RunRepository()
    stage_repo = RunStageRepository()
    metrics_repo = MetricsRepository()

    # Get run
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")

    # Get stages
    stages = stage_repo.list_stages(run_id)

    # Find current stage (last non-completed stage)
    current_stage = None
    for stage in reversed(stages):
        if stage.status not in ("passed", "completed"):
            current_stage = stage.stage_name
            break

    # Get latest metrics
    metrics = metrics_repo.get_latest_metric_snapshot(run_id)
    metrics_data = metrics if metrics else {}

    # Build stage results
    stage_results = [
        {
            "stage_name": s.stage_name,
            "status": s.status,
            "started_at": s.started_at.isoformat() if s.started_at else None,
            "completed_at": s.completed_at.isoformat() if s.completed_at else None,
            "duration_seconds": s.duration_ms / 1000.0 if s.duration_ms else None,
            "message": s.logs_summary,
            "error_code": s.error_data.get("error_code") if s.error_data else None,
            "warnings": [],
            "errors": [],
            "artifact_paths": [],
            "details": s.error_data or {},
        }
        for s in stages
    ]

    # Get decision (if exists)
    decision = {}
    if run.classification:
        decision = {
            "classification": run.classification,
            "confidence_score": run.confidence_score,
        }

    return BaselineStatusResponse(
        run_id=run.id,
        status=run.status,
        classification=run.classification,
        current_stage=current_stage,
        stage_results=stage_results,
        metrics=metrics_data,
        decision=decision,
        warnings=[],
        errors=[],
    )


@router.get("/baseline/runs/{run_id}/report")
def get_baseline_report(run_id: str) -> dict[str, Any]:
    """
    Return baseline report artifact if it exists.

    If missing, returns controlled 404.
    """
    artifact_repo = ArtifactRepository()

    # Look for baseline report artifact
    artifacts = artifact_repo.list_run_artifacts(run_id)
    report_artifact = None
    for artifact in artifacts:
        if artifact.artifact_type == "report_md" and "baseline" in (artifact.description or "").lower():
            report_artifact = artifact
            break

    if not report_artifact:
        raise HTTPException(
            status_code=404,
            detail=f"Baseline report not found for run {run_id}",
        )

    # Return artifact metadata (not the file content itself)
    return {
        "run_id": run_id,
        "artifact_id": report_artifact.id,
        "artifact_type": report_artifact.artifact_type,
        "description": report_artifact.description,
        "file_path": report_artifact.file_path,
        "sha256": report_artifact.sha256,
        "size_bytes": report_artifact.size_bytes,
        "created_at": report_artifact.created_at.isoformat() if report_artifact.created_at else None,
    }
