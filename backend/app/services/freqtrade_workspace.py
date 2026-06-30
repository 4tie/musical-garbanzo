"""
Workspace helpers for HER's local Freqtrade integration.
"""
from pathlib import Path
import os
from typing import Any

from app.core.config import settings
from app.schemas.freqtrade import FreqtradeDirectoryStatus, FreqtradeWorkspaceStatus


REQUIRED_USER_DATA_SUBDIRS = (
    "strategies",
    "data",
    "backtest_results",
    "hyperopt_results",
    "hyperopts",
    "plot",
    "logs",
)


class FreqtradeWorkspaceService:
    """Resolve, create, and validate the local Freqtrade workspace."""

    def __init__(self, app_settings: Any = settings) -> None:
        self.settings = app_settings

    @property
    def project_root(self) -> Path:
        """Return the configured project root."""
        return Path(self.settings.project_root)

    def _resolve_project_path(self, value: str) -> Path:
        path = Path(value).expanduser()
        if path.is_absolute():
            return path.resolve()
        return (self.project_root / path).resolve()

    def _required_directories(self) -> dict[str, Path]:
        user_data_dir = self.get_user_data_dir()
        directories = {
            "user_data": user_data_dir,
            "config": self.get_config_dir(),
        }
        for subdir in REQUIRED_USER_DATA_SUBDIRS:
            directories[subdir] = user_data_dir / subdir
        return directories

    def _directory_status(self, key: str, path: Path, created: bool = False) -> FreqtradeDirectoryStatus:
        exists = path.exists()
        is_dir = path.is_dir()
        writable = is_dir and path.exists() and path.stat() and self._is_writable(path)
        return FreqtradeDirectoryStatus(
            key=key,
            path=str(path),
            exists=exists,
            is_dir=is_dir,
            writable=writable,
            created=created,
            error=None if exists and is_dir else "Missing or not a directory",
        )

    @staticmethod
    def _is_writable(path: Path) -> bool:
        return path.exists() and path.is_dir() and os.access(path, os.W_OK)

    @staticmethod
    def _safe_run_id(run_id: str) -> str:
        if not run_id or "/" in run_id or "\\" in run_id or ".." in run_id:
            raise ValueError("run_id must be a safe path segment")
        return run_id

    def get_paths(self) -> dict[str, Path]:
        """Return important Freqtrade and run artifact paths."""
        paths = {
            "project_root": self.project_root,
            "user_data_dir": self.get_user_data_dir(),
            "strategy_dir": self.get_strategy_dir(),
            "data_dir": self.get_data_dir(),
            "backtest_results_dir": self.get_backtest_results_dir(),
            "hyperopt_results_dir": self.get_hyperopt_results_dir(),
            "config_dir": self.get_config_dir(),
            "default_config": self._resolve_project_path(self.settings.FREQTRADE_DEFAULT_CONFIG),
        }
        return paths

    def ensure_workspace(self) -> FreqtradeWorkspaceStatus:
        """
        Create missing local workspace directories and return validation status.

        This method only creates directories. It never deletes user data, erases
        downloaded market data, or overwrites strategy files.
        """
        created_dirs: list[str] = []
        directory_statuses: list[FreqtradeDirectoryStatus] = []

        for key, path in self._required_directories().items():
            created = False
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created = True
                created_dirs.append(key)
            directory_statuses.append(self._directory_status(key, path, created=created))

        return self._build_workspace_status(directory_statuses, created_dirs)

    def validate_workspace(self) -> FreqtradeWorkspaceStatus:
        """Validate required workspace directories without creating anything."""
        directory_statuses = [
            self._directory_status(key, path)
            for key, path in self._required_directories().items()
        ]
        return self._build_workspace_status(directory_statuses, created_dirs=[])

    def _build_workspace_status(
        self,
        directory_statuses: list[FreqtradeDirectoryStatus],
        created_dirs: list[str],
    ) -> FreqtradeWorkspaceStatus:
        missing_dirs = [
            status.key
            for status in directory_statuses
            if not status.exists or not status.is_dir
        ]
        non_writable_dirs = [
            status.key
            for status in directory_statuses
            if status.exists and status.is_dir and not status.writable
        ]
        valid = not missing_dirs and not non_writable_dirs

        action = None
        if missing_dirs:
            action = f"Create missing Freqtrade workspace directories: {', '.join(missing_dirs)}"
        elif non_writable_dirs:
            action = f"Fix permissions for Freqtrade workspace directories: {', '.join(non_writable_dirs)}"

        return FreqtradeWorkspaceStatus(
            valid=valid,
            user_data_dir=str(self.get_user_data_dir()),
            config_dir=str(self.get_config_dir()),
            directories=directory_statuses,
            missing_dirs=missing_dirs,
            created_dirs=created_dirs,
            user_action_required=action,
        )

    def get_user_data_dir(self) -> Path:
        """Return the configured Freqtrade user_data directory."""
        return self._resolve_project_path(self.settings.FREQTRADE_USER_DATA_DIR)

    def get_strategy_dir(self) -> Path:
        """Return the Freqtrade strategies directory."""
        return self.get_user_data_dir() / "strategies"

    def get_data_dir(self) -> Path:
        """Return the Freqtrade market data directory."""
        return self.get_user_data_dir() / "data"

    def get_backtest_results_dir(self) -> Path:
        """Return the Freqtrade backtest results directory."""
        return self.get_user_data_dir() / "backtest_results"

    def get_hyperopt_results_dir(self) -> Path:
        """Return the Freqtrade hyperopt results directory."""
        return self.get_user_data_dir() / "hyperopt_results"

    def get_config_dir(self) -> Path:
        """Return the HER Freqtrade config directory."""
        return self._resolve_project_path(self.settings.FREQTRADE_CONFIG_DIR)

    def get_run_config_dir(self, run_id: str) -> Path:
        """Return the run-specific config artifact directory."""
        safe_run_id = self._safe_run_id(run_id)
        return (self.project_root / "artifacts" / "runs" / safe_run_id / "configs").resolve()

    def get_run_raw_freqtrade_dir(self, run_id: str) -> Path:
        """Return the run-specific raw Freqtrade artifact directory."""
        safe_run_id = self._safe_run_id(run_id)
        return (self.project_root / "artifacts" / "runs" / safe_run_id / "freqtrade_raw").resolve()

    def get_run_log_dir(self, run_id: str) -> Path:
        """Return the run-specific log artifact directory."""
        safe_run_id = self._safe_run_id(run_id)
        return (self.project_root / "artifacts" / "runs" / safe_run_id / "logs").resolve()
