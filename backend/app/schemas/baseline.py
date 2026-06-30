"""
Pydantic schemas for Part 07 baseline evaluation contracts.
"""
from pathlib import PurePosixPath
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator

from app.core.constants import (
    BASELINE_PIPELINE_STAGES,
    BASELINE_PIPELINE_STATUSES,
)


ALLOWED_RISK_PROFILES = {"conservative", "balanced", "aggressive"}
ALLOWED_TRADING_MODES = {"spot"}


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


class BaselineEvaluationRequest(BaseModel):
    """Request contract for evaluating an existing strategy baseline."""

    strategy_name: str = Field(..., description="Existing Freqtrade strategy name")
    pairs: list[str] = Field(..., description="Pairs to evaluate")
    timeframe: str = Field(..., description="Freqtrade timeframe")
    exchange: str = Field("binance", description="Exchange name")
    days: Optional[int] = Field(30, description="Historical days to evaluate")
    timerange: Optional[str] = Field(None, description="Optional Freqtrade timerange")
    risk_profile: str = Field("balanced", description="Decision risk profile")
    stake_currency: str = Field("USDT", description="Stake currency")
    stake_amount: float | str = Field("unlimited", description="Stake amount")
    max_open_trades: int = Field(3, description="Maximum open trades")
    trading_mode: str = Field("spot", description="Trading mode")
    download_missing_data: bool = Field(False, description="Whether missing data may be downloaded")
    user_confirmed: bool = Field(False, description="Whether user confirmed real execution")
    apply_decision_to_run: bool = Field(True, description="Apply decision classification to run")
    force_parse: bool = Field(True, description="Replace previous parsed evidence for this run")
    notes: Optional[str] = Field(None, description="Optional user notes")

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, value: str) -> str:
        return _validate_required_string(value, "strategy_name")

    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, value: list[str]) -> list[str]:
        if not value:
            raise ValueError("pairs must not be empty")
        cleaned_pairs = [_validate_required_string(pair, "pair") for pair in value]
        return cleaned_pairs

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, value: str) -> str:
        return _validate_required_string(value, "timeframe")

    @field_validator("exchange")
    @classmethod
    def validate_exchange(cls, value: str) -> str:
        return _validate_required_string(value, "exchange")

    @field_validator("days")
    @classmethod
    def validate_days(cls, value: Optional[int]) -> Optional[int]:
        if value is not None and value <= 0:
            raise ValueError("days must be positive if provided")
        return value

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_RISK_PROFILES:
            raise ValueError(
                "risk_profile must be one of: aggressive, balanced, conservative"
            )
        return cleaned

    @field_validator("stake_currency")
    @classmethod
    def validate_stake_currency(cls, value: str) -> str:
        return _validate_required_string(value, "stake_currency").upper()

    @field_validator("stake_amount")
    @classmethod
    def validate_stake_amount(cls, value: float | str) -> float | str:
        if isinstance(value, str):
            cleaned = value.strip().lower()
            if not cleaned:
                raise ValueError("stake_amount must not be empty")
            if cleaned == "unlimited":
                return cleaned
            try:
                numeric_value = float(cleaned)
            except ValueError as exc:
                raise ValueError("stake_amount must be numeric or unlimited") from exc
            if numeric_value <= 0:
                raise ValueError("stake_amount must be positive")
            return numeric_value
        if value <= 0:
            raise ValueError("stake_amount must be positive")
        return value

    @field_validator("max_open_trades")
    @classmethod
    def validate_max_open_trades(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("max_open_trades must be positive")
        return value

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if cleaned not in ALLOWED_TRADING_MODES:
            raise ValueError("trading_mode must be spot")
        return cleaned


class BaselineStageResult(BaseModel):
    """Status and evidence summary for one baseline pipeline stage."""

    stage_name: str
    status: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("stage_name")
    @classmethod
    def validate_stage_name(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in BASELINE_PIPELINE_STAGES:
            raise ValueError("stage_name must be a known baseline pipeline stage")
        return cleaned

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in BASELINE_PIPELINE_STATUSES:
            raise ValueError("status must be a known baseline pipeline status")
        return cleaned

    @field_validator("duration_seconds")
    @classmethod
    def validate_duration_seconds(cls, value: Optional[float]) -> Optional[float]:
        if value is not None and value < 0:
            raise ValueError("duration_seconds must not be negative")
        return value

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class BaselineEvaluationResult(BaseModel):
    """Frontend-safe result for a baseline evaluation."""

    success: bool
    run_id: Optional[str] = None
    status: str
    classification: Optional[str] = None
    confidence_score: Optional[float] = None
    strategy_name: str
    pairs: list[str] = Field(default_factory=list)
    timeframe: str
    exchange: str
    risk_profile: str
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    quality_flags: list[str] = Field(default_factory=list)
    stage_results: list[BaselineStageResult] = Field(default_factory=list)
    artifact_paths: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in BASELINE_PIPELINE_STATUSES:
            raise ValueError("status must be a known baseline pipeline status")
        return cleaned

    @field_validator("artifact_paths")
    @classmethod
    def validate_artifact_paths(cls, value: list[str]) -> list[str]:
        return [_validate_project_relative_path(path) for path in value]


class BaselineStatusResponse(BaseModel):
    """Frontend-safe status response for an existing baseline evaluation run."""

    run_id: str
    status: str
    classification: Optional[str] = None
    current_stage: Optional[str] = None
    stage_results: list[BaselineStageResult] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)
    decision: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned not in BASELINE_PIPELINE_STATUSES:
            raise ValueError("status must be a known baseline pipeline status")
        return cleaned

    @field_validator("current_stage")
    @classmethod
    def validate_current_stage(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        cleaned = value.strip()
        if cleaned not in BASELINE_PIPELINE_STAGES:
            raise ValueError("current_stage must be a known baseline pipeline stage")
        return cleaned
