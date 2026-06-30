"""
Optimization API router for Part 08.
Exposes optimization data through frontend-ready APIs.
"""
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.repositories.optimization import OptimizationRepository
from app.schemas.optimization import (
    OptimizationRequest,
    OptimizationResult,
    OptimizationRun,
    OptimizationRunListItem,
    OptimizationRunDetail,
    OptimizationTrial,
    OptimizationTrialDetail,
    OptimizationComparison,
    OptimizationStatusResponse,
    OptimizationStatus,
    OptimizationResultStatus,
)
from app.services.optimization_pipeline_service import OptimizationPipelineService
from app.services.strategy_readiness_gate import assert_strategy_ready_for_run


router = APIRouter(prefix="/optimization", tags=["Optimization"])


class OptimizationStartResponse(BaseModel):
    """Response for starting optimization."""
    run_id: str
    status: OptimizationStatus
    message: str


@router.post("/run", response_model=OptimizationStartResponse, status_code=202)
async def start_optimization(request: OptimizationRequest) -> OptimizationStartResponse:
    """
    Start an optimization pipeline run.

    This endpoint validates the request and initiates the optimization pipeline.
    The pipeline runs synchronously for Part 08; use the status endpoint to track progress.

    Requires user_confirmed=true before Hyperopt/backtest execution.

    Args:
        request: Optimization request with strategy, pairs, timeframe, and policy

    Returns:
        Optimization start response with run_id and initial status

    Raises:
        HTTPException: If request validation fails or pipeline cannot be started
    """
    # Validate request
    if not request.strategy_name or not request.pairs or not request.timeframe:
        raise HTTPException(
            status_code=400,
            detail="strategy_name, pairs, and timeframe are required"
        )

    # Validate user confirmation
    if not request.user_confirmed:
        raise HTTPException(
            status_code=400,
            detail="user_confirmed=true is required before Hyperopt/backtest execution"
        )

    # Part 12: Check strategy readiness before starting optimization
    assert_strategy_ready_for_run(request.strategy_name, run_type="optimization")

    # Initialize pipeline service with dependencies
    from app.repositories.optimization import OptimizationRepository
    from app.repositories.runs import RunRepository
    from app.services.hyperopt_policy_service import HyperoptPolicyService
    from app.services.freqtrade_hyperopt_runner import FreqtradeHyperoptRunner
    from app.services.hyperopt_result_parser import HyperoptResultParser
    from app.services.optimized_backtest_service import OptimizedBacktestService
    from app.services.strategy_params_materializer import StrategyParamsMaterializer
    from app.services.freqtrade_config_generator import FreqtradeConfigGenerator

    optimization_repo = OptimizationRepository()
    run_repo = RunRepository()
    hyperopt_policy_service = HyperoptPolicyService()
    hyperopt_runner = FreqtradeHyperoptRunner()
    hyperopt_parser = HyperoptResultParser()
    optimized_backtest_service = OptimizedBacktestService()
    params_materializer = StrategyParamsMaterializer()
    config_generator = FreqtradeConfigGenerator()

    pipeline_service = OptimizationPipelineService(
        optimization_repo=optimization_repo,
        run_repo=run_repo,
        hyperopt_policy_service=hyperopt_policy_service,
        hyperopt_runner=hyperopt_runner,
        hyperopt_parser=hyperopt_parser,
        optimized_backtest_service=optimized_backtest_service,
        params_materializer=params_materializer,
        config_generator=config_generator,
    )

    # Run optimization pipeline (synchronous for Part 08)
    try:
        result = pipeline_service.run_optimization(request)
    except Exception as e:
        # Truncate error message to avoid raw stack traces
        error_msg = str(e)
        if len(error_msg) > 200:
            error_msg = error_msg[:200] + "..."
        raise HTTPException(
            status_code=500,
            detail=f"Optimization pipeline failed: {error_msg}"
        )

    # Return start response
    return OptimizationStartResponse(
        run_id=result["optimization_run_id"],
        status=result["status"],
        message=f"Optimization pipeline completed with status: {result['status']}"
    )


@router.get("/runs", response_model=List[OptimizationRunListItem])
async def list_optimization_runs(
    limit: int = 100,
    offset: int = 0,
    status: Optional[OptimizationStatus] = None,
) -> List[OptimizationRunListItem]:
    """
    List all optimization runs.
    
    Returns a summary list of optimization runs with key metadata.
    Supports pagination and optional status filtering.
    
    Args:
        limit: Maximum number of runs to return (default: 100)
        offset: Number of runs to skip (default: 0)
        status: Optional status filter
        
    Returns:
        List of optimization run summaries
    """
    repo = OptimizationRepository()
    runs = repo.list_optimization_runs(limit=limit, status=status)
    
    # Convert to list items
    run_list_items = []
    for run in runs:
        run_list_items.append(OptimizationRunListItem(
            id=run["id"],
            strategy_name=run["strategy_name"],
            timeframe=run["timeframe"],
            pairs=run.get("pairs", []),
            exchange=run.get("exchange", ""),
            status=run["status"],
            result_status=run.get("result_status"),
            epochs_requested=run.get("epochs_requested"),
            epochs_completed=run.get("epochs_completed"),
            best_trial_id=run.get("best_trial_id"),
            created_at=run["created_at"],
            updated_at=run["updated_at"],
        ))
    
    return run_list_items


@router.get("/runs/{optimization_run_id}", response_model=OptimizationRunDetail)
async def get_optimization_run(optimization_run_id: str) -> OptimizationRunDetail:
    """
    Get full optimization run detail.
    
    Returns comprehensive information about an optimization run including
    metadata, request summary, stage results, baseline/optimized summaries,
    trial summary, best trial, comparison, artifacts, and warnings/errors.
    
    Args:
        optimization_run_id: ID of the optimization run
        
    Returns:
        Full optimization run detail
        
    Raises:
        HTTPException: If run not found (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    # Get best trial if available
    best_trial = None
    if run.get("best_trial_id"):
        trial = repo.get_trial(run["best_trial_id"])
        if trial:
            best_trial = OptimizationTrial(**trial)
    
    # Get comparison if available
    comparison = None
    comparison_data = repo.get_comparison(optimization_run_id)
    if comparison_data:
        comparison = OptimizationComparison(**comparison_data)
    
    return OptimizationRunDetail(
        run=OptimizationRun(**run),
        stages=[],  # TODO: Load stage results when implemented
        best_trial=best_trial,
        comparison=comparison,
        artifact_paths=run.get("artifact_paths", []),
    )


@router.get("/runs/{optimization_run_id}/status", response_model=OptimizationStatusResponse)
async def get_optimization_status(optimization_run_id: str) -> OptimizationStatusResponse:
    """
    Get lightweight optimization run status.
    
    Returns current status, current stage, trial counts, and any warnings/errors.
    Use this endpoint for polling optimization progress.
    
    Args:
        optimization_run_id: ID of the optimization run
        
    Returns:
        Lightweight status response
        
    Raises:
        HTTPException: If run not found (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    # Get trial count
    trials = repo.list_trials(optimization_run_id, limit=1000)
    
    return OptimizationStatusResponse(
        run_id=run["id"],
        status=run["status"],
        current_stage=None,  # TODO: Load current stage when implemented
        stage_progress=None,  # TODO: Load stage progress when implemented
        epochs_completed=run.get("epochs_completed"),
        epochs_total=run.get("epochs_requested"),
        trials_completed=len(trials),
        trials_total=None,  # TODO: Load total trials when implemented
        message=None,
        error_code=None,
        created_at=run["created_at"],
        updated_at=run["updated_at"],
    )


@router.get("/runs/{optimization_run_id}/trials", response_model=List[OptimizationTrial])
async def list_optimization_trials(
    optimization_run_id: str,
    limit: int = 100,
    offset: int = 0,
    status: Optional[str] = None,
) -> List[OptimizationTrial]:
    """
    List all trials for an optimization run.
    
    Returns every persisted trial, not only the best trial.
    Includes trial status, parameters summary, metrics, and rejection/failure reasons.
    
    Args:
        optimization_run_id: ID of the optimization run
        limit: Maximum number of trials to return (default: 100)
        offset: Number of trials to skip (default: 0)
        status: Optional status filter
        
    Returns:
        List of all trials for the run
        
    Raises:
        HTTPException: If run not found (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    trials = repo.list_trials(optimization_run_id, limit=limit, offset=offset)
    
    # Convert to schema objects
    trial_list = []
    for trial in trials:
        trial_list.append(OptimizationTrial(**trial))
    
    return trial_list


@router.get("/runs/{optimization_run_id}/trials/{trial_id}", response_model=OptimizationTrialDetail)
async def get_optimization_trial(
    optimization_run_id: str,
    trial_id: str,
) -> OptimizationTrialDetail:
    """
    Get full trial details.
    
    Returns complete trial information including full parameters (buy, sell, roi,
    stoploss, trailing), metrics, raw trial JSON if safe, artifact paths, and
    rejection/failure reasons.
    
    Args:
        optimization_run_id: ID of the optimization run
        trial_id: ID of the trial
        
    Returns:
        Full trial detail
        
    Raises:
        HTTPException: If run or trial not found (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    trial = repo.get_trial(trial_id)
    
    if not trial:
        raise HTTPException(
            status_code=404,
            detail=f"Trial {trial_id} not found"
        )
    
    return OptimizationTrialDetail(
        trial=OptimizationTrial(**trial),
        artifact_paths=trial.get("artifact_paths", []),
    )


@router.get("/runs/{optimization_run_id}/best-trial", response_model=OptimizationTrial)
async def get_best_trial(optimization_run_id: str) -> OptimizationTrial:
    """
    Get the best trial for an optimization run.
    
    Returns the trial marked as best with full parameters and metrics.
    
    Args:
        optimization_run_id: ID of the optimization run
        
    Returns:
        Best trial with full details
        
    Raises:
        HTTPException: If run not found (404) or no best trial exists (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    best_trial_id = run.get("best_trial_id")
    
    if not best_trial_id:
        raise HTTPException(
            status_code=404,
            detail=f"No best trial found for optimization run {optimization_run_id}"
        )
    
    trial = repo.get_trial(best_trial_id)
    
    if not trial:
        raise HTTPException(
            status_code=404,
            detail=f"Best trial {best_trial_id} not found"
        )
    
    return OptimizationTrial(**trial)


@router.get("/runs/{optimization_run_id}/comparison", response_model=OptimizationComparison)
async def get_optimization_comparison(optimization_run_id: str) -> OptimizationComparison:
    """
    Get baseline vs optimized comparison.
    
    Returns comparison data between baseline and optimized results including
    metric deltas, classification changes, and recommendations.
    
    Args:
        optimization_run_id: ID of the optimization run
        
    Returns:
        Baseline vs optimized comparison
        
    Raises:
        HTTPException: If run not found (404) or comparison not available (404)
    """
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    comparison_data = repo.get_comparison(optimization_run_id)
    
    if not comparison_data:
        raise HTTPException(
            status_code=404,
            detail=f"Comparison not available for optimization run {optimization_run_id}"
        )
    
    return OptimizationComparison(**comparison_data)


@router.get("/runs/{optimization_run_id}/report")
async def get_optimization_report(optimization_run_id: str):
    """
    Get optimization report artifact content.
    
    Returns the optimization report content if available.
    If the report does not exist, returns a controlled 404.
    
    Args:
        optimization_run_id: ID of the optimization run
        
    Returns:
        Report artifact content
        
    Raises:
        HTTPException: If run not found (404) or report not available (404)
    """
    import json
    from pathlib import Path
    
    repo = OptimizationRepository()
    run = repo.get_run(optimization_run_id)
    
    if not run:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization run {optimization_run_id} not found"
        )
    
    report_path = run.get("report_artifact_path")
    
    if not report_path:
        raise HTTPException(
            status_code=404,
            detail=f"Optimization report not available for run {optimization_run_id}"
        )
    
    # Try to read and return report content
    report_file = Path(report_path)
    if not report_file.exists():
        raise HTTPException(
            status_code=404,
            detail=f"Optimization report file not found at {report_path}"
        )
    
    try:
        with open(report_file, "r") as f:
            report_content = json.load(f)
        
        return {
            "optimization_run_id": optimization_run_id,
            "report_artifact_path": report_path,
            "status": "available",
            "report": report_content,
        }
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization report file exists but could not be parsed as JSON"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reading optimization report: {str(e)}"
        )
