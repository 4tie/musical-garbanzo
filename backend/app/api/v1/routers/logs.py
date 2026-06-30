"""
API router for Run Logs operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.logs import RunLogRepository
from app.schemas.logs import RunLogCreate, RunLogRead

router = APIRouter(tags=["Logs"])
log_repo = RunLogRepository()


@router.get("/runs/{run_id}/logs", response_model=list[RunLogRead])
def list_logs(
    run_id: str,
    stage_key: str = None,
    level: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List log entries for a run.
    
    Supports filtering by stage_key and level.
    Returns logs in descending order by creation time.
    """
    logs = log_repo.list_logs(
        run_id=run_id,
        stage_key=stage_key,
        level=level,
        limit=limit,
        offset=offset,
    )
    return logs


@router.post("/runs/{run_id}/logs", response_model=RunLogRead, status_code=201)
def add_log(run_id: str, data: RunLogCreate):
    """
    Add a log entry.
    
    Creates a log entry for the specified run.
    Secret-like values in details are automatically sanitized.
    """
    # Override run_id to match URL parameter
    data.run_id = run_id
    
    try:
        log = log_repo.add_log(
            run_id=data.run_id,
            level=data.level,
            source=data.source,
            message=data.message,
            stage_key=data.stage_key,
            details=data.details,
        )
        return log
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
