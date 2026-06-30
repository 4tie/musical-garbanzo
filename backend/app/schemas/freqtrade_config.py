"""
Pydantic schemas for Freqtrade backtest config generation.
"""
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class FreqtradeBacktestConfigRequest(BaseModel):
    """Request schema for generating a Freqtrade backtest configuration."""

    run_id: str = Field(..., description="Associated run ID")
    exchange: str = Field("binance", description="Exchange name (default from settings)")
    trading_mode: str = Field("spot", description="Trading mode: spot, futures, margin")
    stake_currency: str = Field("USDT", description="Stake currency")
    stake_amount: Optional[str] = Field("unlimited", description="Stake amount (unlimited or numeric)")
    dry_run_wallet: float = Field(10000.0, description="Dry run wallet amount")
    max_open_trades: int = Field(3, description="Maximum open trades")
    pairs: list[str] = Field(..., description="Trading pairs (required, non-empty)")
    timeframe: str = Field(..., description="Timeframe (required, non-empty)")
    timerange: Optional[str] = Field(None, description="Timerange for backtest (e.g., 20240101-20240131)")
    strategy_name: str = Field(..., description="Strategy name (must be safe class-name style)")
    data_format_ohlcv: str = Field("feather", description="OHLCV data format")
    cancel_open_orders_on_exit: bool = Field(True, description="Cancel open orders on exit")
    additional_safe_config: Optional[dict] = Field(None, description="Additional safe config fields")

    @field_validator("pairs")
    @classmethod
    def validate_pairs_not_empty(cls, v: list[str]) -> list[str]:
        """Validate that pairs list is not empty."""
        if not v:
            raise ValueError("pairs must not be empty")
        return v

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name_safe(cls, v: str) -> str:
        """Validate that strategy name is safe class-name style."""
        if not v or not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("strategy_name must be safe class-name style (alphanumeric with underscores/hyphens)")
        return v

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe_not_empty(cls, v: str) -> str:
        """Validate that timeframe is not empty."""
        if not v or not v.strip():
            raise ValueError("timeframe must not be empty")
        return v.strip()

    @field_validator("trading_mode")
    @classmethod
    def validate_trading_mode(cls, v: str) -> str:
        """Validate trading mode is allowed."""
        allowed_modes = {"spot", "futures", "margin"}
        if v.lower() not in allowed_modes:
            raise ValueError(f"trading_mode must be one of: {', '.join(allowed_modes)}")
        return v.lower()

    @field_validator("additional_safe_config")
    @classmethod
    def validate_no_secrets_in_additional_config(cls, v: Optional[dict]) -> Optional[dict]:
        """Validate that additional config does not contain secret-like keys."""
        if not v:
            return v

        secret_keys = {
            "api_key", "apikey", "secret", "password", "token",
            "private_key", "app_secret", "discord_token", "exchange_key"
        }

        for key in v.keys():
            if key.lower() in secret_keys:
                raise ValueError(f"additional_safe_config must not contain secret-like keys: {key}")

        return v


class FreqtradeBacktestConfigResult(BaseModel):
    """Result schema for Freqtrade backtest config generation."""

    run_id: str
    config_path: str
    config: dict
    artifact_id: Optional[str] = None
    success: bool = True
    error: Optional[str] = None
