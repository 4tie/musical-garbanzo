"""
Common response schemas shared by HER API routers.
"""
from typing import Any, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


T = TypeVar("T")


class ApiError(BaseModel):
    """Standard API error envelope."""
    error: bool = True
    type: str = Field(..., description="Stable error type")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] = Field(default_factory=dict)


class ApiMessage(BaseModel):
    """Generic success message."""
    message: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper for future list endpoints."""
    items: List[T]
    limit: int
    offset: int
    total: Optional[int] = None


class HealthStatus(BaseModel):
    """Health check response."""
    status: str
    app: str
    environment: str
    backend: str


class StatusResponse(BaseModel):
    """Generic operation status response."""
    status: str = "ok"
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    count: Optional[int] = None


class IdResponse(BaseModel):
    """Generic response containing a created or affected resource ID."""
    id: str
