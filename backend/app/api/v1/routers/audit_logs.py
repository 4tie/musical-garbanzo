"""
API router for Audit Logs operations.
"""
from fastapi import APIRouter, HTTPException

from app.repositories.audit_logs import AuditLogRepository
from app.schemas.audit_logs import AuditLogCreate, AuditLogRead

router = APIRouter(tags=["Audit Logs"])
audit_repo = AuditLogRepository()


@router.get("/audit-logs", response_model=list[AuditLogRead])
def list_audit_logs(
    run_id: str = None,
    action_type: str = None,
    limit: int = 100,
    offset: int = 0,
):
    """
    List audit logs with optional filters.
    
    Supports filtering by run_id and action_type.
    Returns logs in descending order by creation time.
    """
    logs = audit_repo.list_audit_logs(
        run_id=run_id,
        action_type=action_type,
        limit=limit,
        offset=offset,
    )
    return logs


@router.post("/audit-logs", response_model=AuditLogRead, status_code=201)
def create_audit_log(data: AuditLogCreate):
    """
    Create an audit log entry.
    
    Creates an audit log entry for tracking AI/user/system actions.
    """
    try:
        log = audit_repo.create_audit_log(data)
        return log
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
