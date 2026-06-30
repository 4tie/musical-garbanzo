"""
Strategy params materializer for Part 08 optimization pipeline.
Safely materializes best trial parameters without overwriting original strategy files.
"""
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from app.core.constants import HER_ARTIFACTS_RUNS
from app.repositories.artifacts import ArtifactRepository
from app.schemas.artifacts import ArtifactCreate

logger = logging.getLogger(__name__)


class StrategyParamsMaterializer:
    """Safely materializes best trial parameters for optimized backtest."""

    def __init__(
        self,
        artifact_repository: Optional[ArtifactRepository] = None,
    ) -> None:
        """
        Initialize the params materializer.

        Args:
            artifact_repository: Optional artifact repository for persistence
        """
        self.artifact_repository = artifact_repository or ArtifactRepository()

    def materialize_params(
        self,
        run_id: str,
        strategy_name: str,
        trial_id: str,
        trial_number: int,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Materialize best trial parameters safely.

        Creates a run-owned params artifact that contains the optimized parameters.
        Never overwrites the original strategy file or sidecar JSON.

        Args:
            run_id: Optimization run ID
            strategy_name: Name of the strategy
            trial_id: Source trial ID
            trial_number: Trial number for reference
            params: Best trial parameters (buy, sell, roi, stoploss, trailing)

        Returns:
            Dictionary with artifact path and metadata

        Raises:
            ValueError: If params are invalid or artifact creation fails
        """
        # Validate params structure
        self._validate_params(params)

        # Build params artifact content with separated sections
        params_content = {
            "strategy_name": strategy_name,
            "source_trial_id": trial_id,
            "source_trial_number": trial_number,
            "params": params,
            "buy_params": params.get("buy", {}),
            "sell_params": params.get("sell", {}),
            "roi_params": params.get("roi", {}),
            "stoploss_params": params.get("stoploss", {}),
            "trailing_params": params.get("trailing", {}),
            "created_at": self._now_iso(),
            "warning": "This is validation materialization, not approved export. Do not use for live trading without explicit approval.",
        }

        # Create run-specific optimized_params directory
        optimized_params_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "optimized_params"
        optimized_params_dir.mkdir(parents=True, exist_ok=True)

        # Write params artifact (never overwrites original strategy)
        params_filename = f"{strategy_name}.json"
        params_path = optimized_params_dir / params_filename

        try:
            with open(params_path, "w") as f:
                json.dump(params_content, f, indent=2)
            logger.info(f"Materialized params to {params_path}")
        except Exception as e:
            logger.error(f"Failed to write params artifact: {e}")
            raise ValueError(f"Failed to materialize params: {e}")

        # Register artifact in repository
        artifact_data = ArtifactCreate(
            run_id=run_id,
            artifact_type="optimized_params",
            file_path=str(params_path),
            description=f"Optimized params for {strategy_name} from trial {trial_id}",
        )

        artifact = self.artifact_repository.create_artifact(artifact_data)
        logger.info(f"Registered params artifact {artifact['id']}")

        return {
            "artifact_id": artifact["id"],
            "artifact_path": str(params_path),
            "params_content": params_content,
        }

    def _validate_params(self, params: Dict[str, Any]) -> None:
        """
        Validate params structure.

        Args:
            params: Parameters dictionary to validate

        Raises:
            ValueError: If params are invalid
        """
        required_sections = ["buy", "sell"]
        for section in required_sections:
            if section not in params:
                raise ValueError(f"Missing required params section: {section}")

        # Validate buy params
        if not isinstance(params["buy"], dict) or not params["buy"]:
            raise ValueError("Buy params must be a non-empty dictionary")

        # Validate sell params
        if not isinstance(params["sell"], dict) or not params["sell"]:
            raise ValueError("Sell params must be a non-empty dictionary")

        # Optional sections validation
        optional_sections = ["roi", "stoploss", "trailing"]
        for section in optional_sections:
            if section in params and not isinstance(params[section], dict):
                raise ValueError(f"{section} params must be a dictionary if present")

    def _now_iso(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + "Z"
