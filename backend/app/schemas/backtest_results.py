"""
Schemas for backtest result discovery and parsing.
"""
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


BacktestOutputFileType = Literal[
    "json",
    "zip",
    "meta_json",
    "stdout_log",
    "stderr_log",
    "unknown",
]

BacktestOutputSource = Literal[
    "raw_freqtrade_dir",
    "backtest_results_dir",
    "artifact_registry",
    "freqtrade_workspace",
    "unknown",
]


class BacktestOutputFile(BaseModel):
    """Metadata for one discovered backtest output file."""

    path: str
    relative_path: str
    file_name: str
    file_type: BacktestOutputFileType
    size_bytes: int
    modified_at: str
    source: BacktestOutputSource
    is_candidate_result: bool = False
    warnings: list[str] = Field(default_factory=list)


class BacktestOutputDiscoveryRequest(BaseModel):
    """Request to discover raw Freqtrade outputs for a run."""

    run_id: str


class BacktestOutputDiscoveryResult(BaseModel):
    """Structured result for raw Freqtrade output discovery."""

    run_id: str
    success: bool = False
    primary_result_path: Optional[str] = None
    files: list[BacktestOutputFile] = Field(default_factory=list)
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RawBacktestPayload(BaseModel):
    """One loaded raw Freqtrade backtest payload."""

    source_path: str
    source_type: str
    parser_type: str
    raw_data: Optional[dict] = None
    raw_text: Optional[str] = None
    zip_members: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class RawBacktestLoadRequest(BaseModel):
    """Request to load raw Freqtrade backtest result data."""

    path: Optional[str] = None
    run_id: Optional[str] = None


class RawBacktestLoadResult(BaseModel):
    """Result of loading raw Freqtrade backtest result data."""

    success: bool = False
    primary_payload: Optional[RawBacktestPayload] = None
    payloads: list[RawBacktestPayload] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExpectancyBreakdown(BaseModel):
    """Details for an expectancy calculation."""

    expectancy: Optional[float] = None
    method: str
    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    loss_rate: Optional[float] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    total_profit: Optional[float] = None
    warnings: list[str] = Field(default_factory=list)


class ExtractedBacktestMetrics(BaseModel):
    """Normalized metrics extracted from a raw Freqtrade payload."""

    net_profit: Optional[float] = None
    net_profit_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown: Optional[float] = None
    max_drawdown_pct: Optional[float] = None
    sharpe: Optional[float] = None
    calmar: Optional[float] = None
    win_rate: Optional[float] = None
    trade_count: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    avg_win: Optional[float] = None
    avg_loss: Optional[float] = None
    expectancy: Optional[float] = None
    expectancy_source: Optional[str] = None
    avg_duration: Optional[str] = None
    best_pair: Optional[str] = None
    worst_pair: Optional[str] = None
    source_type: str
    raw_metrics: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class MetricsExtractionResult(BaseModel):
    """Result envelope for backtest metrics extraction."""

    success: bool = False
    metrics: Optional[ExtractedBacktestMetrics] = None
    expectancy: Optional[ExpectancyBreakdown] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class ExtractedPairResult(BaseModel):
    """Normalized per-pair backtest result."""

    pair: str
    trade_count: Optional[int] = None
    net_profit: Optional[float] = None
    net_profit_pct: Optional[float] = None
    profit_factor: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    expectancy: Optional[float] = None
    avg_duration: Optional[str] = None
    raw_json: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ExtractedTradeSummary(BaseModel):
    """Normalized aggregate trade summary."""

    total_trades: Optional[int] = None
    wins: Optional[int] = None
    losses: Optional[int] = None
    draws: Optional[int] = None
    avg_duration: Optional[str] = None
    best_pair: Optional[str] = None
    worst_pair: Optional[str] = None
    raw_json: dict = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class PairTradeParseResult(BaseModel):
    """Result envelope for pair-level and trade-summary parsing."""

    success: bool = False
    pair_results: list[ExtractedPairResult] = Field(default_factory=list)
    trade_summary: Optional[ExtractedTradeSummary] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


ResultQualitySeverity = Literal["info", "warning", "error", "critical"]


class ResultQualityFlag(BaseModel):
    """One quality flag attached to parsed backtest results."""

    code: str
    severity: ResultQualitySeverity
    message: str
    details: Optional[dict] = None


class ResultQualityReport(BaseModel):
    """Quality report for parsed backtest result evidence."""

    run_id: Optional[str] = None
    parse_quality: str
    flags: list[ResultQualityFlag] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    is_usable_for_metrics: bool = False
    is_usable_for_decision: bool = False


class BacktestParseRequest(BaseModel):
    """Request to parse and persist backtest results for a run."""

    run_id: Optional[str] = None
    paths: list[str] = Field(default_factory=list)
    force: bool = False


class NormalizedBacktestResult(BaseModel):
    """Normalized parsed backtest result artifact payload."""

    run_id: str
    metrics: Optional[ExtractedBacktestMetrics] = None
    pair_results: list[ExtractedPairResult] = Field(default_factory=list)
    trade_summary: Optional[ExtractedTradeSummary] = None
    quality_flags: list[ResultQualityFlag] = Field(default_factory=list)
    parser_metadata: dict[str, Any] = Field(default_factory=dict)
    source_files: list[str] = Field(default_factory=list)
    created_at: str


class BacktestParseResult(BaseModel):
    """End-to-end parse and persistence result."""

    run_id: str
    success: bool = False
    discovery: Optional[BacktestOutputDiscoveryResult] = None
    loader: Optional[RawBacktestLoadResult] = None
    metrics: Optional[MetricsExtractionResult] = None
    pair_results: list[ExtractedPairResult] = Field(default_factory=list)
    trade_summary: Optional[ExtractedTradeSummary] = None
    quality_report: Optional[ResultQualityReport] = None
    saved_records: dict[str, Any] = Field(default_factory=dict)
    normalized_result_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class BacktestCombinedResult(BaseModel):
    """Combined latest parsed backtest result for API consumers."""

    run_id: str
    latest_metrics: Optional[dict[str, Any]] = None
    pair_results: list[dict[str, Any]] = Field(default_factory=list)
    trade_summary: Optional[dict[str, Any]] = None
    quality_report: Optional[ResultQualityReport] = None
    normalized_result_path: Optional[str] = None
    warnings: list[str] = Field(default_factory=list)
