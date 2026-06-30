"""
Safe static utilities for inspecting the local Freqtrade strategy workspace.

This module never imports strategy files, never executes strategy code, and
never calls Freqtrade. It only performs bounded file reads, JSON parsing, and
Python AST parsing inside the configured strategies directory.
"""
from __future__ import annotations

import ast
import json
import re
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Optional

from app.core.config import settings
from app.schemas.strategies import (
    StrategyDetail,
    StrategyIssue,
    StrategyParamsSummary,
    StrategyReadiness,
    StrategySummary,
)
from app.services.freqtrade_workspace import FreqtradeWorkspaceService


SAFE_EXTENSIONS = {".py", ".json"}
PARAM_SECTIONS = (
    "buy",
    "sell",
    "roi",
    "stoploss",
    "trailing",
    "protection",
    "max_open_trades",
    "timeframe",
)
SECRET_KEY_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "private_key",
    "app_secret",
    "discord_token",
    "exchange_key",
    "key",
)


class StrategyWorkspaceError(ValueError):
    """Raised when a workspace path or read operation is unsafe."""


class StrategyWorkspaceUtils:
    """Static, read-only inspection helpers for strategy workspace files."""

    MAX_TEXT_BYTES = 512 * 1024
    MAX_JSON_BYTES = 512 * 1024
    MAX_PREVIEW_ITEMS = 8
    STRATEGY_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

    def __init__(self, app_settings: Any = settings) -> None:
        self.settings = app_settings
        self.workspace_service = FreqtradeWorkspaceService(app_settings)

    @property
    def project_root(self) -> Path:
        """Return the configured project root."""
        return Path(self.settings.project_root).resolve()

    @property
    def strategy_dir(self) -> Path:
        """Return the configured strategies directory."""
        return self.workspace_service.get_strategy_dir().resolve()

    def validate_strategy_name(self, strategy_name: str) -> str:
        """Validate a strategy name as a deterministic filename stem."""
        cleaned = strategy_name.strip()
        if not cleaned:
            raise StrategyWorkspaceError("strategy_name must not be empty")
        if not self.STRATEGY_NAME_PATTERN.match(cleaned):
            raise StrategyWorkspaceError("strategy_name must be alphanumeric with underscores or hyphens")
        if ".." in cleaned or "/" in cleaned or "\\" in cleaned:
            raise StrategyWorkspaceError("strategy_name must be a safe path segment")
        return cleaned

    def strategy_py_path(self, strategy_name: str) -> Path:
        """Return the deterministic `{StrategyName}.py` path."""
        safe_name = self.validate_strategy_name(strategy_name)
        return self.validate_workspace_file_path(self.strategy_dir / f"{safe_name}.py", expected_suffix=".py")

    def strategy_json_path(self, strategy_name: str) -> Path:
        """Return the deterministic `{StrategyName}.json` path."""
        safe_name = self.validate_strategy_name(strategy_name)
        return self.validate_workspace_file_path(self.strategy_dir / f"{safe_name}.json", expected_suffix=".json")

    def resolve_project_relative_path(self, relative_path: str, expected_suffix: Optional[str] = None) -> Path:
        """
        Resolve a project-relative path and ensure it stays in the strategy workspace.

        Absolute input paths and traversal are rejected. This method is for
        user/API-supplied paths; deterministic strategy name helpers build paths
        directly from validated names.
        """
        cleaned = relative_path.strip()
        if not cleaned:
            raise StrategyWorkspaceError("path must not be empty")

        posix_path = PurePosixPath(cleaned)
        if posix_path.is_absolute() or ".." in posix_path.parts:
            raise StrategyWorkspaceError("path must be project-relative and must not contain traversal")

        return self.validate_workspace_file_path(self.project_root / cleaned, expected_suffix=expected_suffix)

    def validate_workspace_file_path(self, path: Path | str, expected_suffix: Optional[str] = None) -> Path:
        """Validate that a path is a supported file under the strategies directory."""
        path_obj = Path(path)
        resolved = path_obj.resolve(strict=False)

        try:
            resolved.relative_to(self.strategy_dir)
        except ValueError as exc:
            raise StrategyWorkspaceError("path must stay inside the configured strategies directory") from exc

        suffix = resolved.suffix.lower()
        if suffix not in SAFE_EXTENSIONS:
            raise StrategyWorkspaceError("only .py and .json strategy workspace files are allowed")
        if expected_suffix and suffix != expected_suffix:
            raise StrategyWorkspaceError(f"path must be a {expected_suffix} file")

        return resolved

    def project_relative_path(self, path: Path | str) -> str:
        """Return a project-relative POSIX path after containment validation."""
        resolved = Path(path).resolve(strict=False)
        try:
            relative = resolved.relative_to(self.project_root)
        except ValueError as exc:
            raise StrategyWorkspaceError("path must stay inside the project root") from exc
        return relative.as_posix()

    def safe_read_text(self, path: Path | str, max_bytes: Optional[int] = None) -> str:
        """Read text from a validated workspace file with a strict size limit."""
        resolved = self.validate_workspace_file_path(path)
        byte_limit = max_bytes or self.MAX_TEXT_BYTES

        if not resolved.exists() or not resolved.is_file():
            raise StrategyWorkspaceError(f"file does not exist: {self.project_relative_path(resolved)}")

        size = resolved.stat().st_size
        if size > byte_limit:
            raise StrategyWorkspaceError(f"file exceeds size limit of {byte_limit} bytes")

        payload = resolved.read_bytes()
        if len(payload) > byte_limit:
            raise StrategyWorkspaceError(f"file exceeds size limit of {byte_limit} bytes")

        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StrategyWorkspaceError("file must be valid UTF-8 text") from exc

    def safe_read_json(self, path: Path | str) -> dict[str, Any]:
        """Read and parse a JSON object from a validated sidecar file."""
        resolved = self.validate_workspace_file_path(path, expected_suffix=".json")
        text = self.safe_read_text(resolved, max_bytes=self.MAX_JSON_BYTES)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise StrategyWorkspaceError(f"malformed JSON: {exc.msg}") from exc

        if not isinstance(data, dict):
            raise StrategyWorkspaceError("sidecar JSON must be a top-level object")
        return self.sanitize_secret_like(data)

    def list_strategy_names(self) -> list[str]:
        """List deterministic strategy names from local `*.py` files."""
        if not self.strategy_dir.exists() or not self.strategy_dir.is_dir():
            return []
        names = []
        for py_path in sorted(self.strategy_dir.glob("*.py")):
            if py_path.name.startswith("__"):
                continue
            names.append(py_path.stem)
        return names

    def build_strategy_summary(self, strategy_name: str) -> StrategySummary:
        """Build a static strategy summary from deterministic workspace files."""
        detail = self.build_strategy_detail(strategy_name)
        return StrategySummary(**detail.model_dump())

    def build_strategy_detail(self, strategy_name: str) -> StrategyDetail:
        """Build a static strategy detail without importing or executing code."""
        issues: list[StrategyIssue] = []
        warnings: list[str] = []
        metadata: dict[str, Any] = {}
        static_checks: dict[str, bool] = {}
        syntax_valid = False
        class_name: Optional[str] = None

        try:
            safe_name = self.validate_strategy_name(strategy_name)
            strategy_path = self.strategy_py_path(safe_name)
            sidecar_path = self.strategy_json_path(safe_name)
        except StrategyWorkspaceError as exc:
            issue = self._issue("unsafe_path", "critical", str(exc), {"strategy_name": strategy_name})
            return self._unsafe_detail(strategy_name, issue)

        if not strategy_path.exists():
            issues.append(self._issue("strategy_file_missing", "error", "Strategy file is missing"))
            return self._detail(
                strategy_name=safe_name,
                strategy_path=strategy_path,
                sidecar_path=sidecar_path if sidecar_path.exists() else None,
                readiness=StrategyReadiness.INVALID,
                issues=issues,
                warnings=warnings,
                metadata=metadata,
                params_summary=StrategyParamsSummary(strategy_name=safe_name),
                class_name=None,
                syntax_valid=False,
                static_checks={},
            )

        try:
            source_text = self.safe_read_text(strategy_path)
        except StrategyWorkspaceError as exc:
            issues.append(self._issue("strategy_read_error", "error", str(exc)))
            return self._detail(
                strategy_name=safe_name,
                strategy_path=strategy_path,
                sidecar_path=sidecar_path if sidecar_path.exists() else None,
                readiness=StrategyReadiness.UNSAFE,
                issues=issues,
                warnings=warnings,
                metadata=metadata,
                params_summary=StrategyParamsSummary(strategy_name=safe_name),
                class_name=None,
                syntax_valid=False,
                static_checks={},
            )

        try:
            tree = ast.parse(source_text, filename=str(strategy_path))
            syntax_valid = True
            metadata = self.extract_strategy_metadata(tree, safe_name)
            class_name = metadata.get("class_name")
            static_checks = self._static_checks(metadata)
        except SyntaxError as exc:
            issues.append(
                self._issue(
                    "python_syntax_error",
                    "error",
                    "Strategy Python syntax is invalid",
                    {"lineno": exc.lineno, "offset": exc.offset, "message": exc.msg},
                )
            )
            metadata = self.extract_strategy_metadata_from_text(source_text, safe_name)
            class_name = metadata.get("class_name")
            readiness = StrategyReadiness.PARSE_ERROR
            params_summary = self.parse_params_summary(safe_name, sidecar_path)
            return self._detail(
                strategy_name=safe_name,
                strategy_path=strategy_path,
                sidecar_path=sidecar_path if sidecar_path.exists() else None,
                readiness=readiness,
                issues=issues + params_summary.issues,
                warnings=warnings + params_summary.warnings,
                metadata=metadata,
                params_summary=params_summary,
                class_name=class_name,
                syntax_valid=False,
                static_checks={},
            )

        if not metadata.get("has_strategy_class"):
            issues.append(self._issue("strategy_class_missing", "error", "No matching strategy class or IStrategy subclass found"))
        if not metadata.get("has_populate_indicators"):
            issues.append(self._issue("populate_indicators_missing", "error", "populate_indicators method is missing"))
        if not metadata.get("has_entry_method"):
            issues.append(self._issue("entry_method_missing", "error", "populate_entry_trend or populate_buy_trend method is missing"))
        if not metadata.get("has_exit_method"):
            issues.append(self._issue("exit_method_missing", "error", "populate_exit_trend or populate_sell_trend method is missing"))

        params_summary = self.parse_params_summary(safe_name, sidecar_path)
        issues.extend(params_summary.issues)
        warnings.extend(params_summary.warnings)

        readiness = self._readiness_from_issues(issues, params_summary.exists)

        return self._detail(
            strategy_name=safe_name,
            strategy_path=strategy_path,
            sidecar_path=sidecar_path if sidecar_path.exists() else None,
            readiness=readiness,
            issues=issues,
            warnings=warnings,
            metadata=metadata,
            params_summary=params_summary,
            class_name=class_name,
            syntax_valid=syntax_valid,
            static_checks=static_checks,
        )

    def extract_strategy_metadata(self, tree: ast.AST, strategy_name: str) -> dict[str, Any]:
        """Extract strategy metadata from an AST without executing code."""
        class_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]
        selected_class: Optional[ast.ClassDef] = None

        for class_node in class_nodes:
            if class_node.name == strategy_name or self._inherits_istrategy(class_node):
                selected_class = class_node
                break

        metadata: dict[str, Any] = {
            "file_name": f"{strategy_name}.py",
            "apparent_strategy_name": strategy_name,
            "class_name": selected_class.name if selected_class else None,
            "has_strategy_class": selected_class is not None,
            "inherits_istrategy": self._inherits_istrategy(selected_class) if selected_class else False,
            "timeframe": None,
            "can_short": None,
            "has_minimal_roi": False,
            "has_stoploss": False,
            "has_trailing_fields": False,
            "has_buy_params": False,
            "has_sell_params": False,
            "has_populate_indicators": False,
            "has_entry_method": False,
            "has_exit_method": False,
        }

        if not selected_class:
            return metadata

        trailing_names = {
            "trailing_stop",
            "trailing_stop_positive",
            "trailing_stop_positive_offset",
            "trailing_only_offset_is_reached",
        }
        class_assignments: dict[str, ast.AST] = {}

        for node in selected_class.body:
            if isinstance(node, (ast.Assign, ast.AnnAssign)):
                targets = node.targets if isinstance(node, ast.Assign) else [node.target]
                for target in targets:
                    if isinstance(target, ast.Name):
                        class_assignments[target.id] = node.value
            elif isinstance(node, ast.FunctionDef):
                if node.name == "populate_indicators":
                    metadata["has_populate_indicators"] = True
                if node.name in {"populate_entry_trend", "populate_buy_trend"}:
                    metadata["has_entry_method"] = True
                if node.name in {"populate_exit_trend", "populate_sell_trend"}:
                    metadata["has_exit_method"] = True

        metadata["timeframe"] = self._literal_value(class_assignments.get("timeframe"))
        metadata["can_short"] = self._literal_value(class_assignments.get("can_short"))
        metadata["has_minimal_roi"] = "minimal_roi" in class_assignments
        metadata["has_stoploss"] = "stoploss" in class_assignments
        metadata["has_trailing_fields"] = any(name in class_assignments for name in trailing_names)
        metadata["has_buy_params"] = any("buy" in name.lower() and name.lower().endswith("params") for name in class_assignments)
        metadata["has_sell_params"] = any("sell" in name.lower() and name.lower().endswith("params") for name in class_assignments)

        return metadata

    def extract_strategy_metadata_from_text(self, source_text: str, strategy_name: str) -> dict[str, Any]:
        """Best-effort text metadata used only after AST parse failure."""
        return {
            "file_name": f"{strategy_name}.py",
            "apparent_strategy_name": strategy_name,
            "class_name": strategy_name if f"class {strategy_name}" in source_text else None,
            "has_strategy_class": f"class {strategy_name}" in source_text or "IStrategy" in source_text,
            "inherits_istrategy": "IStrategy" in source_text,
            "timeframe": self._extract_text_assignment(source_text, "timeframe"),
            "can_short": None,
            "has_minimal_roi": "minimal_roi" in source_text,
            "has_stoploss": "stoploss" in source_text,
            "has_trailing_fields": "trailing_stop" in source_text,
            "has_buy_params": "buy_params" in source_text,
            "has_sell_params": "sell_params" in source_text,
            "has_populate_indicators": "def populate_indicators" in source_text,
            "has_entry_method": "def populate_entry_trend" in source_text or "def populate_buy_trend" in source_text,
            "has_exit_method": "def populate_exit_trend" in source_text or "def populate_sell_trend" in source_text,
        }

    def parse_params_summary(self, strategy_name: str, sidecar_path: Optional[Path] = None) -> StrategyParamsSummary:
        """Parse and summarize a strategy sidecar JSON file safely."""
        safe_name = self.validate_strategy_name(strategy_name)
        json_path = sidecar_path or self.strategy_json_path(safe_name)
        relative_path = self.project_relative_path(json_path)

        if not json_path.exists():
            issue = self._issue("sidecar_missing", "warning", "Strategy sidecar JSON is missing")
            return StrategyParamsSummary(
                strategy_name=safe_name,
                sidecar_json_path=None,
                exists=False,
                parse_success=False,
                issues=[issue],
                warnings=["Strategy missing sidecar .json file"],
            )

        try:
            data = self.safe_read_json(json_path)
        except StrategyWorkspaceError as exc:
            return StrategyParamsSummary(
                strategy_name=safe_name,
                sidecar_json_path=relative_path,
                exists=True,
                parse_success=False,
                issues=[self._issue("sidecar_parse_error", "error", str(exc))],
            )

        sections_present = [section for section in PARAM_SECTIONS if section in data]
        section_counts = {
            section: self._count_section(data.get(section))
            for section in sections_present
        }
        preview = {
            section: self._preview_value(data.get(section))
            for section in sections_present
        }

        return StrategyParamsSummary(
            strategy_name=safe_name,
            sidecar_json_path=relative_path,
            exists=True,
            parse_success=True,
            sections_present=sections_present,
            section_counts=section_counts,
            timeframe=data.get("timeframe") if isinstance(data.get("timeframe"), str) else None,
            max_open_trades=data.get("max_open_trades") if isinstance(data.get("max_open_trades"), int) else None,
            preview=preview,
        )

    def sanitize_secret_like(self, value: Any) -> Any:
        """Redact values under obvious secret-like keys in nested JSON."""
        if isinstance(value, dict):
            sanitized: dict[str, Any] = {}
            for key, item in value.items():
                key_lower = str(key).lower()
                if self._is_secret_like_key(key_lower):
                    sanitized[key] = "[REDACTED]"
                else:
                    sanitized[key] = self.sanitize_secret_like(item)
            return sanitized
        if isinstance(value, list):
            return [self.sanitize_secret_like(item) for item in value]
        return value

    def _detail(
        self,
        strategy_name: str,
        strategy_path: Path,
        sidecar_path: Optional[Path],
        readiness: StrategyReadiness,
        issues: list[StrategyIssue],
        warnings: list[str],
        metadata: dict[str, Any],
        params_summary: StrategyParamsSummary,
        class_name: Optional[str],
        syntax_valid: bool,
        static_checks: dict[str, bool],
    ) -> StrategyDetail:
        updated_at = None
        if strategy_path.exists():
            updated_at = datetime.fromtimestamp(strategy_path.stat().st_mtime, tz=timezone.utc).isoformat()

        return StrategyDetail(
            strategy_name=strategy_name,
            strategy_file_path=self.project_relative_path(strategy_path),
            sidecar_json_path=self.project_relative_path(sidecar_path) if sidecar_path else None,
            has_sidecar=sidecar_path is not None,
            readiness=readiness,
            issues=issues,
            warnings=warnings,
            metadata=metadata,
            params_summary=params_summary,
            updated_at=updated_at,
            class_name=class_name,
            file_name=strategy_path.name,
            apparent_strategy_name=strategy_name,
            syntax_valid=syntax_valid,
            static_checks=static_checks,
        )

    def _unsafe_detail(self, strategy_name: str, issue: StrategyIssue) -> StrategyDetail:
        return StrategyDetail(
            strategy_name=strategy_name,
            strategy_file_path="freqtrade_workspace/user_data/strategies/invalid.py",
            sidecar_json_path=None,
            has_sidecar=False,
            readiness=StrategyReadiness.UNSAFE,
            issues=[issue],
            warnings=[],
            metadata={},
            params_summary=StrategyParamsSummary(strategy_name=strategy_name),
            updated_at=None,
            class_name=None,
            file_name="invalid.py",
            apparent_strategy_name=strategy_name,
            syntax_valid=False,
            static_checks={},
        )

    def _readiness_from_issues(self, issues: list[StrategyIssue], params_exists: bool) -> StrategyReadiness:
        codes = {issue.code for issue in issues}
        severities = {issue.severity for issue in issues}

        if "sidecar_parse_error" in codes or "python_syntax_error" in codes:
            return StrategyReadiness.PARSE_ERROR
        if not params_exists:
            return StrategyReadiness.MISSING_SIDECAR
        if "critical" in severities:
            return StrategyReadiness.UNSAFE
        if "error" in severities:
            return StrategyReadiness.INVALID
        if "warning" in severities:
            return StrategyReadiness.WARNING
        return StrategyReadiness.READY

    def _static_checks(self, metadata: dict[str, Any]) -> dict[str, bool]:
        return {
            "has_strategy_class": bool(metadata.get("has_strategy_class")),
            "has_populate_indicators": bool(metadata.get("has_populate_indicators")),
            "has_entry_method": bool(metadata.get("has_entry_method")),
            "has_exit_method": bool(metadata.get("has_exit_method")),
            "has_minimal_roi": bool(metadata.get("has_minimal_roi")),
            "has_stoploss": bool(metadata.get("has_stoploss")),
        }

    @staticmethod
    def _inherits_istrategy(class_node: Optional[ast.ClassDef]) -> bool:
        if class_node is None:
            return False
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id == "IStrategy":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "IStrategy":
                return True
        return False

    @staticmethod
    def _literal_value(node: Optional[ast.AST]) -> Any:
        if node is None:
            return None
        try:
            return ast.literal_eval(node)
        except (ValueError, SyntaxError):
            return None

    @staticmethod
    def _extract_text_assignment(source_text: str, name: str) -> Optional[str]:
        match = re.search(rf"^\s*{re.escape(name)}\s*=\s*['\"]([^'\"]+)['\"]", source_text, flags=re.MULTILINE)
        return match.group(1) if match else None

    def _preview_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {
                key: self.sanitize_secret_like(item)
                for key, item in list(value.items())[: self.MAX_PREVIEW_ITEMS]
            }
        if isinstance(value, list):
            return self.sanitize_secret_like(value[: self.MAX_PREVIEW_ITEMS])
        return self.sanitize_secret_like(value)

    @staticmethod
    def _count_section(value: Any) -> int:
        if isinstance(value, dict):
            return len(value)
        if isinstance(value, list):
            return len(value)
        if value is None:
            return 0
        return 1

    @staticmethod
    def _issue(
        code: str,
        severity: str,
        message: str,
        details: Optional[dict[str, Any]] = None,
    ) -> StrategyIssue:
        return StrategyIssue(
            code=code,
            severity=severity,
            message=message,
            details=details or {},
        )

    @staticmethod
    def _is_secret_like_key(key_lower: str) -> bool:
        return (
            key_lower in SECRET_KEY_MARKERS
            or key_lower.endswith("_key")
            or key_lower.endswith("-key")
            or "secret" in key_lower
            or "token" in key_lower
            or "password" in key_lower
        )
