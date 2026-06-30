"""
Raw Freqtrade backtest result loader.

The loader reads project-owned JSON, ZIP JSON members, and stdout/stderr text
fallbacks. It intentionally does not normalize metrics or classify results.
"""
from __future__ import annotations

import json
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

from app.core.config import settings
from app.schemas.backtest_results import (
    BacktestOutputDiscoveryResult,
    RawBacktestLoadResult,
    RawBacktestPayload,
)


class BacktestResultLoader:
    """Load raw Freqtrade backtest result payloads safely."""

    MAX_TEXT_BYTES = 5_000_000
    MAX_JSON_BYTES = 25_000_000
    MAX_ZIP_MEMBER_BYTES = 25_000_000
    MAX_ZIP_TOTAL_JSON_BYTES = 50_000_000

    def __init__(self, project_root: Optional[Path] = None) -> None:
        self.project_root = (project_root or settings.project_root).resolve()

    def load_from_discovery(self, discovery_result: BacktestOutputDiscoveryResult) -> RawBacktestLoadResult:
        """Load supported files from a discovery result."""
        payloads: list[RawBacktestPayload] = []
        warnings = list(discovery_result.warnings)
        errors = list(discovery_result.errors)

        primary_path = discovery_result.primary_result_path
        ordered_files = sorted(
            discovery_result.files,
            key=lambda file: (0 if file.path == primary_path else 1, file.path),
        )

        for output_file in ordered_files:
            if output_file.file_type not in {"json", "zip", "stdout_log", "stderr_log"}:
                continue

            payload = self.load_file(Path(output_file.path))
            if isinstance(payload, list):
                payloads.extend(payload)
            else:
                payloads.append(payload)

        primary_payload = self.select_primary_payload(payloads)
        for payload in payloads:
            warnings.extend(payload.warnings)
            errors.extend(payload.errors)

        if not payloads:
            warnings.append("no_supported_payloads_loaded")
        elif primary_payload is None:
            warnings.append("no_structured_primary_payload_loaded")

        return RawBacktestLoadResult(
            success=primary_payload is not None,
            primary_payload=primary_payload,
            payloads=payloads,
            warnings=self._unique_strings(warnings),
            errors=self._unique_strings(errors),
        )

    def load_file(self, path: Path) -> RawBacktestPayload | list[RawBacktestPayload]:
        """Load one supported raw result file by extension or log name."""
        resolved = path.resolve(strict=False)
        if resolved.name == ".env":
            return RawBacktestPayload(
                source_path=str(resolved),
                source_type="rejected",
                parser_type="rejected",
                errors=["env_file_rejected"],
            )
        if resolved.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            return RawBacktestPayload(
                source_path=str(resolved),
                source_type="rejected",
                parser_type="rejected",
                errors=["database_file_rejected"],
            )

        file_type = self._classify_path(path)
        if file_type == "json":
            return self.load_json(path)
        if file_type == "zip":
            return self.load_zip(path)
        if file_type == "stdout_log":
            return self.load_stdout(path)
        if file_type == "stderr_log":
            return self._load_stderr(path)

        resolved = path.resolve(strict=False)
        return RawBacktestPayload(
            source_path=str(resolved),
            source_type=file_type,
            parser_type="unsupported",
            warnings=["unsupported_file_type"],
        )

    def load_json(self, path: Path) -> RawBacktestPayload:
        """Load a JSON result file into a raw payload."""
        resolved = path.resolve(strict=False)
        warnings: list[str] = []
        errors: list[str] = []
        raw_data: Optional[dict] = None

        try:
            raw_data = self.safe_read_json(resolved)
            if not self._looks_like_freqtrade_payload(raw_data):
                warnings.append("unrecognized_freqtrade_json_shape")
        except Exception as exc:
            errors.append(f"json_load_error: {exc}")

        return RawBacktestPayload(
            source_path=str(resolved),
            source_type="json",
            parser_type="freqtrade_json",
            raw_data=raw_data,
            warnings=warnings,
            errors=errors,
        )

    def load_zip(self, path: Path) -> list[RawBacktestPayload]:
        """Load safe JSON members from a ZIP without extracting to disk."""
        resolved = path.resolve(strict=False)
        base_payload = RawBacktestPayload(
            source_path=str(resolved),
            source_type="zip",
            parser_type="freqtrade_zip_json",
        )

        try:
            self._ensure_safe_input_path(resolved)
            with zipfile.ZipFile(resolved) as archive:
                json_members = self.find_json_members_in_zip(resolved)
                safe_infos = {
                    info.filename: info
                    for info in archive.infolist()
                    if info.filename in json_members
                }

                if not json_members:
                    base_payload.warnings.append("zip_no_json_members")
                    return [base_payload]

                payloads: list[RawBacktestPayload] = []
                total_size = 0
                for member in json_members:
                    info = safe_infos[member]
                    total_size += info.file_size
                    if info.file_size > self.MAX_ZIP_MEMBER_BYTES:
                        payloads.append(
                            RawBacktestPayload(
                                source_path=str(resolved),
                                source_type="zip",
                                parser_type="freqtrade_zip_json",
                                zip_members=[member],
                                errors=["zip_member_too_large"],
                            )
                        )
                        continue
                    if total_size > self.MAX_ZIP_TOTAL_JSON_BYTES:
                        payloads.append(
                            RawBacktestPayload(
                                source_path=str(resolved),
                                source_type="zip",
                                parser_type="freqtrade_zip_json",
                                zip_members=[member],
                                errors=["zip_total_json_too_large"],
                            )
                        )
                        break

                    with archive.open(info) as member_file:
                        raw_bytes = member_file.read(info.file_size + 1)
                    try:
                        raw_data = json.loads(raw_bytes.decode("utf-8"))
                        warnings = []
                        if not isinstance(raw_data, dict):
                            raise ValueError("top-level JSON value must be an object")
                        if not self._looks_like_freqtrade_payload(raw_data):
                            warnings.append("unrecognized_freqtrade_json_shape")
                        payloads.append(
                            RawBacktestPayload(
                                source_path=str(resolved),
                                source_type="zip",
                                parser_type="freqtrade_zip_json",
                                raw_data=raw_data,
                                zip_members=[member],
                                warnings=warnings,
                            )
                        )
                    except Exception as exc:
                        payloads.append(
                            RawBacktestPayload(
                                source_path=str(resolved),
                                source_type="zip",
                                parser_type="freqtrade_zip_json",
                                zip_members=[member],
                                errors=[f"zip_json_load_error: {exc}"],
                            )
                        )

                return payloads
        except Exception as exc:
            base_payload.errors.append(f"zip_load_error: {exc}")
            return [base_payload]

    def load_stdout(self, path: Path) -> RawBacktestPayload:
        """Load stdout fallback text."""
        resolved = path.resolve(strict=False)
        warnings = ["stdout_fallback_only"]
        errors: list[str] = []
        raw_text: Optional[str] = None

        try:
            raw_text = self.safe_read_text(resolved)
        except Exception as exc:
            errors.append(f"stdout_load_error: {exc}")

        return RawBacktestPayload(
            source_path=str(resolved),
            source_type="stdout_log",
            parser_type="stdout_table_fallback",
            raw_text=raw_text,
            warnings=warnings,
            errors=errors,
        )

    def safe_read_text(self, path: Path, max_bytes: int = MAX_TEXT_BYTES) -> str:
        """Read bounded text from a safe project-owned path."""
        resolved = path.resolve(strict=False)
        self._ensure_safe_input_path(resolved)
        self._ensure_file_size(resolved, max_bytes)
        return resolved.read_text(encoding="utf-8", errors="replace")

    def safe_read_json(self, path: Path, max_bytes: int = MAX_JSON_BYTES) -> dict:
        """Read bounded JSON from a safe project-owned path."""
        resolved = path.resolve(strict=False)
        self._ensure_safe_input_path(resolved)
        self._ensure_file_size(resolved, max_bytes)
        with resolved.open("r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            raise ValueError("top-level JSON value must be an object")
        return loaded

    def find_json_members_in_zip(self, path: Path) -> list[str]:
        """Return safe JSON member names from a ZIP file."""
        resolved = path.resolve(strict=False)
        self._ensure_safe_input_path(resolved)
        self._ensure_file_size(resolved, self.MAX_JSON_BYTES)

        members: list[str] = []
        with zipfile.ZipFile(resolved) as archive:
            for info in archive.infolist():
                member = info.filename
                if not self._is_safe_zip_member(member):
                    continue
                if member.lower().endswith(".json") and not member.endswith("/"):
                    members.append(member)
        return members

    def select_primary_payload(self, payloads: list[RawBacktestPayload]) -> Optional[RawBacktestPayload]:
        """Select the best structured loaded payload."""
        candidates = [
            payload for payload in payloads
            if payload.raw_data is not None
            and not payload.errors
            and payload.parser_type in {"freqtrade_json", "freqtrade_zip_json"}
        ]
        if not candidates:
            return None

        candidates.sort(key=self._primary_payload_sort_key)
        return candidates[0]

    def _load_stderr(self, path: Path) -> RawBacktestPayload:
        """Load stderr text as diagnostics only."""
        resolved = path.resolve(strict=False)
        warnings = ["stderr_diagnostics_only"]
        errors: list[str] = []
        raw_text: Optional[str] = None

        try:
            raw_text = self.safe_read_text(resolved)
        except Exception as exc:
            errors.append(f"stderr_load_error: {exc}")

        return RawBacktestPayload(
            source_path=str(resolved),
            source_type="stderr_log",
            parser_type="stderr_error_text",
            raw_text=raw_text,
            warnings=warnings,
            errors=errors,
        )

    def _ensure_safe_input_path(self, path: Path) -> None:
        """Validate a result input path before reading."""
        resolved = path.resolve(strict=False)
        if not self._is_relative_to(resolved, self.project_root):
            raise ValueError("path_outside_project_root")
        if resolved.name == ".env":
            raise ValueError("env_file_rejected")
        if resolved.suffix.lower() in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("database_file_rejected")
        if not resolved.exists():
            raise FileNotFoundError("file_not_found")
        if not resolved.is_file():
            raise ValueError("not_a_file")

    @staticmethod
    def _ensure_file_size(path: Path, max_bytes: int) -> None:
        """Reject files larger than the allowed input size."""
        size = path.stat().st_size
        if size > max_bytes:
            raise ValueError(f"file_too_large: {size} > {max_bytes}")

    @staticmethod
    def _classify_path(path: Path) -> str:
        """Classify a file path for loading."""
        name = path.name.lower()
        if name == "stdout.log":
            return "stdout_log"
        if name == "stderr.log":
            return "stderr_log"
        if path.suffix.lower() == ".json":
            return "json"
        if path.suffix.lower() == ".zip":
            return "zip"
        return "unknown"

    @staticmethod
    def _is_safe_zip_member(member: str) -> bool:
        """Return whether a ZIP member path is safe to inspect in memory."""
        if not member or member.startswith(("/", "\\")):
            return False
        normalized = PurePosixPath(member.replace("\\", "/"))
        return ".." not in normalized.parts and not normalized.is_absolute()

    @staticmethod
    def _looks_like_freqtrade_payload(raw_data: dict) -> bool:
        """Detect common Freqtrade result shapes without normalizing metrics."""
        known_keys = {
            "strategy",
            "strategy_comparison",
            "metadata",
            "backtest_start_time",
            "backtest_end_time",
        }
        return any(key in raw_data for key in known_keys)

    @staticmethod
    def _is_relative_to(path: Path, parent: Path) -> bool:
        """Compatibility helper for containment checks."""
        try:
            path.relative_to(parent)
            return True
        except ValueError:
            return False

    @staticmethod
    def _primary_payload_sort_key(payload: RawBacktestPayload) -> tuple[int, str]:
        """Prefer direct JSON over ZIP JSON, then stable path."""
        parser_priority = {
            "freqtrade_json": 0,
            "freqtrade_zip_json": 1,
            "stdout_table_fallback": 2,
            "stderr_error_text": 3,
        }
        return (parser_priority.get(payload.parser_type, 9), payload.source_path)

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
