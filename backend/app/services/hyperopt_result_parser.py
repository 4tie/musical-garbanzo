"""
Hyperopt result parser for Part 08 optimization pipeline.
Parses Freqtrade hyperopt outputs and extracts all trials.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.core.constants import HER_ARTIFACTS_RUNS
from app.repositories.optimization import OptimizationRepository
from app.schemas.optimization import HyperoptPolicy, OptimizationTrial, OptimizationTrialStatus

logger = logging.getLogger(__name__)


class HyperoptResultParser:
    """Parser for Freqtrade hyperopt result files."""

    def __init__(
        self,
        repository: Optional[OptimizationRepository] = None,
    ) -> None:
        """
        Initialize the hyperopt result parser.

        Args:
            repository: Optional optimization repository for persistence
        """
        self.repository = repository or OptimizationRepository()

    def discover_hyperopt_outputs(
        self, run_id: str, result_files: Optional[List[str]] = None
    ) -> List[str]:
        """
        Discover hyperopt output files for a run.

        Args:
            run_id: Run ID to search for
            result_files: Optional list of result file paths

        Returns:
            List of discovered result file paths

        Raises:
            ValueError: If no result files can be discovered
        """
        if result_files:
            return result_files

        discovered_files: List[str] = []

        # Search run-specific locations only. The runner passes exact global
        # Freqtrade result files for the current execution.

        # Location 1: Run-specific hyperopt artifact directory
        run_hyperopt_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "hyperopt"
        if run_hyperopt_dir.exists() and run_hyperopt_dir.is_dir():
            result_files = self._find_parseable_result_files(run_hyperopt_dir)
            discovered_files.extend([str(f) for f in result_files])
            logger.debug(f"Found {len(result_files)} parseable result files in {run_hyperopt_dir}")

        # Location 2: Run-specific artifact directory (any JSON files)
        run_artifacts_dir = Path(HER_ARTIFACTS_RUNS) / run_id
        if run_artifacts_dir.exists() and run_artifacts_dir.is_dir():
            json_files = [
                f for f in run_artifacts_dir.glob("*.json")
                if self._is_parseable_result_file(f)
            ]
            # Add files not already discovered
            for json_file in json_files:
                json_path = str(json_file)
                if json_path not in discovered_files:
                    discovered_files.append(json_path)
            logger.debug(f"Found {len(json_files)} JSON files in {run_artifacts_dir}")

        # If no files discovered, raise error with diagnostics
        if not discovered_files:
            error_msg = (
                f"No hyperopt result files discovered for run {run_id}. "
                f"Searched locations:\n"
                f"  1. {run_hyperopt_dir} (exists: {run_hyperopt_dir.exists()})\n"
                f"  2. {run_artifacts_dir} (exists: {run_artifacts_dir.exists()})\n"
                f"Please ensure hyperopt has been executed and result files are available."
            )
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Discovered {len(discovered_files)} hyperopt result files for run {run_id}")
        return discovered_files

    def load_hyperopt_result(self, path: str) -> Any:
        """
        Load a hyperopt result file.

        Args:
            path: Path to result file

        Returns:
            Parsed JSON data (dict or list)
        """
        try:
            result_path = Path(path)
            if result_path.suffix == ".fthypt":
                trials = []
                with open(result_path, "r") as f:
                    for line in f:
                        stripped = line.strip()
                        if stripped:
                            trials.append(json.loads(stripped))
                return trials

            with open(result_path, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            raise ValueError(f"Failed to load hyperopt result from {path}: {e}")

    @staticmethod
    def _find_parseable_result_files(directory: Path) -> List[Path]:
        files: List[Path] = []
        for pattern in ("*.fthypt", "*.json"):
            files.extend(
                path for path in directory.glob(pattern)
                if HyperoptResultParser._is_parseable_result_file(path)
            )
        return files

    @staticmethod
    def _is_parseable_result_file(path: Path) -> bool:
        if path.name.startswith("."):
            return False
        if path.name == "command_metadata.json":
            return False
        return path.suffix in {".fthypt", ".json"}

    def parse_trials(self, raw_result: Any) -> List[OptimizationTrial]:
        """
        Parse trials from raw hyperopt result.

        Args:
            raw_result: Raw hyperopt result (dict or list)

        Returns:
            List of parsed OptimizationTrial objects
        """
        trials: List[OptimizationTrial] = []

        # Try different result shapes
        if isinstance(raw_result, list):
            # Shape: list of trial objects
            for i, raw_trial in enumerate(raw_result):
                trial_number = raw_trial.get("current_epoch", i + 1)
                trial = self.normalize_trial(raw_trial, trial_number)
                trials.append(trial)
        elif isinstance(raw_result, dict):
            # Shape: object with results or trials key
            trial_list = raw_result.get("results") or raw_result.get("trials")
            
            if isinstance(trial_list, list) and trial_list:
                for i, raw_trial in enumerate(trial_list):
                    trial_number = raw_trial.get("current_epoch", i + 1)
                    trial = self.normalize_trial(raw_trial, trial_number)
                    trials.append(trial)
            else:
                # Single trial object (if it has loss, it's a trial)
                if "loss" in raw_result or "loss_result" in raw_result:
                    trial = self.normalize_trial(raw_result, 1)
                    trials.append(trial)

        return trials

    def parse_best_trial(
        self, raw_result: Any, trials: List[OptimizationTrial]
    ) -> Optional[OptimizationTrial]:
        """
        Parse the best trial from raw hyperopt result.

        Args:
            raw_result: Raw hyperopt result
            trials: List of all parsed trials

        Returns:
            Best trial or None
        """
        # Try explicit best_result
        if isinstance(raw_result, dict) and "best_result" in raw_result:
            best_raw = raw_result["best_result"]
            best_trial = self.normalize_trial(best_raw, 0)
            # Find the matching trial in the list
            for trial in trials:
                if self._trials_match(trial, best_trial):
                    trial.is_best = True
                    return trial
            # If not found, add it
            best_trial.is_best = True
            return best_trial

        marked_best = [trial for trial in trials if trial.raw_trial.get("is_best") is True]
        if marked_best:
            best_trial = marked_best[-1]
            best_trial.is_best = True
            return best_trial

        # Find by lowest loss score
        if trials:
            best_trial = min(
                trials,
                key=lambda t: t.loss_score if t.loss_score is not None else float("inf"),
            )
            best_trial.is_best = True
            return best_trial

        return None

    def normalize_trial(
        self, raw_trial: Dict[str, Any], trial_number: int
    ) -> OptimizationTrial:
        """
        Normalize a raw trial into an OptimizationTrial.

        Args:
            raw_trial: Raw trial data
            trial_number: Trial sequence number

        Returns:
            Normalized OptimizationTrial
        """
        params = self.extract_params(raw_trial)
        metrics = self.extract_metrics(raw_trial)

        # Generate temporary ID (will be replaced during persistence)
        import uuid
        temp_id = str(uuid.uuid4())

        # Use current time as placeholder
        from datetime import datetime, timezone
        temp_created_at = datetime.now(timezone.utc).isoformat()

        return OptimizationTrial(
            id=temp_id,
            optimization_run_id="",  # Will be set during persistence
            trial_number=trial_number,
            status=self._classify_trial_status(raw_trial, metrics),
            is_best=False,  # Will be set by best trial detection
            is_selected_for_validation=False,
            params=params,
            buy_params=params.get("buy"),
            sell_params=params.get("sell"),
            roi_params=params.get("roi"),
            stoploss_params=params.get("stoploss"),
            trailing_params=params.get("trailing"),
            metrics=metrics,
            loss_score=raw_trial.get("loss") if raw_trial.get("loss") is not None else raw_trial.get("loss_result"),
            profit_total=metrics.get("profit_total"),
            profit_factor=metrics.get("profit_factor"),
            expectancy=metrics.get("expectancy"),
            max_drawdown=metrics.get("max_drawdown"),
            trade_count=metrics.get("trade_count"),
            win_rate=metrics.get("win_rate"),
            rejection_reason=None,
            failure_reason=raw_trial.get("error") or raw_trial.get("failure_reason"),
            artifact_paths=[],
            raw_trial=raw_trial,
            created_at=temp_created_at,
        )

    def extract_params(self, raw_trial: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract parameters from raw trial.

        Args:
            raw_trial: Raw trial data

        Returns:
            Dictionary of parameters (separated by space)
        """
        params: Dict[str, Any] = {}

        # Try different parameter locations
        if "params_details" in raw_trial:
            params = raw_trial["params_details"]
        elif "params" in raw_trial:
            params = raw_trial["params"]
        elif "params_dict" in raw_trial:
            params = raw_trial["params_dict"]
        elif "strategy_params" in raw_trial:
            params = raw_trial["strategy_params"]
        else:
            # Extract from flat structure
            for key, value in raw_trial.items():
                if key.startswith("buy_") or key.startswith("sell_") or key.startswith("roi_") or key.startswith("stoploss") or key.startswith("trailing"):
                    params[key] = value

        # Check if params are already separated by space
        # If params contains keys like "buy", "sell", "roi", they're already separated
        if any(key in params for key in ["buy", "sell", "roi", "stoploss", "trailing"]):
            return params

        # Separate by space
        separated: Dict[str, Any] = {}
        for key, value in params.items():
            if key.startswith("buy_"):
                if "buy" not in separated:
                    separated["buy"] = {}
                separated["buy"][key[4:]] = value
            elif key.startswith("sell_"):
                if "sell" not in separated:
                    separated["sell"] = {}
                separated["sell"][key[5:]] = value
            elif key.startswith("roi_"):
                if "roi" not in separated:
                    separated["roi"] = {}
                separated["roi"][key[4:]] = value
            elif key.startswith("stoploss"):
                if "stoploss" not in separated:
                    separated["stoploss"] = {}
                # Handle both stoploss and stoploss_
                if key == "stoploss":
                    separated["stoploss"]["value"] = value
                else:
                    separated["stoploss"][key[9:]] = value
            elif key.startswith("trailing"):
                if "trailing" not in separated:
                    separated["trailing"] = {}
                # Handle both trailing_stop and trailing_
                if key == "trailing_stop":
                    separated["trailing"]["stop"] = value
                else:
                    separated["trailing"][key[9:]] = value
            else:
                # Keep other params as-is in a general params dict
                if "params" not in separated:
                    separated["params"] = {}
                separated["params"][key] = value

        # If no separation happened, return original params
        if not separated:
            return params

        return separated

    def extract_metrics(self, raw_trial: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract metrics from raw trial.

        Args:
            raw_trial: Raw trial data

        Returns:
            Dictionary of metrics
        """
        metrics: Dict[str, Any] = {}

        # Try different metric locations
        if "metrics" in raw_trial:
            metrics = raw_trial["metrics"]
        elif "results_metrics" in raw_trial:
            metrics = raw_trial["results_metrics"]
        else:
            # Extract from flat structure
            metric_keys = [
                "profit_total",
                "profit_factor",
                "expectancy",
                "max_drawdown",
                "trade_count",
                "win_rate",
                "profit",
                "abs_profit",
                "profit_mean",
                "profit_median",
                "profit_std",
                "sharpe",
                "sortino",
                "calmar",
            ]
            for key in metric_keys:
                if key in raw_trial:
                    metrics[key] = raw_trial[key]

        if "total_profit" in raw_trial and "profit_total" not in metrics:
            metrics["profit_total"] = raw_trial["total_profit"]
        if "total_trades" in metrics and "trade_count" not in metrics:
            metrics["trade_count"] = metrics["total_trades"]
        if "max_drawdown_account" in metrics and "max_drawdown" not in metrics:
            metrics["max_drawdown"] = metrics["max_drawdown_account"]
        if "winrate" in metrics and "win_rate" not in metrics:
            metrics["win_rate"] = metrics["winrate"]

        return metrics

    def extract_rejection_reason(
        self, raw_trial: Dict[str, Any], policy: HyperoptPolicy
    ) -> Optional[str]:
        """
        Extract rejection reason based on policy.

        Args:
            raw_trial: Raw trial data
            policy: Hyperopt policy

        Returns:
            Rejection reason or None
        """
        metrics = self.extract_metrics(raw_trial)
        trade_count = metrics.get("trade_count", 0)

        # Check minimum trades
        if trade_count < policy.min_trades:
            return f"Trade count ({trade_count}) below minimum ({policy.min_trades})"

        # Check zero trades
        if trade_count == 0 and policy.stop_on_zero_trades:
            return "Zero trades - not acceptable evidence"

        return None

    def parse_and_persist_trials(
        self,
        optimization_run_id: str,
        result_files: List[str],
        policy: Optional[HyperoptPolicy] = None,
    ) -> Dict[str, Any]:
        """
        Parse and persist trials from hyperopt result files.

        Args:
            optimization_run_id: Optimization run ID
            result_files: List of result file paths
            policy: Optional hyperopt policy for validation

        Returns:
            Dictionary with parsing results
        """
        results: Dict[str, Any] = {
            "trials_count": 0,
            "persisted_trials_count": 0,
            "best_trial_id": None,
            "best_trial_number": None,
            "partial_trial_history": False,
            "warnings": [],
            "errors": [],
            "source_files": result_files,
        }

        all_trials: List[OptimizationTrial] = []

        # Load and parse each result file
        for result_file in result_files:
            try:
                raw_result = self.load_hyperopt_result(result_file)
                trials = self.parse_trials(raw_result)
                all_trials.extend(trials)
            except Exception as e:
                results["errors"].append(f"Failed to parse {result_file}: {e}")

        # Check if we have any trials
        if not all_trials:
            results["warnings"].append("No trials found in result files")
            results["partial_trial_history"] = True
            return results

        results["trials_count"] = len(all_trials)

        # Detect best trial
        best_trial = self.parse_best_trial(
            raw_result if result_files else {}, all_trials
        )
        if best_trial:
            results["best_trial_id"] = best_trial.id
            results["best_trial_number"] = best_trial.trial_number

        # Apply policy validation if provided
        if policy:
            for trial in all_trials:
                rejection_reason = self.extract_rejection_reason(trial.raw_trial, policy)
                if rejection_reason:
                    trial.rejection_reason = rejection_reason
                    trial.status = OptimizationTrialStatus.REJECTED

        # Persist all trials
        for trial in all_trials:
            trial.optimization_run_id = optimization_run_id
            try:
                trial_dict = trial.model_dump()
                # Convert OptimizationTrial to dict format expected by repository
                trial_data = {
                    "optimization_run_id": trial.optimization_run_id,
                    "trial_number": trial.trial_number,
                    "status": trial.status.value if hasattr(trial.status, "value") else str(trial.status),
                    "is_best": 1 if trial.is_best else 0,
                    "is_selected_for_validation": 1 if trial.is_selected_for_validation else 0,
                    "params": trial.params,
                    "buy_params": trial.buy_params,
                    "sell_params": trial.sell_params,
                    "roi_params": trial.roi_params,
                    "stoploss_params": trial.stoploss_params,
                    "trailing_params": trial.trailing_params,
                    "metrics": trial.metrics,
                    "loss_score": trial.loss_score,
                    "profit_total": trial.profit_total,
                    "profit_factor": trial.profit_factor,
                    "expectancy": trial.expectancy,
                    "max_drawdown": trial.max_drawdown,
                    "trade_count": trial.trade_count,
                    "win_rate": trial.win_rate,
                    "rejection_reason": trial.rejection_reason,
                    "failure_reason": trial.failure_reason,
                    "artifact_paths": trial.artifact_paths,
                    "raw_trial": trial.raw_trial,
                }
                self.repository.create_trial(trial_data)
                results["persisted_trials_count"] += 1
            except Exception as e:
                results["errors"].append(f"Failed to persist trial {trial.trial_number}: {e}")

        # Check for partial history
        if results["persisted_trials_count"] < results["trials_count"]:
            results["partial_trial_history"] = True
            results["warnings"].append(
                f"Partial trial history: {results['persisted_trials_count']}/{results['trials_count']} trials persisted"
            )

        return results

    def _classify_trial_status(
        self, raw_trial: Dict[str, Any], metrics: Dict[str, Any]
    ) -> OptimizationTrialStatus:
        """
        Classify trial status based on raw data.

        Args:
            raw_trial: Raw trial data
            metrics: Extracted metrics

        Returns:
            Trial status
        """
        # Check for errors
        if raw_trial.get("error") or raw_trial.get("failed"):
            return OptimizationTrialStatus.FAILED

        # Check for completion
        if raw_trial.get("loss") is not None or raw_trial.get("loss_result") is not None:
            return OptimizationTrialStatus.COMPLETED

        # Default to ignored if incomplete
        return OptimizationTrialStatus.IGNORED

    def _trials_match(self, trial1: OptimizationTrial, trial2: OptimizationTrial) -> bool:
        """
        Check if two trials match based on their parameters.

        Args:
            trial1: First trial
            trial2: Second trial

        Returns:
            True if trials match
        """
        # Compare params
        return trial1.params == trial2.params
