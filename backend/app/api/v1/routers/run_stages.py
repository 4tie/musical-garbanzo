"""
API router for Run Stage operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.run_stages import RunStageRepository, RunStageNotFoundError
from app.repositories.runs import RunRepository, RunNotFoundError
from app.schemas.run_stages import (
    RunStageRead,
    RunStageCompleteRequest,
    RunStageFailRequest,
)
from app.schemas.common import StatusResponse

router = APIRouter(tags=["Run Stages"])
stage_repo = RunStageRepository()
run_repo = RunRepository()


@router.get("/runs/{run_id}/stages", response_model=list[RunStageRead])
def list_stages(run_id: str):
    """
    List all stages for a run.
    
    Returns stages ordered by their execution order.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    stages = stage_repo.list_stages(run_id)
    return stages


@router.get("/runs/{run_id}/stages/{stage_key}", response_model=RunStageRead)
def get_stage(run_id: str, stage_key: str):
    """
    Get a specific stage for a run.
    
    Returns detailed information about a specific stage.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    stage = stage_repo.get_stage(run_id, stage_key)
    if not stage:
        raise HTTPException(status_code=404, detail=f"Stage {stage_key} not found for run {run_id}")
    
    return stage


@router.post("/runs/{run_id}/stages/{stage_key}/start", response_model=RunStageRead)
def start_stage(run_id: str, stage_key: str, input_data: dict = None):
    """
    Start a stage.
    
    Updates the stage status to 'running' and sets started_at.
    Optionally accepts input data for the stage.
    This does not execute the actual stage logic - it only updates the state.
    
    Request body should be the input data directly, not wrapped in an object.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        stage = stage_repo.start_stage(run_id, stage_key, input_data=input_data)
        return stage
    except RunStageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Stage {stage_key} not found for run {run_id}")


@router.post("/runs/{run_id}/stages/{stage_key}/complete", response_model=RunStageRead)
def complete_stage(run_id: str, stage_key: str, data: RunStageCompleteRequest):
    """
    Complete a stage.
    
    Updates the stage status to 'passed' and sets completed_at.
    Optionally accepts output data and log summary.
    Calculates duration_ms based on started_at.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        stage = stage_repo.complete_stage(
            run_id,
            stage_key,
            output_data=data.output_data,
            logs_summary=data.logs_summary,
        )
        return stage
    except RunStageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Stage {stage_key} not found for run {run_id}")


@router.post("/runs/{run_id}/stages/{stage_key}/fail", response_model=RunStageRead)
def fail_stage(run_id: str, stage_key: str, data: RunStageFailRequest):
    """
    Fail a stage.
    
    Updates the stage status to 'failed' and sets completed_at.
    Optionally accepts error data and log summary.
    Calculates duration_ms based on started_at.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        stage = stage_repo.fail_stage(
            run_id,
            stage_key,
            error_data=data.error_data,
            logs_summary=data.logs_summary,
        )
        return stage
    except RunStageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Stage {stage_key} not found for run {run_id}")


@router.post("/runs/{run_id}/stages/{stage_key}/skip", response_model=RunStageRead)
def skip_stage(run_id: str, stage_key: str, reason: str = None):
    """
    Skip a stage.
    
    Updates the stage status to 'skipped' and sets completed_at.
    Optionally accepts a reason for skipping.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    try:
        stage = stage_repo.skip_stage(run_id, stage_key, reason=reason)
        return stage
    except RunStageNotFoundError:
        raise HTTPException(status_code=404, detail=f"Stage {stage_key} not found for run {run_id}")


@router.post("/runs/{run_id}/stages/reset", response_model=StatusResponse)
def reset_stages(run_id: str):
    """
    Reset all stages for a run.
    
    Resets all stages to 'pending' status and clears timestamps and data.
    Returns the number of stages reset.
    """
    # Verify run exists
    run = run_repo.get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    
    count = stage_repo.reset_stages(run_id)
    return {
        "status": "ok",
        "message": f"Reset {count} stages for run {run_id}",
        "details": {"count": count},
        "count": count,
    }
