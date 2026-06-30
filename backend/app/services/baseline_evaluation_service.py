"""
Part 07 Baseline Evaluation Service.

Orchestrates end-to-end baseline evaluation of an existing strategy by reusing
Part 04 (Freqtrade integration), Part 05 (result parsing), and Part 06 (decision engine)
services. This service coordinates the pipeline stages without implementing
low-level Freqtrade command logic, parsing logic, or decision logic.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings
from app.core.constants import (
    BASELINE_PIPELINE_STAGES,
    BASELINE_PIPELINE_STATUSES,
    BASELINE_ERROR_CODES,
    BASELINE_ERROR_MESSAGES,
)
from app.repositories.artifacts import ArtifactRepository
from app.repositories.audit_logs import AuditLogRepository
from app.repositories.logs import RunLogRepository
from app.repositories.runs import RunRepository
from app.repositories.run_stages import RunStageRepository
from app.schemas.artifacts import ArtifactCreate
from app.schemas.baseline import (
    BaselineEvaluationRequest,
    BaselineEvaluationResult,
    BaselineStageResult,
)
from app.schemas.decisions import DecisionEvaluationRequest
from app.schemas.freqtrade_config import FreqtradeBacktestConfigRequest
from app.schemas.freqtrade_data import FreqtradeDataCheckRequest, FreqtradeDataDownloadRequest
from app.schemas.freqtrade_backtest import FreqtradeBacktestRequest
from app.services.backtest_result_parser import BacktestResultParser
from app.services.decision_service import DecisionService
from app.services.freqtrade_backtest_runner import FreqtradeBacktestRunner
from app.services.freqtrade_config_generator import FreqtradeConfigGenerator
from app.services.freqtrade_data_service import FreqtradeDataService
from app.services.freqtrade_strategy_service import FreqtradeStrategyService


class BaselineEvaluationService:
    """
    Orchestrate baseline evaluation of an existing strategy.

    This service coordinates the complete pipeline:
    1. Run setup
    2. Strategy validation
    3. Config generation
    4. Data check
    5. Data download (if needed and confirmed)
    6. Baseline backtest (if confirmed)
    7. Result parsing
    8. Decision evaluation
    9. Baseline report
    10. Completion

    The service reuses existing Part 04, 05, and 06 services and does not
    duplicate Freqtrade command logic, parsing logic, or decision logic.
    """

    REPORT_RELATIVE_PATH = "artifacts/runs/{run_id}/baseline/baseline_evaluation_report.json"

    def __init__(
        self,
        run_repository: Optional[RunRepository] = None,
        run_stage_repository: Optional[RunStageRepository] = None,
        artifact_repository: Optional[ArtifactRepository] = None,
        log_repository: Optional[RunLogRepository] = None,
        audit_repository: Optional[AuditLogRepository] = None,
        strategy_service: Optional[FreqtradeStrategyService] = None,
        config_generator: Optional[FreqtradeConfigGenerator] = None,
        data_service: Optional[FreqtradeDataService] = None,
        backtest_runner: Optional[FreqtradeBacktestRunner] = None,
        result_parser: Optional[BacktestResultParser] = None,
        decision_service: Optional[DecisionService] = None,
        project_root: Optional[Path] = None,
    ) -> None:
        self.project_root = (project_root or settings.project_root).resolve()
        self.run_repository = run_repository or RunRepository()
        self.run_stage_repository = run_stage_repository or RunStageRepository()
        self.artifact_repository = artifact_repository or ArtifactRepository()
        self.log_repository = log_repository or RunLogRepository()
        self.audit_repository = audit_repository or AuditLogRepository()
        self.strategy_service = strategy_service or FreqtradeStrategyService()
        self.config_generator = config_generator or FreqtradeConfigGenerator()
        self.data_service = data_service or FreqtradeDataService()
        self.backtest_runner = backtest_runner or FreqtradeBacktestRunner()
        self.result_parser = result_parser or BacktestResultParser()
        self.decision_service = decision_service or DecisionService()

    def _start_stage(self, stage_name: str, run_id: str) -> datetime:
        """Start a stage and return the start timestamp."""
        started_at = datetime.now(timezone.utc)
        self.run_stage_repository.start_stage(run_id, stage_name)
        return started_at

    def _complete_stage(
        self,
        stage_name: str,
        run_id: str,
        started_at: datetime,
        message: str,
        details: Optional[dict] = None,
        artifacts: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
    ) -> BaselineStageResult:
        """Complete a stage successfully."""
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        output_data = details or {}
        if artifacts:
            output_data["artifact_paths"] = artifacts

        self.run_stage_repository.complete_stage(
            run_id,
            stage_name,
            output_data=output_data,
            logs_summary=message,
        )

        self._add_run_log(run_id, "info", message, details)

        return BaselineStageResult(
            stage_name=stage_name,
            status="completed",
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
            message=message,
            warnings=warnings or [],
            errors=[],
            artifact_paths=artifacts or [],
            details=details or {},
        )

    def _fail_stage(
        self,
        stage_name: str,
        run_id: str,
        started_at: datetime,
        message: str,
        error_code: str,
        details: Optional[dict] = None,
        warnings: Optional[list[str]] = None,
    ) -> BaselineStageResult:
        """Fail a stage with controlled error."""
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        error_data = details or {}
        error_data["error_code"] = error_code

        self.run_stage_repository.fail_stage(
            run_id,
            stage_name,
            error_data=error_data,
            logs_summary=message,
        )

        self._add_run_log(run_id, "error", message, details)

        return BaselineStageResult(
            stage_name=stage_name,
            status="failed_controlled",
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
            message=message,
            error_code=error_code,
            warnings=warnings or [],
            errors=[message],
            artifact_paths=[],
            details=details or {},
        )

    def _confirmation_required(
        self,
        stage_name: str,
        run_id: str,
        started_at: datetime,
        message: str,
        details: Optional[dict] = None,
        error_code: Optional[str] = None,
    ) -> BaselineStageResult:
        """Mark stage as requiring user confirmation."""
        completed_at = datetime.now(timezone.utc)
        duration_seconds = (completed_at - started_at).total_seconds()

        self.run_stage_repository.mark_stage_waiting(
            run_id,
            stage_name,
            message=message,
        )

        self._add_run_log(run_id, "warning", message, details)

        return BaselineStageResult(
            stage_name=stage_name,
            status="confirmation_required",
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            duration_seconds=duration_seconds,
            message=message,
            error_code=error_code,
            warnings=[message],
            errors=[],
            artifact_paths=[],
            details=details or {},
        )

    def _add_run_log(
        self,
        run_id: str,
        level: str,
        message: str,
        details: Optional[dict] = None,
    ) -> None:
        """Add a log entry for the run."""
        self.log_repository.add_log(
            run_id=run_id,
            level=level,
            message=message,
            source="baseline_evaluation",
            details=details,
        )

    def _add_audit_log(
        self,
        run_id: str,
        action_type: str,
        before: Optional[dict] = None,
        after: Optional[dict] = None,
    ) -> None:
        """Add an audit log entry."""
        self.audit_repository.create_audit_log(
            {
                "run_id": run_id,
                "actor": "system",
                "action": action_type,
                "resource_type": "run",
                "resource_id": run_id,
                "before": before,
                "after": after,
            }
        )

    def _get_error_message(self, error_code: str) -> dict:
        """Get user-facing error message for an error code."""
        return BASELINE_ERROR_MESSAGES.get(error_code, {
            "short_message": "Unknown error",
            "user_message": "An unknown error occurred",
            "next_actions": ["Review system logs", "Contact support"],
        })

    def evaluate(self, request: BaselineEvaluationRequest) -> BaselineEvaluationResult:
        """
        Evaluate an existing strategy baseline end-to-end.

        Args:
            request: Baseline evaluation request

        Returns:
            Baseline evaluation result with stage outcomes and final status
        """
        stage_results = []
        errors = []
        warnings = []
        artifact_paths = []
        next_actions = []

        try:
            # Stage 1: Run Setup
            setup_result = self._stage_run_setup(request)
            stage_results.append(setup_result)
            run_id = setup_result.details.get("run_id")
            if not run_id:
                return self._failure_result(
                    request,
                    stage_results,
                    ["Run setup failed to create run ID"],
                    [],
                    artifact_paths,
                    next_actions,
                )

            if setup_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    setup_result.status,
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    setup_result.errors,
                    setup_result.warnings,
                    next_actions,
                )

            # Stage 2: Strategy Validation
            validation_result = self._stage_strategy_validation(run_id, request)
            stage_results.append(validation_result)
            if validation_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    validation_result.status,
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    validation_result.errors,
                    validation_result.warnings,
                    ["Fix strategy validation errors and retry"],
                )

            # Stage 3: Config Generation
            config_result = self._stage_config_generation(run_id, request)
            stage_results.append(config_result)
            if config_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    config_result.errors,
                    config_result.warnings,
                    ["Review config generation errors"],
                )
            artifact_paths.extend(config_result.artifact_paths)

            # Stage 4: Data Check
            data_check_result = self._stage_data_check(run_id, request, config_result.details.get("config_path"))
            stage_results.append(data_check_result)
            
            if data_check_result.status == "failed_controlled":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    data_check_result.errors,
                    data_check_result.warnings,
                    ["Review data check errors"],
                )

            # Stage 5: Data Download (if needed)
            data_download_result = self._stage_data_download(
                run_id,
                request,
                data_check_result.details.get("missing_data", False),
            )
            stage_results.append(data_download_result)
            
            if data_download_result.status == "confirmation_required":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "confirmation_required",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    data_download_result.errors,
                    data_download_result.warnings,
                    ["Confirm data download to proceed"],
                )
            
            if data_download_result.status == "failed_controlled":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    data_download_result.errors,
                    data_download_result.warnings,
                    ["Review data download errors"],
                )

            # Stage 6: Baseline Backtest
            backtest_result = self._stage_baseline_backtest(
                run_id,
                request,
                config_result.details.get("config_path"),
            )
            stage_results.append(backtest_result)
            
            if backtest_result.status == "confirmation_required":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "confirmation_required",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    backtest_result.errors,
                    backtest_result.warnings,
                    ["Confirm backtest execution to proceed"],
                )
            
            if backtest_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    backtest_result.errors,
                    backtest_result.warnings,
                    ["Review backtest errors and logs"],
                )
            artifact_paths.extend(backtest_result.artifact_paths)

            # Stage 7: Result Parsing
            parse_result = self._stage_result_parsing(run_id, request)
            stage_results.append(parse_result)
            
            if parse_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    parse_result.errors,
                    parse_result.warnings,
                    ["Review parsing errors and raw backtest outputs"],
                )
            artifact_paths.extend(parse_result.artifact_paths)

            # Stage 8: Decision Evaluation
            decision_result = self._stage_decision_evaluation(run_id, request)
            stage_results.append(decision_result)
            
            if decision_result.status != "completed":
                return self._build_result(
                    request,
                    run_id,
                    False,
                    "failed_controlled",
                    None,
                    None,
                    stage_results,
                    artifact_paths,
                    decision_result.errors,
                    decision_result.warnings,
                    ["Review decision evaluation errors"],
                )
            artifact_paths.extend(decision_result.artifact_paths)

            # Stage 9: Baseline Report
            report_result = self._stage_baseline_report(
                run_id,
                request,
                stage_results,
                decision_result.details,
            )
            stage_results.append(report_result)
            artifact_paths.extend(report_result.artifact_paths)

            # Stage 10: Completion
            completion_result = self._stage_completion(
                run_id,
                request,
                decision_result.details.get("classification"),
            )
            stage_results.append(completion_result)

            # Build final success result
            return self._build_result(
                request,
                run_id,
                True,
                "completed",
                decision_result.details.get("classification"),
                decision_result.details.get("confidence_score"),
                stage_results,
                artifact_paths,
                completion_result.errors,
                completion_result.warnings,
                decision_result.details.get("next_actions", []),
            )

        except Exception as exc:
            # Controlled failure: catch any unhandled exception
            self.log_repository.add_log(
                run_id=run_id if run_id else "unknown",
                level="error",
                message=f"Unhandled exception in baseline evaluation: {exc}",
                source="baseline_evaluation_service",
            )
            return self._failure_result(
                request,
                stage_results,
                [f"System error: {exc}"],
                [],
                artifact_paths,
                ["Review system logs and contact support if issue persists"],
            )

    def _stage_run_setup(self, request: BaselineEvaluationRequest) -> BaselineStageResult:
        """Stage 1: Create run and baseline stages."""
        stage_name = "run_setup"
        run_id = None
        details = {}

        try:
            # Create run
            from app.schemas.runs import RunCreate

            run_create = RunCreate(
                name=f"Baseline Evaluation - {request.strategy_name}",
                mode="baseline_evaluation",
                strategy_id=None,  # Will be linked to strategy later if needed
                exchange=request.exchange,
                quote_currency=request.stake_currency,
                trading_mode=request.trading_mode,
                timeframe=request.timeframe,
                pairs=request.pairs,
                timerange=request.timerange,
                risk_profile=request.risk_profile,
                analysis_depth=None,
                is_demo=False,
            )

            run = self.run_repository.create_run(run_create, create_default_stages=False)
            run_id = run["id"]

            # Create baseline-specific stages
            self.run_stage_repository.create_baseline_stages(run_id)

            # Update run status to running
            self.run_repository.update_status(run_id, "running")

            # Record request details safely
            details["run_id"] = run_id
            details["request_summary"] = {
                "strategy_name": request.strategy_name,
                "pairs": request.pairs,
                "timeframe": request.timeframe,
                "exchange": request.exchange,
                "risk_profile": request.risk_profile,
            }

            started_at = self._start_stage(stage_name, run_id)

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Run setup completed successfully",
                details=details,
            )

        except Exception as exc:
            if run_id:
                self.run_repository.update_status(run_id, "failed_controlled", str(exc))
            
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id or "unknown",
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_strategy_validation(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
    ) -> BaselineStageResult:
        """Stage 2: Validate strategy exists and is safe."""
        stage_name = "strategy_validation"
        details = {}
        warnings = []

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Validate strategy name
            is_valid_name, name_error = self.strategy_service.validate_strategy_name(request.strategy_name)
            if not is_valid_name:
                error_msg = self._get_error_message("strategy_validation_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="strategy_validation_failed",
                    details={"error": name_error},
                )

            # Check strategy exists
            strategy = self.strategy_service.find_strategy_by_name(request.strategy_name)
            if not strategy:
                error_msg = self._get_error_message("strategy_not_found")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="strategy_not_found",
                    details={"strategy_name": request.strategy_name},
                )

            # Validate strategy file path is safe
            if strategy.file_path:
                is_valid_path, path_error = self.strategy_service.validate_strategy_file_path(strategy.file_path)
                if not is_valid_path:
                    error_msg = self._get_error_message("unsafe_strategy_path")
                    return self._fail_stage(
                        stage_name=stage_name,
                        run_id=run_id,
                        started_at=started_at,
                        message=error_msg["short_message"],
                        error_code="unsafe_strategy_path",
                        details={"file_path": strategy.file_path, "error": path_error},
                    )

            details["strategy"] = {
                "strategy_name": strategy.strategy_name,
                "file_path": strategy.file_path,
                "has_sidecar": strategy.has_sidecar_json,
            }

            if not strategy.has_sidecar_json:
                warnings.append("Strategy missing sidecar .json file")

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Strategy validation completed successfully",
                details=details,
                warnings=warnings,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_config_generation(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
    ) -> BaselineStageResult:
        """Stage 3: Generate safe backtest configuration."""
        stage_name = "config_generation"
        details = {}

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Build config request
            # Convert stake_amount to string as required by FreqtradeBacktestConfigRequest
            if isinstance(request.stake_amount, str):
                stake_amount_str = request.stake_amount
            else:
                # It's a float or int, convert to string
                stake_amount_str = str(request.stake_amount)
            
            config_request = FreqtradeBacktestConfigRequest(
                run_id=run_id,
                strategy_name=request.strategy_name,
                pairs=request.pairs,
                timeframe=request.timeframe,
                exchange=request.exchange,
                stake_currency=request.stake_currency,
                stake_amount=stake_amount_str,
                max_open_trades=request.max_open_trades,
                trading_mode=request.trading_mode,
                timerange=request.timerange,
                dry_run_wallet=1000,  # Safe default
                data_format_ohlcv="feather",
            )

            # Generate config
            config_result = self.config_generator.write_backtest_config(config_request)

            if not config_result.success:
                error_msg = self._get_error_message("config_generation_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="config_generation_failed",
                    details={"error": config_result.error},
                )

            details["config_path"] = config_result.config_path
            details["artifact_id"] = config_result.artifact_id

            artifact_paths = []
            if config_result.config_path:
                artifact_paths.append(self._make_project_relative(config_result.config_path))

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Config generation completed successfully",
                details=details,
                artifacts=artifact_paths,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_data_check(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
        config_path: Optional[str],
    ) -> BaselineStageResult:
        """Stage 4: Check if required data exists."""
        stage_name = "data_check"
        details = {}
        warnings = []

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Build data check request
            data_check_request = FreqtradeDataCheckRequest(
                run_id=run_id,
                exchange=request.exchange,
                trading_mode=request.trading_mode,
                pairs=request.pairs,
                timeframe=request.timeframe,
                config_path=config_path,
            )

            # Check data availability
            data_check_result = self.data_service.check_data(data_check_request)

            # Check if any data is missing
            missing_data = any(not pair.exists for pair in data_check_result.pairs)
            details["missing_data"] = missing_data
            details["pair_statuses"] = [
                {"pair": p.pair, "exists": p.exists} for p in data_check_result.pairs
            ]

            if missing_data:
                if not request.download_missing_data:
                    error_msg = self._get_error_message("data_missing")
                    return self._fail_stage(
                        stage_name=stage_name,
                        run_id=run_id,
                        started_at=started_at,
                        message=error_msg["short_message"],
                        error_code="data_missing",
                        details={"missing_pairs": [p.pair for p in data_check_result.pairs if not p.exists]},
                    )
                else:
                    warnings.append("Required data is missing, download will be required")
                    if not request.user_confirmed:
                        error_msg = self._get_error_message("confirmation_required_for_download")
                        return self._confirmation_required(
                            stage_name=stage_name,
                            run_id=run_id,
                            started_at=started_at,
                            message=error_msg["short_message"],
                            details={"requires_confirmation": True},
                            error_code="confirmation_required_for_download",
                        )

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Data check completed successfully",
                details=details,
                warnings=warnings,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_data_download(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
        missing_data: bool,
    ) -> BaselineStageResult:
        """Stage 5: Download missing data if needed and confirmed."""
        stage_name = "data_download"
        details = {}

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Skip download if no missing data
            if not missing_data:
                return self._complete_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message="Data download skipped: data already exists",
                    details={"skipped": True, "reason": "No missing data"},
                )

            # Check if download is allowed and confirmed
            if not request.download_missing_data:
                return self._complete_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message="Data download skipped: download disabled",
                    details={"skipped": True, "reason": "Download disabled"},
                )

            if not request.user_confirmed:
                error_msg = self._get_error_message("confirmation_required_for_download")
                return self._confirmation_required(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    details={"requires_confirmation": True},
                )

            # Build download request
            download_request = FreqtradeDataDownloadRequest(
                run_id=run_id,
                exchange=request.exchange,
                trading_mode=request.trading_mode,
                pairs=request.pairs,
                timeframes=[request.timeframe],
                days=request.days,
                timerange=request.timerange,
                user_confirmed=True,
            )

            # Download data
            download_result = self.data_service.download_data(download_request)

            if not download_result.success:
                error_msg = self._get_error_message("data_download_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="data_download_failed",
                    details={"error": download_result.error},
                )

            details["download_duration"] = download_result.duration
            details["downloaded_pairs"] = download_result.pairs

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Data download completed successfully",
                details=details,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_baseline_backtest(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
        config_path: Optional[str],
    ) -> BaselineStageResult:
        """Stage 6: Run Freqtrade backtest if confirmed."""
        stage_name = "baseline_backtest"
        details = {}

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Check user confirmation
            if not request.user_confirmed:
                error_msg = self._get_error_message("confirmation_required_for_backtest")
                return self._confirmation_required(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    details={"requires_confirmation": True},
                    error_code="confirmation_required_for_backtest",
                )

            # Build backtest request
            backtest_request = FreqtradeBacktestRequest(
                run_id=run_id,
                strategy_name=request.strategy_name,
                config_path=config_path,
                timeframe=request.timeframe,
                pairs=request.pairs,
                timerange=request.timerange,
                export="trades",
            )

            # Run backtest
            backtest_result = self.backtest_runner.run_backtest(backtest_request)

            if not backtest_result.success:
                error_msg = self._get_error_message("backtest_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="backtest_failed",
                    details={
                        "error": backtest_result.error,
                        "exit_code": backtest_result.exit_code,
                    },
                )

            details["duration"] = backtest_result.duration_seconds
            details["exit_code"] = backtest_result.exit_code
            details["backtest_directory"] = backtest_result.backtest_directory

            # Collect artifact paths
            artifact_paths = []
            for artifact in backtest_result.artifacts:
                if artifact.path:
                    artifact_paths.append(self._make_project_relative(artifact.path))

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Backtest completed successfully",
                details=details,
                artifacts=artifact_paths,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_result_parsing(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
    ) -> BaselineStageResult:
        """Stage 7: Parse backtest results using Part 05 service."""
        stage_name = "result_parsing"
        details = {}
        warnings = []

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Parse results using existing service
            parse_result = self.result_parser.parse_run(run_id, force=request.force_parse)

            if not parse_result.success:
                error_msg = self._get_error_message("parse_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="parse_failed",
                    details={"errors": parse_result.errors},
                    warnings=parse_result.warnings,
                )

            details["metrics_saved"] = parse_result.metrics is not None
            details["pair_results_count"] = len(parse_result.pair_results) if parse_result.pair_results else 0
            details["trade_summary_saved"] = parse_result.trade_summary is not None
            details["quality_flags_count"] = len(parse_result.quality_report.flags) if parse_result.quality_report else 0

            if parse_result.warnings:
                warnings.extend(parse_result.warnings)

            # Collect normalized artifact path
            artifact_paths = []
            if parse_result.normalized_result_path:
                artifact_paths.append(self._make_project_relative(parse_result.normalized_result_path))

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Result parsing completed successfully",
                details=details,
                artifacts=artifact_paths,
                warnings=warnings,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_decision_evaluation(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
    ) -> BaselineStageResult:
        """Stage 8: Evaluate decision using Part 06 service."""
        stage_name = "decision_evaluation"
        details = {}
        warnings = []

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Build decision request
            decision_request = DecisionEvaluationRequest(
                run_id=run_id,
                policy_name=f"default_{request.risk_profile}",
                risk_profile=request.risk_profile,
                timeframe=request.timeframe,
                apply_to_run=request.apply_decision_to_run,
                force=False,
            )

            # Evaluate decision using existing service
            decision_response = self.decision_service.evaluate_run(decision_request)

            if not decision_response.success:
                error_msg = self._get_error_message("decision_failed")
                return self._fail_stage(
                    stage_name=stage_name,
                    run_id=run_id,
                    started_at=started_at,
                    message=error_msg["short_message"],
                    error_code="decision_failed",
                    details={"error": "Decision evaluation failed"},
                )

            details["classification"] = decision_response.classification
            details["confidence_score"] = decision_response.confidence_score
            details["policy_name"] = decision_response.policy_name
            details["next_actions"] = decision_response.next_actions or []
            details["run_updated"] = decision_response.run_updated

            if decision_response.warnings:
                warnings.extend(decision_response.warnings)

            # Collect decision report artifact path
            artifact_paths = []
            if decision_response.decision_report_path:
                artifact_paths.append(self._make_project_relative(decision_response.decision_report_path))

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Decision evaluation completed successfully",
                details=details,
                artifacts=artifact_paths,
                warnings=warnings,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _stage_baseline_report(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
        stage_results: list[BaselineStageResult],
        decision_details: dict,
    ) -> BaselineStageResult:
        """Stage 9: Create baseline evaluation report artifact."""
        stage_name = "baseline_report"
        details = {}

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Build report
            report = {
                "run_id": run_id,
                "request_summary": {
                    "strategy_name": request.strategy_name,
                    "pairs": request.pairs,
                    "timeframe": request.timeframe,
                    "exchange": request.exchange,
                    "risk_profile": request.risk_profile,
                    "stake_currency": request.stake_currency,
                    "stake_amount": request.stake_amount,
                    "max_open_trades": request.max_open_trades,
                    "trading_mode": request.trading_mode,
                },
                "stage_summary": {
                    stage.stage_name: {
                        "status": stage.status,
                        "duration_seconds": stage.duration_seconds,
                        "message": stage.message,
                    }
                    for stage in stage_results
                },
                "decision_summary": {
                    "classification": decision_details.get("classification"),
                    "confidence_score": decision_details.get("confidence_score"),
                    "policy_name": decision_details.get("policy_name"),
                },
                "warnings": [w for stage in stage_results for w in stage.warnings],
                "errors": [e for stage in stage_results for e in stage.errors],
                "next_actions": decision_details.get("next_actions", []),
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            # Write report artifact
            report_path = self.project_root / self.REPORT_RELATIVE_PATH.format(run_id=run_id)
            report_path.parent.mkdir(parents=True, exist_ok=True)

            with open(report_path, "w") as f:
                json.dump(report, f, indent=2)

            # Register artifact
            artifact = self.artifact_repository.create_artifact(
                ArtifactCreate(
                    run_id=run_id,
                    artifact_type="report_md",
                    file_path=str(report_path.relative_to(self.project_root)),
                    description="Baseline evaluation report",
                    metadata={"stage": "baseline_report"},
                )
            )

            details["report_path"] = str(report_path.relative_to(self.project_root))
            details["artifact_id"] = artifact["id"]

            artifact_paths = [str(report_path.relative_to(self.project_root))]

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Baseline report created successfully",
                details=details,
                artifacts=artifact_paths,
            )

        except Exception as exc:
            error_msg = self._get_error_message("baseline_report_failed")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="baseline_report_failed",
                details={"error": str(exc)},
            )

    def _stage_completion(
        self,
        run_id: str,
        request: BaselineEvaluationRequest,
        classification: Optional[str],
    ) -> BaselineStageResult:
        """Stage 10: Complete the run and set final status."""
        stage_name = "completion"
        details = {}

        try:
            started_at = self._start_stage(stage_name, run_id)

            # Update run status to completed
            self.run_repository.update_status(run_id, "completed")

            details["final_status"] = "completed"
            details["classification"] = classification

            # Audit log
            self._add_audit_log(
                run_id=run_id,
                action_type="baseline_evaluation_completed",
                before=None,
                after={
                    "status": "completed",
                    "classification": classification,
                },
            )

            return self._complete_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=started_at,
                message="Completion stage finished successfully",
                details=details,
            )

        except Exception as exc:
            error_msg = self._get_error_message("unexpected_pipeline_error")
            return self._fail_stage(
                stage_name=stage_name,
                run_id=run_id,
                started_at=datetime.now(timezone.utc),
                message=error_msg["short_message"],
                error_code="unexpected_pipeline_error",
                details={"error": str(exc)},
            )

    def _build_result(
        self,
        request: BaselineEvaluationRequest,
        run_id: str,
        success: bool,
        status: str,
        classification: Optional[str],
        confidence_score: Optional[float],
        stage_results: list[BaselineStageResult],
        artifact_paths: list[str],
        errors: list[str],
        warnings: list[str],
        next_actions: list[str],
    ) -> BaselineEvaluationResult:
        """Build the final baseline evaluation result."""
        # If no next_actions provided but we have a failed stage with error code, use its next_actions
        if not next_actions and stage_results:
            failed_stage = next((s for s in stage_results if s.status == "failed_controlled" and s.error_code), None)
            if failed_stage and failed_stage.error_code:
                error_msg = self._get_error_message(failed_stage.error_code)
                next_actions = error_msg.get("next_actions", [])
        
        # If confirmation required, use appropriate next_actions
        if status == "confirmation_required" and stage_results:
            waiting_stage = next((s for s in stage_results if s.status == "confirmation_required"), None)
            if waiting_stage and waiting_stage.error_code:
                error_msg = self._get_error_message(waiting_stage.error_code)
                next_actions = error_msg.get("next_actions", [])

        return BaselineEvaluationResult(
            success=success,
            run_id=run_id,
            status=status,
            classification=classification,
            confidence_score=confidence_score,
            strategy_name=request.strategy_name,
            pairs=request.pairs,
            timeframe=request.timeframe,
            exchange=request.exchange,
            risk_profile=request.risk_profile,
            metrics={},
            decision={},
            quality_flags=[],
            stage_results=stage_results,
            artifact_paths=artifact_paths,
            warnings=warnings,
            errors=errors,
            next_actions=next_actions,
        )

    def _failure_result(
        self,
        request: BaselineEvaluationRequest,
        stage_results: list[BaselineStageResult],
        errors: list[str],
        warnings: list[str],
        artifact_paths: list[str],
        next_actions: list[str],
    ) -> BaselineEvaluationResult:
        """Build a failure result."""
        return BaselineEvaluationResult(
            success=False,
            run_id=None,
            status="failed_controlled",
            classification=None,
            confidence_score=None,
            strategy_name=request.strategy_name,
            pairs=request.pairs,
            timeframe=request.timeframe,
            exchange=request.exchange,
            risk_profile=request.risk_profile,
            metrics={},
            decision={},
            quality_flags=[],
            stage_results=stage_results,
            artifact_paths=artifact_paths,
            warnings=warnings,
            errors=errors,
            next_actions=next_actions,
        )

    def _make_project_relative(self, absolute_path: str) -> str:
        """Convert an absolute path to project-relative."""
        try:
            path = Path(absolute_path)
            if path.is_absolute():
                return str(path.relative_to(self.project_root))
            return absolute_path
        except Exception:
            return absolute_path
