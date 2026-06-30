"""
Pydantic schemas for Run Stage API requests and responses.
"""
from typing import Optional, Any
from pydantic import BaseModel, Field


class RunStageCreate(BaseModel):
    """Schema for creating a new run stage."""
    run_id: str = Field(..., description="Parent run ID")
    stage_key: str = Field(..., description="Stage identifier")
    stage_name: str = Field(..., description="Human-readable stage name")
    order_index: int = Field(..., description="Execution order")
    input_data: Optional[Any] = Field(None, description="Stage input data")


class RunStageUpdate(BaseModel):
    """Schema for updating a run stage."""
    stage_name: Optional[str] = Field(None, description="Stage name")
    input_data: Optional[Any] = Field(None, description="Stage input data")
    output_data: Optional[Any] = Field(None, description="Stage output data")
    error_data: Optional[Any] = Field(None, description="Stage error data")
    logs_summary: Optional[str] = Field(None, description="Log summary")


class RunStageStatusUpdate(BaseModel):
    """Schema for updating run stage status."""
    status: str = Field(..., description="New status")


class RunStageCompleteRequest(BaseModel):
    """Schema for completing a run stage."""
    output_data: Optional[Any] = Field(None, description="Stage output data")
    logs_summary: Optional[str] = Field(None, description="Log summary")


class RunStageFailRequest(BaseModel):
    """Schema for failing a run stage."""
    error_data: Optional[Any] = Field(None, description="Error details")
    logs_summary: Optional[str] = Field(None, description="Log summary")


class RunStageRead(BaseModel):
    """Schema for run stage response."""
    id: str
    run_id: str
    stage_key: str
    stage_name: str
    order_index: int
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    input: Optional[Any]
    output: Optional[Any]
    error: Optional[Any]
    logs_summary: Optional[str]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True
