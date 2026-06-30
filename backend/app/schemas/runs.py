"""
Pydantic schemas for Run API requests and responses.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RunCreate(BaseModel):
    """Schema for creating a new run."""
    name: str = Field(..., description="Run name")
    mode: str = Field(..., description="Run mode")
    strategy_id: Optional[str] = Field(None, description="Associated strategy ID")
    parent_run_id: Optional[str] = Field(None, description="Parent run ID for retries")
    exchange: Optional[str] = Field(None, description="Exchange name")
    quote_currency: Optional[str] = Field(None, description="Quote currency")
    trading_mode: Optional[str] = Field(None, description="Trading mode")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    pairs: Optional[List[str]] = Field(None, description="Trading pairs")
    timerange: Optional[str] = Field(None, description="Time range for backtest")
    risk_profile: Optional[str] = Field(None, description="Risk profile")
    analysis_depth: Optional[str] = Field(None, description="Analysis depth level")
    is_demo: bool = Field(False, description="Whether this is a demo run")


class RunUpdate(BaseModel):
    """Schema for updating a run."""
    name: Optional[str] = Field(None, description="Run name")
    exchange: Optional[str] = Field(None, description="Exchange name")
    quote_currency: Optional[str] = Field(None, description="Quote currency")
    trading_mode: Optional[str] = Field(None, description="Trading mode")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    pairs: Optional[List[str]] = Field(None, description="Trading pairs")
    timerange: Optional[str] = Field(None, description="Time range for backtest")
    risk_profile: Optional[str] = Field(None, description="Risk profile")
    analysis_depth: Optional[str] = Field(None, description="Analysis depth level")


class RunStatusUpdate(BaseModel):
    """Schema for updating run status."""
    status: str = Field(..., description="New status")
    failure_reason: Optional[str] = Field(None, description="Failure reason if status is failed")


class RunClassificationUpdate(BaseModel):
    """Schema for updating run classification."""
    classification: str = Field(..., description="Classification value")


class RunFailRequest(BaseModel):
    """Schema for marking a run as failed."""
    failure_type: str = Field(..., description="Type of failure (controlled or system)")
    reason: str = Field(..., description="Failure reason")


class RunRead(BaseModel):
    """Schema for run response."""
    id: str
    name: str
    mode: str
    status: str
    classification: Optional[str]
    strategy_id: Optional[str]
    parent_run_id: Optional[str]
    exchange: Optional[str]
    quote_currency: Optional[str]
    trading_mode: Optional[str]
    timeframe: Optional[str]
    pairs: Optional[List[str]]
    timerange: Optional[str]
    risk_profile: Optional[str]
    analysis_depth: Optional[str]
    is_demo: bool
    failure_reason: Optional[str]
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True


class RunListItem(BaseModel):
    """Schema for run list item (lighter than RunRead)."""
    id: str
    name: str
    mode: str
    status: str
    classification: Optional[str]
    strategy_id: Optional[str]
    parent_run_id: Optional[str]
    is_demo: bool
    created_at: str
    updated_at: str
    started_at: Optional[str]
    completed_at: Optional[str]

    class Config:
        from_attributes = True
