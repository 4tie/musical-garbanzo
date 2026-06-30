"""
API router for Part 11 strategy workspace inspection.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.strategies import (
    StrategyDetail,
    StrategyImportRequest,
    StrategyImportResult,
    StrategyParamsSummary,
    StrategyReadiness,
    StrategySummary,
)
from app.services.strategy_workspace_service import StrategyWorkspaceService
from app.services.strategy_workspace_utils import StrategyWorkspaceError


router = APIRouter(tags=["Strategy Workspace"])


def _service() -> StrategyWorkspaceService:
    return StrategyWorkspaceService()


def _is_missing_strategy(detail: StrategyDetail) -> bool:
    return any(issue.code == "strategy_file_missing" for issue in detail.issues)


def _is_unsafe_request(detail: StrategyDetail) -> bool:
    return any(issue.code == "unsafe_path" for issue in detail.issues)


def _raise_for_detail_errors(detail: StrategyDetail) -> None:
    if _is_unsafe_request(detail):
        raise HTTPException(status_code=400, detail="Invalid or unsafe strategy name")
    if _is_missing_strategy(detail):
        raise HTTPException(status_code=404, detail=f"Strategy {detail.strategy_name} not found")


def _filtered_page(
    strategies: list[StrategySummary],
    readiness: Optional[StrategyReadiness],
    has_sidecar: Optional[bool],
    search: Optional[str],
    limit: int,
    offset: int,
) -> list[StrategySummary]:
    filtered = strategies
    if readiness is not None:
        filtered = [strategy for strategy in filtered if strategy.readiness == readiness]
    if has_sidecar is not None:
        filtered = [strategy for strategy in filtered if strategy.has_sidecar == has_sidecar]
    if search:
        needle = search.strip().lower()
        if needle:
            filtered = [
                strategy
                for strategy in filtered
                if needle in strategy.strategy_name.lower()
            ]
    return filtered[offset : offset + limit]


@router.get("/strategies", response_model=list[StrategySummary])
def list_strategy_workspace(
    readiness: Optional[StrategyReadiness] = None,
    has_sidecar: Optional[bool] = None,
    search: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> list[StrategySummary]:
    """Return real local strategy workspace summaries."""
    try:
        strategies = _service().list_strategies()
    except StrategyWorkspaceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _filtered_page(strategies, readiness, has_sidecar, search, limit, offset)


@router.post("/strategies/import", response_model=StrategyImportResult)
def import_strategy_workspace(request: StrategyImportRequest) -> StrategyImportResult:
    """Safely import project-relative strategy files into the workspace."""
    result = _service().import_strategy(request)
    if any(issue.code == "unsafe_import_path" for issue in result.issues):
        raise HTTPException(status_code=400, detail=result.issues[0].message)
    return result


@router.get("/strategies/{strategy_name}/params", response_model=StrategyParamsSummary)
def get_strategy_workspace_params(strategy_name: str) -> StrategyParamsSummary:
    """Return a safe sidecar JSON summary for one local strategy."""
    detail = _service().get_strategy(strategy_name)
    _raise_for_detail_errors(detail)
    return detail.params_summary


@router.post("/strategies/{strategy_name}/validate", response_model=StrategyDetail)
def validate_strategy_workspace(strategy_name: str) -> StrategyDetail:
    """Rerun static readiness checks for one local strategy."""
    detail = _service().validate_strategy(strategy_name)
    _raise_for_detail_errors(detail)
    return detail


@router.get("/strategies/{strategy_name}", response_model=StrategyDetail)
def get_strategy_workspace_detail(strategy_name: str) -> StrategyDetail:
    """Return static inspection detail for one local strategy."""
    detail = _service().get_strategy(strategy_name)
    _raise_for_detail_errors(detail)
    return detail
