"""
Pydantic schemas for Strategy and Strategy Version API requests and responses.
"""
from enum import Enum
from pathlib import PurePosixPath
from typing import Optional, Any
from pydantic import BaseModel, Field, field_validator


class StrategyCreate(BaseModel):
    """Schema for creating a new strategy."""
    name: str = Field(..., description="Strategy name")
    class_name: Optional[str] = Field(None, description="Strategy class name")
    source_type: str = Field(..., description="Source type: uploaded, generated, repaired, manual, imported, demo")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    direction: str = Field("unknown", description="Direction: long, short, both, unknown")
    file_path: Optional[str] = Field(None, description="Strategy file path")
    params_path: Optional[str] = Field(None, description="Parameters file path")
    status: str = Field("draft", description="Status: draft, active, archived")
    is_demo: bool = Field(False, description="Is this a demo strategy")


class StrategyUpdate(BaseModel):
    """Schema for updating a strategy."""
    name: Optional[str] = Field(None, description="Strategy name")
    class_name: Optional[str] = Field(None, description="Strategy class name")
    timeframe: Optional[str] = Field(None, description="Timeframe")
    direction: Optional[str] = Field(None, description="Direction")
    file_path: Optional[str] = Field(None, description="Strategy file path")
    params_path: Optional[str] = Field(None, description="Parameters file path")
    status: Optional[str] = Field(None, description="Status")


class StrategyRead(BaseModel):
    """Schema for strategy response."""
    id: str
    name: str
    class_name: Optional[str]
    source_type: str
    timeframe: Optional[str]
    direction: str
    file_path: Optional[str]
    params_path: Optional[str]
    status: str
    current_version_id: Optional[str]
    is_demo: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class StrategyListItem(BaseModel):
    """Schema for strategy list item."""
    id: str
    name: str
    source_type: str
    status: str
    direction: str
    timeframe: Optional[str]
    current_version_id: Optional[str]
    is_demo: bool
    created_at: str

    class Config:
        from_attributes = True


class StrategyVersionCreate(BaseModel):
    """Schema for creating a new strategy version."""
    strategy_id: Optional[str] = Field(None, description="Parent strategy ID (set from URL)")
    version_number: Optional[int] = Field(None, description="Version number (auto-incremented if not provided)")
    py_path: Optional[str] = Field(None, description="Python file path")
    json_path: Optional[str] = Field(None, description="JSON sidecar file path")
    spec: Optional[dict] = Field(None, description="Strategy specification")
    params: Optional[dict] = Field(None, description="Strategy parameters")
    code_hash: Optional[str] = Field(None, description="Code hash for integrity")
    created_from_run_id: Optional[str] = Field(None, description="Run ID that created this version")
    notes: Optional[str] = Field(None, description="Version notes")


class StrategyVersionRead(BaseModel):
    """Schema for strategy version response."""
    id: str
    strategy_id: str
    version_number: int
    py_path: Optional[str]
    json_path: Optional[str]
    spec: Optional[dict]
    params: Optional[dict]
    code_hash: Optional[str]
    created_from_run_id: Optional[str]
    notes: Optional[str]
    is_current: bool = False
    created_at: str

    class Config:
        from_attributes = True


class StrategyVersionListItem(BaseModel):
    """Schema for strategy version list item."""
    id: str
    version_number: int
    py_path: Optional[str]
    json_path: Optional[str]
    is_current: bool
    code_hash: Optional[str]
    created_from_run_id: Optional[str]
    notes: Optional[str]
    created_at: str

    class Config:
        from_attributes = True


class StrategyReadiness(str, Enum):
    """Readiness states for real local strategy workspace files."""

    READY = "ready"
    WARNING = "warning"
    MISSING_SIDECAR = "missing_sidecar"
    INVALID = "invalid"
    PARSE_ERROR = "parse_error"
    UNSAFE = "unsafe"


class StrategyIssue(BaseModel):
    """User-facing issue discovered during static strategy inspection."""

    code: str = Field(..., description="Stable issue code")
    severity: str = Field(..., description="info, warning, error, or critical")
    message: str = Field(..., description="Human-readable issue message")
    details: dict[str, Any] = Field(default_factory=dict, description="Structured issue details")

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in {"info", "warning", "error", "critical"}:
            raise ValueError("severity must be one of: info, warning, error, critical")
        return cleaned


class StrategyParamsSummary(BaseModel):
    """Bounded, frontend-safe summary of a strategy sidecar JSON file."""

    strategy_name: str
    sidecar_json_path: Optional[str] = None
    exists: bool = False
    parse_success: bool = False
    sections_present: list[str] = Field(default_factory=list)
    section_counts: dict[str, int] = Field(default_factory=dict)
    timeframe: Optional[str] = None
    max_open_trades: Optional[int] = None
    preview: dict[str, Any] = Field(default_factory=dict)
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class StrategySummary(BaseModel):
    """Summary row for one real strategy file in the local workspace."""

    strategy_name: str
    strategy_file_path: str
    sidecar_json_path: Optional[str] = None
    has_sidecar: bool = False
    readiness: StrategyReadiness
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    params_summary: StrategyParamsSummary = Field(
        default_factory=lambda: StrategyParamsSummary(strategy_name="")
    )
    updated_at: Optional[str] = None

    @field_validator("strategy_file_path", "sidecar_json_path")
    @classmethod
    def validate_project_relative_paths(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("path must not be empty")
        posix_path = PurePosixPath(cleaned)
        if posix_path.is_absolute() or ".." in posix_path.parts:
            raise ValueError("paths must be project-relative")
        return cleaned


class StrategyDetail(StrategySummary):
    """Detailed static inspection result for one strategy workspace file."""

    class_name: Optional[str] = None
    file_name: str
    apparent_strategy_name: str
    syntax_valid: bool = False
    static_checks: dict[str, bool] = Field(default_factory=dict)


class StrategyImportRequest(BaseModel):
    """Safe strategy import request contract for project-relative files."""

    source_path: str = Field(..., description="Project-relative source path to import from")
    sidecar_source_path: Optional[str] = Field(None, description="Optional project-relative sidecar JSON source path")
    strategy_name: Optional[str] = Field(None, description="Optional destination strategy name")
    overwrite_confirmed: bool = Field(False, description="Explicit confirmation for overwrites")

    @field_validator("source_path", "sidecar_source_path")
    @classmethod
    def validate_source_path(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("source paths must not be empty")
        posix_path = PurePosixPath(cleaned)
        if posix_path.is_absolute() or ".." in posix_path.parts:
            raise ValueError("source paths must be project-relative")
        return cleaned


class StrategyReadinessGateResult(BaseModel):
    """Result of strategy readiness gate check for run execution."""

    strategy_name: str
    readiness: StrategyReadiness
    allowed: bool
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str
    next_actions: list[str] = Field(default_factory=list)


class StrategyReadinessBlockedError(BaseModel):
    """Structured error response when strategy readiness blocks run execution."""

    error: bool = True
    code: str = "strategy_not_ready"
    message: str = "Strategy is not ready for validation."
    strategy_name: str
    readiness: StrategyReadiness
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(
        default_factory=lambda: [
            "Open Strategy Workspace",
            "Inspect strategy readiness issues",
            "Fix the strategy or sidecar JSON manually",
            "Revalidate before starting baseline or optimization"
        ]
    )


class StrategyImportResult(BaseModel):
    """Safe strategy import result contract."""

    success: bool
    imported: bool = False
    conflict: bool = False
    strategy_name: Optional[str] = None
    strategy_file_path: Optional[str] = None
    sidecar_json_path: Optional[str] = None
    readiness: Optional[StrategyReadiness] = None
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    existing_files: dict[str, str] = Field(default_factory=dict)
    detail: Optional[StrategyDetail] = None
