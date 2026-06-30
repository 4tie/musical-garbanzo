"""
Pydantic schemas for Freqtrade integration status and command results.
"""
from typing import Optional

from pydantic import BaseModel, Field


class FreqtradeCommandResult(BaseModel):
    """Safe result envelope for a Freqtrade command."""

    command: list[str] = Field(default_factory=list)
    sanitized_command: list[str] = Field(default_factory=list)
    return_code: Optional[int] = None
    stdout: str = ""
    stderr: str = ""
    duration_seconds: Optional[float] = None
    timed_out: bool = False
    success: bool = False
    blocked: bool = False
    error: Optional[str] = None


class FreqtradeVersion(BaseModel):
    """Freqtrade version detection result."""

    available: bool = False
    executable_path: Optional[str] = None
    version: Optional[str] = None
    command_result: Optional[FreqtradeCommandResult] = None
    error: Optional[str] = None


class FreqtradeDirectoryStatus(BaseModel):
    """Status for one required Freqtrade workspace directory."""

    key: str
    path: str
    exists: bool
    is_dir: bool
    writable: bool
    created: bool = False
    required: bool = True
    error: Optional[str] = None


class FreqtradeWorkspaceStatus(BaseModel):
    """Structured Freqtrade workspace validation result."""

    valid: bool
    user_data_dir: str
    config_dir: str
    directories: list[FreqtradeDirectoryStatus] = Field(default_factory=list)
    missing_dirs: list[str] = Field(default_factory=list)
    created_dirs: list[str] = Field(default_factory=list)
    user_action_required: Optional[str] = None


class FreqtradeStatus(BaseModel):
    """Combined Freqtrade environment and workspace status."""

    configured: bool
    executable_available: bool
    executable_path: Optional[str] = None
    path_source: str = "missing"
    version: Optional[str] = None
    workspace_valid: bool = False
    workspace: Optional[FreqtradeWorkspaceStatus] = None
    user_action_required: Optional[str] = None
    error: Optional[str] = None
    allowed_commands: list[str] = Field(default_factory=list)
    forbidden_commands: list[str] = Field(default_factory=list)
    real_smoke_enabled: bool = False
    warnings: list[str] = Field(default_factory=list)
