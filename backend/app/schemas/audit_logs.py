"""
Pydantic schemas for Audit Logs API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class AuditLogCreate(BaseModel):
    """Schema for creating an audit log entry."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    actor: str = Field(..., description="Actor (user, system, ai_assistant, ai_strategy_designer, ai_repair_agent)")
    action_type: str = Field(..., description="Action type (create, update, delete, approve, reject, etc.)")
    description: Optional[str] = Field(None, description="Human-readable action description")
    target_type: Optional[str] = Field(None, description="Target type (strategy, run, config, etc.)")
    target_id: Optional[str] = Field(None, description="Target ID")
    before: Optional[dict] = Field(None, description="State before action as JSON")
    after: Optional[dict] = Field(None, description="State after action as JSON")
    changed_files: Optional[list] = Field(None, description="List of changed files")
    rollback_path: Optional[str] = Field(None, description="Path to rollback evidence if available")
    approved: bool = Field(False, description="Whether action was approved")
    notes: Optional[str] = Field(None, description="Additional notes")


class AuditLogRead(BaseModel):
    """Schema for audit log response."""
    id: str
    run_id: Optional[str]
    actor: str
    action_type: str
    description: Optional[str]
    target_type: Optional[str]
    target_id: Optional[str]
    before: Optional[dict]
    after: Optional[dict]
    changed_files: Optional[list]
    rollback_path: Optional[str]
    approved: bool
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True
