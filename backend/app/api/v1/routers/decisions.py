"""
API router for Part 06 decision policies and decision results.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException

from app.repositories.decisions import DecisionRepository
from app.repositories.runs import RunRepository
from app.schemas.decisions import (
    DecisionEvaluationRequest,
    DecisionEvaluationResponse,
    DecisionPolicy,
    DecisionPolicySummary,
)
from app.services.decision_policy import DecisionPolicyService
from app.services.decision_service import DecisionService


router = APIRouter(tags=["Decisions"])


@router.get("/decisions/policies", response_model=list[DecisionPolicySummary])
def list_decision_policies():
    """Return available deterministic decision policy summaries."""
    service = DecisionPolicyService()
    return [
        service.summarize_policy(service.get_policy(policy_name=policy_name))
        for policy_name in ("default_conservative", "default_balanced", "default_aggressive")
    ]


@router.get("/decisions/policies/{policy_name}", response_model=DecisionPolicy)
def get_decision_policy(policy_name: str):
    """Return one decision policy by name."""
    service = DecisionPolicyService()
    try:
        return service.get_policy(policy_name=policy_name)
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Decision policy {policy_name} not found")


@router.post("/decisions/runs/{run_id}/evaluate", response_model=DecisionEvaluationResponse)
def evaluate_run_decision(
    run_id: str,
    request_body: Optional[dict] = Body(default=None),
):
    """
    Evaluate a run using already-parsed Part 05 evidence.

    This endpoint does not run Freqtrade, parse raw output, call Ollama, send
    Discord messages, approve strategies, or export strategies.
    """
    request_body = request_body or {}
    request = DecisionEvaluationRequest(
        run_id=run_id,
        policy_name=request_body.get("policy_name"),
        risk_profile=request_body.get("risk_profile"),
        timeframe=request_body.get("timeframe"),
        apply_to_run=request_body.get("apply_to_run", True),
        force=request_body.get("force", False),
    )
    response = DecisionService().evaluate_run(request)
    if not response.success and "run_not_found" in response.errors:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return _sanitize_api_payload(response)


@router.get("/decisions/runs/{run_id}")
def list_run_decisions(run_id: str):
    """Return all saved decisions for a run."""
    _get_run_or_404(run_id)
    decisions = DecisionRepository().list_decisions_for_run(run_id)
    return _sanitize_api_payload(decisions)


@router.get("/decisions/runs/{run_id}/latest")
def get_latest_run_decision(run_id: str):
    """Return the latest saved decision for a run."""
    return _latest_decision_or_404(run_id)


@router.get("/results/backtest/{run_id}/decision")
def get_backtest_decision(run_id: str):
    """Compatibility endpoint for the latest backtest decision."""
    return _latest_decision_or_404(run_id)


@router.get("/runs/{run_id}/decision")
def get_run_decision(run_id: str):
    """Compatibility endpoint for the latest run decision."""
    return _latest_decision_or_404(run_id)


def _get_run_or_404(run_id: str) -> dict:
    """Return a run or raise a clean 404."""
    run = RunRepository().get_run(run_id)
    if not run:
        raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
    return run


def _latest_decision_or_404(run_id: str):
    """Return latest decision or raise 404."""
    _get_run_or_404(run_id)
    decision = DecisionRepository().get_latest_decision_for_run(run_id)
    if not decision:
        raise HTTPException(status_code=404, detail=f"No decision found for run {run_id}")
    return _sanitize_api_payload(decision)


def _sanitize_api_payload(value: Any) -> Any:
    """Remove deployment-oriented wording from outward decision API payloads."""
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    elif hasattr(value, "dict"):
        value = value.dict()

    if isinstance(value, dict):
        return {key: _sanitize_api_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize_api_payload(item) for item in value]
    if isinstance(value, str):
        replacements = {
            "Do not export this strategy.": "Keep this strategy in review only.",
            "approved": "accepted",
            "Approved": "Accepted",
            "exported": "packaged",
            "Exported": "Packaged",
            "export": "package",
            "Export": "Package",
            "live_ready": "deployment_ready",
            "live-ready": "deployment-ready",
            "live ready": "deployment ready",
        }
        sanitized = value
        for needle, replacement in replacements.items():
            sanitized = sanitized.replace(needle, replacement)
        return sanitized
    return value
