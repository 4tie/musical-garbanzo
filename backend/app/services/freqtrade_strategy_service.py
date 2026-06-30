"""
Freqtrade strategy detection and validation service.
"""
import re
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.schemas.freqtrade_strategy import (
    FreqtradeStrategyFile,
    FreqtradeStrategyListResult,
    FreqtradeStrategyStatus,
)
from app.services.freqtrade_command_runner import FreqtradeCommandRunner


class FreqtradeStrategyService:
    """Service for detecting and validating Freqtrade strategies."""

    def __init__(
        self,
        command_runner: Optional[FreqtradeCommandRunner] = None,
    ) -> None:
        self.command_runner = command_runner or FreqtradeCommandRunner()

    def get_strategy_dir(self) -> Path:
        """
        Get the Freqtrade strategies directory path.

        Returns:
            Path to the strategies directory
        """
        return settings.freqtrade_user_data_dir_path / "strategies"

    def list_strategy_files(self) -> FreqtradeStrategyListResult:
        """
        List all strategy files in the strategies directory.

        Returns:
            List result with detected strategies
        """
        strategies = []
        errors = []
        warnings = []

        strategy_dir = self.get_strategy_dir()

        if not strategy_dir.exists():
            return FreqtradeStrategyListResult(
                strategies=[],
                freqtrade_visible=False,
                source="file",
                errors=[f"Strategies directory does not exist: {strategy_dir}"],
            )

        try:
            for py_file in strategy_dir.glob("*.py"):
                if py_file.name.startswith("__"):
                    continue

                strategy_name = py_file.stem
                sidecar_path = strategy_dir / f"{strategy_name}.json"
                has_sidecar = sidecar_path.exists()

                if not has_sidecar:
                    warnings.append(f"Strategy {strategy_name} missing sidecar .json file")

                strategy = FreqtradeStrategyFile(
                    strategy_name=strategy_name,
                    class_name=None,
                    file_path=str(py_file),
                    params_path=str(sidecar_path) if has_sidecar else None,
                    exists=True,
                    has_sidecar_json=has_sidecar,
                    source="file",
                    errors=[],
                    warnings=[f"Missing sidecar .json"] if not has_sidecar else [],
                )
                strategies.append(strategy)

        except Exception as exc:
            errors.append(f"Error listing strategy files: {exc}")

        return FreqtradeStrategyListResult(
            strategies=strategies,
            freqtrade_visible=False,
            source="file",
            errors=errors,
            warnings=warnings,
        )

    def detect_sidecar_json(self, py_path: Path) -> Optional[Path]:
        """
        Detect the sidecar JSON file for a strategy.

        Args:
            py_path: Path to the strategy .py file

        Returns:
            Path to sidecar .json if exists, None otherwise
        """
        if not py_path.exists():
            return None

        strategy_dir = py_path.parent
        strategy_name = py_path.stem
        sidecar_path = strategy_dir / f"{strategy_name}.json"

        return sidecar_path if sidecar_path.exists() else None

    def validate_strategy_file_path(self, path: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a strategy file path is safe and within the strategies directory.

        Args:
            path: Strategy file path to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        strategy_dir = self.get_strategy_dir()
        path_obj = Path(path).resolve()

        # Check if path is within strategies directory
        try:
            path_obj.relative_to(strategy_dir.resolve())
        except ValueError:
            return False, f"Path is not within strategies directory: {path}"

        # Check if path is a .py file
        if path_obj.suffix != ".py":
            return False, f"Path is not a .py file: {path}"

        # Check for path traversal attempts
        if ".." in str(path):
            return False, f"Path contains traversal sequences: {path}"

        return True, None

    def validate_strategy_name(self, strategy_name: str) -> tuple[bool, Optional[str]]:
        """
        Validate that a strategy name is safe.

        Args:
            strategy_name: Strategy name to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not strategy_name:
            return False, "Strategy name cannot be empty"

        # Check for safe class-name style (alphanumeric with underscores/hyphens)
        if not re.match(r"^[a-zA-Z0-9_-]+$", strategy_name):
            return False, f"Strategy name must be alphanumeric with underscores/hyphens: {strategy_name}"

        # Check for path traversal
        if ".." in strategy_name or "/" in strategy_name or "\\" in strategy_name:
            return False, f"Strategy name contains invalid characters: {strategy_name}"

        return True, None

    def find_strategy_by_name(self, strategy_name: str) -> Optional[FreqtradeStrategyFile]:
        """
        Find a strategy by name in the strategies directory.

        Args:
            strategy_name: Strategy name to find

        Returns:
            Strategy file info if found, None otherwise
        """
        is_valid, error = self.validate_strategy_name(strategy_name)
        if not is_valid:
            return None

        strategy_dir = self.get_strategy_dir()
        py_path = strategy_dir / f"{strategy_name}.py"

        if not py_path.exists():
            return None

        sidecar_path = self.detect_sidecar_json(py_path)

        return FreqtradeStrategyFile(
            strategy_name=strategy_name,
            class_name=None,
            file_path=str(py_path),
            params_path=str(sidecar_path) if sidecar_path else None,
            exists=True,
            has_sidecar_json=sidecar_path is not None,
            source="file",
            errors=[],
            warnings=[f"Missing sidecar .json"] if not sidecar_path else [],
        )

    def list_strategies_via_freqtrade(self, config_path: Optional[str] = None) -> FreqtradeStrategyListResult:
        """
        List strategies using Freqtrade's list-strategies command.

        Args:
            config_path: Optional config path to use

        Returns:
            List result with strategies detected by Freqtrade
        """
        strategies = []
        errors = []
        warnings = []

        command = ["list-strategies"]
        if config_path:
            command.extend(["--config", config_path])
        else:
            command.extend(["--userdir", str(settings.freqtrade_user_data_dir_path)])

        result = self.command_runner.run(command)

        if not result.success:
            return FreqtradeStrategyListResult(
                strategies=[],
                freqtrade_visible=False,
                source="freqtrade",
                errors=[result.error or "Freqtrade command failed"],
            )

        # Parse Freqtrade output
        # Expected format: "StrategyName: ClassName"
        for line in result.stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue

            parts = line.split(":", 1)
            if len(parts) == 2:
                strategy_name = parts[0].strip()
                class_name = parts[1].strip()

                strategy_dir = self.get_strategy_dir()
                py_path = strategy_dir / f"{strategy_name}.py"
                sidecar_path = self.detect_sidecar_json(py_path)

                strategy = FreqtradeStrategyFile(
                    strategy_name=strategy_name,
                    class_name=class_name,
                    file_path=str(py_path) if py_path.exists() else None,
                    params_path=str(sidecar_path) if sidecar_path else None,
                    exists=py_path.exists(),
                    has_sidecar_json=sidecar_path is not None,
                    source="freqtrade",
                    errors=[],
                    warnings=[f"Missing sidecar .json"] if not sidecar_path else [],
                )
                strategies.append(strategy)

        return FreqtradeStrategyListResult(
            strategies=strategies,
            freqtrade_visible=True,
            source="freqtrade",
            errors=errors,
            warnings=warnings,
        )

    def get_strategy_status(
        self, strategy_name: str, config_path: Optional[str] = None
    ) -> FreqtradeStrategyStatus:
        """
        Get the status of a specific strategy.

        Args:
            strategy_name: Strategy name to check
            config_path: Optional config path for Freqtrade visibility check

        Returns:
            Strategy status
        """
        is_valid, error = self.validate_strategy_name(strategy_name)
        if not is_valid:
            return FreqtradeStrategyStatus(
                strategy_name=strategy_name,
                exists=False,
                freqtrade_visible=False,
                has_sidecar_json=False,
                file_path=None,
                params_path=None,
                source="file",
                errors=[error],
            )

        # Check file existence
        strategy = self.find_strategy_by_name(strategy_name)
        if not strategy:
            return FreqtradeStrategyStatus(
                strategy_name=strategy_name,
                exists=False,
                freqtrade_visible=False,
                has_sidecar_json=False,
                file_path=None,
                params_path=None,
                source="file",
                errors=[f"Strategy file not found: {strategy_name}.py"],
            )

        # Check Freqtrade visibility
        freqtrade_visible = False
        if config_path or settings.freqtrade_configured:
            try:
                result = self.list_strategies_via_freqtrade(config_path)
                freqtrade_visible = result.freqtrade_visible
                if freqtrade_visible:
                    freqtrade_visible = any(s.strategy_name == strategy_name for s in result.strategies)
            except Exception:
                freqtrade_visible = False

        return FreqtradeStrategyStatus(
            strategy_name=strategy_name,
            exists=strategy.exists,
            freqtrade_visible=freqtrade_visible,
            has_sidecar_json=strategy.has_sidecar_json,
            file_path=strategy.file_path,
            params_path=strategy.params_path,
            source=strategy.source,
            errors=strategy.errors,
            warnings=strategy.warnings,
        )
