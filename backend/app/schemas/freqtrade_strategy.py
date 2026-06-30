"""
Pydantic schemas for Freqtrade strategy detection and validation.
"""
from typing import Optional
from pydantic import BaseModel, Field


class FreqtradeStrategyFile(BaseModel):
    """Represents a detected Freqtrade strategy file."""

    strategy_name: str = Field(..., description="Strategy name (filename without .py)")
    class_name: Optional[str] = Field(None, description="Strategy class name if detected")
    file_path: Optional[str] = Field(None, description="Absolute path to the strategy .py file")
    params_path: Optional[str] = Field(None, description="Path to sidecar .json file if exists")
    exists: bool = Field(True, description="Whether the strategy file exists")
    has_sidecar_json: bool = Field(False, description="Whether sidecar .json file exists")
    source: str = Field("file", description="Detection source: 'file' or 'freqtrade'")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class FreqtradeStrategyStatus(BaseModel):
    """Represents the status of a specific strategy."""

    strategy_name: str = Field(..., description="Strategy name")
    exists: bool = Field(..., description="Whether the strategy file exists")
    freqtrade_visible: bool = Field(..., description="Whether Freqtrade can see the strategy")
    has_sidecar_json: bool = Field(..., description="Whether sidecar .json file exists")
    file_path: Optional[str] = Field(None, description="Path to strategy file if exists")
    params_path: Optional[str] = Field(None, description="Path to sidecar if exists")
    source: str = Field("file", description="Detection source")
    errors: list[str] = Field(default_factory=list, description="Validation errors")
    warnings: list[str] = Field(default_factory=list, description="Validation warnings")


class FreqtradeStrategyListResult(BaseModel):
    """Result of listing Freqtrade strategies."""

    strategies: list[FreqtradeStrategyFile] = Field(default_factory=list, description="List of detected strategies")
    freqtrade_visible: bool = Field(False, description="Whether Freqtrade is configured and visible")
    source: str = Field("file", description="Detection source: 'file' or 'freqtrade'")
    errors: list[str] = Field(default_factory=list, description="Detection errors")
    warnings: list[str] = Field(default_factory=list, description="Detection warnings")
