"""
Backtest result parser orchestrator.

This service connects discovery, raw loading, metric extraction, pair/trade
parsing, quality flags, repositories, logs, audit records, and normalized
artifacts. It does not approve, reject, classify, or run strategies.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.logs import RunLogRepository
from app.repositories.metrics import MetricsRepository
from app.schemas.artifacts import ArtifactCreate
from app.schemas.backtest_results import (
    BacktestParseResult,
    BacktestOutputDiscoveryResult,
    ExtractedBacktestMetrics,
    ExtractedPairResult,
    ExtractedTradeSummary,
    MetricsExtractionResult,
    NormalizedBacktestResult,
    RawBacktestLoadResult,
    RawBacktestPayload,
    ResultQualityReport,
)
from app.schemas.metrics import MetricSnapshotCreate, PairResultCreate, TradeSummaryCreate
from app.services.backtest_metrics_extractor import BacktestMetricsExtractor
from app.services.backtest_output_discovery import BacktestOutputDiscoveryService
from app.services.backtest_pair_trade_parser import BacktestPairTradeParser
from app.services.backtest_result_loader import BacktestResultLoader
from app.services.result_quality_service import ResultQualityService


class BacktestResultParser:
    """End-to-end parser pipeline for persisted backtest result evidence."""

    STAGE_KEY = "backtest_result_parse"

    def __init__(
        self,
        discovery_service: Optional[BacktestOutputDiscoveryService] = None,
        loader: Optional[BacktestResultLoader] = None,
        metrics_extractor: Optional[BacktestMetricsExtractor] = None,
        pair_trade_parser: Optional[BacktestPairTradeParser] = None,
        quality_service: Optional[ResultQualityService] = None,
        metrics_repository: Optional[MetricsRepository] = None,
        artifact_repository: Optional[ArtifactRepository] = None,
        log_repository: Optional[RunLogRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.project_root = (project_root or settings.project_root).resolve()
        self.discovery_service = discovery_service or BacktestOutputDiscoveryService(project_root=self.project_root)
        self.loader = loader or BacktestResultLoader(project_root=self.project_root)
        self.metrics_extractor = metrics_extractor or BacktestMetricsExtractor()
        self.pair_trade_parser = pair_trade_parser or BacktestPairTradeParser()
        self.quality_service = quality_service or ResultQualityService()
        self.metrics_repository = metrics_repository or MetricsRepository()
        self.artifact_repository = artifact_repository or ArtifactRepository()
        self.log_repository = log_repository or RunLogRepository()
        self.audit_repository = audit_repository or AuditLogRepository()

    def parse_run(self, run_id: str, force: bool = False) -> BacktestParseResult:
        """Discover, parse, and persist backtest result evidence for a run."""
        discovery = self.discovery_service.discover_outputs(run_id)
        loader_result = self.loader.load_from_discovery(discovery)
        return self._parse_loaded(run_id, loader_result, discovery=discovery, force=force)

    def parse_from_paths(self, run_id: str, paths: list[str], force: bool = False) -> BacktestParseResult:
        """Parse and persist backtest result evidence from explicit file paths."""
        payloads: list[RawBacktestPayload] = []
        warnings: list[str] = []
        errors: list[str] = []

        for raw_path in paths:
            loaded = self.loader.load_file(Path(raw_path))
            if isinstance(loaded, list):
                payloads.extend(loaded)
            else:
                payloads.append(loaded)

        for payload in payloads:
            warnings.extend(payload.warnings)
            errors.extend(payload.errors)

        primary_payload = self.loader.select_primary_payload(payloads)
        if primary_payload is None:
            primary_payload = self._select_fallback_payload(payloads)
            if primary_payload is None:
                warnings.append("no_primary_payload_available")

        loader_result = RawBacktestLoadResult(
            success=primary_payload is not None and not errors,
            primary_payload=primary_payload,
            payloads=payloads,
            warnings=self._unique_strings(warnings),
            errors=self._unique_strings(errors),
        )
        return self._parse_loaded(run_id, loader_result, discovery=None, force=force)

    def save_metrics(self, run_id, metrics, raw_payload) -> dict:
        """Save an extracted metrics snapshot."""
        raw_json = {
            "metrics": metrics.model_dump(mode="json"),
            "source_path": raw_payload.source_path if raw_payload else None,
            "source_type": raw_payload.source_type if raw_payload else None,
            "parser_type": raw_payload.parser_type if raw_payload else None,
        }
        return self.metrics_repository.create_metric_snapshot(
            MetricSnapshotCreate(
                run_id=run_id,
                stage_key=self.STAGE_KEY,
                net_profit=metrics.net_profit,
                profit_factor=metrics.profit_factor,
                max_drawdown=metrics.max_drawdown if metrics.max_drawdown is not None else metrics.max_drawdown_pct,
                sharpe=metrics.sharpe,
                calmar=metrics.calmar,
                win_rate=metrics.win_rate,
                trade_count=metrics.trade_count,
                expectancy=metrics.expectancy,
                avg_win=metrics.avg_win,
                avg_loss=metrics.avg_loss,
                raw_json=raw_json,
            )
        )

    def save_pair_results(self, run_id, pair_results) -> list[dict]:
        """Upsert pair results for a run."""
        saved = []
        for pair in pair_results:
            saved.append(
                self.metrics_repository.upsert_pair_result(
                    PairResultCreate(
                        run_id=run_id,
                        pair=pair.pair,
                        net_profit=pair.net_profit,
                        profit_factor=pair.profit_factor,
                        max_drawdown=pair.max_drawdown,
                        trade_count=pair.trade_count,
                        win_rate=pair.win_rate,
                        expectancy=pair.expectancy,
                        raw_json=pair.model_dump(mode="json"),
                    )
                )
            )
        return saved

    def save_trade_summary(self, run_id, trade_summary) -> dict:
        """Replace the trade summary for a run."""
        return self.metrics_repository.replace_trade_summary(
            TradeSummaryCreate(
                run_id=run_id,
                total_trades=trade_summary.total_trades,
                wins=trade_summary.wins,
                losses=trade_summary.losses,
                draws=trade_summary.draws,
                avg_duration=trade_summary.avg_duration,
                best_pair=trade_summary.best_pair,
                worst_pair=trade_summary.worst_pair,
                raw_json=trade_summary.model_dump(mode="json"),
            )
        )

    def save_quality_report(self, run_id, quality_report) -> dict:
        """Persist quality flags as an audit evidence record."""
        audit = self.audit_repository.create_audit_log(
            {
                "run_id": run_id,
                "actor": "system",
                "action_type": "backtest_result_quality",
                "target_type": "run",
                "target_id": run_id,
                "after": quality_report.model_dump(mode="json"),
                "approved": False,
                "description": "Backtest parse quality report recorded",
            }
        )
        return {
            "id": audit["id"],
            "action_type": audit["action_type"],
            "flag_count": len(quality_report.flags),
        }

    def write_normalized_result_artifact(self, run_id, parse_result) -> dict:
        """Write and register the normalized parsed result artifact."""
        normalized_dir = self.project_root / "artifacts" / "runs" / run_id / "normalized"
        normalized_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = normalized_dir / "backtest_result.normalized.json"

        source_files = []
        if parse_result.loader:
            source_files = [self._project_relative_path(payload.source_path) for payload in parse_result.loader.payloads]

        normalized = NormalizedBacktestResult(
            run_id=run_id,
            metrics=parse_result.metrics.metrics if parse_result.metrics else None,
            pair_results=parse_result.pair_results,
            trade_summary=parse_result.trade_summary,
            quality_flags=parse_result.quality_report.flags if parse_result.quality_report else [],
            parser_metadata={
                "parser": "BacktestResultParser",
                "stage_key": self.STAGE_KEY,
                "success": parse_result.success,
                "warnings": parse_result.warnings,
                "errors": parse_result.errors,
            },
            source_files=source_files,
            created_at=self._now(),
        )

        artifact_payload = normalized.model_dump(mode="json")
        artifact_path.write_text(
            json.dumps(artifact_payload, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        payload_bytes = artifact_path.read_bytes()
        sha256 = hashlib.sha256(payload_bytes).hexdigest()

        artifact = self.artifact_repository.create_or_update_artifact(
            ArtifactCreate(
                run_id=run_id,
                artifact_type="metrics_json",
                file_path=str(artifact_path),
                description="Normalized parsed backtest result",
                sha256=sha256,
                size_bytes=len(payload_bytes),
            )
        )
        parse_result.normalized_result_path = str(artifact_path)
        return artifact

    def add_parse_logs(self, run_id, parse_result) -> None:
        """Add parse pipeline run logs."""
        level = "info" if parse_result.success else "error"
        self.log_repository.add_log(
            run_id=run_id,
            level=level,
            source="backtest_result_parser",
            message="Backtest result parse completed" if parse_result.success else "Backtest result parse failed",
            stage_key=self.STAGE_KEY,
            details={
                "success": parse_result.success,
                "warnings": parse_result.warnings,
                "errors": parse_result.errors,
                "saved_records": parse_result.saved_records,
            },
        )

        for warning in parse_result.warnings:
            self.log_repository.add_log(
                run_id=run_id,
                level="warning",
                source="backtest_result_parser",
                message=f"Backtest parse warning: {warning}",
                stage_key=self.STAGE_KEY,
            )

    def _parse_loaded(
        self,
        run_id: str,
        loader_result: RawBacktestLoadResult,
        discovery: Optional[BacktestOutputDiscoveryResult],
        force: bool,
    ) -> BacktestParseResult:
        """Parse loaded payloads, persist results, and return the full envelope."""
        warnings = []
        errors = []
        warnings.extend(discovery.warnings if discovery else [])
        errors.extend(discovery.errors if discovery else [])
        warnings.extend(loader_result.warnings)
        errors.extend(loader_result.errors)

        primary_payload = loader_result.primary_payload or self._select_fallback_payload(loader_result.payloads)
        if primary_payload is None:
            warnings.append("no_parseable_payload")
            quality_report = self.quality_service.build_quality_report(
                None,
                [],
                None,
                loader_result=loader_result,
                discovery_result=discovery,
            )
            result = BacktestParseResult(
                run_id=run_id,
                success=False,
                discovery=discovery,
                loader=loader_result,
                metrics=None,
                pair_results=[],
                trade_summary=None,
                quality_report=quality_report,
                saved_records={},
                warnings=self._unique_strings(warnings + quality_report.warnings),
                errors=self._unique_strings(errors + quality_report.errors),
            )
            result.saved_records["quality_audit"] = self.save_quality_report(run_id, quality_report)
            self.add_parse_logs(run_id, result)
            self._add_parse_audit(run_id, result)
            return result

        metrics_result = self.metrics_extractor.extract(primary_payload)
        pair_trade_result = self.pair_trade_parser.parse(primary_payload)
        quality_report = self.quality_service.build_quality_report(
            metrics_result,
            pair_trade_result,
            pair_trade_result.trade_summary,
            loader_result=loader_result,
            discovery_result=discovery,
        )

        warnings.extend(metrics_result.warnings)
        warnings.extend(pair_trade_result.warnings)
        warnings.extend(quality_report.warnings)
        errors.extend(metrics_result.errors)
        errors.extend(pair_trade_result.errors)
        errors.extend(quality_report.errors)

        saved_records: dict = {}
        if force:
            saved_records["deleted_metric_snapshots"] = self.metrics_repository.delete_metric_snapshots(run_id)

        metrics = metrics_result.metrics
        if metrics is not None and self._has_metric_content(metrics):
            saved_records["metric_snapshot"] = self.save_metrics(run_id, metrics, primary_payload)

        if pair_trade_result.pair_results:
            saved_records["pair_results"] = self.save_pair_results(run_id, pair_trade_result.pair_results)
        else:
            saved_records["pair_results"] = []

        if pair_trade_result.trade_summary and self._summary_has_data(pair_trade_result.trade_summary):
            saved_records["trade_summary"] = self.save_trade_summary(run_id, pair_trade_result.trade_summary)

        saved_records["quality_audit"] = self.save_quality_report(run_id, quality_report)

        success = bool(
            saved_records.get("metric_snapshot")
            or saved_records.get("pair_results")
            or saved_records.get("trade_summary")
        ) and not errors

        result = BacktestParseResult(
            run_id=run_id,
            success=success,
            discovery=discovery,
            loader=loader_result,
            metrics=metrics_result,
            pair_results=pair_trade_result.pair_results,
            trade_summary=pair_trade_result.trade_summary,
            quality_report=quality_report,
            saved_records=saved_records,
            warnings=self._unique_strings(warnings),
            errors=self._unique_strings(errors),
        )

        saved_records["normalized_artifact"] = self.write_normalized_result_artifact(run_id, result)
        self.add_parse_logs(run_id, result)
        self._add_parse_audit(run_id, result)
        return result

    def _add_parse_audit(self, run_id: str, parse_result: BacktestParseResult) -> dict:
        """Record parse execution audit log without approval semantics."""
        return self.audit_repository.create_audit_log(
            {
                "run_id": run_id,
                "actor": "system",
                "action_type": "backtest_result_parse",
                "target_type": "run",
                "target_id": run_id,
                "after": {
                    "success": parse_result.success,
                    "normalized_result_path": parse_result.normalized_result_path,
                    "saved_record_keys": list(parse_result.saved_records.keys()),
                    "quality_flags": [
                        flag.code for flag in parse_result.quality_report.flags
                    ] if parse_result.quality_report else [],
                },
                "approved": False,
                "description": "Backtest result parse attempted",
            }
        )

    @staticmethod
    def _select_fallback_payload(payloads: list[RawBacktestPayload]) -> Optional[RawBacktestPayload]:
        """Select stdout fallback when no structured primary exists."""
        for payload in payloads:
            if payload.parser_type == "stdout_table_fallback" and payload.raw_text is not None:
                return payload
        return None

    @staticmethod
    def _has_metric_content(metrics: ExtractedBacktestMetrics) -> bool:
        """Return whether the metrics object contains data worth persisting."""
        return any(
            value is not None
            for value in (
                metrics.net_profit,
                metrics.net_profit_pct,
                metrics.profit_factor,
                metrics.max_drawdown,
                metrics.max_drawdown_pct,
                metrics.sharpe,
                metrics.calmar,
                metrics.win_rate,
                metrics.trade_count,
                metrics.expectancy,
            )
        )

    @staticmethod
    def _summary_has_data(summary: ExtractedTradeSummary) -> bool:
        """Return whether a trade summary has data worth persisting."""
        return any(
            getattr(summary, field, None) is not None
            for field in ("total_trades", "wins", "losses", "draws", "avg_duration", "best_pair", "worst_pair")
        )

    @staticmethod
    def _now() -> str:
        """Return current UTC timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _project_relative_path(self, path: str) -> str:
        """Return project-relative path when possible."""
        try:
            return str(Path(path).resolve(strict=False).relative_to(self.project_root))
        except ValueError:
            return path

    @staticmethod
    def _unique_strings(values: list[str]) -> list[str]:
        """Return stable unique strings."""
        return list(dict.fromkeys(values))
