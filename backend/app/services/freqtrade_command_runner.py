"""
Safe command runner for the Part 04 Freqtrade integration.
"""
from pathlib import Path
import re
import subprocess
import time
from typing import Optional

from app.core.constants import (
    FREQTRADE_ALLOWED_COMMANDS_PART_04,
    FREQTRADE_ALLOWED_COMMANDS_PART_08,
    FREQTRADE_FORBIDDEN_COMMANDS,
    FREQTRADE_VERSION_COMMAND,
)
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.logs import RunLogRepository
from app.schemas.audit_logs import AuditLogCreate
from app.schemas.freqtrade import FreqtradeCommandResult
from app.services.freqtrade_detection import FreqtradeDetectionService


SHELL_OPERATOR_TOKENS = ("&&", ";", "|", ">", "<", "`", "$(")
ENV_DUMP_TOKENS = ("env", "printenv", "set", "export")
LIVE_INTENT_MARKERS = (
    "live",
    "order",
    "orders",
    "forcebuy",
    "force-buy",
    "forcesell",
    "force-sell",
    "cancel-open-orders",
)
SECRET_MARKERS = (
    "token",
    "secret",
    "password",
    "api_key",
    "api-key",
    "apikey",
    "private_key",
    "private-key",
    "app_secret_key",
    "app-secret-key",
    "discord_bot_token",
    "discord-bot-token",
)


class FreqtradeCommandRunner:
    """Run only explicitly allowed Freqtrade commands with sanitized logging."""

    ALLOWED_COMMANDS_PART_04 = FREQTRADE_ALLOWED_COMMANDS_PART_04
    ALLOWED_COMMANDS_PART_08 = FREQTRADE_ALLOWED_COMMANDS_PART_08
    FORBIDDEN_COMMANDS = FREQTRADE_FORBIDDEN_COMMANDS

    def __init__(
        self,
        detection_service: Optional[FreqtradeDetectionService] = None,
        log_repository: Optional[RunLogRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
        use_part_08_commands: bool = False,
    ) -> None:
        self.detection_service = detection_service or FreqtradeDetectionService()
        self.log_repository = log_repository or RunLogRepository()
        self.audit_repository = audit_repository or AuditLogRepository()
        self.use_part_08_commands = use_part_08_commands

    @property
    def ALLOWED_COMMANDS(self) -> list[str]:
        """Return the appropriate allowed commands list based on mode."""
        return (
            self.ALLOWED_COMMANDS_PART_08
            if self.use_part_08_commands
            else self.ALLOWED_COMMANDS_PART_04
        )

    def build_base_command(self) -> list[str]:
        """Return the configured Freqtrade executable as a subprocess command prefix."""
        executable = self.detection_service.get_freqtrade_executable()
        if executable is None:
            return []
        return [str(executable)]

    def validate_command(self, command: list[str]) -> None:
        """
        Validate a Freqtrade command before execution.

        Raises:
            ValueError: If the command is outside the Part 04 safety boundary.
        """
        if not command:
            raise ValueError("Freqtrade command cannot be empty.")

        if not all(isinstance(arg, str) and arg for arg in command):
            raise ValueError("Freqtrade command arguments must be non-empty strings.")

        lowered = [arg.lower() for arg in command]
        for arg in lowered:
            if any(operator in arg for operator in SHELL_OPERATOR_TOKENS):
                raise ValueError("Shell operators are not allowed in Freqtrade commands.")
            if ".env" in arg:
                raise ValueError("Commands may not access .env files.")
            if arg in ENV_DUMP_TOKENS or arg.endswith("/env") or arg.endswith("/printenv"):
                raise ValueError("Environment dump commands are not allowed.")

        subcommand = self._extract_subcommand(command)
        if subcommand == FREQTRADE_VERSION_COMMAND:
            if len(command) != 2:
                raise ValueError("Version check must be exactly: freqtrade --version.")
            return

        if subcommand in FREQTRADE_FORBIDDEN_COMMANDS:
            raise ValueError(f"Forbidden Freqtrade command blocked: {subcommand}.")

        if subcommand not in self.ALLOWED_COMMANDS:
            raise ValueError(f"Unknown or disallowed Freqtrade command blocked: {subcommand}.")

        # Skip live intent validation for hyperopt (it's a backtesting/optimization tool)
        if subcommand != "hyperopt":
            if any(marker in arg for marker in LIVE_INTENT_MARKERS for arg in lowered):
                raise ValueError("Commands containing live order execution intent are blocked.")

    def run(
        self,
        command: list[str],
        run_id: Optional[str] = None,
        stage_key: Optional[str] = None,
        timeout_seconds: int = 300,
        cwd: Optional[str | Path] = None,
    ) -> FreqtradeCommandResult:
        """Validate and run a safe Freqtrade command with captured output."""
        start_time = time.monotonic()
        normalized_command = self._normalize_command(command)

        if not normalized_command:
            result = FreqtradeCommandResult(
                command=[],
                sanitized_command=[],
                success=False,
                blocked=True,
                error="Freqtrade executable is not configured or was not found.",
                duration_seconds=0.0,
            )
            self.write_command_log(result, run_id=run_id, stage_key=stage_key)
            self._write_audit_log(result, run_id=run_id)
            return result

        try:
            self.validate_command(normalized_command)
        except ValueError as exc:
            result = FreqtradeCommandResult(
                command=normalized_command,
                sanitized_command=self.sanitize_command_for_logs(normalized_command),
                success=False,
                blocked=True,
                error=str(exc),
                duration_seconds=round(time.monotonic() - start_time, 6),
            )
            self.write_command_log(result, run_id=run_id, stage_key=stage_key)
            self._write_audit_log(result, run_id=run_id)
            return result

        if not self.detection_service.is_executable_available():
            result = FreqtradeCommandResult(
                command=normalized_command,
                sanitized_command=self.sanitize_command_for_logs(normalized_command),
                success=False,
                error="Freqtrade executable is not available.",
                duration_seconds=round(time.monotonic() - start_time, 6),
            )
            self.write_command_log(result, run_id=run_id, stage_key=stage_key)
            self._write_audit_log(result, run_id=run_id)
            return result

        try:
            completed = subprocess.run(
                normalized_command,
                shell=False,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                cwd=str(cwd) if cwd else None,
                check=False,
            )
            result = FreqtradeCommandResult(
                command=normalized_command,
                sanitized_command=self.sanitize_command_for_logs(normalized_command),
                return_code=completed.returncode,
                stdout=self._sanitize_text(completed.stdout or ""),
                stderr=self._sanitize_text(completed.stderr or ""),
                duration_seconds=round(time.monotonic() - start_time, 6),
                success=completed.returncode == 0,
                error=None if completed.returncode == 0 else "Freqtrade command failed.",
            )
        except subprocess.TimeoutExpired as exc:
            result = FreqtradeCommandResult(
                command=normalized_command,
                sanitized_command=self.sanitize_command_for_logs(normalized_command),
                stdout=self._sanitize_text(exc.stdout or ""),
                stderr=self._sanitize_text(exc.stderr or ""),
                duration_seconds=round(time.monotonic() - start_time, 6),
                timed_out=True,
                success=False,
                error=f"Freqtrade command timed out after {timeout_seconds} seconds.",
            )
        except OSError as exc:
            result = FreqtradeCommandResult(
                command=normalized_command,
                sanitized_command=self.sanitize_command_for_logs(normalized_command),
                duration_seconds=round(time.monotonic() - start_time, 6),
                success=False,
                error=f"Unable to run Freqtrade command: {exc}",
            )

        self.write_command_log(result, run_id=run_id, stage_key=stage_key)
        self._write_audit_log(result, run_id=run_id)
        return result

    def run_version(self) -> FreqtradeCommandResult:
        """Run the safe Freqtrade version check."""
        return self.run([FREQTRADE_VERSION_COMMAND], timeout_seconds=10)

    def sanitize_command_for_logs(self, command: list[str]) -> list[str]:
        """Return a command array safe for logs and audit records."""
        sanitized: list[str] = []
        redact_next = False
        for arg in command:
            lower = arg.lower()
            if redact_next:
                sanitized.append("[REDACTED]")
                redact_next = False
                continue
            if any(marker in lower for marker in SECRET_MARKERS) or ".env" in lower:
                sanitized.append("[REDACTED]")
                if lower.startswith("--") and "=" not in lower:
                    redact_next = True
            else:
                sanitized.append(arg)
        return sanitized

    def write_command_log(
        self,
        result: FreqtradeCommandResult,
        run_id: Optional[str] = None,
        stage_key: Optional[str] = None,
    ) -> None:
        """Record a run log entry when a run_id is available."""
        if not run_id:
            return

        level = "info" if result.success else "warning"
        if result.timed_out or (result.return_code is not None and result.return_code != 0):
            level = "error"

        try:
            self.log_repository.add_log(
                run_id=run_id,
                level=level,
                source="freqtrade",
                message="Freqtrade command blocked" if result.blocked else "Freqtrade command executed",
                stage_key=stage_key,
                details=self._result_details(result),
            )
        except Exception:
            # Command execution results must not be hidden by logging failures.
            return

    def _write_audit_log(self, result: FreqtradeCommandResult, run_id: Optional[str]) -> None:
        """Record an audit entry for the command attempt."""
        try:
            self.audit_repository.create_audit_log(
                AuditLogCreate(
                    run_id=run_id,
                    actor="system",
                    action_type="freqtrade_command_attempt",
                    target_type="freqtrade_command",
                    description="Freqtrade command blocked" if result.blocked else "Freqtrade command execution attempted",
                    after=self._result_details(result),
                    approved=not result.blocked,
                )
            )
        except Exception:
            return

    def _normalize_command(self, command: list[str]) -> list[str]:
        """Normalize subcommand arrays to full executable command arrays."""
        if not command:
            return command

        if self._looks_like_freqtrade_executable(command[0]):
            return command

        base_command = self.build_base_command()
        if not base_command:
            return []
        return base_command + command

    def _extract_subcommand(self, command: list[str]) -> str:
        """Extract the first Freqtrade subcommand from a full command array."""
        if self._looks_like_freqtrade_executable(command[0]):
            if len(command) < 2:
                raise ValueError("Freqtrade subcommand is required.")
            return command[1]
        return command[0]

    @staticmethod
    def _looks_like_freqtrade_executable(arg: str) -> bool:
        executable_name = Path(arg).name.lower()
        return executable_name == "freqtrade" or executable_name.startswith("freqtrade.")

    @staticmethod
    def _sanitize_text(text: str) -> str:
        """Redact secret-like lines and key/value fragments from command output."""
        if not text:
            return ""

        sanitized_lines = []
        for line in str(text).splitlines():
            lower = line.lower()
            if any(marker in lower for marker in SECRET_MARKERS):
                sanitized_lines.append("[REDACTED]")
            else:
                sanitized_lines.append(line)

        sanitized = "\n".join(sanitized_lines)
        sanitized = re.sub(
            r"(?i)(token|secret|password|api[_-]?key|private[_-]?key)(\s*[:=]\s*)\S+",
            r"\1\2[REDACTED]",
            sanitized,
        )
        return sanitized

    @staticmethod
    def _result_details(result: FreqtradeCommandResult) -> dict:
        return {
            "command": result.sanitized_command,
            "return_code": result.return_code,
            "success": result.success,
            "blocked": result.blocked,
            "timed_out": result.timed_out,
            "duration_seconds": result.duration_seconds,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "error": result.error,
        }
