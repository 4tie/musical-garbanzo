"""
Optimization schemas for Part 08.
Defines request/response models for optimization pipeline.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class OptimizationStage(str, Enum):
    """Optimization pipeline stages."""
    OPTIMIZATION_SETUP = "optimization_setup"
    BASELINE_REFERENCE = "baseline_reference"
    HYPEROPT_POLICY_VALIDATION = "hyperopt_policy_validation"
    HYPEROPT_CONFIG_GENERATION = "hyperopt_config_generation"
    DATA_CHECK = "data_check"
    DATA_DOWNLOAD = "data_download"
    HYPEROPT_EXECUTION = "hyperopt_execution"
    HYPEROPT_RESULT_PARSING = "hyperopt_result_parsing"
    TRIAL_PERSISTENCE = "trial_persistence"
    BEST_TRIAL_SELECTION = "best_trial_selection"
    OPTIMIZED_CONFIG_GENERATION = "optimized_config_generation"
    OPTIMIZED_BACKTEST = "optimized_backtest"
    OPTIMIZED_RESULT_PARSING = "optimized_result_parsing"
    OPTIMIZED_DECISION_EVALUATION = "optimized_decision_evaluation"
    BASELINE_VS_OPTIMIZED_COMPARISON = "baseline_vs_optimized_comparison"
    OPTIMIZATION_REPORT = "optimization_report"
    COMPLETION = "completion"


class OptimizationStatus(str, Enum):
    """Optimization run statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED_CONTROLLED = "failed_controlled"
    CONFIRMATION_REQUIRED = "confirmation_required"


class OptimizationResultStatus(str, Enum):
    """Optimization result statuses."""
    NOT_IMPROVED = "not_improved"
    IMPROVED = "improved"
    OPTIMIZATION_CANDIDATE = "optimization_candidate"
    OPTIMIZATION_PROMISING = "optimization_promising"
    OPTIMIZATION_REJECTED = "optimization_rejected"
    OVERFIT_SUSPECTED = "overfit_suspected"
    INVALID_OPTIMIZATION = "invalid_optimization"


class OptimizationTrialStatus(str, Enum):
    """Optimization trial statuses."""
    COMPLETED = "completed"
    FAILED = "failed"
    IGNORED = "ignored"
    BEST = "best"
    SELECTED_FOR_VALIDATION = "selected_for_validation"
    REJECTED = "rejected"


class HyperoptPolicy(BaseModel):
    """Hyperopt policy configuration."""
    max_epochs: int = 200
    default_epochs: int = 50
    allowed_spaces: List[str] = ["buy", "sell"]
    locked_spaces: List[str] = ["roi", "stoploss", "trailing", "protection"]
    max_optimized_parameters: int = 6
    allow_roi_optimization: bool = False
    allow_stoploss_optimization: bool = False
    allow_trailing_optimization: bool = False
    timeout_seconds: int = 3600
    min_trades: int = 10
    stop_on_zero_trades: bool = True
    notes: Optional[str] = None


class OptimizationRequest(BaseModel):
    """Request to start optimization pipeline."""
    strategy_name: str = Field(..., description="Strategy name in Freqtrade workspace")
    pairs: List[str] = Field(..., description="Trading pairs to optimize")
    timeframe: str = Field(..., description="Timeframe for optimization")
    exchange: str = Field(default="binance", description="Exchange name")
    days: Optional[int] = Field(default=30, description="Number of days of data")
    timerange: Optional[str] = Field(default=None, description="Specific time range")
    risk_profile: str = Field(default="balanced", description="Risk profile")
    baseline_run_id: Optional[str] = Field(default=None, description="Existing baseline run ID to reuse")
    run_baseline_first: bool = Field(default=True, description="Run baseline before optimization")
    download_missing_data: bool = Field(default=False, description="Download missing market data")
    user_confirmed: bool = Field(default=False, description="User confirmation for resource-intensive operations")
    epochs: int = Field(default=50, description="Number of hyperopt epochs")
    spaces: List[str] = Field(default=["buy", "sell"], description="Hyperopt spaces to optimize")
    max_open_trades: int = Field(default=3, description="Maximum open trades")
    stake_currency: str = Field(default="USDT", description="Stake currency")
    stake_amount: float | str = Field(default="unlimited", description="Stake amount")
    apply_decision_to_run: bool = Field(default=True, description="Apply decision classification to run")
    notes: Optional[str] = Field(default=None, description="Optional notes")

    @field_validator("strategy_name")
    @classmethod
    def validate_strategy_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("strategy_name is required and cannot be empty")
        return v.strip()

    @field_validator("pairs")
    @classmethod
    def validate_pairs(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("pairs must be non-empty")
        return [p.strip() for p in v if p.strip()]

    @field_validator("timeframe")
    @classmethod
    def validate_timeframe(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("timeframe is required and cannot be empty")
        return v.strip()

    @field_validator("epochs")
    @classmethod
    def validate_epochs(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("epochs must be greater than 0")
        if v > 200:
            raise ValueError("epochs cannot exceed 200")
        return v

    @field_validator("spaces")
    @classmethod
    def validate_spaces(cls, v: List[str]) -> List[str]:
        allowed = ["buy", "sell", "roi", "stoploss", "trailing", "protection"]
        for space in v:
            if space not in allowed:
                raise ValueError(f"Invalid space: {space}. Allowed spaces: {allowed}")
        return v

    @field_validator("risk_profile")
    @classmethod
    def validate_risk_profile(cls, v: str) -> str:
        allowed = ["conservative", "balanced", "aggressive"]
        if v not in allowed:
            raise ValueError(f"Invalid risk_profile: {v}. Allowed: {allowed}")
        return v


class OptimizationStageResult(BaseModel):
    """Result of a single optimization stage."""
    stage_name: OptimizationStage
    status: OptimizationStatus
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    artifact_paths: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)


class OptimizationTrial(BaseModel):
    """Optimization trial data."""
    id: str
    optimization_run_id: str
    trial_number: int
    status: OptimizationTrialStatus
    is_best: bool = False
    is_selected_for_validation: bool = False
    params: Dict[str, Any] = Field(default_factory=dict)
    buy_params: Optional[Dict[str, Any]] = None
    sell_params: Optional[Dict[str, Any]] = None
    roi_params: Optional[Dict[str, Any]] = None
    stoploss_params: Optional[Dict[str, Any]] = None
    trailing_params: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None
    loss_score: Optional[float] = None
    profit_total: Optional[float] = None
    profit_factor: Optional[float] = None
    expectancy: Optional[float] = None
    max_drawdown: Optional[float] = None
    trade_count: Optional[int] = None
    win_rate: Optional[float] = None
    rejection_reason: Optional[str] = None
    failure_reason: Optional[str] = None
    artifact_paths: List[str] = Field(default_factory=list)
    raw_trial: Optional[Dict[str, Any]] = None
    created_at: datetime


class OptimizationRun(BaseModel):
    """Optimization run data."""
    id: str
    parent_run_id: Optional[str] = None
    baseline_run_id: Optional[str] = None
    optimized_run_id: Optional[str] = None
    strategy_name: str
    timeframe: str
    pairs: List[str]
    exchange: str
    risk_profile: Optional[str] = None
    status: OptimizationStatus
    result_status: Optional[OptimizationResultStatus] = None
    best_trial_id: Optional[str] = None
    epochs_requested: Optional[int] = None
    epochs_completed: Optional[int] = None
    spaces: Optional[List[str]] = None
    policy: Optional[HyperoptPolicy] = None
    request: Optional[Dict[str, Any]] = None
    comparison: Optional[Dict[str, Any]] = None
    report_artifact_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OptimizationComparison(BaseModel):
    """Baseline vs optimized comparison."""
    optimization_run_id: str
    baseline_run_id: Optional[str] = None
    optimized_run_id: Optional[str] = None
    best_trial_id: Optional[str] = None
    baseline_metrics: Optional[Dict[str, Any]] = None
    optimized_metrics: Optional[Dict[str, Any]] = None
    delta_profit_factor: Optional[float] = None
    delta_expectancy: Optional[float] = None
    delta_drawdown: Optional[float] = None
    delta_trade_count: Optional[int] = None
    baseline_classification: Optional[str] = None
    optimized_classification: Optional[str] = None
    result_status: Optional[OptimizationResultStatus] = None
    improvement_summary: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    overfit_suspected: bool = False
    created_at: Optional[datetime] = None


class OptimizationResult(BaseModel):
    """Optimization pipeline result."""
    run_id: str
    status: OptimizationStatus
    result_status: Optional[OptimizationResultStatus] = None
    stages: List[OptimizationStageResult] = Field(default_factory=list)
    best_trial: Optional[OptimizationTrial] = None
    comparison: Optional[OptimizationComparison] = None
    artifact_paths: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None


class OptimizationStatusResponse(BaseModel):
    """Optimization run status response."""
    run_id: str
    status: OptimizationStatus
    current_stage: Optional[OptimizationStage] = None
    stage_progress: Optional[Dict[str, OptimizationStatus]] = None
    epochs_completed: Optional[int] = None
    epochs_total: Optional[int] = None
    trials_completed: Optional[int] = None
    trials_total: Optional[int] = None
    message: Optional[str] = None
    error_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OptimizationRunListItem(BaseModel):
    """Optimization run list item (summary)."""
    id: str
    strategy_name: str
    timeframe: str
    pairs: List[str]
    exchange: str
    status: OptimizationStatus
    result_status: Optional[OptimizationResultStatus] = None
    epochs_requested: Optional[int] = None
    epochs_completed: Optional[int] = None
    best_trial_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class OptimizationRunDetail(BaseModel):
    """Optimization run detail."""
    run: OptimizationRun
    stages: List[OptimizationStageResult] = Field(default_factory=list)
    best_trial: Optional[OptimizationTrial] = None
    comparison: Optional[OptimizationComparison] = None
    artifact_paths: List[str] = Field(default_factory=list)


class OptimizationTrialDetail(BaseModel):
    """Optimization trial detail."""
    trial: OptimizationTrial
    artifact_paths: List[str] = Field(default_factory=list)


class HyperoptRunResult(BaseModel):
    """Result of a hyperopt execution."""
    success: bool
    exit_code: Optional[int] = None
    duration_seconds: float
    stdout_path: Optional[str] = None
    stderr_path: Optional[str] = None
    result_files: List[str] = Field(default_factory=list)
    command_metadata: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    timed_out: bool = False
    blocked: bool = False
