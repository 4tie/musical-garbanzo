"""
Freqtrade backtest runner service.
"""
from pathlib import Path
from typing import Optional
from datetime import datetime

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.repositories.logs import RunLogRepository
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.freqtrade_backtest import (
    FreqtradeBacktestRequest,
    FreqtradeBacktestResult,
    FreqtradeBacktestArtifact,
)
from app.schemas.artifacts import ArtifactCreate
from app.services.freqtrade_command_runner import FreqtradeCommandRunner
from app.services.freqtrade_strategy_service import FreqtradeStrategyService


class FreqtradeBacktestRunner:
    """Service for running Freqtrade backtests and capturing raw outputs."""

    def __init__(
        self,
        command_runner: Optional[FreqtradeCommandRunner] = None,
        strategy_service: Optional[FreqtradeStrategyService] = None,
        artifact_repository: Optional[ArtifactRepository] = None,
        log_repository: Optional[RunLogRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
    ) -> None:
        self.command_runner = command_runner or FreqtradeCommandRunner(
            log_repository=log_repository or RunLogRepository(),
            audit_repository=audit_repository or AuditLogRepository(),
        )
        self.strategy_service = strategy_service or FreqtradeStrategyService()
        self.artifact_repository = artifact_repository or ArtifactRepository()
        self.log_repository = log_repository or RunLogRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    def get_artifacts_dir(self) -> Path:
        """Get the artifacts directory path."""
        return settings.project_root / "artifacts"

    def prepare_backtest_directory(self, run_id: str) -> Path:
        """
        Prepare the backtest output directory for a run.

        Args:
            run_id: Run ID

        Returns:
            Path to backtest directory
        """
        backtest_dir = self.get_artifacts_dir() / "runs" / run_id / "raw_freqtrade" / "backtest_results"
        backtest_dir.mkdir(parents=True, exist_ok=True)
        return backtest_dir

    def _freqtrade_available(self) -> bool:
        """Return whether Freqtrade is available for execution."""
        if not hasattr(self.command_runner, "detection_service"):
            return bool(settings.FREQTRADE_PATH or settings.freqtrade_default_config_path.exists())
        return (
            self.command_runner.detection_service.is_configured()
            and self.command_runner.detection_service.is_executable_available()
        )

    def build_backtest_command(self, request: FreqtradeBacktestRequest) -> list[str]:
        """
        Build the backtest command.

        Args:
            request: Backtest request

        Returns:
            Command list for subprocess
        """
        command = ["backtesting"]

        command.extend(["--config", request.config_path])
        command.extend(["--userdir", str(settings.freqtrade_user_data_dir_path)])
        command.extend(["--strategy", request.strategy_name])
        command.extend(["--timeframe", request.timeframe])
        command.extend(["--export", request.export])

        # Use prepared backtest directory or custom one
        backtest_dir = request.backtest_directory or str(self.prepare_backtest_directory(request.run_id))
        command.extend(["--backtest-directory", backtest_dir])

        if request.timerange:
            command.extend(["--timerange", request.timerange])

        if request.pairs:
            command.extend(["--pairs", ",".join(request.pairs)])

        # CRITICAL: Never run 'trade' command, only 'backtesting'
        # CRITICAL: Never set dry_run false (config ensures dry_run true)

        return command

    def run_backtest(self, request: FreqtradeBacktestRequest) -> FreqtradeBacktestResult:
        """
        Run a Freqtrade backtest.

        Args:
            request: Backtest request

        Returns:
            Backtest result with raw outputs
        """
        errors = []
        warnings = []

        # Validate prerequisites
        if not self._freqtrade_available():
            return FreqtradeBacktestResult(
                run_id=request.run_id,
                success=False,
                blocked=True,
                error="Freqtrade is not configured",
                errors=["Freqtrade is not configured"],
            )

        # Check strategy exists
        strategy_status = self.strategy_service.get_strategy_status(request.strategy_name)
        if not strategy_status.exists:
            return FreqtradeBacktestResult(
                run_id=request.run_id,
                success=False,
                blocked=True,
                error=f"Strategy not found: {request.strategy_name}",
                errors=[f"Strategy not found: {request.strategy_name}"],
            )

        # Prepare backtest directory
        backtest_dir = self.prepare_backtest_directory(request.run_id)
        started_at = datetime.now()

        # Log start
        self.log_repository.add_log(
            run_id=request.run_id,
            level="info",
            message=f"Starting Freqtrade backtest: strategy={request.strategy_name}, timeframe={request.timeframe}",
            source="freqtrade_backtest",
        )

        # Build and run command
        command = self.build_backtest_command(request)
        command_result = self.command_runner.run(
            command,
            run_id=request.run_id,
            timeout_seconds=request.timeout_seconds,
        )

        # Write stdout/stderr logs
        log_paths = self.write_stdout_stderr_logs(request.run_id, command_result)

        # Discover artifacts
        artifacts = self.discover_backtest_outputs(backtest_dir, started_at)

        # Register artifacts
        registered_artifacts = self.register_backtest_artifacts(request.run_id, command_result, artifacts)

        # Log completion
        if command_result.success:
            self.log_repository.add_log(
                run_id=request.run_id,
                level="info",
                message=f"Freqtrade backtest completed successfully in {command_result.duration_seconds:.2f}s",
                source="freqtrade_backtest",
            )
        else:
            self.log_repository.add_log(
                run_id=request.run_id,
                level="error",
                message=f"Freqtrade backtest failed: {command_result.error}",
                source="freqtrade_backtest",
            )

        # Audit log
        self.audit_repository.create_audit_log(
            {
                "run_id": request.run_id,
                "actor": "system",
                "action": "freqtrade_backtest",
                "resource_type": "backtest",
                "resource_id": request.run_id,
                "before": {"strategy": request.strategy_name, "timeframe": request.timeframe},
                "after": {
                    "success": command_result.success,
                    "exit_code": command_result.return_code,
                    "duration": command_result.duration_seconds,
                },
                "description": "Freqtrade backtest execution attempted",
            }
        )

        return FreqtradeBacktestResult(
            run_id=request.run_id,
            success=command_result.success,
            blocked=command_result.blocked,
            exit_code=command_result.return_code,
            stdout=command_result.stdout,
            stderr=command_result.stderr,
            duration_seconds=command_result.duration_seconds or 0.0,
            backtest_directory=str(backtest_dir),
            artifacts=registered_artifacts,
            error=command_result.error,
            errors=[command_result.error] if command_result.error else [],
            warnings=warnings,
        )

    def discover_backtest_outputs(self, backtest_directory: Path, started_at: datetime) -> list[FreqtradeBacktestArtifact]:
        """
        Discover backtest output files.

        Args:
            backtest_directory: Path to backtest directory
            started_at: When backtest started

        Returns:
            List of discovered artifacts
        """
        artifacts = []

        if not backtest_directory.exists():
            return artifacts

        for file_path in backtest_directory.rglob("*"):
            if file_path.is_file():
                # Only include files created after backtest started
                try:
                    file_stat = file_path.stat()
                    file_time = datetime.fromtimestamp(file_stat.st_mtime)
                    if file_time >= started_at:
                        artifacts.append(
                            FreqtradeBacktestArtifact(
                                artifact_type="backtest_raw",
                                path=str(file_path),
                                size_bytes=file_stat.st_size,
                                created_at=file_time.isoformat(),
                            )
                        )
                except Exception:
                    # Skip files that can't be accessed
                    continue

        return artifacts

    def register_backtest_artifacts(
        self, run_id: str, command_result, artifacts: list[FreqtradeBacktestArtifact]
    ) -> list[FreqtradeBacktestArtifact]:
        """
        Register backtest artifacts.

        Args:
            run_id: Run ID
            command_result: Command result
            artifacts: Discovered artifacts

        Returns:
            List of registered artifact data
        """
        registered: list[FreqtradeBacktestArtifact] = []

        # Register stdout/stderr logs
        logs_dir = self.get_artifacts_dir() / "runs" / run_id / "raw_freqtrade"
        stdout_path = logs_dir / "stdout.log"
        stderr_path = logs_dir / "stderr.log"

        if stdout_path.exists():
            try:
                self.artifact_repository.create_artifact(
                    ArtifactCreate(
                        run_id=run_id,
                        artifact_type="log_file",
                        file_path=str(stdout_path),
                        description="Freqtrade backtest stdout",
                    )
                )
                registered.append(
                    FreqtradeBacktestArtifact(
                        artifact_type="log_file",
                        path=str(stdout_path),
                        size_bytes=stdout_path.stat().st_size,
                    )
                )
            except Exception:
                pass

        if stderr_path.exists():
            try:
                self.artifact_repository.create_artifact(
                    ArtifactCreate(
                        run_id=run_id,
                        artifact_type="log_file",
                        file_path=str(stderr_path),
                        description="Freqtrade backtest stderr",
                    )
                )
                registered.append(
                    FreqtradeBacktestArtifact(
                        artifact_type="log_file",
                        path=str(stderr_path),
                        size_bytes=stderr_path.stat().st_size,
                    )
                )
            except Exception:
                pass

        # Register backtest artifacts
        for artifact in artifacts:
            try:
                self.artifact_repository.create_artifact(
                    ArtifactCreate(
                        run_id=run_id,
                        artifact_type=artifact.artifact_type,
                        file_path=artifact.path,
                        description=f"Backtest output: {Path(artifact.path).name}",
                    )
                )
                registered.append(artifact)
            except Exception:
                pass

        return registered

    def write_stdout_stderr_logs(self, run_id: str, command_result) -> dict:
        """
        Write stdout and stderr to log files.

        Args:
            run_id: Run ID
            command_result: Command result

        Returns:
            Dict with paths to log files
        """
        logs_dir = self.get_artifacts_dir() / "runs" / run_id / "raw_freqtrade"
        logs_dir.mkdir(parents=True, exist_ok=True)

        stdout_path = logs_dir / "stdout.log"
        stderr_path = logs_dir / "stderr.log"

        stdout_path.write_text(command_result.stdout)
        stderr_path.write_text(command_result.stderr)

        return {"stdout": str(stdout_path), "stderr": str(stderr_path)}
