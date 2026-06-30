"""
Constants for HER backend.
Defines all allowed values for enums, statuses, and configurations.
"""
import os
from pathlib import Path

# =============================================================================
# Project Paths
# =============================================================================
# PROJECT_ROOT is derived from the location of this constants file
# This ensures the project root is always relative to the codebase location
# rather than hardcoded to a specific absolute path.
_CURRENT_FILE_PATH = Path(__file__).resolve()
_BACKEND_DIR = _CURRENT_FILE_PATH.parent.parent  # Go up from app/core to backend
_PROJECT_ROOT = _BACKEND_DIR.parent.parent  # Go up from backend to project root (backend is inside project root)

PROJECT_ROOT = str(_PROJECT_ROOT)
FREQTRADE_WORKSPACE = f"{PROJECT_ROOT}/freqtrade_workspace"
FREQTRADE_USER_DATA = f"{FREQTRADE_WORKSPACE}/user_data"
FREQTRADE_HYPEROPT_RESULTS = f"{FREQTRADE_USER_DATA}/hyperopt_results"
HER_ARTIFACTS = f"{PROJECT_ROOT}/artifacts"
HER_ARTIFACTS_RUNS = f"{HER_ARTIFACTS}/runs"

# =============================================================================
# Run Modes
# =============================================================================
RUN_MODES = [
    "upload_strategy",
    "generate_strategy",
    "repair_strategy",
    "optimize_strategy",
    "manual_test",
    "baseline_evaluation",
]

# =============================================================================
# Run Statuses
# =============================================================================
RUN_STATUSES = [
    "created",
    "queued",
    "running",
    "waiting_for_confirmation",
    "failed_controlled",
    "failed_system",
    "rejected",
    "candidate",
    "promising",
    "validated",
    "approved",
    "exported",
    "cancelled",
    "completed",
]

# =============================================================================
# Classifications
# =============================================================================
CLASSIFICATIONS = [
    "rejected",
    "candidate",
    "promising",
    "validated",
    "approved",
]

# =============================================================================
# Part 06 Decision Engine Persistence
# =============================================================================
DECISION_CLASSIFICATIONS = [
    "rejected",
    "candidate",
    "promising",
    "validated",
]

DECISION_GATE_STATUSES = [
    "passed",
    "failed",
    "warning",
    "not_applicable",
    "insufficient_data",
]

DECISION_REASON_SEVERITIES = [
    "info",
    "warning",
    "blocking",
]

DECISION_POLICY_NAMES = [
    "default_conservative",
    "default_balanced",
    "default_aggressive",
]

# =============================================================================
# Part 07 Baseline Evaluation Pipeline
# =============================================================================
BASELINE_PIPELINE_STAGES = [
    "run_setup",
    "strategy_validation",
    "config_generation",
    "data_check",
    "data_download",
    "baseline_backtest",
    "result_parsing",
    "decision_evaluation",
    "baseline_report",
    "completion",
]

BASELINE_PIPELINE_STATUSES = [
    "pending",
    "running",
    "completed",
    "failed_controlled",
    "confirmation_required",
]

BASELINE_ERROR_CODES = [
    "strategy_not_found",
    "strategy_validation_failed",
    "unsafe_strategy_path",
    "config_generation_failed",
    "data_missing",
    "confirmation_required_for_download",
    "confirmation_required_for_backtest",
    "data_download_failed",
    "backtest_failed",
    "backtest_artifacts_missing",
    "parse_failed",
    "decision_failed",
    "baseline_report_failed",
    "unexpected_pipeline_error",
]

BASELINE_ERROR_MESSAGES = {
    "strategy_not_found": {
        "short_message": "Strategy not found in Freqtrade workspace",
        "user_message": "The specified strategy was not found in the Freqtrade user strategies directory. Verify the strategy name and ensure it exists.",
        "next_actions": ["Verify strategy name spelling", "Check if strategy exists in Freqtrade workspace", "Upload strategy if missing"],
    },
    "strategy_validation_failed": {
        "short_message": "Strategy validation failed",
        "user_message": "Strategy name or structure validation failed. The strategy may have invalid naming or structure.",
        "next_actions": ["Review strategy naming conventions", "Check strategy file structure", "Fix validation errors and retry"],
    },
    "unsafe_strategy_path": {
        "short_message": "Strategy file path is unsafe",
        "user_message": "The strategy file path is outside the allowed workspace or contains unsafe components. HER only allows strategies within the Freqtrade user strategies directory.",
        "next_actions": ["Move strategy to Freqtrade user strategies directory", "Remove path traversal components", "Use a valid strategy path"],
    },
    "config_generation_failed": {
        "short_message": "Backtest configuration generation failed",
        "user_message": "HER could not generate a safe backtest configuration. This may be due to invalid parameters or configuration errors.",
        "next_actions": ["Review backtest parameters", "Check Freqtrade configuration requirements", "Review service logs for details"],
    },
    "data_missing": {
        "short_message": "Market data is missing",
        "user_message": "Market data is missing for the selected pair/timeframe. Enable download_missing_data and user_confirmed to let HER download it.",
        "next_actions": ["Enable download_missing_data in request", "Set user_confirmed to True", "Download data manually via Freqtrade"],
    },
    "confirmation_required_for_download": {
        "short_message": "Data download requires confirmation",
        "user_message": "Data download is required but needs user confirmation. Set user_confirmed to True to proceed with data download.",
        "next_actions": ["Set user_confirmed to True in request", "Review data download settings", "Confirm and retry"],
    },
    "confirmation_required_for_backtest": {
        "short_message": "Backtest execution requires confirmation",
        "user_message": "Backtest execution requires user confirmation. Set user_confirmed to True to proceed with backtest.",
        "next_actions": ["Set user_confirmed to True in request", "Review backtest parameters", "Confirm and retry"],
    },
    "data_download_failed": {
        "short_message": "Data download failed",
        "user_message": "HER attempted to download market data but the download failed. This may be due to network issues or exchange API limits.",
        "next_actions": ["Check network connectivity", "Review exchange API rate limits", "Download data manually via Freqtrade"],
    },
    "backtest_failed": {
        "short_message": "Freqtrade backtest failed",
        "user_message": "Freqtrade backtest failed. HER saved raw stdout/stderr artifacts for inspection and stopped before parsing.",
        "next_actions": ["Review backtest error logs in artifacts", "Check strategy for runtime errors", "Verify backtest configuration"],
    },
    "backtest_artifacts_missing": {
        "short_message": "Backtest artifacts are missing",
        "user_message": "Backtest completed but expected output files are missing. HER cannot parse results without artifacts.",
        "next_actions": ["Check Freqtrade backtest directory", "Review backtest logs", "Re-run backtest with debugging"],
    },
    "parse_failed": {
        "short_message": "Backtest result parsing failed",
        "user_message": "HER could not parse backtest results. The output format may be unexpected or corrupted.",
        "next_actions": ["Review raw backtest outputs", "Check Freqtrade version compatibility", "Review parsing service logs"],
    },
    "decision_failed": {
        "short_message": "Decision evaluation failed",
        "user_message": "Backtest parsed, but HER could not evaluate the decision. Check parsed metrics and decision service logs.",
        "next_actions": ["Review parsed metrics in database", "Check decision engine configuration", "Review decision service logs"],
    },
    "baseline_report_failed": {
        "short_message": "Baseline report creation failed",
        "user_message": "HER could not create the baseline evaluation report artifact. This may be due to file system issues.",
        "next_actions": ["Check file system permissions", "Review artifact directory", "Review service logs"],
    },
    "unexpected_pipeline_error": {
        "short_message": "Unexpected pipeline error occurred",
        "user_message": "An unexpected error occurred during pipeline execution. Review system logs for details.",
        "next_actions": ["Review system logs", "Contact support if issue persists", "Check system resources"],
    },
}

BASELINE_EVALUATION_MODES = [
    "real",
]

# =============================================================================
# Part 08 Optimization Pipeline
# =============================================================================
OPTIMIZATION_STAGES = [
    "optimization_setup",
    "baseline_reference",
    "hyperopt_policy_validation",
    "hyperopt_config_generation",
    "data_check",
    "data_download",
    "hyperopt_execution",
    "hyperopt_result_parsing",
    "trial_persistence",
    "best_trial_selection",
    "optimized_config_generation",
    "optimized_backtest",
    "optimized_result_parsing",
    "optimized_decision_evaluation",
    "baseline_vs_optimized_comparison",
    "optimization_report",
    "completion",
]

OPTIMIZATION_STATUSES = [
    "pending",
    "running",
    "completed",
    "failed_controlled",
    "confirmation_required",
]

OPTIMIZATION_RESULT_STATUSES = [
    "not_improved",
    "improved",
    "optimization_candidate",
    "optimization_promising",
    "optimization_rejected",
    "overfit_suspected",
    "invalid_optimization",
]

OPTIMIZATION_TRIAL_STATUSES = [
    "completed",
    "failed",
    "ignored",
    "best",
    "selected_for_validation",
    "rejected",
]

OPTIMIZATION_ERROR_CODES = [
    "hyperopt_policy_invalid",
    "hyperopt_config_generation_failed",
    "hyperopt_execution_failed",
    "hyperopt_results_missing",
    "trial_persistence_failed",
    "best_trial_selection_failed",
    "optimized_config_generation_failed",
    "optimized_backtest_failed",
    "optimized_parse_failed",
    "optimized_decision_failed",
    "comparison_failed",
    "optimization_report_failed",
]

OPTIMIZATION_ERROR_MESSAGES = {
    "hyperopt_policy_invalid": {
        "short_message": "Hyperopt policy is invalid",
        "user_message": "The hyperopt configuration violates safety rules. Check epochs, spaces, and parameter limits.",
        "next_actions": ["Review hyperopt policy settings", "Check epochs are within limits", "Verify spaces are allowed"],
    },
    "hyperopt_config_generation_failed": {
        "short_message": "Hyperopt config generation failed",
        "user_message": "HER could not generate a safe hyperopt configuration. This may be due to invalid parameters.",
        "next_actions": ["Review hyperopt parameters", "Check Freqtrade hyperopt requirements", "Review service logs for details"],
    },
    "hyperopt_execution_failed": {
        "short_message": "Freqtrade hyperopt failed",
        "user_message": "Freqtrade hyperopt failed. HER saved raw stdout/stderr artifacts for inspection.",
        "next_actions": ["Review hyperopt error logs in artifacts", "Check strategy for runtime errors", "Verify hyperopt configuration"],
    },
    "hyperopt_results_missing": {
        "short_message": "Hyperopt results are missing",
        "user_message": "Hyperopt completed but expected output files are missing. HER cannot parse results without artifacts.",
        "next_actions": ["Check Freqtrade hyperopt directory", "Review hyperopt logs", "Re-run hyperopt with debugging"],
    },
    "trial_persistence_failed": {
        "short_message": "Trial persistence failed",
        "user_message": "HER could not persist optimization trials to the database. This may be due to database issues.",
        "next_actions": ["Check database connectivity", "Review database logs", "Retry the optimization"],
    },
    "best_trial_selection_failed": {
        "short_message": "Best trial selection failed",
        "user_message": "HER could not select the best trial from the optimization results. Check trial data quality.",
        "next_actions": ["Review trial data in database", "Check objective function", "Review selection logic"],
    },
    "optimized_config_generation_failed": {
        "short_message": "Optimized config generation failed",
        "user_message": "HER could not generate a config with the best trial parameters. This may be due to invalid parameters.",
        "next_actions": ["Review best trial parameters", "Check parameter validation", "Review service logs for details"],
    },
    "optimized_backtest_failed": {
        "short_message": "Optimized backtest failed",
        "user_message": "Freqtrade backtest with optimized parameters failed. HER saved raw stdout/stderr artifacts for inspection.",
        "next_actions": ["Review backtest error logs in artifacts", "Check optimized parameters", "Verify backtest configuration"],
    },
    "optimized_parse_failed": {
        "short_message": "Optimized result parsing failed",
        "user_message": "HER could not parse optimized backtest results. The output format may be unexpected or corrupted.",
        "next_actions": ["Review raw backtest outputs", "Check Freqtrade version compatibility", "Review parsing service logs"],
    },
    "optimized_decision_failed": {
        "short_message": "Optimized decision evaluation failed",
        "user_message": "Optimized backtest parsed, but HER could not evaluate the decision. Check parsed metrics and decision service logs.",
        "next_actions": ["Review parsed metrics in database", "Check decision engine configuration", "Review decision service logs"],
    },
    "comparison_failed": {
        "short_message": "Baseline vs optimized comparison failed",
        "user_message": "HER could not compare baseline and optimized results. Check both result sets exist.",
        "next_actions": ["Review baseline results", "Review optimized results", "Check comparison logic"],
    },
    "optimization_report_failed": {
        "short_message": "Optimization report creation failed",
        "user_message": "HER could not create the optimization report artifact. This may be due to file system issues.",
        "next_actions": ["Check file system permissions", "Review artifact directory", "Review service logs"],
    },
}

# =============================================================================
# Part 13 Validation Evidence Layer
# =============================================================================
VALIDATION_STAGES = [
    "validation_setup",
    "candidate_reference",
    "readiness_gate",
    "oos_timerange_split",
    "oos_backtest",
    "oos_result_parsing",
    "oos_decision",
    "wfo_window_generation",
    "wfo_window_execution",
    "wfo_result_parsing",
    "wfo_decision",
    "robustness_checks",
    "sensitivity_checks",
    "validation_decision",
    "validation_report",
    "completion",
]

VALIDATION_STATUSES = [
    "pending",
    "running",
    "completed",
    "failed_controlled",
    "confirmation_required",
]

VALIDATION_DECISION_STATUSES = [
    "not_validated",
    "oos_failed",
    "oos_passed",
    "wfo_failed",
    "wfo_passed",
    "robustness_failed",
    "robustness_passed",
    "validated",
    "rejected",
    "validation_error",
]

VALIDATION_SOURCE_TYPES = [
    "strategy",
    "baseline_run",
    "optimization_run",
    "optimized_run",
]

VALIDATION_EVIDENCE_TYPES = [
    "oos",
    "wfo_window",
    "wfo_summary",
    "robustness",
    "sensitivity",
    "validation_decision",
]

# =============================================================================
# Stage Statuses
# =============================================================================
STAGE_STATUSES = [
    "pending",
    "running",
    "passed",
    "failed",
    "skipped",
    "waiting",
]

# =============================================================================
# Strategy Source Types
# =============================================================================
STRATEGY_SOURCE_TYPES = [
    "uploaded",
    "generated",
    "repaired",
    "manual",
    "imported",
    "demo",
]

# =============================================================================
# Strategy Directions
# =============================================================================
STRATEGY_DIRECTIONS = [
    "long",
    "short",
    "both",
    "unknown",
]

# =============================================================================
# Strategy Statuses
# =============================================================================
STRATEGY_STATUSES = [
    "draft",
    "active",
    "candidate",
    "validated",
    "approved",
    "rejected",
    "archived",
]

# =============================================================================
# Artifact Types
# =============================================================================
ARTIFACT_TYPES = [
    "strategy_py",
    "strategy_json",
    "strategy_spec",
    "freqtrade_config",
    "backtest_raw",
    "hyperopt_raw",
    "optimized_params",
    "metrics_json",
    "report_md",
    "export_package",
    "log_file",
    "chart",
    "other",
]

# =============================================================================
# Log Levels
# =============================================================================
LOG_LEVELS = [
    "info",
    "warning",
    "error",
    "debug",
    "critical",
]

# =============================================================================
# Retry Statuses
# =============================================================================
RETRY_STATUSES = [
    "proposed",
    "approved",
    "applied",
    "failed",
    "rejected",
    "skipped",
]

# =============================================================================
# Audit Actors
# =============================================================================
AUDIT_ACTORS = [
    "user",
    "system",
    "ai_assistant",
    "ai_strategy_designer",
    "ai_repair_agent",
]

# =============================================================================
# Freqtrade Command Safety
# =============================================================================
FREQTRADE_ALLOWED_COMMANDS_PART_04 = [
    "create-userdir",
    "show-config",
    "list-strategies",
    "list-data",
    "download-data",
    "backtesting",
]

# Part 08 adds hyperopt commands
FREQTRADE_ALLOWED_COMMANDS_PART_08 = [
    "create-userdir",
    "show-config",
    "list-strategies",
    "list-data",
    "download-data",
    "backtesting",
    "hyperopt",
    "hyperopt-list",
    "hyperopt-show",
]

FREQTRADE_VERSION_COMMAND = "--version"

FREQTRADE_FORBIDDEN_COMMANDS = [
    "trade",
    "webserver",
    "edge",
    "install-ui",
]

# =============================================================================
# Default AutoQuant Run Stages
# =============================================================================
DEFAULT_RUN_STAGES = [
    {
        "stage_key": "run_setup",
        "stage_name": "Run Setup",
        "order_index": 1,
    },
    {
        "stage_key": "preflight_checks",
        "stage_name": "Preflight Checks",
        "order_index": 2,
    },
    {
        "stage_key": "strategy_normalization",
        "stage_name": "Strategy Normalization",
        "order_index": 3,
    },
    {
        "stage_key": "pair_timeframe_selection",
        "stage_name": "Pair and Timeframe Selection",
        "order_index": 4,
    },
    {
        "stage_key": "data_availability",
        "stage_name": "Data Availability Check",
        "order_index": 5,
    },
    {
        "stage_key": "baseline_backtest",
        "stage_name": "Baseline Backtest",
        "order_index": 6,
    },
    {
        "stage_key": "initial_decision",
        "stage_name": "Initial Decision",
        "order_index": 7,
    },
    {
        "stage_key": "hyperopt",
        "stage_name": "Hyperopt Optimization",
        "order_index": 8,
    },
    {
        "stage_key": "walk_forward_oos",
        "stage_name": "Walk-Forward Out-of-Sample",
        "order_index": 9,
    },
    {
        "stage_key": "robustness",
        "stage_name": "Robustness Analysis",
        "order_index": 10,
    },
    {
        "stage_key": "final_classification",
        "stage_name": "Final Classification",
        "order_index": 11,
    },
    {
        "stage_key": "export",
        "stage_name": "Export Strategy",
        "order_index": 12,
    },
    {
        "stage_key": "notification",
        "stage_name": "Notification",
        "order_index": 13,
    },
]
