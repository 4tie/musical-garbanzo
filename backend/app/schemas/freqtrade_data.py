"""
Pydantic schemas for Freqtrade data availability and download.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class PairDataStatus(BaseModel):
    """Status of data availability for a specific pair."""

    pair: str = Field(..., description="Trading pair")
    timeframe: str = Field(..., description="Timeframe")
    exists: bool = Field(..., description="Whether data exists locally")
    file_path: Optional[str] = Field(None, description="Path to data file if exists")
    timerange: Optional[str] = Field(None, description="Available timerange if known")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class FreqtradeDataCheckRequest(BaseModel):
    """Request for checking data availability."""

    run_id: Optional[str] = Field(None, description="Associated run ID")
    config_path: Optional[str] = Field(None, description="Optional config path")
    exchange: str = Field(..., description="Exchange name")
    trading_mode: str = Field("spot", description="Trading mode: spot, futures, margin")
    pairs: list[str] = Field(..., description="Trading pairs to check")
    timeframe: str = Field(..., description="Timeframe to check")
    timerange: Optional[str] = Field(None, description="Optional timerange to check")
    show_timerange: bool = Field(True, description="Whether to show timerange info")

    @field_validator("pairs")
    @classmethod
    def validate_pairs_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that pairs list is not empty."""
        if not v:
            raise ValueError("pairs must not be empty")
        return v

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """Validate trading mode is allowed."""
        allowed_modes = {"spot", "futures", "margin"}
        if v.lower() not in allowed_modes:
            raise ValueError(f"trading_mode must be one of: {', '.join(allowed_modes)}")
        return v.lower()


class FreqtradeDataCheckResult(BaseModel):
    """Result of data availability check."""

    run_id: Optional[str] = Field(None, description="Associated run ID")
    exchange: str = Field(..., description="Exchange name")
    trading_mode: str = Field(..., description="Trading mode")
    pairs: list[PairDataStatus] = Field(default_factory=list, description="Pair data statuses")
    freqtrade_visible: bool = Field(False, description="Whether Freqtrade is configured and visible")
    source: str = Field("file", description="Detection source: 'file' or 'freqtrade'")
    errors: list[str] = Field(default_factory=list, description="Check errors")
    warnings: list[str] = Field(default_factory=list, description="Check warnings")


class FreqtradeDataDownloadRequest(BaseModel):
    """Request for downloading market data."""

    run_id: Optional[str] = Field(None, description="Associated run ID")
    config_path: Optional[str] = Field(None, description="Optional config path")
    exchange: str = Field(..., description="Exchange name")
    trading_mode: str = Field("spot", description="Trading mode: spot, futures, margin")
    pairs: list[str] = Field(..., description="Trading pairs to download")
    timeframes: list[str] = Field(..., description="Timeframes to download")
    days: Optional[int] = Field(None, description="Number of days to download")
    timerange: Optional[str] = Field(None, description="Timerange to download")
    data_format_ohlcv: str = Field("feather", description="OHLCV data format")
    user_confirmed: bool = Field(False, description="User must confirm to run real download")

    @field_validator("pairs")
    @classmethod
    def validate_pairs_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that pairs list is not empty."""
        if not v:
            raise ValueError("pairs must not be empty")
        return v

    @field_validator("timeframes")
    @classmethod
    def validate_timeframes_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that timeframes list is not empty."""
        if not v:
            raise ValueError("timeframes must not be empty")
        return v

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """Validate trading mode is allowed."""
        allowed_modes = {"spot", "futures", "margin"}
        if v.lower() not in allowed_modes:
            raise ValueError(f"trading_mode must be one of: {', '.join(allowed_modes)}")
        return v.lower()

    @field_validator("user_confirmed")
    @classmethod
    def validate_user_confirmed(cls, v: bool) -> bool:
        """Validate that user has confirmed the download."""
        if not v:
            raise ValueError("user_confirmed must be true to run real download")
        return v

    @model_validator(mode="after")
    def validate_days_or_timerange(self) -> "FreqtradeDataDownloadRequest":
        """Validate that either days or timerange is provided."""
        if self.days is None and self.timerange is None:
            raise ValueError("Either days or timerange must be provided for download")
        return self


class FreqtradeDataDownloadResult(BaseModel):
    """Result of data download operation."""

    run_id: Optional[str] = Field(None, description="Associated run ID")
    exchange: str = Field(..., description="Exchange name")
    trading_mode: str = Field(..., description="Trading mode")
    pairs: list[str] = Field(..., description="Pairs requested")
    timeframes: list[str] = Field(..., description="Timeframes requested")
    success: bool = Field(..., description="Whether download succeeded")
    blocked: bool = Field(False, description="Whether download was blocked")
    stdout: str = Field("", description="Stdout from download command")
    stderr: str = Field("", description="Stderr from download command")
    error: Optional[str] = Field(None, description="Error message if failed")
    duration: float = Field(0.0, description="Duration in seconds")
    errors: list[str] = Field(default_factory=list, description="Download errors")
    warnings: list[str] = Field(default_factory=list, description="Download warnings")
