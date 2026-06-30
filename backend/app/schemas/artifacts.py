"""
Pydantic schemas for Artifacts API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class ArtifactCreate(BaseModel):
    """Schema for creating a new artifact."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    strategy_id: Optional[str] = Field(None, description="Associated strategy ID")
    artifact_type: str = Field(..., description="Type of artifact (strategy_py, strategy_json, strategy_spec, backtest_result, etc.)")
    file_path: str = Field(..., description="Path to the artifact file")
    description: Optional[str] = Field(None, description="Artifact description")
    sha256: Optional[str] = Field(None, description="SHA256 hash of the file")
    size_bytes: Optional[int] = Field(None, description="File size in bytes")


class ArtifactRead(BaseModel):
    """Schema for artifact response."""
    id: str
    run_id: Optional[str]
    strategy_id: Optional[str]
    artifact_type: str
    file_path: str
    description: Optional[str]
    sha256: Optional[str]
    size_bytes: Optional[int]
    created_at: str

    class Config:
        from_attributes = True


class ArtifactListItem(BaseModel):
    """Schema for artifact list item."""
    id: str
    run_id: Optional[str]
    strategy_id: Optional[str]
    artifact_type: str
    file_path: str
    description: Optional[str]
    created_at: str

    class Config:
        from_attributes = True
