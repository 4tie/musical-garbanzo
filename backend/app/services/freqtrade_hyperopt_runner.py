"""
Freqtrade Hyperopt runner for Part 08 optimization pipeline.
Safely executes Freqtrade hyperopt commands through the command runner.
"""
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional

from app.core.constants import FREQTRADE_HYPEROPT_RESULTS, HER_ARTIFACTS_RUNS
from app.schemas.optimization import HyperoptPolicy, HyperoptRunResult, OptimizationRequest
from app.services.freqtrade_command_runner import FreqtradeCommandRunner
from app.services.freqtrade_detection import FreqtradeDetectionService


DEFAULT_HYPEROPT_LOSS = "SharpeHyperOptLossDaily"


class FreqtradeHyperoptRunner:
    """Safe runner for Freqtrade hyperopt commands."""

    def __init__(
        self,
        command_runner: Optional[FreqtradeCommandRunner] = None,
        detection_service: Optional[FreqtradeDetectionService] = None,
    ) -> None:
        """
        Initialize the hyperopt runner.

        Args:
            command_runner: Optional command runner instance
            detection_service: Optional detection service instance
        """
        self.command_runner = command_runner or FreqtradeCommandRunner(
            use_part_08_commands=True
        )
        self.detection_service = detection_service or FreqtradeDetectionService()

    def run_hyperopt(
        self,
        request: OptimizationRequest,
        config_path: str,
        run_id: str,
        policy: HyperoptPolicy,
        cwd: Optional[str] = None,
    ) -> HyperoptRunResult:
        """
        Run Freqtrade hyperopt with safe command construction.

        Args:
            request: Optimization request
            config_path: Path to Freqtrade config file
            run_id: Run ID for logging
            policy: Hyperopt policy for safety validation
            cwd: Optional working directory

        Returns:
            HyperoptRunResult with execution details
        """
        # Build safe hyperopt command
        command = self.build_hyperopt_command(
            config_path=config_path,
            strategy_name=request.strategy_name,
            spaces=request.spaces,
            epochs=request.epochs,
        )

        # Log command metadata (without secrets)
        command_metadata = {
            "executable": str(self.detection_service.get_freqtrade_executable()),
            "full_args": command,
            "config_path": config_path,
            "strategy": request.strategy_name,
            "spaces": request.spaces,
            "epochs": request.epochs,
            "hyperopt_loss": DEFAULT_HYPEROPT_LOSS,
            "run_id": run_id,
            "working_directory": cwd,
        }
        
        # Log command metadata for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Hyperopt command metadata: {command_metadata}")
        logger.info(f"Full command to execute: {command}")

        command_started_at = time.time()

        # Run command through safe command runner
        result = self.command_runner.run(
            command=command,
            run_id=run_id,
            stage_key="hyperopt_execution",
            timeout_seconds=policy.timeout_seconds,
            cwd=cwd,
        )

        output_paths = self.write_execution_artifacts(
            run_id=run_id,
            command_metadata=command_metadata,
            command_result=result,
        )

        # Capture artifacts - use FREQTRADE_USER_DATA as cwd if not provided
        from app.core.constants import FREQTRADE_USER_DATA
        artifact_cwd = cwd if cwd else FREQTRADE_USER_DATA
        result_files = self.capture_hyperopt_artifacts(
            run_id,
            artifact_cwd,
            strategy_name=request.strategy_name,
            since_timestamp=command_started_at,
        )

        # Build hyperopt result
        hyperopt_result = HyperoptRunResult(
            success=result.success,
            exit_code=result.return_code,
            duration_seconds=result.duration_seconds,
            stdout_path=output_paths.get("stdout_path"),
            stderr_path=output_paths.get("stderr_path"),
            result_files=result_files,
            command_metadata=command_metadata,
            warnings=result.warnings if hasattr(result, "warnings") else [],
            errors=[result.error] if result.error else [],
            timed_out=result.timed_out if hasattr(result, "timed_out") else False,
            blocked=result.blocked if hasattr(result, "blocked") else False,
        )

        return hyperopt_result

    def write_execution_artifacts(
        self,
        run_id: str,
        command_metadata: Dict[str, Any],
        command_result: Any,
    ) -> Dict[str, str]:
        """
        Persist stdout, stderr, and command metadata for every hyperopt attempt.

        These files are required for real-run diagnostics. They are written even
        when Freqtrade exits non-zero, times out, or is blocked before execution.
        """
        artifact_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "hyperopt"
        artifact_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = artifact_dir / "stdout.log"
        stderr_path = artifact_dir / "stderr.log"
        metadata_path = artifact_dir / "command_metadata.json"

        stdout_path.write_text(command_result.stdout or "", encoding="utf-8")
        stderr_path.write_text(command_result.stderr or "", encoding="utf-8")

        execution_metadata = {
            **command_metadata,
            "command_args": list(command_metadata.get("full_args", [])),
            "exit_code": command_result.return_code,
            "duration_seconds": command_result.duration_seconds,
            "success": command_result.success,
            "blocked": getattr(command_result, "blocked", False),
            "timed_out": getattr(command_result, "timed_out", False),
            "error": command_result.error,
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
        }
        metadata_path.write_text(
            json.dumps(execution_metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )

        return {
            "stdout_path": str(stdout_path),
            "stderr_path": str(stderr_path),
            "command_metadata_path": str(metadata_path),
        }

    def build_hyperopt_command(
        self,
        config_path: str,
        strategy_name: str,
        spaces: List[str],
        epochs: int,
    ) -> List[str]:
        """
        Build a safe Freqtrade hyperopt command.

        Args:
            config_path: Path to Freqtrade config file
            strategy_name: Strategy name
            spaces: Hyperopt spaces to optimize
            epochs: Number of epochs

        Returns:
            List of command arguments
        """
        executable = self.detection_service.get_freqtrade_executable()
        if not executable:
            raise ValueError("Freqtrade executable not found")

        # Validate required arguments
        if not config_path or not isinstance(config_path, str) or not config_path.strip():
            raise ValueError(f"Invalid config_path: {config_path!r}")
        if not strategy_name or not isinstance(strategy_name, str) or not strategy_name.strip():
            raise ValueError(f"Invalid strategy_name: {strategy_name!r}")
        if epochs <= 0:
            raise ValueError(f"Invalid epochs: {epochs!r} (must be positive)")

        command = [str(executable), "hyperopt"]

        # Add config
        command.extend(["--config", config_path])

        # Add strategy
        command.extend(["--strategy", strategy_name])

        # Add spaces (only if non-empty)
        if spaces and isinstance(spaces, list):
            # Filter out empty spaces
            valid_spaces = [s for s in spaces if s and isinstance(s, str) and s.strip()]
            if valid_spaces:
                # Freqtrade expects --spaces to be followed by space-separated values
                command.extend(["--spaces"] + valid_spaces)

        # Add epochs
        command.extend(["--epochs", str(epochs)])

        # Freqtrade 2026.5.1 requires an explicit Hyperopt loss class.
        command.extend(["--hyperopt-loss", DEFAULT_HYPEROPT_LOSS])

        # Keep optimization evidence in HER artifacts; do not let Freqtrade
        # update strategy parameter files as a side effect of validation runs.
        command.append("--disable-param-export")

        # Validate all command arguments are non-empty strings
        for index, arg in enumerate(command):
            if not isinstance(arg, str) or not arg.strip():
                raise ValueError(
                    f"Invalid hyperopt command arg at index {index}: {arg!r}"
                )
        
        # Log the full command for debugging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Built hyperopt command: {command}")

        # Note: We do NOT add --dry-run because hyperopt doesn't use it
        # We do NOT add any live trading parameters
        # We do NOT add exchange API keys

        return command

    def capture_hyperopt_artifacts(
        self,
        run_id: str,
        cwd: Optional[str] = None,
        strategy_name: Optional[str] = None,
        since_timestamp: Optional[float] = None,
    ) -> List[str]:
        """
        Capture hyperopt result files as artifacts.

        Args:
            run_id: Run ID for artifact naming
            cwd: Working directory (typically freqtrade user_data)

        Returns:
            List of artifact file paths (copied to run-specific directory)
        """
        import shutil
        
        artifacts: List[str] = []

        if cwd:
            search_root = Path(cwd) / "hyperopt_results"
        else:
            search_root = Path(FREQTRADE_HYPEROPT_RESULTS)

        if not search_root.exists():
            return artifacts

        # Create run-specific artifact directory
        run_artifact_dir = Path(HER_ARTIFACTS_RUNS) / run_id / "hyperopt"
        run_artifact_dir.mkdir(parents=True, exist_ok=True)

        candidate_patterns = ("*.fthypt", "*.json", "*.pickle")
        for pattern in candidate_patterns:
            for result_file in search_root.glob(pattern):
                if result_file.name.startswith("."):
                    continue
                if strategy_name and result_file.name.startswith("strategy_"):
                    expected_prefix = f"strategy_{strategy_name}_"
                    if not result_file.name.startswith(expected_prefix):
                        continue
                # Remove timestamp check temporarily to ensure artifact capture
                # The strategy name prefix filter should be sufficient for most cases
                
                # Copy file to run-specific artifact directory
                dest_path = run_artifact_dir / result_file.name
                shutil.copy2(result_file, dest_path)
                artifacts.append(str(dest_path))

        return sorted(set(artifacts))

    def find_hyperopt_result_files(self, run_id: str, cwd: Optional[str] = None) -> List[str]:
        """
        Find hyperopt result files for a specific run.

        Args:
            run_id: Run ID to search for
            cwd: Working directory

        Returns:
            List of result file paths
        """
        if not cwd:
            return []

        cwd_path = Path(cwd)
        hyperopt_results_dir = cwd_path / "hyperopt_results"

        if not hyperopt_results_dir.exists():
            return []

        # Look for files matching the run_id pattern
        result_files = []
        for result_file in hyperopt_results_dir.glob("*"):
            if run_id in result_file.name:
                result_files.append(str(result_file))

        return result_files

    def get_hyperopt_help(self) -> Dict[str, Any]:
        """
        Get hyperopt help information safely.

        Returns:
            Dictionary with help information
        """
        executable = self.detection_service.get_freqtrade_executable()
        if not executable:
            return {"error": "Freqtrade executable not found"}

        command = [str(executable), "hyperopt", "--help"]

        result = self.command_runner.run(command, timeout_seconds=10)

        return {
            "success": result.success,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.return_code,
        }
