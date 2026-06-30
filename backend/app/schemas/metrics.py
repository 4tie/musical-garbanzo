"""
Pydantic schemas for Metrics API.
"""
from typing import Optional
from pydantic import BaseModel, Field


class MetricSnapshotCreate(BaseModel):
    """Schema for creating a metric snapshot."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    stage_key: Optional[str] = Field(None, description="Associated stage key")
    net_profit: Optional[float] = Field(None, description="Net profit")
    profit_factor: Optional[float] = Field(None, description="Profit factor")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    sharpe: Optional[float] = Field(None, description="Sharpe ratio")
    calmar: Optional[float] = Field(None, description="Calmar ratio")
    win_rate: Optional[float] = Field(None, description="Win rate")
    trade_count: Optional[int] = Field(None, description="Trade count")
    expectancy: Optional[float] = Field(None, description="Expectancy")
    avg_win: Optional[float] = Field(None, description="Average winning trade")
    avg_loss: Optional[float] = Field(None, description="Average losing trade")
    raw_json: Optional[dict] = Field(None, description="Raw metrics data as JSON")


class MetricSnapshotRead(BaseModel):
    """Schema for metric snapshot response."""
    id: str
    run_id: str
    stage_key: Optional[str]
    net_profit: Optional[float]
    profit_factor: Optional[float]
    max_drawdown: Optional[float]
    sharpe: Optional[float]
    calmar: Optional[float]
    win_rate: Optional[float]
    trade_count: Optional[int]
    expectancy: Optional[float]
    avg_win: Optional[float]
    avg_loss: Optional[float]
    raw_json: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


class PairResultCreate(BaseModel):
    """Schema for creating a pair result."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    pair: str = Field(..., description="Trading pair (e.g., BTC/USDT)")
    net_profit: Optional[float] = Field(None, description="Net profit")
    profit_factor: Optional[float] = Field(None, description="Profit factor")
    max_drawdown: Optional[float] = Field(None, description="Maximum drawdown")
    trade_count: Optional[int] = Field(None, description="Trade count")
    win_rate: Optional[float] = Field(None, description="Win rate")
    expectancy: Optional[float] = Field(None, description="Expectancy")
    raw_json: Optional[dict] = Field(None, description="Raw pair result data as JSON")


class PairResultRead(BaseModel):
    """Schema for pair result response."""
    id: str
    run_id: str
    pair: str
    net_profit: Optional[float]
    profit_factor: Optional[float]
    max_drawdown: Optional[float]
    trade_count: Optional[int]
    win_rate: Optional[float]
    expectancy: Optional[float]
    raw_json: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True


class TradeSummaryCreate(BaseModel):
    """Schema for creating a trade summary."""
    run_id: Optional[str] = Field(None, description="Associated run ID")
    total_trades: Optional[int] = Field(None, description="Total number of trades")
    wins: Optional[int] = Field(None, description="Number of winning trades")
    losses: Optional[int] = Field(None, description="Number of losing trades")
    draws: Optional[int] = Field(None, description="Number of draw trades")
    avg_duration: Optional[str] = Field(None, description="Average trade duration")
    best_pair: Optional[str] = Field(None, description="Best performing pair")
    worst_pair: Optional[str] = Field(None, description="Worst performing pair")
    raw_json: Optional[dict] = Field(None, description="Raw trade summary data as JSON")


class TradeSummaryRead(BaseModel):
    """Schema for trade summary response."""
    id: str
    run_id: str
    total_trades: Optional[int]
    wins: Optional[int]
    losses: Optional[int]
    draws: Optional[int]
    avg_duration: Optional[str]
    best_pair: Optional[str]
    worst_pair: Optional[str]
    raw_json: Optional[dict]
    created_at: str

    class Config:
        from_attributes = True
