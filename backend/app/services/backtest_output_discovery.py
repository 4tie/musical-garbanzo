"""
Backtest output discovery service.

This service locates raw Freqtrade backtest output files for a HER run without
reading or parsing metrics. It is intentionally limited to project-owned paths.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.schemas.backtest_results import (
    BacktestOutputDiscoveryResult,
    BacktestOutputFile,
)


class BacktestOutputDiscoveryService:
    """Discover raw Freqtrade backtest outputs for a run."""

    RESULT_FILE_TYPES = {"json", "zip"}
    DISCOVERABLE_ARTIFACT_TYPES = {"backtest_raw", "log_file"}
    SHELL_SAFE_RUN_ID = re.compile(r"^[A-Za-z0-9_.-]+$")

    def __init__(
        self,
        artifact_repository: Optional[ArtifactRepository] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.artifact_repository = artifact_repository or ArtifactRepository()
        self.project_root = (project_root or settings.project_root).resolve()
        self._warnings: list[str] = []
        self._errors: list[str] = []

    def get_run_raw_freqtrade_dir(self, run_id: str) -> Path:
        """Return the Part 04 raw Freqtrade artifact directory for a run."""
        return self.project_root / "artifacts" / "runs" / self._safe_run_id(run_id) / "raw_freqtrade"

    def get_run_backtest_results_dir(self, run_id: str) -> Path:
        """Return the Part 04 run-specific backtest result artifact directory."""
        return self.get_run_raw_freqtrade_dir(run_id) / "backtest_results"

    def discover_outputs(self, run_id: str) -> BacktestOutputDiscoveryResult:
        """Discover all known raw Freqtrade output files for a run."""
        self._warnings = []
        self._errors = []

        files: list[BacktestOutputFile] = []
        files.extend(self.discover_from_artifacts(run_id))
        files.extend(self.discover_from_raw_freqtrade_dir(run_id))
        files.extend(self.discover_stdout_stderr(run_id))
        files.extend(self._discover_from_workspace_if_linked(run_id, files))

        files = self._dedupe_files(files)
        primary = self.pick_primary_result_file(files)
        stdout_file = self._pick_log_file(files, "stdout_log")
        stderr_file = self._pick_log_file(files, "stderr_log")

        if not files:
            self._warnings.append("no_backtest_output_files_found")
        elif primary is None:
            log_files = [file for file in files if file.file_type in {"stdout_log", "stderr_log"}]
            if log_files:
                self._warnings.append("only_stdout_stderr_available")
            else:
                self._warnings.append("no_candidate_result_file_found")

        return BacktestOutputDiscoveryResult(
            run_id=run_id,
            success=primary is not None,
            primary_result_path=primary.path if primary else None,
            files=files,
            stdout_path=stdout_file.path if stdout_file else None,
            stderr_path=stderr_file.path if stderr_file else None,
            warnings=self._unique_strings(self._warnings),
            errors=self._unique_strings(self._errors),
        )

    def discover_from_artifacts(self, run_id: str) -> list[BacktestOutputFile]:
        """Discover files referenced by artifact records for the run."""
        try:
            artifacts = self.artifact_repository.list_run_artifacts(run_id)
        except Exception as exc:
            self._warnings.append("artifact_registry_unavailable")
            self._errors.append(f"artifact_registry_error: {exc}")
            return []

        files: list[BacktestOutputFile] = []
        for artifact in artifacts:
            artifact_type = artifact.get("artifact_type")
            if artifact_type and artifact_type not in self.DISCOVERABLE_ARTIFACT_TYPES:
                continue

            raw_path = artifact.get("file_path") or artifact.get("path")
            if not raw_path:
                continue

            path = self._resolve_project_path(raw_path)
            if path is None:
                self._warnings.append("artifact_path_outside_project_root")
                continue

            output_file = self._build_output_file(path, "artifact_registry")
            if output_file:
                files.append(output_file)

        return files

    def discover_from_raw_freqtrade_dir(self, run_id: str) -> list[BacktestOutputFile]:
        """Discover result files in the run's raw Freqtrade artifact directory."""
        raw_dir = self.get_run_raw_freqtrade_dir(run_id)
        backtest_dir = self.get_run_backtest_results_dir(run_id)

        files: list[BacktestOutputFile] = []
        files.extend(self._discover_directory(backtest_dir, "backtest_results_dir"))

        if raw_dir.exists():
            for path in raw_dir.iterdir():
                if path.is_file() and path.name not in {"stdout.log", "stderr.log"}:
                    output_file = self._build_output_file(path, "raw_freqtrade_dir")
                    if output_file:
                        files.append(output_file)
        elif not backtest_dir.exists():
            self._warnings.append("raw_freqtrade_dir_missing")

        return files

    def discover_stdout_stderr(self, run_id: str) -> list[BacktestOutputFile]:
        """Discover captured Freqtrade stdout and stderr logs for the run."""
        raw_dir = self.get_run_raw_freqtrade_dir(run_id)
        files: list[BacktestOutputFile] = []
        for file_name in ("stdout.log", "stderr.log"):
            output_file = self._build_output_file(raw_dir / file_name, "raw_freqtrade_dir")
            if output_file:
                files.append(output_file)
        return files

    def pick_primary_result_file(self, files: list[BacktestOutputFile]) -> Optional[BacktestOutputFile]:
        """Pick the best structured result file from discovered outputs."""
        candidates = [
            file for file in files
            if file.file_type in self.RESULT_FILE_TYPES and file.is_candidate_result
        ]
        if not candidates:
            return None

        candidates.sort(key=self._primary_sort_key)
        return candidates[0]

    def classify_file(self, path: Path) -> str:
        """Classify a file without reading its contents."""
        name = path.name.lower()
        suffix = path.suffix.lower()

        if name == "stdout.log":
            return "stdout_log"
        if name == "stderr.log":
            return "stderr_log"
        if suffix == ".zip":
            return "zip"
        if suffix == ".json":
            if (
                name == ".last_result.json"
                or name == "meta.json"
                or name.endswith(".meta.json")
                or name.endswith("-meta.json")
                or "metadata" in name
            ):
                return "meta_json"
            return "json"
        return "unknown"

    def _discover_directory(self, directory: Path, source: str) -> list[BacktestOutputFile]:
        """Return metadata for files in a known project-owned directory."""
        if not self._is_safe_project_path(directory):
            self._warnings.append("discovery_path_outside_project_root")
            return []
        if not directory.exists():
            return []
        if not directory.is_dir():
            self._warnings.append("discovery_path_not_directory")
            return []

        files: list[BacktestOutputFile] = []
        for path in directory.rglob("*"):
            if path.is_file():
                output_file = self._build_output_file(path, source)
                if output_file:
                    files.append(output_file)
        return files

    def _discover_from_workspace_if_linked(
        self,
        run_id: str,
        known_files: list[BacktestOutputFile],
    ) -> list[BacktestOutputFile]:
        """Discover workspace results only when artifacts or names link them to the run."""
        workspace_dir = (self.project_root / settings.FREQTRADE_USER_DATA_DIR / "backtest_results").resolve()
        if not self._is_safe_project_path(workspace_dir) or not workspace_dir.exists():
            return []

        linked_to_workspace = any(
            self._is_relative_to(Path(file.path).resolve(), workspace_dir)
            for file in known_files
        )

        if not linked_to_workspace:
            candidates: list[BacktestOutputFile] = []
            for path in workspace_dir.glob(f"*{self._safe_run_id(run_id)}*"):
                if path.is_file():
                    output_file = self._build_output_file(path, "freqtrade_workspace")
                    if output_file:
                        candidates.append(output_file)
            return candidates

        return self._discover_directory(workspace_dir, "freqtrade_workspace")

    def _build_output_file(self, path: Path, source: str) -> Optional[BacktestOutputFile]:
        """Build output file metadata without reading file contents."""
        if path.name == ".env":
            self._warnings.append("env_file_skipped")
            return None

        resolved = path.resolve(strict=False)
        if not self._is_safe_project_path(resolved):
            self._warnings.append("file_path_outside_project_root")
            return None
        if not resolved.exists() or not resolved.is_file():
            return None

        try:
            stat_result = resolved.stat()
        except OSError as exc:
            self._warnings.append("file_stat_failed")
            self._errors.append(f"file_stat_error: {exc}")
            return None

        file_type = self.classify_file(resolved)
        warnings: list[str] = []
        if file_type == "unknown":
            warnings.append("unsupported_file_type")
        if file_type == "meta_json":
            warnings.append("metadata_file_not_primary_result")
        if file_type in {"stdout_log", "stderr_log"}:
            warnings.append("log_file_fallback_only")

        return BacktestOutputFile(
            path=str(resolved),
            relative_path=self._relative_path(resolved),
            file_name=resolved.name,
            file_type=file_type,
            size_bytes=stat_result.st_size,
            modified_at=datetime.fromtimestamp(stat_result.st_mtime, timezone.utc).isoformat(),
            source=source,
            is_candidate_result=file_type in self.RESULT_FILE_TYPES,
            warnings=warnings,
        )

    def _resolve_project_path(self, raw_path: str) -> Optional[Path]:
        """Resolve a raw artifact path only if it stays inside the project root."""
        path = Path(raw_path)
        if not path.is_absolute():
            path = self.project_root / path

        resolved = path.resolve(strict=False)
        if not self._is_safe_project_path(resolved):
            return None
        return resolved

    def _is_safe_project_path(self, path: Path) -> bool:
        """Return whether a path resolves under the configured project root."""
        return self._is_relative_to(path.resolve(strict=False), self.project_root)

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        """Compatibility helper for project-root containment checks."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    def _relative_path(self, path: Path) -> str:
        """Return project-relative path when possible."""
        try:
            return str(path.relative_to(self.project_root))
        except ValueError:
            return path.name

    def _safe_run_id(self, run_id: str) -> str:
        """Return a path-safe run ID segment."""
        if self.SHELL_SAFE_RUN_ID.match(run_id):
            return run_id
        self._warnings.append("invalid_run_id_path_segment")
        return "invalid-run-id"

    def _primary_sort_key(self, file: BacktestOutputFile) -> tuple[int, int, int, str]:
        """Sort primary candidates by source, type, recency, and path."""
        source_priority = {
            "artifact_registry": 0,
            "backtest_results_dir": 1,
            "raw_freqtrade_dir": 2,
            "freqtrade_workspace": 3,
            "unknown": 4,
        }
        type_priority = {"json": 0, "zip": 1}
        return (
            source_priority.get(file.source, 9),
            type_priority.get(file.file_type, 9),
            -file.size_bytes,
            file.path,
        )

    @staticmethod
    def _pick_log_file(files: list[BacktestOutputFile], file_type: str) -> Optional[BacktestOutputFile]:
        """Pick one stdout/stderr file by type."""
        matches = [file for file in files if file.file_type == file_type]
        if not matches:
            return None
        matches.sort(key=lambda file: file.path)
        return matches[0]

    @staticmethod
    def _dedupe_files(files: list[BacktestOutputFile]) -> list[BacktestOutputFile]:
        """Deduplicate files by absolute path while preserving first discovery."""
        seen: set[str] = set()
        deduped: list[BacktestOutputFile] = []
        for file in files:
            if file.path in seen:
                continue
            seen.add(file.path)
            deduped.append(file)
        return deduped

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
