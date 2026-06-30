"""
Strategy readiness gate service for Part 12.

Enforces strategy readiness checks before baseline and optimization runs.
This service validates strategy readiness without executing strategy code or running Freqtrade.
"""
from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException

from app.schemas.strategies import (
    StrategyDetail,
    StrategyIssue,
    StrategyReadiness,
    StrategyReadinessBlockedError,
    StrategyReadinessGateResult,
)
from app.services.strategy_workspace_service import StrategyWorkspaceService
from app.services.strategy_workspace_utils import StrategyWorkspaceError


# Allowed readiness states for run execution
_ALLOWED_READINESS_STATES = {
    StrategyReadiness.READY,
    StrategyReadiness.WARNING,
}

# Blocked readiness states for run execution
_BLOCKED_READINESS_STATES = {
    StrategyReadiness.MISSING_SIDECAR,
    StrategyReadiness.INVALID,
    StrategyReadiness.PARSE_ERROR,
    StrategyReadiness.UNSAFE,
}


def assert_strategy_ready_for_run(
    strategy_name: str,
    run_type: str = "baseline",
    workspace_service: Optional[StrategyWorkspaceService] = None,
) -> StrategyReadinessGateResult:
    """
    Assert that a strategy is ready for baseline or optimization run execution.

    This function performs static validation only - it does not execute strategy code,
    run Freqtrade, modify files, or auto-fix anything.

    Args:
        strategy_name: Name of the strategy to validate
        run_type: Type of run (baseline or optimization) for context in messages
        workspace_service: Optional StrategyWorkspaceService instance for testing

    Returns:
        StrategyReadinessGateResult with allowed=True if strategy is ready

    Raises:
        HTTPException: With structured StrategyReadinessBlockedError if strategy is not ready
    """
    service = workspace_service or StrategyWorkspaceService()

    try:
        detail = service.get_strategy(strategy_name)
    except StrategyWorkspaceError as exc:
        # Handle workspace errors (unsafe paths, missing strategy, etc.) as blocked
        blocked_error = StrategyReadinessBlockedError(
            strategy_name=strategy_name,
            readiness=StrategyReadiness.UNSAFE,
            issues=[
                StrategyIssue(
                    code="workspace_error",
                    severity="critical",
                    message=str(exc),
                )
            ],
            warnings=[],
        )
        blocked_error.message = f"Strategy '{strategy_name}' is not accessible: {exc}"
        raise HTTPException(
            status_code=400,
            detail=blocked_error.model_dump(),
        ) from exc

    # Check if readiness is allowed
    if detail.readiness in _ALLOWED_READINESS_STATES:
        return StrategyReadinessGateResult(
            strategy_name=strategy_name,
            readiness=detail.readiness,
            allowed=True,
            issues=detail.issues,
            warnings=detail.warnings,
            message=f"Strategy '{strategy_name}' is ready for {run_type} execution.",
            next_actions=[],
        )

    # Strategy is not ready - build blocked error response
    blocked_error = StrategyReadinessBlockedError(
        strategy_name=strategy_name,
        readiness=detail.readiness,
        issues=detail.issues,
        warnings=detail.warnings,
    )

    # Customize message based on readiness state
    if detail.readiness == StrategyReadiness.MISSING_SIDECAR:
        blocked_error.message = f"Strategy '{strategy_name}' is missing required sidecar JSON file."
    elif detail.readiness == StrategyReadiness.INVALID:
        blocked_error.message = f"Strategy '{strategy_name}' has invalid structure."
    elif detail.readiness == StrategyReadiness.PARSE_ERROR:
        blocked_error.message = f"Strategy '{strategy_name}' has parsing errors."
    elif detail.readiness == StrategyReadiness.UNSAFE:
        blocked_error.message = f"Strategy '{strategy_name}' contains unsafe patterns."

    # Raise HTTPException with structured error
    raise HTTPException(
        status_code=400,
        detail=blocked_error.model_dump(),
    )


def check_strategy_readiness(
    strategy_name: str,
    workspace_service: Optional[StrategyWorkspaceService] = None,
) -> StrategyReadinessGateResult:
    """
    Check strategy readiness without raising exceptions.

    This is a non-asserting version that returns the result regardless of readiness state.
    Useful for checking readiness without blocking execution.

    Args:
        strategy_name: Name of the strategy to validate
        workspace_service: Optional StrategyWorkspaceService instance for testing

    Returns:
        StrategyReadinessGateResult with allowed field indicating readiness
    """
    service = workspace_service or StrategyWorkspaceService()

    try:
        detail = service.get_strategy(strategy_name)
    except StrategyWorkspaceError as exc:
        # If strategy cannot be loaded, return blocked result
        return StrategyReadinessGateResult(
            strategy_name=strategy_name,
            readiness=StrategyReadiness.UNSAFE,
            allowed=False,
            issues=[
                StrategyIssue(
                    code="strategy_load_error",
                    severity="critical",
                    message=str(exc),
                )
            ],
            warnings=[],
            message=f"Strategy '{strategy_name}' could not be loaded: {exc}",
            next_actions=[
                "Verify strategy name is correct",
                "Check strategy file exists in workspace",
                "Inspect strategy workspace for errors",
            ],
        )

    # Determine if allowed
    allowed = detail.readiness in _ALLOWED_READINESS_STATES

    # Build message
    if allowed:
        message = f"Strategy '{strategy_name}' is ready for execution."
        next_actions = []
    else:
        message = f"Strategy '{strategy_name}' is not ready for execution."
        next_actions = [
            "Open Strategy Workspace",
            "Inspect strategy readiness issues",
            "Fix the strategy or sidecar JSON manually",
            "Revalidate before starting baseline or optimization",
        ]

    return StrategyReadinessGateResult(
        strategy_name=strategy_name,
        readiness=detail.readiness,
        allowed=allowed,
        issues=detail.issues,
        warnings=detail.warnings,
        message=message,
        next_actions=next_actions,
    )
