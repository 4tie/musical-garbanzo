"""
Optimization pipeline service for Part 08.
Orchestrates the full optimization pipeline from baseline reference to final report.
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import HER_ARTIFACTS_RUNS
from app.repositories.optimization import OptimizationRepository
from app.repositories.runs import RunRepository
from app.schemas.optimization import (
    OptimizationRequest,
    OptimizationStatus,
    OptimizationResultStatus,
    OptimizationStage,
    HyperoptPolicy,
    OptimizationComparison,
)
from app.schemas.runs import RunCreate
from app.services.hyperopt_policy_service import HyperoptPolicyService
from app.services.freqtrade_hyperopt_runner import FreqtradeHyperoptRunner
from app.services.hyperopt_result_parser import HyperoptResultParser
from app.services.optimized_backtest_service import OptimizedBacktestService
from app.services.strategy_params_materializer import StrategyParamsMaterializer
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator

logger = logging.getLogger(__name__)


class OptimizationPipelineService:
    """Orchestrates the full optimization pipeline."""

    def __init__(
        self,
        optimization_repo: Optional[OptimizationRepository] = None,
        run_repo: Optional[RunRepository] = None,
        hyperopt_policy_service: Optional[HyperoptPolicyService] = None,
        hyperopt_runner: Optional[FreqtradeHyperoptRunner] = None,
        hyperopt_parser: Optional[HyperoptResultParser] = None,
        optimized_backtest_service: Optional[OptimizedBacktestService] = None,
        params_materializer: Optional[StrategyParamsMaterializer] = None,
        config_generator: Optional[FreqtradeConfigGenerator] = None,
    ) -> None:
        """
        Initialize the optimization pipeline service.

        Args:
            optimization_repo: Optional optimization repository
            run_repo: Optional run repository
            hyperopt_policy_service: Optional hyperopt policy service
            hyperopt_runner: Optional hyperopt runner
            hyperopt_parser: Optional hyperopt result parser
            optimized_backtest_service: Optional optimized backtest service
            params_materializer: Optional params materializer
            config_generator: Optional config generator
        """
        self.optimization_repo = optimization_repo or OptimizationRepository()
        self.run_repo = run_repo or RunRepository()
        self.hyperopt_policy_service = hyperopt_policy_service or HyperoptPolicyService()
        self.hyperopt_runner = hyperopt_runner or FreqtradeHyperoptRunner()
        self.hyperopt_parser = hyperopt_parser or HyperoptResultParser()
        self.optimized_backtest_service = optimized_backtest_service or OptimizedBacktestService()
        self.params_materializer = params_materializer or StrategyParamsMaterializer()
        self.config_generator = config_generator or FreqtradeConfigGenerator()

    def run_optimization(
        self,
        request: OptimizationRequest,
    ) -> Dict[str, Any]:
        """
        Run the full optimization pipeline.

        Args:
            request: Optimization request

        Returns:
            Dictionary with optimization run ID, status, and results

        Raises:
            ValueError: If pipeline configuration is invalid
        """
        logger.info(f"Starting optimization pipeline for strategy {request.strategy_name}")

        optimization_run_id = None
        baseline_run_id = None

        try:
            # Stage 1: optimization_setup
            optimization_run_id = self._stage_optimization_setup(request)
            logger.info(f"Created optimization run: {optimization_run_id}")
            # Stage 2: baseline_reference
            baseline_run_id = self._stage_baseline_reference(
                optimization_run_id, request
            )
            logger.info(f"Baseline reference: {baseline_run_id}")

            # Stage 3: hyperopt_policy_validation
            policy = self._stage_hyperopt_policy_validation(request)
            logger.info("Hyperopt policy validated")

            # Stage 4: hyperopt_config_generation
            config_path = self._stage_hyperopt_config_generation(request, optimization_run_id)
            logger.info(f"Hyperopt config generated: {config_path}")

            # Stage 5: data_check
            self._stage_data_check(request)
            logger.info("Data check passed")

            # Stage 6: data_download (if needed)
            self._stage_data_download(request)
            logger.info("Data download completed")

            # Stage 7: hyperopt_execution
            hyperopt_result = self._stage_hyperopt_execution(
                optimization_run_id, request, config_path, policy
            )
            logger.info(f"Hyperopt execution completed: {hyperopt_result.success}")
            logger.info(f"Hyperopt result files: {hyperopt_result.result_files}")

            if not hyperopt_result.success:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "hyperopt_failed",
                    hyperopt_result.errors,
                )

            # Stage 8: hyperopt_result_parsing
            parse_result = self._stage_hyperopt_result_parsing(
                optimization_run_id, hyperopt_result.result_files, policy
            )
            logger.info(f"Parsed {parse_result['persisted_trials_count']} trials")

            if parse_result["persisted_trials_count"] == 0:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "no_trials_parsed",
                    ["No trials could be parsed from hyperopt results"],
                )

            # Stage 9: trial_persistence (done in parsing stage)

            # Stage 10: best_trial_selection
            best_trial = self._stage_best_trial_selection(optimization_run_id)
            best_trial_id = None
            if best_trial:
                if isinstance(best_trial, dict):
                    best_trial_id = best_trial.get("id")
                else:
                    best_trial_id = getattr(best_trial, "id", None)
            logger.info(f"Best trial selected: {best_trial_id}")

            if not best_trial:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "best_trial_missing",
                    ["No best trial could be selected"],
                )

            # Stage 11: optimized_config_generation (done in optimized backtest)

            # Stage 12: optimized_backtest
            optimized_result = self._stage_optimized_backtest(
                optimization_run_id, baseline_run_id, best_trial, request
            )
            logger.info(f"Optimized backtest completed: {optimized_result['success']}")

            if not optimized_result["success"]:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "optimized_backtest_failed",
                    [optimized_result.get("error", "Unknown error")],
                    optimized_run_id=optimized_result.get("optimized_run_id"),
                )

            # Stage 13: optimized_result_parsing (done in backtest service)

            # Stage 14: optimized_decision_evaluation (done in backtest service)

            # Stage 15: baseline_vs_optimized_comparison
            comparison = self._stage_baseline_vs_optimized_comparison(
                optimization_run_id, baseline_run_id, optimized_result, best_trial
            )
            logger.info("Comparison completed")

            # Stage 16: optimization_report
            self._stage_optimization_report(
                optimization_run_id, request, baseline_run_id, best_trial, optimized_result, comparison
            )
            logger.info("Optimization report generated")

            # Stage 17: completion
            self._stage_completion(optimization_run_id, optimized_result, comparison)

            return self._build_success_result(
                optimization_run_id,
                baseline_run_id,
                optimized_result,
                best_trial,
                comparison,
                parse_result["persisted_trials_count"],
            )

        except ValueError as e:
            logger.error(f"Pipeline failed with controlled error: {e}")
            # Map known ValueError messages to specific error codes
            error_msg = str(e)
            if "Baseline run" in error_msg and "not found" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "baseline_missing",
                    [error_msg],
                )
            elif "no parsed metrics" in error_msg.lower():
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "baseline_missing",
                    [error_msg],
                )
            elif "no decision classification" in error_msg.lower():
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "baseline_missing",
                    [error_msg],
                )
            elif "No baseline run provided" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "baseline_missing",
                    [error_msg],
                )
            elif "Data missing" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "data_missing",
                    [error_msg],
                )
            elif "Data download requires user confirmation" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "confirmation_required_for_download",
                    [error_msg],
                )
            elif "User confirmation required" in error_msg and "Hyperopt" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "confirmation_required_for_hyperopt",
                    [error_msg],
                )
            elif "Data download failed" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "data_download_failed",
                    [error_msg],
                )
            elif "Hyperopt execution failed" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "hyperopt_failed",
                    [error_msg],
                )
            elif "Baseline evaluation failed" in error_msg:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "baseline_failed",
                    [error_msg],
                )
            else:
                return self._controlled_failure(
                    optimization_run_id,
                    baseline_run_id,
                    "unexpected_optimization_error",
                    [error_msg],
                )
        except Exception as e:
            logger.error(f"Pipeline failed with unhandled error: {e}")
            # Truncate error message to avoid raw stack traces
            error_msg = str(e)
            if len(error_msg) > 200:
                error_msg = error_msg[:200] + "..."
            return self._controlled_failure(
                optimization_run_id,
                baseline_run_id,
                "unexpected_optimization_error",
                [error_msg],
            )

    def _stage_optimization_setup(self, request: OptimizationRequest) -> str:
        """Stage 1: optimization_setup."""
        return self.optimization_repo.create_optimization_run(
            {
                "strategy_name": request.strategy_name,
                "timeframe": request.timeframe,
                "pairs": request.pairs,
                "exchange": request.exchange or "binance",
                "risk_profile": request.risk_profile,
                "status": OptimizationStatus.RUNNING,
                "epochs_requested": request.epochs,
                "spaces": request.spaces,
                "policy": None,  # Policy is determined in validation stage
                "request": request.model_dump(mode="json"),
            }
        )["id"]

    def _stage_baseline_reference(
        self,
        optimization_run_id: str,
        request: OptimizationRequest,
    ) -> str:
        """Stage 2: baseline_reference."""
        if request.baseline_run_id:
            # Use provided baseline - verify it has parsed metrics and decision
            baseline_run = self.run_repo.get_run(request.baseline_run_id)
            if not baseline_run:
                raise ValueError(f"Baseline run {request.baseline_run_id} not found")
            
            # Verify baseline has metrics and decision
            if not baseline_run.get("metrics"):
                raise ValueError(f"Baseline run {request.baseline_run_id} has no parsed metrics")
            if not baseline_run.get("classification"):
                raise ValueError(f"Baseline run {request.baseline_run_id} has no decision classification")
            
            self.optimization_repo.update_optimization_run(
                optimization_run_id, {"baseline_run_id": request.baseline_run_id}
            )
            return request.baseline_run_id

        if request.run_baseline_first:
            # Call BaselineEvaluationService to run real baseline evaluation
            from app.services.baseline_evaluation_service import BaselineEvaluationService
            from app.schemas.baseline import BaselineEvaluationRequest
            
            baseline_service = BaselineEvaluationService()
            
            # Build baseline evaluation request
            baseline_request = BaselineEvaluationRequest(
                strategy_name=request.strategy_name,
                exchange=request.exchange or "binance",
                trading_mode="spot",
                stake_currency="USDT",
                stake_amount="unlimited",
                max_open_trades=1,
                timeframe=request.timeframe,
                pairs=request.pairs,
                timerange=None,
                days=request.days,
                risk_profile=request.risk_profile,
                download_missing_data=request.download_missing_data,
                user_confirmed=request.user_confirmed,
                apply_decision_to_run=True,
                force_parse=True,
            )
            
            # Run baseline evaluation
            baseline_result = baseline_service.evaluate(baseline_request)
            
            if not baseline_result.success or baseline_result.status != "completed":
                raise ValueError(f"Baseline evaluation failed: {baseline_result.status}")
            
            baseline_run_id = baseline_result.run_id
            self.optimization_repo.update_optimization_run(
                optimization_run_id, {"baseline_run_id": baseline_run_id}
            )
            return baseline_run_id

        # No baseline - controlled failure
        return self._controlled_failure(
            optimization_run_id,
            None,
            "baseline_missing",
            ["No baseline run provided and run_baseline_first is false"],
        )

    def _stage_hyperopt_policy_validation(
        self, request: OptimizationRequest
    ) -> HyperoptPolicy:
        """Stage 3: hyperopt_policy_validation."""
        if not request.user_confirmed:
            raise ValueError("User confirmation required before Hyperopt execution")

        policy = self.hyperopt_policy_service.get_default_policy(
            risk_profile=request.risk_profile,
            timeframe=request.timeframe
        )
        warnings = self.hyperopt_policy_service.validate_request_against_policy(request, policy)
        if warnings:
            logger.warning(f"Hyperopt policy validation warnings: {warnings}")
        return policy

    def _stage_hyperopt_config_generation(
        self, request: OptimizationRequest, optimization_run_id: str
    ) -> str:
        """Stage 4: hyperopt_config_generation."""
        from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
        config_request = FreqtradeBacktestConfigRequest(
            run_id=optimization_run_id,
            strategy_name=request.strategy_name,
            pairs=request.pairs,
            timeframe=request.timeframe,
            exchange=request.exchange or "binance",
        )
        config_result = self.config_generator.write_backtest_config(config_request)
        if isinstance(config_result, dict):
            return config_result.get("config_path", "")
        return config_result.config_path if config_result.success else ""

    def _stage_data_check(self, request: OptimizationRequest) -> None:
        """Stage 5: data_check."""
        from app.services.freqtrade_data_service import FreqtradeDataService
        from app.schemas.freqtrade_data import FreqtradeDataCheckRequest
        
        data_service = FreqtradeDataService()
        
        # Build data check request
        data_check_request = FreqtradeDataCheckRequest(
            run_id=None,  # No run_id yet in optimization pipeline
            exchange=request.exchange or "binance",
            trading_mode="spot",
            pairs=request.pairs,
            timeframe=request.timeframe,
            config_path=None,
            show_timerange=False,
        )
        
        # Check data availability
        data_check_result = data_service.check_data(data_check_request)
        
        # Check if any data is missing
        missing_data = any(not pair.exists for pair in data_check_result.pairs)
        
        if missing_data:
            if not request.download_missing_data:
                raise ValueError(
                    f"Data missing for pairs: {[p.pair for p in data_check_result.pairs if not p.exists]}. "
                    "Set download_missing_data=true to download."
                )
            else:
                if not request.user_confirmed:
                    raise ValueError(
                        "Data download requires user confirmation. Set user_confirmed=true."
                    )
        
        logger.info(f"Data check completed for {request.pairs} at {request.timeframe}")

    def _stage_data_download(self, request: OptimizationRequest) -> None:
        """Stage 6: data_download."""
        from app.services.freqtrade_data_service import FreqtradeDataService
        from app.schemas.freqtrade_data import FreqtradeDataDownloadRequest
        
        if not request.download_missing_data:
            logger.info("Data download skipped: download_missing_data=false")
            return
        
        if not request.user_confirmed:
            raise ValueError("Data download requires user confirmation. Set user_confirmed=true.")
        
        data_service = FreqtradeDataService()
        
        # Build data download request
        data_download_request = FreqtradeDataDownloadRequest(
            run_id=None,  # No run_id yet in optimization pipeline
            exchange=request.exchange or "binance",
            trading_mode="spot",
            pairs=request.pairs,
            timeframes=[request.timeframe],
            days=request.days or 30,  # Use request days or default to 30
            timerange=None,
            config_path=None,
            data_format_ohlcv="feather",
            user_confirmed=True,
        )
        
        # Download data
        download_result = data_service.download_data(data_download_request)
        
        if not download_result.success:
            raise ValueError(f"Data download failed: {download_result.error}")
        
        logger.info(f"Data download completed for {request.pairs} at {request.timeframe}")

    def _stage_hyperopt_execution(
        self,
        optimization_run_id: str,
        request: OptimizationRequest,
        config_path: str,
        policy: HyperoptPolicy,
    ) -> Any:
        """Stage 7: hyperopt_execution."""
        return self.hyperopt_runner.run_hyperopt(
            request=request,
            config_path=config_path,
            run_id=optimization_run_id,
            policy=policy,
        )

    def _stage_hyperopt_result_parsing(
        self,
        optimization_run_id: str,
        result_files: Optional[list[str]],
        policy: HyperoptPolicy,
    ) -> list:
        """Stage 8: hyperopt_result_parsing."""
        return self.hyperopt_parser.parse_and_persist_trials(
            optimization_run_id=optimization_run_id,
            result_files=result_files,
            policy=policy,
        )

    def _stage_best_trial_selection(
        self, optimization_run_id: str
    ) -> Optional[Any]:
        """Stage 10: best_trial_selection."""
        trials = self.optimization_repo.list_trials(optimization_run_id, limit=1000)
        if not trials:
            return None

        # Find best trial (parser should have marked it)
        best_trial = None
        for trial in trials:
            if trial.get("status") == "best" or trial.get("is_best") is True:
                best_trial = trial
                break

        if not best_trial:
            # Fallback to highest profit
            best_trial = max(
                trials,
                key=lambda t: t.get("metrics", {}).get("profit_total", 0),
                default=None,
            )

        if best_trial:
            self.optimization_repo.update_optimization_run(
                optimization_run_id, {"best_trial_id": best_trial["id"]}
            )

        return best_trial

    def _stage_optimized_backtest(
        self,
        optimization_run_id: str,
        baseline_run_id: str,
        best_trial: Any,
        request: OptimizationRequest,
    ) -> Dict[str, Any]:
        """Stage 12: optimized_backtest."""
        from app.schemas.optimization import OptimizationTrial
        # Handle both dict and object cases
        if isinstance(best_trial, dict):
            trial_obj = OptimizationTrial(**best_trial)
        else:
            trial_obj = best_trial
        return self.optimized_backtest_service.run_optimized_backtest(
            optimization_run_id=optimization_run_id,
            baseline_run_id=baseline_run_id,
            best_trial=trial_obj,
            strategy_name=request.strategy_name,
            pairs=request.pairs,
            timeframe=request.timeframe,
        )

    def _stage_baseline_vs_optimized_comparison(
        self,
        optimization_run_id: str,
        baseline_run_id: str,
        optimized_result: Dict[str, Any],
        best_trial: Any,
    ) -> Dict[str, Any]:
        """Stage 15: baseline_vs_optimized_comparison."""
        # Load baseline metrics (simplified)
        baseline_metrics = {}
        if baseline_run_id:
            baseline_run = self.run_repo.get_run(baseline_run_id)
            if baseline_run:
                baseline_metrics = baseline_run.get("metrics", {})

        optimized_metrics = optimized_result.get("metrics", {})

        # Get best trial ID
        best_trial_id = None
        if best_trial:
            if isinstance(best_trial, dict):
                best_trial_id = best_trial.get("id")
            else:
                best_trial_id = getattr(best_trial, "id", None)

        # Calculate deltas
        delta_profit_factor = (
            optimized_metrics.get("profit_factor", 0) - baseline_metrics.get("profit_factor", 0)
        )
        delta_expectancy = (
            optimized_metrics.get("expectancy", 0) - baseline_metrics.get("expectancy", 0)
        )
        delta_drawdown = (
            optimized_metrics.get("max_drawdown", 0) - baseline_metrics.get("max_drawdown", 0)
        )
        delta_trade_count = (
            optimized_metrics.get("trade_count", 0) - baseline_metrics.get("trade_count", 0)
        )

        # Determine result status
        result_status = self._determine_comparison_status(
            optimized_result.get("classification"),
            delta_profit_factor,
            delta_expectancy,
            delta_drawdown,
            delta_trade_count,
        )

        comparison = {
            "optimization_run_id": optimization_run_id,
            "baseline_run_id": baseline_run_id,
            "optimized_run_id": optimized_result.get("optimized_run_id"),
            "best_trial_id": best_trial_id,
            "baseline_metrics": baseline_metrics,
            "optimized_metrics": optimized_metrics,
            "delta_profit_factor": delta_profit_factor,
            "delta_expectancy": delta_expectancy,
            "delta_drawdown": delta_drawdown,
            "delta_trade_count": delta_trade_count,
            "baseline_classification": baseline_metrics.get("classification"),
            "optimized_classification": optimized_result.get("classification"),
            "result_status": result_status,
            "improvement_summary": self._build_improvement_summary(
                delta_profit_factor, delta_expectancy, delta_drawdown
            ),
            "warnings": [],
            "overfit_suspected": result_status == OptimizationResultStatus.OVERFIT_SUSPECTED,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        self.optimization_repo.update_optimization_run(
            optimization_run_id, {"comparison": comparison}
        )
        return comparison

    def _stage_optimization_report(
        self,
        optimization_run_id: str,
        request: OptimizationRequest,
        baseline_run_id: str,
        best_trial: Any,
        optimized_result: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> None:
        """Stage 16: optimization_report."""
        report_dir = Path(HER_ARTIFACTS_RUNS) / optimization_run_id / "optimization"
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / "optimization_report.json"

        # Get best trial ID safely
        best_trial_id = None
        if best_trial:
            if isinstance(best_trial, dict):
                best_trial_id = best_trial.get("id")
            else:
                best_trial_id = getattr(best_trial, "id", None)

        report = {
            "optimization_run_id": optimization_run_id,
            "request": request.model_dump(mode="json"),
            "baseline_run_id": baseline_run_id,
            "best_trial_id": best_trial_id,
            "best_trial": best_trial,
            "optimized_run_id": optimized_result.get("optimized_run_id"),
            "optimized_classification": optimized_result.get("classification"),
            "optimized_metrics": optimized_result.get("metrics"),
            "comparison": comparison,
            "artifact_paths": optimized_result.get("backtest_artifacts", []),
            "warnings": optimized_result.get("warnings", []),
            "errors": optimized_result.get("errors", []),
            "frontend_display_hints": {
                "show_comparison": True,
                "show_trial_history": True,
                "show_optimized_backtest": True,
            },
            "created_at": datetime.utcnow().isoformat() + "Z",
        }

        with open(report_path, "w") as f:
            json.dump(report, f, indent=2, default=str)

        self.optimization_repo.update_optimization_run(
            optimization_run_id, {"report_artifact_path": str(report_path)}
        )

    def _stage_completion(
        self,
        optimization_run_id: str,
        optimized_result: Dict[str, Any],
        comparison: Dict[str, Any],
    ) -> None:
        """Stage 17: completion."""
        self.optimization_repo.update_optimization_run(
            optimization_run_id,
            {
                "status": OptimizationStatus.COMPLETED,
                "result_status": comparison.get("result_status"),
                "optimized_run_id": optimized_result.get("optimized_run_id"),
            },
        )

    def _controlled_failure(
        self,
        optimization_run_id: str,
        baseline_run_id: Optional[str],
        error_code: str,
        errors: list,
        optimized_run_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Return controlled failure response."""
        self.optimization_repo.update_optimization_run(
            optimization_run_id,
            {
                "status": OptimizationStatus.FAILED_CONTROLLED,
            },
        )
        return {
            "optimization_run_id": optimization_run_id,
            "status": OptimizationStatus.FAILED_CONTROLLED,
            "success": False,
            "error_code": error_code,
            "errors": errors,
            "baseline_run_id": baseline_run_id,
            "optimized_run_id": optimized_run_id,
        }

    def _build_success_result(
        self,
        optimization_run_id: str,
        baseline_run_id: str,
        optimized_result: Dict[str, Any],
        best_trial: Any,
        comparison: Dict[str, Any],
        trials_count: int,
    ) -> Dict[str, Any]:
        """Build success response."""
        best_trial_id = None
        if best_trial:
            if isinstance(best_trial, dict):
                best_trial_id = best_trial.get("id")
            else:
                best_trial_id = getattr(best_trial, "id", None)

        return {
            "optimization_run_id": optimization_run_id,
            "status": OptimizationStatus.COMPLETED,
            "success": True,
            "baseline_run_id": baseline_run_id,
            "optimized_run_id": optimized_result.get("optimized_run_id"),
            "best_trial_id": best_trial_id,
            "baseline_metrics": comparison.get("baseline_metrics"),
            "optimized_metrics": comparison.get("optimized_metrics"),
            "comparison": comparison,
            "trials_count": trials_count,
            "best_trial": best_trial,
            "classification": optimized_result.get("classification"),
            "confidence_score": optimized_result.get("confidence_score"),
            "metrics": optimized_result.get("metrics"),
            "warnings": optimized_result.get("warnings", []),
            "errors": [],
            "next_actions": [
                "Review optimization report",
                "Compare baseline vs optimized metrics",
                "Evaluate best trial parameters",
            ],
        }

    def _determine_comparison_status(
        self,
        classification: Optional[str],
        delta_profit_factor: float,
        delta_expectancy: float,
        delta_drawdown: float,
        delta_trade_count: int,
    ) -> str:
        """Determine comparison result status."""
        if classification == "rejected":
            return OptimizationResultStatus.OPTIMIZATION_REJECTED

        if classification in ["candidate", "promising", "validated"]:
            # Check for improvement
            if delta_profit_factor > 0 and delta_expectancy > 0 and delta_drawdown <= 0:
                return OptimizationResultStatus.IMPROVED
            elif delta_profit_factor > 0 or delta_expectancy > 0:
                return OptimizationResultStatus.OPTIMIZATION_CANDIDATE
            else:
                return OptimizationResultStatus.NOT_IMPROVED

        # Check for overfit
        if delta_trade_count < -10:  # Significant trade count collapse
            return OptimizationResultStatus.OVERFIT_SUSPECTED

        return OptimizationResultStatus.NOT_IMPROVED

    def _build_improvement_summary(
        self,
        delta_profit_factor: float,
        delta_expectancy: float,
        delta_drawdown: float,
    ) -> str:
        """Build improvement summary string."""
        improvements = []
        if delta_profit_factor > 0:
            improvements.append(f"Profit factor +{delta_profit_factor:.2f}")
        if delta_expectancy > 0:
            improvements.append(f"Expectancy +{delta_expectancy:.2f}")
        if delta_drawdown < 0:
            improvements.append(f"Drawdown {delta_drawdown:.2f}")

        if improvements:
            return "Improved: " + ", ".join(improvements)
        return "No significant improvement"
