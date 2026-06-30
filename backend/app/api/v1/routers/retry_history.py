"""
API router for Retry History operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.retry_history import RetryHistoryRepository
from app.schemas.retry_history import (
    RetryCompleteRequest,
    RetryHistoryCreate,
    RetryHistoryRead,
)

router = APIRouter(tags=["Retry History"])
retry_repo = RetryHistoryRepository()


@router.get("/runs/{run_id}/retry-history", response_model=list[RetryHistoryRead])
def list_retry_history(run_id: str):
    """
    List retry history for a run.
    
    Returns retry entries in descending order by creation time.
    """
    history = retry_repo.list_retry_history(run_id)
    return history


@router.post("/runs/{run_id}/retry-history", response_model=RetryHistoryRead, status_code=201)
def create_retry_entry(run_id: str, data: RetryHistoryCreate):
    """
    Create a retry history entry.
    
    Creates a retry entry for the specified run.
    """
    # Override run_id to match URL parameter
    data.run_id = run_id
    
    try:
        entry = retry_repo.create_retry_entry(data)
        return entry
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/retry-history/{retry_id}/complete", response_model=RetryHistoryRead)
def complete_retry(retry_id: str, data: RetryCompleteRequest):
    """
    Complete a retry entry.
    
    Marks a retry entry as completed or failed with optional applied fix.
    """
    try:
        entry = retry_repo.complete_retry(
            retry_id=retry_id,
            status=data.status,
            applied_fix=data.applied_fix,
            error_message=data.error_message,
        )
        return entry
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
