"""
Pydantic schemas for Part 13 validation evidence contracts.

These schemas define request, persistence-facing, and frontend-safe response
shapes only. They do not execute Freqtrade, approve strategies, export
strategies, call AI services, or synthesize validation evidence.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import PurePosixPath
from typing import Any, ClassVar, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.constants import (
    VALIDATION_DECISION_STATUSES,
    VALIDATION_EVIDENCE_TYPES,
    VALIDATION_SOURCE_TYPES,
    VALIDATION_STATUSES,
)


ALLOWED_RISK_PROFILES = {"conservative", "balanced", "aggressive"}


def _validate_required_string(value: str, field_name: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError(f"{field_name} is required")
    return cleaned


def _validate_project_relative_path(path: str) -> str:
    cleaned = path.strip()
    if not cleaned:
        raise ValueError("artifact path must not be empty")
    posix_path = PurePosixPath(cleaned)
    if posix_path.is_absolute() or ".." in posix_path.parts:
        raise ValueError("artifact paths must be project-relative")
    return cleaned


class StrictValidationModel(BaseModel):
    """Base model that rejects undeclared evidence fields."""

    model_config = ConfigDict(extra="forbid")


class ValidationIssue(StrictValidationModel):
    """One validation issue, warning, or blocking reason."""

    code: str
    message: str
    severity: str = "warning"
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("code", "message", "severity")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        return _validate_required_string(value, "value")


class ValidationPolicy(StrictValidationModel):
    """Deterministic aggregate validation policy summary."""

    policy_name: str = "default_validation_policy"
    risk_profile: str = "balanced"
    timeframe: Optional[str] = None
    min_oos_profit_factor: float = 1.10
    min_oos_expectancy: float = 0.0
    min_oos_trades: int = 10
    max_oos_drawdown_pct: float = 35.0
    min_wfo_pass_rate: float = 0.60
    max_robustness_critical_failures: int = 0
    require_robustness_pass: bool = True
    notes: Optional[str] = None

    @field_validator("policy_name")
    @classmethod
    def validate_policy_name(cls, value: str) -> str:
        return _validate_required_string(value, "policy_name")

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_RISK_PROFILES:
            raise ValueError(
                "risk_profile must be one of: aggressive, balanced, conservative"
            )
        return cleaned

    @field_validator("min_oos_trades")
    @classmethod
    def validate_min_oos_trades(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("min_oos_trades must be positive")
        return value

    @field_validator("min_oos_profit_factor")
    @classmethod
    def validate_min_oos_profit_factor(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("min_oos_profit_factor must be positive")
        return value

    @field_validator("max_oos_drawdown_pct")
    @classmethod
    def validate_max_oos_drawdown_pct(cls, value: float) -> float:
        if value <= 0:
            raise ValueError("max_oos_drawdown_pct must be positive")
        return value

    @field_validator("min_wfo_pass_rate")
    @classmethod
    def validate_min_wfo_pass_rate(cls, value: float) -> float:
        if value <= 0 or value > 1:
            raise ValueError("min_wfo_pass_rate must be between 0 and 1")
        return value

    @field_validator("max_robustness_critical_failures")
    @classmethod
    def validate_max_robustness_critical_failures(cls, value: int) -> int:
        if value < 0:
            raise ValueError("max_robustness_critical_failures must not be negative")
        return value


class ValidationRunRequest(StrictValidationModel):
    """Request to prepare a validation evidence workflow."""

    source_type: str
    source_run_id: Optional[str] = None
    strategy_name: str
    pairs: list[str]
    timeframe: str
    exchange: str = "binance"
    risk_profile: str = "balanced"
    timerange: Optional[str] = None
    days: Optional[int] = 90
    oos_ratio: float = 0.30
    wfo_enabled: bool = True
    wfo_train_days: int = 60
    wfo_test_days: int = 15
    wfo_step_days: int = 15
    wfo_max_windows: int = 5
    robustness_enabled: bool = True
    sensitivity_enabled: bool = False
    download_missing_data: bool = False
    user_confirmed: bool = False
    notes: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_SOURCE_TYPES:
            raise ValueError(
                "source_type must be one of: baseline_run, optimization_run, optimized_run, strategy"
            )
        return cleaned

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, value: str) -> str:
        return _validate_required_string(value, "strategy_name")

    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("pairs must be non-empty")
        cleaned_pairs = [_validate_required_string(pair, "pair") for pair in value]
        if not cleaned_pairs:
            raise ValueError("pairs must be non-empty")
        return cleaned_pairs

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        return _validate_required_string(value, "timeframe")

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        return _validate_required_string(value, "exchange")

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_RISK_PROFILES:
            raise ValueError(
                "risk_profile must be one of: aggressive, balanced, conservative"
            )
        return cleaned

    @field_validator("days")
    @classmethod
    def validate_days(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("days must be positive if provided")
        return value

    @field_validator("oos_ratio")
    @classmethod
    def validate_oos_ratio(cls, value: float) -> float:
        if value < 0.10 or value > 0.50:
            raise ValueError("oos_ratio must be between 0.10 and 0.50")
        return value

    @field_validator("wfo_train_days", "wfo_test_days", "wfo_step_days", "wfo_max_windows")
    @classmethod
    def validate_wfo_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("WFO values must be positive")
        return value


class ValidationEvidence(StrictValidationModel):
    """Persisted evidence item for OOS, WFO, robustness, or sensitivity."""

    id: Optional[str] = None
    validation_run_id: str
    evidence_type: str
    status: str
    window_index: Optional[int] = None
    timerange: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None

    @field_validator("validation_run_id")
    @classmethod
    def validate_validation_run_id(cls, value: str) -> str:
        return _validate_required_string(value, "validation_run_id")

    @field_validator("evidence_type")
    @classmethod
    def validate_evidence_type(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_EVIDENCE_TYPES:
            raise ValueError("evidence_type must be a known validation evidence type")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_STATUSES and cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("window_index")
    @classmethod
    def validate_window_index(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value < 0:
            raise ValueError("window_index must not be negative")
        return value

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class OOSValidationResult(StrictValidationModel):
    """Out-of-sample validation result summary."""

    status: str
    timerange: Optional[str] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    evidence_id: Optional[str] = None
    artifact_paths: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES and cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class WFOWindowResult(StrictValidationModel):
    """One walk-forward validation window result."""

    window_index: int
    timerange: str
    status: str
    train_timerange: Optional[str] = None
    test_timerange: Optional[str] = None
    train_start: Optional[datetime] = None
    train_end: Optional[datetime] = None
    test_start: Optional[datetime] = None
    test_end: Optional[datetime] = None
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    evidence_id: Optional[str] = None
    artifact_paths: list[str] = Field(default_factory=list)
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("window_index")
    @classmethod
    def validate_window_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("window_index must not be negative")
        return value

    @field_validator("timerange")
    @classmethod
    def validate_timerange(cls, value: str) -> str:
        return _validate_required_string(value, "timerange")

    @field_validator("train_timerange", "test_timerange")
    @classmethod
    def validate_optional_timerange(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return _validate_required_string(value, "timerange")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES and cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class WFOValidationResult(StrictValidationModel):
    """Walk-forward validation aggregate result."""

    status: str
    windows: list[WFOWindowResult] = Field(default_factory=list)
    pass_count: int = 0
    fail_count: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES and cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("pass_count", "fail_count")
    @classmethod
    def validate_counts(cls, value: int) -> int:
        if value < 0:
            raise ValueError("counts must not be negative")
        return value


class RobustnessCheckResult(StrictValidationModel):
    """One robustness check result."""

    ROBUSTNESS_STATUSES: ClassVar[set[str]] = {"passed", "warning", "failed"}

    check_name: str
    status: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)

    @field_validator("check_name")
    @classmethod
    def validate_check_name(cls, value: str) -> str:
        return _validate_required_string(value, "check_name")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if (
            cleaned not in VALIDATION_DECISION_STATUSES
            and cleaned not in VALIDATION_STATUSES
            and cleaned not in cls.ROBUSTNESS_STATUSES
        ):
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class SensitivityCheckResult(RobustnessCheckResult):
    """One sensitivity check result."""


class ValidationDecision(StrictValidationModel):
    """Aggregate validation decision."""

    decision_status: str
    confidence_score: Optional[float] = None
    policy_name: Optional[str] = None
    reasons: list[str] = Field(default_factory=list)
    blocking_failures: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @field_validator("decision_status")
    @classmethod
    def validate_decision_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("decision_status must be a known validation decision status")
        return cleaned

    @field_validator("confidence_score")
    @classmethod
    def validate_confidence_score(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and (value < 0 or value > 100):
            raise ValueError("confidence_score must be between 0 and 100")
        return value


class ValidationSummary(StrictValidationModel):
    """Frontend-safe validation evidence summary."""

    decision_status: str = "not_validated"
    oos_status: Optional[str] = None
    wfo_status: Optional[str] = None
    robustness_status: Optional[str] = None
    sensitivity_status: Optional[str] = None
    evidence_count: int = 0
    issues: list[ValidationIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @field_validator("decision_status")
    @classmethod
    def validate_decision_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("decision_status must be a known validation decision status")
        return cleaned

    @field_validator("evidence_count")
    @classmethod
    def validate_evidence_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("evidence_count must not be negative")
        return value


class ValidationRunResponse(StrictValidationModel):
    """Response returned when a validation run record is created or updated."""

    validation_run_id: str
    status: str
    decision_status: Optional[str] = None
    strategy_name: str
    pairs: list[str]
    timeframe: str
    exchange: str
    risk_profile: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @field_validator("validation_run_id")
    @classmethod
    def validate_validation_run_id(cls, value: str) -> str:
        return _validate_required_string(value, "validation_run_id")

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("decision_status")
    @classmethod
    def validate_decision_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("decision_status must be a known validation decision status")
        return cleaned


class ValidationRunListItem(StrictValidationModel):
    """Validation run list item."""

    id: str
    source_type: str
    source_run_id: Optional[str] = None
    strategy_name: str
    timeframe: str
    pairs: list[str]
    exchange: str
    risk_profile: Optional[str] = None
    status: str
    decision_status: Optional[str] = None
    timerange: Optional[str] = None
    oos_timerange: Optional[str] = None
    report_artifact_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ValidationRunAPIListItem(StrictValidationModel):
    """Frontend-ready validation run list item."""

    validation_run_id: str
    strategy_name: str
    source_type: str
    source_run_id: Optional[str] = None
    pairs: list[str]
    timeframe: str
    status: str
    decision_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    summary: Optional[dict[str, Any]] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("decision_status")
    @classmethod
    def validate_decision_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("decision_status must be a known validation decision status")
        return cleaned


class ValidationRunDetail(StrictValidationModel):
    """Full validation run detail for frontend evidence views."""

    run: ValidationRunListItem
    evidence: list[ValidationEvidence] = Field(default_factory=list)
    oos: Optional[OOSValidationResult] = None
    wfo: Optional[WFOValidationResult] = None
    robustness: list[RobustnessCheckResult] = Field(default_factory=list)
    sensitivity: list[SensitivityCheckResult] = Field(default_factory=list)
    decision: Optional[ValidationDecision] = None
    summary: Optional[ValidationSummary] = None
    artifact_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class ValidationStatusResponse(StrictValidationModel):
    """Lightweight validation run status response."""

    validation_run_id: str
    status: str
    decision_status: Optional[str] = None
    current_stage: Optional[str] = None
    evidence_count: int = 0
    message: Optional[str] = None
    completed_stages: list[str] = Field(default_factory=list)
    failed_stage: Optional[str] = None
    summary: Optional[dict[str, Any]] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in VALIDATION_STATUSES:
            raise ValueError("status must be a known validation status")
        return cleaned

    @field_validator("decision_status")
    @classmethod
    def validate_decision_status(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in VALIDATION_DECISION_STATUSES:
            raise ValueError("decision_status must be a known validation decision status")
        return cleaned

    @field_validator("evidence_count")
    @classmethod
    def validate_evidence_count(cls, value: int) -> int:
        if value < 0:
            raise ValueError("evidence_count must not be negative")
        return value
