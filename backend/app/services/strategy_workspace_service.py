"""
Read-only strategy workspace service for Part 11.

The service scans local strategy files, computes readiness, and adds
conservative safety issues without importing strategies or executing Freqtrade.
"""
from __future__ import annotations

import ast
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.schemas.strategies import (
    StrategyDetail,
    StrategyImportRequest,
    StrategyImportResult,
    StrategyIssue,
    StrategyParamsSummary,
    StrategyReadiness,
    StrategySummary,
)
from app.services.strategy_workspace_utils import (
    StrategyWorkspaceError,
    StrategyWorkspaceUtils,
)


IGNORED_PREFIXES = ("_", ".")
IGNORED_NAME_PARTS = (
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
)
RUNTIME_NAME_SUFFIXES = (
    "_backup",
    "_baseline_backup",
)
PARAM_WARNING_SECTIONS = ("buy", "sell")
SECRET_MARKERS = (
    "api_key",
    "apikey",
    "secret",
    "password",
    "token",
    "private_key",
    "exchange_key",
)


class StrategyWorkspaceService:
    """Backend service for static strategy workspace inspection."""

    def __init__(
        self,
        utils: Optional[StrategyWorkspaceUtils] = None,
        app_settings: Any = settings,
    ) -> None:
        self.utils = utils or StrategyWorkspaceUtils(app_settings)

    @property
    def strategy_dir(self) -> Path:
        """Return the configured strategy directory."""
        return self.utils.strategy_dir

    def list_strategies(self) -> list[StrategySummary]:
        """Return readiness summaries for all visible local strategy files."""
        if not self.strategy_dir.exists() or not self.strategy_dir.is_dir():
            return []

        summaries: list[StrategySummary] = []
        for py_path in sorted(self.strategy_dir.glob("*.py")):
            if self._should_ignore_strategy_file(py_path):
                continue
            detail = self.get_strategy(py_path.stem)
            summaries.append(StrategySummary(**detail.model_dump()))

        return summaries

    def get_strategy(self, strategy_name: str) -> StrategyDetail:
        """Return full static detail for one strategy name."""
        detail = self.utils.build_strategy_detail(strategy_name)
        if detail.readiness == StrategyReadiness.UNSAFE:
            return detail

        safety_issues = self._inspect_safety_patterns(detail.strategy_name)
        params_issues = self._params_completeness_issues(detail.params_summary)
        combined_issues = self._dedupe_issues(detail.issues + safety_issues + params_issues)
        combined_warnings = self._dedupe_warnings(
            detail.warnings
            + [issue.message for issue in safety_issues + params_issues if issue.severity == "warning"]
        )

        return detail.model_copy(
            update={
                "issues": combined_issues,
                "warnings": combined_warnings,
                "readiness": self._compute_readiness(detail, combined_issues),
            }
        )

    def get_strategy_params(self, strategy_name: str) -> StrategyParamsSummary:
        """Return a safe summary of one strategy sidecar JSON file."""
        safe_name = self.utils.validate_strategy_name(strategy_name)
        return self.utils.parse_params_summary(safe_name)

    def validate_strategy(self, strategy_name: str) -> StrategyDetail:
        """Alias for full static strategy validation detail."""
        return self.get_strategy(strategy_name)

    def resolve_strategy_for_run(self, strategy_name: str) -> StrategyDetail:
        """
        Resolve a strategy for baseline/optimization run usage.

        This does not start any run. It returns the same static detail so callers
        can decide which readiness states are allowed for their workflow.
        """
        return self.get_strategy(strategy_name)

    def import_strategy(self, request: StrategyImportRequest) -> StrategyImportResult:
        """
        Import a project-relative strategy file into the configured workspace.

        This method copies files only after static validation succeeds and only
        when the destination does not already exist. It never imports or
        executes strategy code and it never overwrites existing strategy files.
        """
        issues: list[StrategyIssue] = []
        warnings: list[str] = []

        try:
            source_path = self._resolve_import_source(request.source_path, ".py")
            strategy_name = self.utils.validate_strategy_name(request.strategy_name or source_path.stem)
            sidecar_source_path = self._resolve_sidecar_source(request, source_path)
            target_py_path = self.utils.strategy_py_path(strategy_name)
            target_json_path = self.utils.strategy_json_path(strategy_name)
        except StrategyWorkspaceError as exc:
            return StrategyImportResult(
                success=False,
                imported=False,
                strategy_name=request.strategy_name,
                readiness=StrategyReadiness.UNSAFE,
                issues=[self._issue("unsafe_import_path", "critical", str(exc))],
            )

        source_issue = self._validate_import_strategy_source(source_path, strategy_name)
        if source_issue:
            return StrategyImportResult(
                success=False,
                imported=False,
                strategy_name=strategy_name,
                readiness=StrategyReadiness.PARSE_ERROR if source_issue.code == "python_syntax_error" else StrategyReadiness.INVALID,
                issues=[source_issue],
            )

        if sidecar_source_path:
            sidecar_issue = self._validate_import_sidecar_source(sidecar_source_path)
            if sidecar_issue:
                return StrategyImportResult(
                    success=False,
                    imported=False,
                    strategy_name=strategy_name,
                    readiness=StrategyReadiness.PARSE_ERROR,
                    issues=[sidecar_issue],
                )

        existing_files = self._existing_import_targets(target_py_path, target_json_path)
        if existing_files:
            return StrategyImportResult(
                success=False,
                imported=False,
                conflict=True,
                strategy_name=strategy_name,
                strategy_file_path=self.utils.project_relative_path(target_py_path),
                sidecar_json_path=self.utils.project_relative_path(target_json_path) if sidecar_source_path else None,
                readiness=self.get_strategy(strategy_name).readiness if target_py_path.exists() else None,
                issues=[
                    self._issue(
                        "import_target_conflict",
                        "error",
                        "Strategy import target already exists; overwrite is not performed in Part 11",
                        {"overwrite_confirmed": request.overwrite_confirmed},
                    )
                ],
                warnings=["Existing strategy files were left unchanged"],
                existing_files=existing_files,
            )

        target_py_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, target_py_path)
        if sidecar_source_path:
            shutil.copy2(sidecar_source_path, target_json_path)
        else:
            warnings.append("No sidecar JSON imported")

        detail = self.get_strategy(strategy_name)
        return StrategyImportResult(
            success=True,
            imported=True,
            conflict=False,
            strategy_name=strategy_name,
            strategy_file_path=detail.strategy_file_path,
            sidecar_json_path=detail.sidecar_json_path,
            readiness=detail.readiness,
            issues=detail.issues,
            warnings=warnings + detail.warnings,
            detail=detail,
        )

    def _should_ignore_strategy_file(self, path: Path) -> bool:
        name = path.name
        stem = path.stem
        if name.startswith(IGNORED_PREFIXES):
            return True
        if any(part in path.parts for part in IGNORED_NAME_PARTS):
            return True
        if stem.endswith(RUNTIME_NAME_SUFFIXES):
            return True
        return False

    def _resolve_import_source(self, source_path: str, expected_suffix: str) -> Path:
        cleaned = source_path.strip()
        if not cleaned:
            raise StrategyWorkspaceError("source path must not be empty")
        source_posix = Path(cleaned)
        if source_posix.is_absolute() or ".." in source_posix.parts:
            raise StrategyWorkspaceError("source path must be project-relative and must not contain traversal")

        resolved = (self.utils.project_root / cleaned).resolve(strict=False)
        try:
            resolved.relative_to(self.utils.project_root)
        except ValueError as exc:
            raise StrategyWorkspaceError("source path must stay inside the project root") from exc

        if resolved.suffix.lower() != expected_suffix:
            raise StrategyWorkspaceError(f"source path must be a {expected_suffix} file")
        if not resolved.exists() or not resolved.is_file():
            raise StrategyWorkspaceError("source file does not exist")
        return resolved

    def _resolve_sidecar_source(
        self,
        request: StrategyImportRequest,
        source_path: Path,
    ) -> Optional[Path]:
        if request.sidecar_source_path:
            return self._resolve_import_source(request.sidecar_source_path, ".json")

        adjacent_sidecar = source_path.with_suffix(".json")
        if adjacent_sidecar.exists() and adjacent_sidecar.is_file():
            try:
                adjacent_sidecar.relative_to(self.utils.project_root)
            except ValueError as exc:
                raise StrategyWorkspaceError("adjacent sidecar must stay inside the project root") from exc
            return adjacent_sidecar
        return None

    def _validate_import_strategy_source(
        self,
        source_path: Path,
        strategy_name: str,
    ) -> Optional[StrategyIssue]:
        try:
            source_text = self._safe_read_import_text(source_path, self.utils.MAX_TEXT_BYTES)
            tree = ast.parse(source_text, filename=str(source_path))
        except SyntaxError as exc:
            return self._issue(
                "python_syntax_error",
                "error",
                "Imported strategy Python syntax is invalid",
                {"lineno": exc.lineno, "offset": exc.offset, "message": exc.msg},
            )
        except StrategyWorkspaceError as exc:
            return self._issue("unsafe_import_read", "critical", str(exc))

        metadata = self.utils.extract_strategy_metadata(tree, strategy_name)
        if not metadata.get("has_strategy_class"):
            return self._issue(
                "strategy_class_missing",
                "error",
                "Imported strategy does not define the requested strategy class or an IStrategy subclass",
            )
        return None

    def _validate_import_sidecar_source(self, sidecar_source_path: Path) -> Optional[StrategyIssue]:
        try:
            source_text = self._safe_read_import_text(sidecar_source_path, self.utils.MAX_JSON_BYTES)
            data = self.utils.sanitize_secret_like(json.loads(source_text))
        except json.JSONDecodeError as exc:
            return self._issue(
                "sidecar_parse_error",
                "error",
                "Imported sidecar JSON is malformed",
                {"message": exc.msg, "lineno": exc.lineno, "colno": exc.colno},
            )
        except StrategyWorkspaceError as exc:
            return self._issue("unsafe_sidecar_read", "critical", str(exc))
        if not isinstance(data, dict):
            return self._issue("sidecar_parse_error", "error", "Imported sidecar JSON must be a top-level object")
        return None

    def _safe_read_import_text(self, path: Path, max_bytes: int) -> str:
        size = path.stat().st_size
        if size > max_bytes:
            raise StrategyWorkspaceError(f"source file exceeds size limit of {max_bytes} bytes")
        payload = path.read_bytes()
        if len(payload) > max_bytes:
            raise StrategyWorkspaceError(f"source file exceeds size limit of {max_bytes} bytes")
        try:
            return payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise StrategyWorkspaceError("source file must be valid UTF-8 text") from exc

    def _existing_import_targets(self, target_py_path: Path, target_json_path: Path) -> dict[str, str]:
        existing: dict[str, str] = {}
        if target_py_path.exists():
            existing["strategy_file_path"] = self.utils.project_relative_path(target_py_path)
        if target_json_path.exists():
            existing["sidecar_json_path"] = self.utils.project_relative_path(target_json_path)
        return existing

    def _inspect_safety_patterns(self, strategy_name: str) -> list[StrategyIssue]:
        try:
            strategy_path = self.utils.strategy_py_path(strategy_name)
            source_text = self.utils.safe_read_text(strategy_path)
        except StrategyWorkspaceError as exc:
            return [
                self._issue(
                    "unsafe_strategy_read",
                    "critical",
                    str(exc),
                    {"strategy_name": strategy_name},
                )
            ]

        issues: list[StrategyIssue] = []
        try:
            tree = ast.parse(source_text, filename=str(strategy_path))
        except SyntaxError:
            return issues

        imported_modules = self._imported_modules(tree)
        suspicious_imports = sorted(
            module
            for module in imported_modules
            if module.split(".", 1)[0] in {"subprocess", "requests", "urllib", "socket", "ccxt", "ftplib", "httpx"}
        )
        if suspicious_imports:
            issues.append(
                self._issue(
                    "suspicious_import",
                    "warning",
                    "Strategy imports modules that may perform process, network, or exchange operations",
                    {"imports": suspicious_imports},
                )
            )

        call_names = [self._call_name(node) for node in ast.walk(tree) if isinstance(node, ast.Call)]
        call_names = [name for name in call_names if name]

        dangerous_calls = sorted(
            {
                name
                for name in call_names
                if name in {"os.system", "subprocess.run", "subprocess.Popen", "subprocess.call", "subprocess.check_call", "subprocess.check_output"}
            }
        )
        if dangerous_calls:
            issues.append(
                self._issue(
                    "dangerous_process_call",
                    "critical",
                    "Strategy contains process execution calls",
                    {"calls": dangerous_calls},
                )
            )

        network_calls = sorted(
            {
                name
                for name in call_names
                if name.startswith(("requests.", "urllib.", "socket.", "httpx.", "ccxt."))
            }
        )
        if network_calls:
            issues.append(
                self._issue(
                    "network_call",
                    "critical",
                    "Strategy contains network or exchange call patterns",
                    {"calls": network_calls},
                )
            )

        write_calls = sorted(
            {
                name
                for name in call_names
                if name in {"write_text", "write_bytes", "Path.write_text", "Path.write_bytes"}
                or name.endswith(".write_text")
                or name.endswith(".write_bytes")
            }
        )
        if write_calls or self._has_write_mode_open_call(tree):
            issues.append(
                self._issue(
                    "file_write_pattern",
                    "critical",
                    "Strategy contains file write patterns",
                    {"calls": write_calls},
                )
            )

        text_lower = source_text.lower()
        if "freqtrade trade" in text_lower:
            issues.append(
                self._issue(
                    "freqtrade_trade_reference",
                    "critical",
                    "Strategy source references freqtrade trade",
                )
            )

        secret_markers = sorted(marker for marker in SECRET_MARKERS if marker in text_lower)
        if secret_markers:
            issues.append(
                self._issue(
                    "secret_like_text",
                    "warning",
                    "Strategy source contains secret-like field names",
                    {"markers": secret_markers},
                )
            )

        return issues

    def _params_completeness_issues(self, params_summary: StrategyParamsSummary) -> list[StrategyIssue]:
        if not params_summary.exists or not params_summary.parse_success:
            return []

        missing_sections = [
            section
            for section in PARAM_WARNING_SECTIONS
            if section not in params_summary.sections_present
        ]
        if not missing_sections:
            return []

        return [
            self._issue(
                "params_sections_incomplete",
                "warning",
                "Strategy sidecar JSON is missing common buy/sell parameter sections",
                {"missing_sections": missing_sections},
            )
        ]

    def _compute_readiness(
        self,
        detail: StrategyDetail,
        issues: list[StrategyIssue],
    ) -> StrategyReadiness:
        codes = {issue.code for issue in issues}
        severities = {issue.severity for issue in issues}

        if "critical" in severities:
            return StrategyReadiness.UNSAFE
        if "python_syntax_error" in codes or "sidecar_parse_error" in codes:
            return StrategyReadiness.PARSE_ERROR
        if "sidecar_missing" in codes:
            return StrategyReadiness.MISSING_SIDECAR
        if "error" in severities:
            return StrategyReadiness.INVALID
        if "warning" in severities:
            return StrategyReadiness.WARNING
        return detail.readiness

    @staticmethod
    def _imported_modules(tree: ast.AST) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
        return modules

    @staticmethod
    def _call_name(node: ast.Call) -> Optional[str]:
        func = node.func
        if isinstance(func, ast.Name):
            return func.id
        if isinstance(func, ast.Attribute):
            parts = [func.attr]
            value = func.value
            while isinstance(value, ast.Attribute):
                parts.append(value.attr)
                value = value.value
            if isinstance(value, ast.Name):
                parts.append(value.id)
            return ".".join(reversed(parts))
        return None

    @staticmethod
    def _has_write_mode_open_call(tree: ast.AST) -> bool:
        write_modes = {"w", "a", "x", "w+", "a+", "x+", "wb", "ab", "xb"}
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if StrategyWorkspaceService._call_name(node) != "open":
                continue
            mode_node = None
            if len(node.args) >= 2:
                mode_node = node.args[1]
            for keyword in node.keywords:
                if keyword.arg == "mode":
                    mode_node = keyword.value
            if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
                if mode_node.value in write_modes or any(flag in mode_node.value for flag in ("w", "a", "x")):
                    return True
        return False

    @staticmethod
    def _dedupe_issues(issues: list[StrategyIssue]) -> list[StrategyIssue]:
        seen: set[tuple[str, str]] = set()
        deduped: list[StrategyIssue] = []
        for issue in issues:
            key = (issue.code, issue.message)
            if key in seen:
                continue
            seen.add(key)
            deduped.append(issue)
        return deduped

    @staticmethod
    def _dedupe_warnings(warnings: list[str]) -> list[str]:
        return list(dict.fromkeys(warnings))

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
