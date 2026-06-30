"""
Pydantic schemas for Part 06 decision persistence and APIs.
"""
from typing import Any, Optional

from pydantic import BaseModel, Field


class DecisionGateResult(BaseModel):
    """One acceptance-gate result produced by the decision engine."""

    gate_name: str = Field(..., description="Stable decision gate name")
    status: str = Field(..., description="Gate status")
    actual_value: Optional[Any] = Field(None, description="Observed value")
    threshold_value: Optional[Any] = Field(None, description="Configured threshold")
    message: str = Field(..., description="Human-readable gate message")
    severity: str = Field(..., description="Gate severity")
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionReason(BaseModel):
    """One user-facing reason for a decision result."""

    code: str = Field(..., description="Stable reason code")
    severity: str = Field(..., description="Reason severity")
    message: str = Field(..., description="Human-readable reason")
    metric: Optional[str] = Field(None, description="Related metric name")
    actual_value: Optional[Any] = Field(None, description="Observed value")
    threshold_value: Optional[Any] = Field(None, description="Configured threshold")
    details: dict[str, Any] = Field(default_factory=dict)


class DecisionEvidence(BaseModel):
    """Parsed Part 05 evidence used to support a decision result."""

    run_id: str
    metrics_snapshot_id: Optional[str] = None
    trade_summary_id: Optional[str] = None
    pair_count: Optional[int] = None
    trade_count: Optional[int] = None
    profit_factor: Optional[float] = None
    expectancy: Optional[float] = None
    max_drawdown: Optional[float] = None
    win_rate: Optional[float] = None
    quality_flags: list[str] = Field(default_factory=list)
    normalized_result_artifact_path: Optional[str] = None


class DecisionResult(BaseModel):
    """Persisted decision result."""

    id: Optional[str] = None
    run_id: str
    classification: str
    confidence_score: Optional[float] = None
    policy_name: str
    risk_profile: Optional[str] = None
    timeframe: Optional[str] = None
    gates: list[DecisionGateResult] = Field(default_factory=list)
    reasons: list[DecisionReason] = Field(default_factory=list)
    evidence: DecisionEvidence
    warnings: list[str] = Field(default_factory=list)
    blocking_failures: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)
    created_at: Optional[str] = None


class DecisionEvaluationRequest(BaseModel):
    """Request to evaluate a run's already-parsed backtest evidence."""

    run_id: str
    policy_name: Optional[str] = None
    risk_profile: Optional[str] = None
    timeframe: Optional[str] = None
    apply_to_run: bool = True
    force: bool = False


class DecisionEvaluationResponse(BaseModel):
    """Response returned after a decision evaluation is persisted."""

    run_id: str
    success: bool = True
    decision: Optional[DecisionResult] = None
    saved_decision_id: Optional[str] = None
    decision_report_path: Optional[str] = None
    run_updated: bool = False
    errors: list[str] = Field(default_factory=list)
    decision_id: Optional[str] = None
    classification: Optional[str] = None
    confidence_score: Optional[float] = None
    policy_name: Optional[str] = None
    gates: list[DecisionGateResult] = Field(default_factory=list)
    reasons: list[DecisionReason] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    blocking_failures: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(default_factory=list)


class MetricThresholds(BaseModel):
    """Metric thresholds used by a decision policy."""

    min_trades: int
    candidate_profit_factor: float
    promising_profit_factor: float
    validated_profit_factor: float
    max_drawdown_candidate: float
    max_drawdown_promising: float
    max_drawdown_validated: float
    min_expectancy_candidate: float
    min_expectancy_promising: float
    min_expectancy_validated: float
    min_win_rate_optional: Optional[float] = None
    single_pair_dependency_warning_threshold: float
    high_drawdown_block_threshold: float
    min_pair_count_warning: int


class DecisionPolicy(BaseModel):
    """Centralized acceptance policy for parsed backtest evidence."""

    policy_name: str
    risk_profile: str
    timeframe: Optional[str] = None
    thresholds: MetricThresholds
    description: str
    notes: list[str] = Field(default_factory=list)


class DecisionPolicySummary(BaseModel):
    """Summary of an available deterministic decision policy."""

    policy_name: str
    display_name: str
    description: str
    allowed_classifications: list[str] = Field(default_factory=list)
    gate_names: list[str] = Field(default_factory=list)
    risk_profile: Optional[str] = None
    timeframe: Optional[str] = None
    thresholds: Optional[MetricThresholds] = None
    notes: list[str] = Field(default_factory=list)
