"""
Pydantic schemas for Freqtrade backtest execution.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FreqtradeBacktestRequest(BaseModel):
    """Request for running a Freqtrade backtest."""

    run_id: str = Field(..., description="Associated run ID")
    config_path: str = Field(..., description="Path to backtest config file")
    strategy_name: str = Field(..., description="Strategy name to backtest")
    timeframe: str = Field(..., description="Timeframe for backtest")
    timerange: Optional[str] = Field(None, description="Optional timerange for backtest")
    pairs: Optional[list[str]] = Field(None, description="Optional trading pairs")
    export: str = Field("trades", description="Export type: none, trades, signals")
    backtest_directory: Optional[str] = Field(None, description="Optional custom backtest directory")
    user_confirmed: bool = Field(False, description="User must confirm to run real backtest")
    timeout_seconds: int = Field(1800, description="Timeout in seconds")

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        """Validate that strategy name is safe class-name style."""
        import re
        if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", v):
            raise ValueError(f"Strategy name must be valid class-name style: {v}")
        return v

    @field_validator("export")
    @classmethod
    def validate_export(cls, v: str) -> str:
        """Validate export type is allowed."""
        allowed_exports = {"none", "trades", "signals"}
        if v.lower() not in allowed_exports:
            raise ValueError(f"export must be one of: {', '.join(allowed_exports)}")
        return v.lower()

    @field_validator("user_confirmed")
    @classmethod
    def validate_user_confirmed(cls, v: bool) -> bool:
        """Validate that user has confirmed the backtest."""
        if not v:
            raise ValueError("user_confirmed must be true to run real backtest")
        return v


class FreqtradeBacktestArtifact(BaseModel):
    """Represents a backtest output artifact."""

    artifact_type: str = Field(..., description="Type of artifact")
    path: str = Field(..., description="Path to artifact file")
    size_bytes: Optional[int] = Field(None, description="Size in bytes")
    created_at: Optional[str] = Field(None, description="Creation timestamp")


class FreqtradeBacktestResult(BaseModel):
    """Result of a Freqtrade backtest execution."""

    run_id: str = Field(..., description="Associated run ID")
    success: bool = Field(..., description="Whether backtest succeeded")
    blocked: bool = Field(False, description="Whether backtest was blocked")
    exit_code: Optional[int] = Field(None, description="Exit code from backtest command")
    stdout: str = Field("", description="Stdout from backtest command")
    stderr: str = Field("", description="Stderr from backtest command")
    duration_seconds: float = Field(0.0, description="Duration in seconds")
    backtest_directory: Optional[str] = Field(None, description="Backtest output directory")
    artifacts: list[FreqtradeBacktestArtifact] = Field(default_factory=list, description="Discovered artifacts")
    error: Optional[str] = Field(None, description="Error message if failed")
    errors: list[str] = Field(default_factory=list, description="Execution errors")
    warnings: list[str] = Field(default_factory=list, description="Execution warnings")
