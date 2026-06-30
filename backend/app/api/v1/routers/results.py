"""
API router for parsed backtest Results.
"""
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.metrics import MetricsRepository
from app.repositories.runs import RunRepository
from app.schemas.backtest_results import (
    BacktestCombinedResult,
    BacktestParseRequest,
    BacktestParseResult,
    ResultQualityReport,
)
from app.services.backtest_result_parser import BacktestResultParser


router = APIRouter(tags=["Results"])


def get_run_or_404(run_id: str) -> dict:
    """Return a run or raise a clean 404."""
    run = RunRepository().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.post("/results/backtest/{run_id}/parse", response_model=BacktestParseResult)
def parse_backtest_results(
    run_id: str,
    request: Optional[BacktestParseRequest] = Body(default=None),
):
    """
    Parse already captured backtest outputs for a run.

    This endpoint does not run Freqtrade, download data, classify strategies,
    approve strategies, or send notifications.
    """
    get_run_or_404(run_id)
    request = request or BacktestParseRequest()
    parser = BacktestResultParser()
    if request.paths:
        result = parser.parse_from_paths(run_id, request.paths, force=request.force)
    else:
        result = parser.parse_run(run_id, force=request.force)
    return _sanitize_paths(result.model_dump(mode="json"))


@router.get("/results/backtest/{run_id}", response_model=BacktestCombinedResult)
def get_backtest_results(run_id: str):
    """Return the latest combined parsed backtest result for a run."""
    get_run_or_404(run_id)
    metrics_repo = MetricsRepository()

    latest_metrics = metrics_repo.get_latest_metric_snapshot(run_id)
    pair_results = metrics_repo.list_pair_results(run_id)
    trade_summary = metrics_repo.get_trade_summary(run_id)
    quality_report = _get_latest_quality_report(run_id)
    normalized_path = _get_normalized_artifact_path(run_id)

    warnings: list[str] = []
    if latest_metrics is None:
        warnings.append("metrics_missing")
    if not pair_results:
        warnings.append("pair_results_missing")
    if trade_summary is None:
        warnings.append("trade_summary_missing")
    if quality_report is None:
        warnings.append("quality_report_missing")
    if normalized_path is None:
        warnings.append("normalized_artifact_missing")

    return BacktestCombinedResult(
        run_id=run_id,
        latest_metrics=latest_metrics,
        pair_results=pair_results,
        trade_summary=trade_summary,
        quality_report=quality_report,
        normalized_result_path=normalized_path,
        warnings=warnings,
    )


@router.get("/results/backtest/{run_id}/quality", response_model=ResultQualityReport)
def get_backtest_quality(run_id: str):
    """Return the latest result quality report for a run."""
    get_run_or_404(run_id)
    quality_report = _get_latest_quality_report(run_id)
    if quality_report is None:
        raise HTTPException(status_code=404, detail=f"No result quality report found for run {run_id}")
    return quality_report


@router.get("/runs/{run_id}/result-quality", response_model=ResultQualityReport)
def get_run_result_quality(run_id: str):
    """Compatibility endpoint for the latest result quality report."""
    return get_backtest_quality(run_id)


@router.get("/results/backtest/{run_id}/normalized")
def get_backtest_normalized(run_id: str):
    """Return the normalized parsed backtest result artifact JSON."""
    get_run_or_404(run_id)
    artifact = _get_normalized_artifact(run_id)
    if artifact is None:
        raise HTTPException(status_code=404, detail=f"No normalized result artifact found for run {run_id}")

    path = _resolve_project_file(artifact["file_path"])
    if path is None or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail=f"Normalized result artifact is missing for run {run_id}")

    try:
        import json

        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        raise HTTPException(status_code=500, detail="Normalized result artifact could not be read")

    return _sanitize_paths(data)


def _get_latest_quality_report(run_id: str) -> Optional[ResultQualityReport]:
    """Load the latest quality report from audit evidence."""
    audits = AuditLogRepository().list_audit_logs(
        run_id=run_id,
        action_type="backtest_result_quality",
        limit=1,
    )
    if not audits:
        return None
    raw_report = audits[0].get("after")
    if not raw_report:
        return None
    return ResultQualityReport.model_validate(raw_report)


def _get_normalized_artifact(run_id: str) -> Optional[dict]:
    """Return the normalized parsed result artifact row, if any."""
    artifacts = ArtifactRepository().list_artifacts(
        run_id=run_id,
        artifact_type="metrics_json",
        limit=100,
    )
    for artifact in artifacts:
        file_path = artifact.get("file_path") or ""
        description = artifact.get("description") or ""
        if (
            file_path.endswith("normalized/backtest_result.normalized.json")
            or description == "Normalized parsed backtest result"
        ):
            return artifact
    return None


def _get_normalized_artifact_path(run_id: str) -> Optional[str]:
    """Return project-relative normalized artifact path."""
    artifact = _get_normalized_artifact(run_id)
    if not artifact:
        return None
    return _project_relative_path(artifact["file_path"])


def _resolve_project_file(file_path: str) -> Optional[Path]:
    """Resolve a path only when it stays under the project root."""
    project_root = settings.project_root.resolve()
    path = Path(file_path)
    if not path.is_absolute():
        path = project_root / path
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(project_root)
    except ValueError:
        return None
    return resolved


def _project_relative_path(file_path: str) -> str:
    """Return project-relative path when possible."""
    project_root = settings.project_root.resolve()
    path = Path(file_path)
    if not path.is_absolute():
        return str(path)
    try:
        return str(path.resolve(strict=False).relative_to(project_root))
    except ValueError:
        return path.name


def _sanitize_paths(value: Any) -> Any:
    """Recursively convert project absolute paths to project-relative strings."""
    if isinstance(value, dict):
        return {key: _sanitize_paths(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_paths(item) for item in value]
    if isinstance(value, str):
        project_root = str(settings.project_root.resolve())
        if value.startswith(project_root):
            return _project_relative_path(value)
    return value
