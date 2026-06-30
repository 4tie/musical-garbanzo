"""
Freqtrade data availability and controlled download service.
"""
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.repositories.logs import RunLogRepository
from app.repositories.audit_logs import AuditLogRepository
from app.schemas.freqtrade_data import (
    FreqtradeDataCheckRequest,
    FreqtradeDataCheckResult,
    FreqtradeDataDownloadRequest,
    FreqtradeDataDownloadResult,
    PairDataStatus,
)
from app.services.freqtrade_command_runner import FreqtradeCommandRunner


class FreqtradeDataService:
    """Service for checking data availability and downloading market data."""

    def __init__(
        self,
        command_runner: Optional[FreqtradeCommandRunner] = None,
        log_repository: Optional[RunLogRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
    ) -> None:
        self.command_runner = command_runner or FreqtradeCommandRunner(
            log_repository=log_repository or RunLogRepository(),
            audit_repository=audit_repository or AuditLogRepository(),
        )
        self.log_repository = log_repository or RunLogRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    def _freqtrade_available(self) -> bool:
        """Return whether the command runner can see an executable Freqtrade."""
        if not hasattr(self.command_runner, "detection_service"):
            return bool(settings.FREQTRADE_PATH or settings.freqtrade_default_config_path.exists())
        return (
            self.command_runner.detection_service.is_configured()
            and self.command_runner.detection_service.is_executable_available()
        )

    def get_data_dir(self) -> Path:
        """
        Get the Freqtrade data directory path.

        Returns:
            Path to the data directory
        """
        return settings.freqtrade_user_data_dir_path / "data"

    def check_data(self, request: FreqtradeDataCheckRequest) -> FreqtradeDataCheckResult:
        """
        Check data availability for specified pairs and timeframe.

        Args:
            request: Data check request

        Returns:
            Data check result with pair statuses
        """
        pair_statuses = []
        errors = []
        warnings = []

        # Try to use Freqtrade list-data if configured
        if self._freqtrade_available():
            try:
                result = self._check_data_via_freqtrade(request)
                return result
            except Exception as exc:
                warnings.append(f"Freqtrade list-data failed: {exc}")
                # Fall through to local file discovery

        # Fallback to local file discovery
        pair_statuses = self.discover_local_data_files(
            request.exchange,
            request.trading_mode,
            request.pairs,
            request.timeframe,
        )

        return FreqtradeDataCheckResult(
            run_id=request.run_id,
            exchange=request.exchange,
            trading_mode=request.trading_mode,
            pairs=pair_statuses,
            freqtrade_visible=False,
            source="file",
            errors=errors,
            warnings=warnings,
        )

    def _check_data_via_freqtrade(self, request: FreqtradeDataCheckRequest) -> FreqtradeDataCheckResult:
        """
        Check data availability using Freqtrade list-data command.

        Args:
            request: Data check request

        Returns:
            Data check result from Freqtrade
        """
        command = self.build_list_data_command(request)
        result = self.command_runner.run(command, run_id=request.run_id)

        if not result.success:
            return FreqtradeDataCheckResult(
                run_id=request.run_id,
                exchange=request.exchange,
                trading_mode=request.trading_mode,
                pairs=[],
                freqtrade_visible=False,
                source="freqtrade",
                errors=[result.error or "Freqtrade list-data command failed"],
            )

        # Parse Freqtrade output
        pair_statuses = self._parse_list_data_output(result.stdout, request.pairs, request.timeframe)

        return FreqtradeDataCheckResult(
            run_id=request.run_id,
            exchange=request.exchange,
            trading_mode=request.trading_mode,
            pairs=pair_statuses,
            freqtrade_visible=True,
            source="freqtrade",
            errors=[],
            warnings=[],
        )

    def build_list_data_command(self, request: FreqtradeDataCheckRequest) -> list[str]:
        """
        Build the list-data command.

        Args:
            request: Data check request

        Returns:
            Command list for subprocess
        """
        command = ["list-data"]

        if request.config_path:
            command.extend(["--config", request.config_path])
        else:
            command.extend(["--userdir", str(settings.freqtrade_user_data_dir_path)])

        if request.show_timerange:
            command.append("--show-timerange")

        command.extend(["--exchange", request.exchange])

        return command

    def _parse_list_data_output(self, stdout: str, pairs: list[str], timeframe: str) -> list[PairDataStatus]:
        """
        Parse Freqtrade list-data output.

        Args:
            stdout: Stdout from list-data command
            pairs: Requested pairs
            timeframe: Requested timeframe

        Returns:
            List of pair data statuses
        """
        pair_statuses = []

        for pair in pairs:
            # Check if pair appears in output
            pair_found = pair in stdout

            pair_status = PairDataStatus(
                pair=pair,
                timeframe=timeframe,
                exists=pair_found,
                file_path=None,
                timerange=None,
                errors=[],
                warnings=[],
            )
            pair_statuses.append(pair_status)

        return pair_statuses

    def download_data(self, request: FreqtradeDataDownloadRequest) -> FreqtradeDataDownloadResult:
        """
        Download market data for specified pairs and timeframes.

        Args:
            request: Data download request

        Returns:
            Data download result
        """
        # Validate prerequisites
        if not self._freqtrade_available():
            return FreqtradeDataDownloadResult(
                run_id=request.run_id,
                exchange=request.exchange,
                trading_mode=request.trading_mode,
                pairs=request.pairs,
                timeframes=request.timeframes,
                success=False,
                blocked=True,
                error="Freqtrade is not configured",
                errors=["Freqtrade is not configured"],
            )

        if not request.user_confirmed:
            return FreqtradeDataDownloadResult(
                run_id=request.run_id,
                exchange=request.exchange,
                trading_mode=request.trading_mode,
                pairs=request.pairs,
                timeframes=request.timeframes,
                success=False,
                blocked=True,
                error="User confirmation required",
                errors=["User confirmation required"],
            )

        # Build and run command
        command = self.build_download_data_command(request)
        result = self.command_runner.run(command, run_id=request.run_id)

        return FreqtradeDataDownloadResult(
            run_id=request.run_id,
            exchange=request.exchange,
            trading_mode=request.trading_mode,
            pairs=request.pairs,
            timeframes=request.timeframes,
            success=result.success,
            blocked=result.blocked,
            stdout=result.stdout,
            stderr=result.stderr,
            error=result.error,
            duration=result.duration_seconds or 0.0,
            errors=[result.error] if result.error else [],
            warnings=[],
        )

    def build_download_data_command(self, request: FreqtradeDataDownloadRequest) -> list[str]:
        """
        Build the download-data command.

        Args:
            request: Data download request

        Returns:
            Command list for subprocess
        """
        command = ["download-data"]

        if request.config_path:
            command.extend(["--config", request.config_path])
        else:
            command.extend(["--userdir", str(settings.freqtrade_user_data_dir_path)])

        command.extend(["--pairs", ",".join(request.pairs)])
        command.extend(["--timeframes", ",".join(request.timeframes)])
        command.extend(["--exchange", request.exchange])

        if request.days:
            command.extend(["--days", str(request.days)])

        if request.timerange:
            command.extend(["--timerange", request.timerange])

        command.extend(["--trading-mode", request.trading_mode])
        command.extend(["--data-format-ohlcv", request.data_format_ohlcv])

        # CRITICAL: Never use --erase in Part 04
        # This prevents accidental data deletion

        return command

    def discover_local_data_files(
        self, exchange: str, trading_mode: str, pairs: list[str], timeframe: str
    ) -> list[PairDataStatus]:
        """
        Discover local data files for specified pairs and timeframe.

        Args:
            exchange: Exchange name
            trading_mode: Trading mode
            pairs: Trading pairs to check
            timeframe: Timeframe to check

        Returns:
            List of pair data statuses
        """
        pair_statuses = []
        data_dir = self.get_data_dir()

        # Expected path pattern: data_dir / exchange / timeframe / pair.json
        for pair in pairs:
            pair_file = pair.replace("/", "_")
            exchange_dir = data_dir / exchange
            candidate_paths = [
                exchange_dir / f"{pair_file}-{timeframe}.feather",
                exchange_dir / f"{pair_file}-{timeframe}.json",
                exchange_dir / timeframe / f"{pair_file}.feather",
                exchange_dir / timeframe / f"{pair_file}.json",
            ]
            file_path = next((path for path in candidate_paths if path.exists()), candidate_paths[0])
            exists = file_path.exists()

            pair_status = PairDataStatus(
                pair=pair,
                timeframe=timeframe,
                exists=exists,
                file_path=str(file_path) if exists else None,
                timerange=None,
                errors=[],
                warnings=[],
            )
            pair_statuses.append(pair_status)

        return pair_statuses
