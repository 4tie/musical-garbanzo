"""
API router for Metrics operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.metrics import MetricsRepository
from app.schemas.metrics import (
    MetricSnapshotCreate,
    MetricSnapshotRead,
    PairResultCreate,
    PairResultRead,
    TradeSummaryCreate,
    TradeSummaryRead,
)

router = APIRouter(tags=["Metrics"])
metrics_repo = MetricsRepository()


@router.get("/runs/{run_id}/metrics", response_model=list[MetricSnapshotRead])
def list_metric_snapshots(run_id: str):
    """
    List all metric snapshots for a run.
    
    Returns metric snapshots in descending order by creation time.
    """
    snapshots = metrics_repo.list_metric_snapshots(run_id)
    return snapshots


@router.get("/runs/{run_id}/metrics/latest", response_model=MetricSnapshotRead)
def get_latest_metric_snapshot(run_id: str):
    """
    Get the latest metric snapshot for a run.
    
    Returns the most recent metric snapshot.
    """
    snapshot = metrics_repo.get_latest_metric_snapshot(run_id)
    if not snapshot:
        raise HTTPException(status_code=404, detail=f"No metric snapshots found for run {run_id}")
    return snapshot


@router.post("/runs/{run_id}/metrics", response_model=MetricSnapshotRead, status_code=201)
def create_metric_snapshot(run_id: str, data: MetricSnapshotCreate):
    """
    Create a new metric snapshot.
    
    Creates a metric snapshot for the specified run.
    """
    # Override run_id to match URL parameter
    data.run_id = run_id
    
    snapshot = metrics_repo.create_metric_snapshot(data)
    return snapshot


@router.get("/runs/{run_id}/pair-results", response_model=list[PairResultRead])
def list_pair_results(run_id: str):
    """
    List all pair results for a run.
    
    Returns pair results sorted by pair name.
    """
    results = metrics_repo.list_pair_results(run_id)
    return results


@router.post("/runs/{run_id}/pair-results", response_model=PairResultRead, status_code=201)
def create_pair_result(run_id: str, data: PairResultCreate):
    """
    Create a new pair result.
    
    Creates a pair result for the specified run.
    """
    # Override run_id to match URL parameter
    data.run_id = run_id
    
    result = metrics_repo.create_pair_result(data)
    return result


@router.get("/runs/{run_id}/trade-summary", response_model=TradeSummaryRead)
def get_trade_summary(run_id: str):
    """
    Get the trade summary for a run.
    
    Returns the trade summary for the specified run.
    """
    summary = metrics_repo.get_trade_summary_by_run(run_id)
    if not summary:
        raise HTTPException(status_code=404, detail=f"No trade summary found for run {run_id}")
    return summary


@router.post("/runs/{run_id}/trade-summary", response_model=TradeSummaryRead, status_code=201)
def create_trade_summary(run_id: str, data: TradeSummaryCreate):
    """
    Create a new trade summary.
    
    Creates a trade summary for the specified run.
    """
    # Override run_id to match URL parameter
    data.run_id = run_id
    
    summary = metrics_repo.create_trade_summary(data)
    return summary
