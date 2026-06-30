"""
API router for Run operations.
"""
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.repositories.runs import RunRepository, RunNotFoundError
from app.schemas.runs import (
    RunCreate,
    RunUpdate,
    RunRead,
    RunListItem,
    RunStatusUpdate,
    RunClassificationUpdate,
    RunFailRequest,
)

router = APIRouter(tags=["Runs"])
run_repo = RunRepository()


@router.get("/runs", response_model=list[RunListItem])
def list_runs(
    status: Optional[str] = Query(None, description="Filter by status"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    strategy_id: Optional[str] = Query(None, description="Filter by strategy ID"),
    limit: int = Query(50, ge=1, le=500, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
):
    """
    List runs with optional filters.
    
    Returns a paginated list of runs.
    """
    runs = run_repo.list_runs(
        status=status,
        classification=classification,
        strategy_id=strategy_id,
        limit=limit,
        offset=offset,
    )
    return runs


@router.post("/runs", response_model=RunRead, status_code=201)
def create_run(data: RunCreate):
    """
    Create a new run.
    
    Creates a new run with the specified configuration.
    The run starts in 'created' status.
    """
    try:
        run = run_repo.create_run(data)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/runs/{run_id}", response_model=RunRead)
def get_run(run_id: str):
    """
    Get a run by ID.
    
    Returns detailed information about a specific run.
    """
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


@router.patch("/runs/{run_id}", response_model=RunRead)
def update_run(run_id: str, data: RunUpdate):
    """
    Update a run.
    
    Updates the specified fields of a run.
    Only provided fields are updated.
    """
    try:
        run = run_repo.update_run(run_id, data)
        return run
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/runs/{run_id}/status", response_model=RunRead)
def update_run_status(run_id: str, data: RunStatusUpdate):
    """
    Update run status.
    
    Updates the status of a run.
    Optionally includes a failure reason for failed statuses.
    """
    try:
        run = run_repo.update_status(run_id, data.status, data.failure_reason)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/runs/{run_id}/classification", response_model=RunRead)
def update_run_classification(run_id: str, data: RunClassificationUpdate):
    """
    Update run classification.
    
    Sets the classification of a run.
    """
    try:
        run = run_repo.set_classification(run_id, data.classification)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/runs/{run_id}/start", response_model=RunRead)
def start_run(run_id: str):
    """
    Mark a run as started.
    
    Updates the run status to 'running' and sets the started_at timestamp.
    This does not execute the actual pipeline - it only updates the state.
    """
    try:
        run = run_repo.mark_started(run_id)
        return run
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/runs/{run_id}/complete", response_model=RunRead)
def complete_run(
    run_id: str,
    status: Optional[str] = Query(None, description="Final status"),
    classification: Optional[str] = Query(None, description="Classification"),
):
    """
    Mark a run as completed.
    
    Updates the run status and optionally sets classification.
    Sets the completed_at timestamp.
    """
    try:
        run = run_repo.mark_completed(run_id, status=status, classification=classification)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")


@router.post("/runs/{run_id}/fail", response_model=RunRead)
def fail_run(run_id: str, data: RunFailRequest):
    """
    Mark a run as failed.
    
    Updates the run status to a failed state and records the failure reason.
    """
    try:
        run = run_repo.mark_failed(run_id, data.failure_type, data.reason)
        return run
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RunNotFoundError:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
