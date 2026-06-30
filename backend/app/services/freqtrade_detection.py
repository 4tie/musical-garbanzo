"""
Freqtrade executable detection and version checks.
"""
from pathlib import Path
import os
import shutil
import subprocess
from typing import Any, Optional

from app.core.config import settings
from app.schemas.freqtrade import (
    FreqtradeCommandResult,
    FreqtradeStatus,
    FreqtradeVersion,
)
from app.services.freqtrade_workspace import FreqtradeWorkspaceService


class FreqtradeDetectionService:
    """Detect a local Freqtrade executable without running trading workflows."""

    def __init__(
        self,
        app_settings: Any = settings,
        workspace_service: Optional[FreqtradeWorkspaceService] = None,
    ) -> None:
        self.settings = app_settings
        self.workspace_service = workspace_service or FreqtradeWorkspaceService(app_settings)

    def get_freqtrade_executable(self) -> Optional[Path]:
        """
        Return the configured or PATH-resolved Freqtrade executable candidate.

        If FREQTRADE_PATH is set to a missing explicit path, that path is still
        returned so status output can explain what the user configured.
        """
        configured_path = self.settings.FREQTRADE_PATH
        if configured_path:
            path = Path(configured_path).expanduser()
            if path.is_absolute() or path.parent != Path("."):
                return path.resolve()
            resolved = shutil.which(str(path))
            return Path(resolved).resolve() if resolved else path

        resolved = shutil.which("freqtrade")
        return Path(resolved).resolve() if resolved else None

    def _path_source(self) -> str:
        if self.settings.FREQTRADE_PATH:
            return "configured"
        if shutil.which("freqtrade"):
            return "path"
        return "missing"

    def is_configured(self) -> bool:
        """Return whether HER has an explicit or PATH-discovered Freqtrade executable."""
        return self.get_freqtrade_executable() is not None

    def is_executable_available(self) -> bool:
        """Return whether the executable candidate exists and can be executed."""
        executable = self.get_freqtrade_executable()
        if executable is None:
            return False
        if executable.name == "freqtrade" and not executable.is_absolute():
            return shutil.which(str(executable)) is not None
        return executable.exists() and executable.is_file() and os.access(executable, os.X_OK)

    def get_version(self) -> FreqtradeVersion:
        """
        Run the only detection command allowed in Part 04: freqtrade --version.
        """
        executable = self.get_freqtrade_executable()
        if executable is None:
            return FreqtradeVersion(
                available=False,
                error="Freqtrade executable is not configured and was not found in PATH.",
            )

        command = [str(executable), "--version"]
        if not self.is_executable_available():
            return FreqtradeVersion(
                available=False,
                executable_path=str(executable),
                command_result=FreqtradeCommandResult(command=command, success=False),
                error="Freqtrade executable is not available.",
            )

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=10,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return FreqtradeVersion(
                available=False,
                executable_path=str(executable),
                command_result=FreqtradeCommandResult(command=command, timed_out=True, success=False),
                error="Freqtrade version command timed out.",
            )
        except OSError as exc:
            return FreqtradeVersion(
                available=False,
                executable_path=str(executable),
                command_result=FreqtradeCommandResult(command=command, success=False),
                error=f"Unable to run Freqtrade version command: {exc}",
            )

        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        success = result.returncode == 0
        version_text = self._parse_version(stdout)
        return FreqtradeVersion(
            available=success,
            executable_path=str(executable),
            version=version_text if success else None,
            command_result=FreqtradeCommandResult(
                command=command,
                return_code=result.returncode,
                stdout=stdout,
                stderr=stderr,
                success=success,
            ),
            error=None if success else stderr or "Freqtrade version command failed.",
        )

    @staticmethod
    def _parse_version(stdout: str) -> Optional[str]:
        """Extract the Freqtrade version line from varied --version output."""
        lines = [line.strip() for line in stdout.splitlines() if line.strip()]
        for line in lines:
            if "Freqtrade Version:" in line:
                return line.split("Freqtrade Version:", 1)[1].strip()
        for line in lines:
            if "freqtrade" in line.lower():
                return line
        return lines[0] if lines else None

    def get_status(self) -> FreqtradeStatus:
        """Return combined executable and workspace status without raising unhandled errors."""
        executable = self.get_freqtrade_executable()
        workspace_status = self.workspace_service.validate_workspace()
        version = self.get_version()
        executable_available = self.is_executable_available()

        action = None
        if not executable:
            action = "Install Freqtrade or set FREQTRADE_PATH."
        elif not executable_available:
            action = "Fix FREQTRADE_PATH or install Freqtrade in PATH."
        elif not workspace_status.valid:
            action = workspace_status.user_action_required

        return FreqtradeStatus(
            configured=self.is_configured(),
            executable_available=executable_available,
            executable_path=str(executable) if executable else None,
            path_source=self._path_source(),
            version=version.version,
            workspace_valid=workspace_status.valid,
            workspace=workspace_status,
            user_action_required=action,
            error=version.error if executable and not version.available else None,
        )
