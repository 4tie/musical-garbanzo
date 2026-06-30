"""
Pydantic schemas for Retry History API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class RetryHistoryCreate(BaseModel):
    """Schema for creating a retry history entry."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    parent_run_id: Optional[str] = Field(None, description="Parent run ID (if this is a retry)")
    attempt_number: int = Field(1, description="Retry attempt number")
    reason: Optional[str] = Field(None, description="Reason this retry was created")
    stage_key: Optional[str] = Field(None, description="Stage where retry occurred")
    status: str = Field(..., description="Retry status (proposed, approved, applied, failed, rejected, skipped)")
    error_message: Optional[str] = Field(None, description="Error that triggered retry")
    proposed_fix: Optional[dict] = Field(None, description="Proposed fix as JSON")
    applied_fix: Optional[dict] = Field(None, description="Applied fix as JSON")


class RetryHistoryRead(BaseModel):
    """Schema for retry history response."""
    id: str
    run_id: str
    parent_run_id: Optional[str]
    attempt_number: int
    reason: Optional[str]
    stage_key: Optional[str]
    status: str
    error_message: Optional[str]
    proposed_fix: Optional[dict]
    applied_fix: Optional[dict]
    created_at: str
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class RetryCompleteRequest(BaseModel):
    """Schema for completing a retry history entry."""
    status: str = Field(..., description="Final retry status")
    applied_fix: Optional[dict] = Field(None, description="Applied fix as JSON")
    error_message: Optional[str] = Field(None, description="Error message if retry failed")
