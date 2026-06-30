"""
Optimized backtest service for Part 08 optimization pipeline.
Runs optimized backtest with best trial parameters and evaluates results.
"""
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import HER_ARTIFACTS_RUNS, FREQTRADE_WORKSPACE
from app.repositories.optimization import OptimizationRepository
from app.repositories.runs import RunRepository
from app.schemas.optimization import OptimizationTrial
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator
from app.services.decision_service import DecisionService
from app.services.backtest_result_parser import BacktestResultParser
from app.services.strategy_params_materializer import StrategyParamsMaterializer
from app.schemas.freqtrade_backtest import FreqtradeBacktestRequest
from app.schemas.runs import RunCreate
from app.schemas.decisions import DecisionEvaluationRequest

logger = logging.getLogger(__name__)


class OptimizedBacktestService:
    """Service for running optimized backtest with best trial parameters."""

    def __init__(
        self,
        backtest_runner: Optional[FreqtradeBacktestRunner] = None,
        config_generator: Optional[FreqtradeConfigGenerator] = None,
        decision_service: Optional[DecisionService] = None,
        result_parser: Optional[BacktestResultParser] = None,
        params_materializer: Optional[StrategyParamsMaterializer] = None,
        optimization_repo: Optional[OptimizationRepository] = None,
        run_repo: Optional[RunRepository] = None,
    ) -> None:
        """
        Initialize the optimized backtest service.

        Args:
            backtest_runner: Optional backtest runner instance
            config_generator: Optional config generator instance
            decision_service: Optional decision service instance
            result_parser: Optional result parser instance
            params_materializer: Optional params materializer instance
            optimization_repo: Optional optimization repository instance
            run_repo: Optional run repository instance
        """
        self.backtest_runner = backtest_runner or FreqtradeBacktestRunner()
        self.config_generator = config_generator or FreqtradeConfigGenerator()
        self.decision_service = decision_service or DecisionService()
        self.result_parser = result_parser or BacktestResultParser()
        self.params_materializer = params_materializer or StrategyParamsMaterializer()
        self.optimization_repo = optimization_repo or OptimizationRepository()
        self.run_repo = run_repo or RunRepository()

    def run_optimized_backtest(
        self,
        optimization_run_id: str,
        baseline_run_id: str,
        best_trial: OptimizationTrial,
        strategy_name: str,
        pairs: list[str],
        timeframe: str,
        timerange: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run optimized backtest with best trial parameters.

        Args:
            optimization_run_id: Optimization run ID
            baseline_run_id: Baseline run ID for comparison
            best_trial: Best trial with optimized parameters
            strategy_name: Strategy name
            pairs: Trading pairs
            timeframe: Timeframe
            timerange: Optional timerange for backtest

        Returns:
            Dictionary with optimized_run_id, optimized_config_path, params_artifact_path,
            backtest_artifacts, normalized_artifact_path, decision_artifact_path,
            classification, confidence_score, metrics, warnings, errors

        Raises:
            ValueError: If backtest configuration or execution fails
        """
        logger.info(f"Starting optimized backtest for optimization run {optimization_run_id}")

        # Step 1: Create optimized backtest run first to get run_id
        optimized_run_id = self.run_repo.create_run(
            RunCreate(
                name=f"Optimized backtest for {strategy_name}",
                mode="baseline_evaluation",
                parent_run_id=baseline_run_id,
                exchange="binance",
                quote_currency="USDT",
                trading_mode="spot",
                timeframe=timeframe,
                pairs=pairs,
                analysis_depth="optimized_backtest",
            ),
            create_default_stages=False,
        )["id"]
        logger.info(f"Created optimized run: {optimized_run_id}")

        # Step 2: Prepare optimized strategy workspace
        workspace = self.prepare_optimized_strategy_workspace(
            optimized_run_id, strategy_name, best_trial
        )
        logger.info(f"Prepared optimized workspace: {workspace}")

        # Step 3: Generate optimized backtest config with run_id
        config_result = self.generate_optimized_backtest_config(
            optimized_run_id, strategy_name, pairs, timeframe, workspace
        )
        logger.info(f"Generated optimized config: {config_result['config_path']}")

        # Step 4: Run backtest
        backtest_result = self.run_backtest(
            optimized_run_id, config_result["config_path"], strategy_name, pairs, timeframe, timerange
        )

        if not backtest_result["success"]:
            logger.error(f"Optimized backtest failed: {backtest_result['error']}")
            return {
                "success": False,
                "optimized_run_id": optimized_run_id,
                "optimized_config_path": config_result["config_path"],
                "params_artifact_path": workspace["params_path"],
                "backtest_artifacts": [],
                "normalized_artifact_path": None,
                "decision_artifact_path": None,
                "classification": None,
                "confidence_score": None,
                "metrics": {},
                "warnings": backtest_result["warnings"],
                "errors": [backtest_result["error"]],
            }

        logger.info(f"Optimized backtest completed successfully")

        # Step 5: Parse optimized result
        parse_result = self.parse_optimized_result(optimized_run_id)
        if not parse_result["success"]:
            logger.warning(f"Could not parse optimized result for run {optimized_run_id}")
            return {
                "success": False,
                "optimized_run_id": optimized_run_id,
                "optimized_config_path": config_result["config_path"],
                "params_artifact_path": workspace["params_path"],
                "backtest_artifacts": backtest_result["artifacts"],
                "normalized_artifact_path": None,
                "decision_artifact_path": None,
                "classification": None,
                "confidence_score": None,
                "metrics": {},
                "warnings": backtest_result["warnings"],
                "errors": [parse_result["error"]],
            }

        # Step 6: Evaluate optimized decision
        decision_result = self.evaluate_optimized_decision(
            optimized_run_id, parse_result["metrics"], parse_result["pair_results"], parse_result["trade_summary"]
        )

        # Step 7: Update optimization run with optimized run ID
        self.optimization_repo.update_optimization_run(
            optimization_run_id,
            {"optimized_run_id": optimized_run_id},
        )

        return {
            "success": True,
            "optimized_run_id": optimized_run_id,
            "optimized_config_path": config_result["config_path"],
            "params_artifact_path": workspace["params_path"],
            "backtest_artifacts": backtest_result["artifacts"],
            "normalized_artifact_path": parse_result.get("normalized_artifact_path"),
            "decision_artifact_path": decision_result.get("decision_artifact_path"),
            "classification": decision_result.get("classification"),
            "confidence_score": decision_result.get("confidence_score"),
            "metrics": parse_result["metrics"],
            "warnings": backtest_result["warnings"],
            "errors": [],
        }

    def prepare_optimized_strategy_workspace(
        self,
        optimized_run_id: str,
        strategy_name: str,
        best_trial: OptimizationTrial,
    ) -> Dict[str, Any]:
        """
        Prepare optimized strategy workspace with materialized params.

        Creates a run-owned temporary strategy workspace that includes:
        - A copy of the original strategy file (never overwrites original)
        - A sidecar JSON with optimized params (never overwrites original sidecar)
        - The backtest will be configured to use this run-owned workspace

        Args:
            optimized_run_id: Optimized run ID (not optimization_run_id)
            strategy_name: Strategy name
            best_trial: Best trial with optimized parameters

        Returns:
            Dictionary with workspace path, params artifact info, and strategy path
        """
        from app.core.config import settings
        from app.services.freqtrade_strategy_service import FreqtradeStrategyService
        import shutil

        # Build params dict from trial fields
        params = {}
        if best_trial.buy_params:
            params["buy"] = best_trial.buy_params
        if best_trial.sell_params:
            params["sell"] = best_trial.sell_params
        if best_trial.roi_params:
            params["roi"] = best_trial.roi_params
        if best_trial.stoploss_params:
            params["stoploss"] = best_trial.stoploss_params
        if best_trial.trailing_params:
            params["trailing"] = best_trial.trailing_params
        # Fall back to params dict if separated fields not available
        if not params and best_trial.params:
            params = best_trial.params

        # Create run-owned workspace directory using optimized_run_id
        run_workspace_dir = Path(HER_ARTIFACTS_RUNS) / optimized_run_id / "optimized_strategy"
        run_workspace_dir.mkdir(parents=True, exist_ok=True)

        # Find original strategy
        strategy_service = FreqtradeStrategyService()
        original_strategy = strategy_service.find_strategy_by_name(strategy_name)
        if not original_strategy or not original_strategy.file_path:
            raise ValueError(f"Strategy {strategy_name} not found or has no file path")

        original_strategy_path = Path(original_strategy.file_path)

        # Copy original strategy to run-owned workspace (never overwrites original)
        run_strategy_path = run_workspace_dir / original_strategy_path.name
        shutil.copy2(original_strategy_path, run_strategy_path)
        logger.info(f"Copied strategy from {original_strategy_path} to {run_strategy_path}")

        # Write optimized sidecar JSON next to copied strategy
        params_artifact = self.params_materializer.materialize_params(
            run_id=optimized_run_id,
            strategy_name=strategy_name,
            trial_id=best_trial.id,
            trial_number=best_trial.trial_number or 0,
            params=params,
        )

        # Copy params artifact to sidecar location in workspace
        sidecar_path = run_workspace_dir / f"{strategy_name}.json"
        shutil.copy2(params_artifact["artifact_path"], sidecar_path)
        logger.info(f"Created optimized sidecar at {sidecar_path}")

        return {
            "workspace_path": str(run_workspace_dir),
            "strategy_path": str(run_strategy_path),
            "sidecar_path": str(sidecar_path),
            "params_path": params_artifact["artifact_path"],
            "params_artifact_id": params_artifact["artifact_id"],
        }

    def generate_optimized_backtest_config(
        self,
        optimized_run_id: str,
        strategy_name: str,
        pairs: list[str],
        timeframe: str,
        workspace: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Generate optimized backtest config using run-owned workspace.

        Args:
            optimized_run_id: Optimized run ID
            strategy_name: Strategy name
            pairs: Trading pairs
            timeframe: Timeframe
            workspace: Workspace info from prepare_optimized_strategy_workspace

        Returns:
            Dictionary with config_path and workspace info
        """
        config_request = self._build_config_request(optimized_run_id, strategy_name, pairs, timeframe)
        
        # Add custom strategy path to use run-owned workspace
        # Point strategy_path to the parent directory containing the optimized strategy
        workspace_dir = Path(workspace["workspace_path"])
        config_request.additional_safe_config = {
            "strategy_path": str(workspace_dir.parent),
        }
        
        config_result = self.config_generator.write_backtest_config(config_request)
        if isinstance(config_result, dict):
            config_path = config_result.get("config_path", "")
        else:
            config_path = config_result.config_path if config_result.success else ""
        if not config_path:
            raise ValueError("Failed to generate optimized backtest config")
        return {
            "config_path": config_path,
            "workspace": workspace,
        }

    def run_backtest(
        self,
        optimized_run_id: str,
        config_path: str,
        strategy_name: str,
        pairs: list[str],
        timeframe: str,
        timerange: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Run optimized backtest.

        Args:
            optimized_run_id: Optimized run ID
            config_path: Config file path
            strategy_name: Strategy name
            pairs: Trading pairs
            timeframe: Timeframe
            timerange: Optional timerange

        Returns:
            Dictionary with success, artifacts, warnings, error
        """
        backtest_request = FreqtradeBacktestRequest(
            run_id=optimized_run_id,
            config_path=config_path,
            strategy_name=strategy_name,
            timeframe=timeframe,
            pairs=pairs,
            timerange=timerange,
        )
        backtest_result = self.backtest_runner.run_backtest(backtest_request)

        return {
            "success": backtest_result.success,
            "artifacts": backtest_result.artifacts,
            "warnings": backtest_result.warnings,
            "error": backtest_result.error,
        }

    def parse_optimized_result(self, optimized_run_id: str) -> Dict[str, Any]:
        """
        Parse optimized backtest result.

        Args:
            optimized_run_id: Optimized run ID

        Returns:
            Dictionary with success, metrics, pair_results, trade_summary, normalized_artifact_path, error
        """
        parsed_result = self.result_parser.parse_run(optimized_run_id, force=True)
        if not parsed_result.success:
            return {
                "success": False,
                "metrics": {},
                "pair_results": [],
                "trade_summary": {},
                "normalized_artifact_path": None,
                "error": "; ".join(parsed_result.errors) or "Failed to parse optimized result",
            }

        metrics = (
            parsed_result.metrics.metrics.model_dump(mode="json")
            if parsed_result.metrics and parsed_result.metrics.metrics
            else {}
        )
        pair_results = [
            pair.model_dump(mode="json") for pair in parsed_result.pair_results
        ]
        trade_summary = (
            parsed_result.trade_summary.model_dump(mode="json")
            if parsed_result.trade_summary
            else {}
        )

        return {
            "success": True,
            "metrics": metrics,
            "pair_results": pair_results,
            "trade_summary": trade_summary,
            "normalized_artifact_path": parsed_result.normalized_result_path,
            "error": None,
        }

    def evaluate_optimized_decision(
        self,
        optimized_run_id: str,
        metrics: Dict[str, Any],
        pair_results: list,
        trade_summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Evaluate optimized decision.

        Args:
            optimized_run_id: Optimized run ID
            metrics: Backtest metrics
            pair_results: Pair results
            trade_summary: Trade summary

        Returns:
            Dictionary with classification, confidence_score, decision_artifact_path
        """
        decision_result = self.decision_service.evaluate_run(
            DecisionEvaluationRequest(
                run_id=optimized_run_id,
                force=True,
                apply_to_run=True,
            )
        )

        return {
            "classification": decision_result.classification if decision_result else None,
            "confidence_score": getattr(decision_result, "confidence_score", None) if decision_result else None,
            "decision_artifact_path": getattr(decision_result, "decision_report_path", None) if decision_result else None,
        }

    def _build_config_request(
        self,
        optimized_run_id: str,
        strategy_name: str,
        pairs: list[str],
        timeframe: str,
    ) -> Any:
        """
        Build config request for optimized backtest.

        Args:
            optimized_run_id: Optimized run ID
            strategy_name: Strategy name
            pairs: Trading pairs
            timeframe: Timeframe

        Returns:
            FreqtradeBacktestConfigRequest
        """
        from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
        return FreqtradeBacktestConfigRequest(
            run_id=optimized_run_id,
            strategy_name=strategy_name,
            pairs=pairs,
            timeframe=timeframe,
            exchange="binance",
        )
