"""
Pydantic schemas for Run Logs API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class RunLogCreate(BaseModel):
    """Schema for creating a run log entry."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    level: str = Field(..., description="Log level (info, warning, error, debug, critical)")
    source: str = Field(..., description="Log source (system, ai, freqtrade, user)")
    message: str = Field(..., description="Log message")
    stage_key: Optional[str] = Field(None, description="Associated stage key")
    details: Optional[dict] = Field(None, description="Additional details as JSON")


class RunLogRead(BaseModel):
    """Schema for run log response."""
    id: str
    run_id: str
    level: str
    source: str
    message: str
    stage_key: Optional[str]
    details: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True
