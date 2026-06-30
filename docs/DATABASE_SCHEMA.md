# HER Database Schema Documentation

## Overview

HER uses SQLite as its database, stored at `data/her.db`. The schema is designed to support the AutoQuant run lifecycle, strategy management, artifact tracking, metrics storage, and audit logging.

**Schema Version:** 0.5.0  
**Database Layer:** sqlite3_repositories  
**Setup Part:** Part 03 (with Part 06 and Part 08 additions)

## Design Principles

1. **Local-Only Storage:** All data remains on the local machine
2. **Filesystem Artifacts:** Large files (strategies, backtest results, charts) are stored in the filesystem, with metadata in SQLite
3. **Audit Trail:** All important actions are logged for traceability
4. **Idempotent Migrations:** Schema changes use CREATE IF NOT EXISTS for safe re-runs
5. **No ORM:** Direct sqlite3 access for simplicity and control

## Part 02 Tables (System Foundation)

### app_meta
Application metadata and configuration keys.

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT PRIMARY KEY | Metadata key |
| value | TEXT NOT NULL | Metadata value |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Usage:** Stores schema version, project version, setup part, and other application-wide metadata.

### system_events
System-level event logging for debugging and monitoring.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Event ID |
| level | TEXT NOT NULL | Event level (info, warning, error) |
| source | TEXT NOT NULL | Event source (backend, frontend) |
| message | TEXT NOT NULL | Event message |
| details_json | TEXT | Optional details as JSON |
| created_at | TEXT NOT NULL | Event timestamp |

**Indexes:** idx_system_events_created_at, idx_system_events_level, idx_system_events_source

### local_settings
Local configuration settings with secret protection.

| Column | Type | Description |
|--------|------|-------------|
| key | TEXT PRIMARY KEY | Setting key |
| value_json | TEXT NOT NULL | Setting value as JSON |
| is_secret | INTEGER NOT NULL DEFAULT 0 | Whether value contains secrets |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Usage:** Stores user preferences, integration configurations, and other settings. Secret values are never exposed in API responses.

## Part 03 Tables (AutoQuant Backend Core)

### runs
Stores AutoQuant run lifecycle data and configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Run ID (UUID) |
| name | TEXT NOT NULL | Run name |
| mode | TEXT NOT NULL | Run mode (upload_strategy, generate_strategy, repair_strategy, optimize_strategy, manual_test) |
| status | TEXT NOT NULL | Run status (created, queued, running, waiting_for_confirmation, failed_controlled, failed_system, rejected, candidate, promising, validated, approved, exported, cancelled) |
| classification | TEXT | Final classification (rejected, candidate, promising, validated, approved) |
| strategy_id | TEXT | Associated strategy ID |
| parent_run_id | TEXT | Parent run ID for retries |
| exchange | TEXT | Exchange name |
| quote_currency | TEXT | Quote currency |
| trading_mode | TEXT | Trading mode |
| timeframe | TEXT | Timeframe |
| pairs_json | TEXT | Trading pairs as JSON |
| timerange | TEXT | Time range for backtest |
| risk_profile | TEXT | Risk profile (conservative, moderate, aggressive) |
| analysis_depth | TEXT | Analysis depth level |
| is_demo | INTEGER NOT NULL DEFAULT 0 | Whether this is a demo run |
| failure_reason | TEXT | Reason for failure |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |
| started_at | TEXT | Run start timestamp |
| completed_at | TEXT | Run completion timestamp |

**Indexes:** idx_runs_status, idx_runs_classification, idx_runs_strategy_id, idx_runs_created_at, idx_runs_parent_run_id

**Relationships:** 
- strategy_id → strategies.id
- parent_run_id → runs.id (self-reference for retry chains)

### run_stages
Stores individual stage execution data for each run.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Stage ID (UUID) |
| run_id | TEXT NOT NULL | Parent run ID |
| stage_key | TEXT NOT NULL | Stage identifier (e.g., "validation", "backtest", "analysis") |
| stage_name | TEXT NOT NULL | Human-readable stage name |
| order_index | INTEGER NOT NULL | Execution order |
| status | TEXT NOT NULL | Stage status (pending, running, passed, failed, skipped, waiting) |
| started_at | TEXT | Stage start timestamp |
| completed_at | TEXT | Stage completion timestamp |
| duration_ms | INTEGER | Stage duration in milliseconds |
| input_json | TEXT | Stage input as JSON |
| output_json | TEXT | Stage output as JSON |
| error_json | TEXT | Error details as JSON |
| logs_summary | TEXT | Log summary |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Unique Constraint:** (run_id, stage_key)

**Indexes:** idx_run_stages_run_id, idx_run_stages_status, idx_run_stages_order

**Relationships:** run_id → runs.id

### strategies
Stores strategy metadata and current status.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Strategy ID (UUID) |
| name | TEXT NOT NULL | Strategy name |
| class_name | TEXT | Python class name |
| source_type | TEXT NOT NULL | Source type (uploaded, generated, repaired, imported, demo) |
| current_version_id | TEXT | Current version ID |
| timeframe | TEXT | Strategy timeframe |
| direction | TEXT | Trading direction (long, short, both, unknown) |
| file_path | TEXT | Path to strategy .py file |
| params_path | TEXT | Path to strategy .json config |
| status | TEXT NOT NULL | Strategy status (draft, active, candidate, validated, approved, rejected, archived) |
| is_demo | INTEGER NOT NULL DEFAULT 0 | Whether this is a demo strategy |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Indexes:** idx_strategies_name, idx_strategies_status, idx_strategies_source_type

**Relationships:** current_version_id → strategy_versions.id

### strategy_versions
Stores version history for strategies.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Version ID (UUID) |
| strategy_id | TEXT NOT NULL | Parent strategy ID |
| version_number | INTEGER NOT NULL | Version number |
| py_path | TEXT | Path to .py file |
| json_path | TEXT | Path to .json config |
| spec_json | TEXT | Strategy specification as JSON |
| params_json | TEXT | Parameters as JSON |
| code_hash | TEXT | Hash of strategy code |
| created_from_run_id | TEXT | Run that created this version |
| notes | TEXT | Version notes |
| created_at | TEXT NOT NULL | Creation timestamp |

**Unique Constraint:** (strategy_id, version_number)

**Relationships:** 
- strategy_id → strategies.id
- created_from_run_id → runs.id

### artifacts
Stores metadata for generated artifacts (files stored in filesystem).

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Artifact ID (UUID) |
| run_id | TEXT | Associated run ID |
| strategy_id | TEXT | Associated strategy ID |
| artifact_type | TEXT NOT NULL | Artifact type (strategy_py, strategy_json, strategy_spec, freqtrade_config, backtest_raw, hyperopt_raw, metrics_json, report_md, export_package, log_file, chart, other) |
| path | TEXT NOT NULL | Filesystem path to artifact |
| sha256 | TEXT | SHA256 hash of file |
| size_bytes | INTEGER | File size in bytes |
| description | TEXT | Artifact description |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_artifacts_run_id, idx_artifacts_strategy_id, idx_artifacts_type

**Relationships:** 
- run_id → runs.id
- strategy_id → strategies.id

**Note:** Actual file content is stored in the filesystem (artifacts/runs/), not in SQLite.

### metrics_snapshots
Stores metrics snapshots at different stages of a run.

Part 05 backtest parsing writes normalized aggregate metrics here with `stage_key=backtest_result_parse`. Metric snapshots append by default so parse history is preserved. When parser `force=true` is used, previous snapshots for that run may be deleted before saving the current parse result.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Snapshot ID (UUID) |
| run_id | TEXT NOT NULL | Parent run ID |
| stage_key | TEXT | Stage that produced these metrics |
| net_profit | REAL | Net profit |
| profit_factor | REAL | Profit factor |
| max_drawdown | REAL | Maximum drawdown |
| sharpe | REAL | Sharpe ratio |
| calmar | REAL | Calmar ratio |
| win_rate | REAL | Win rate |
| trade_count | INTEGER | Total trade count |
| expectancy | REAL | Expectancy |
| avg_win | REAL | Average win |
| avg_loss | REAL | Average loss |
| raw_json | TEXT | Full metrics as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_metrics_run_id

**Relationships:** run_id → runs.id

### pair_results
Stores per-pair backtest results.

Part 05 parser writes normalized pair results here. Rows are upserted by the existing `(run_id, pair)` unique constraint so repeated parses replace the latest pair evidence instead of duplicating it.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Result ID (UUID) |
| run_id | TEXT NOT NULL | Parent run ID |
| pair | TEXT NOT NULL | Trading pair |
| net_profit | REAL | Net profit for pair |
| profit_factor | REAL | Profit factor for pair |
| max_drawdown | REAL | Max drawdown for pair |
| trade_count | INTEGER | Trade count for pair |
| win_rate | REAL | Win rate for pair |
| expectancy | REAL | Expectancy for pair |
| raw_json | TEXT | Full results as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Unique Constraint:** (run_id, pair)

**Indexes:** idx_pair_results_run_id

**Relationships:** run_id → runs.id

### trade_summaries
Stores aggregated trade statistics for a run.

Part 05 parser writes the normalized aggregate trade summary here. Because this table has no unique `run_id` constraint, parser re-runs replace prior summaries for the run before inserting the latest summary.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Summary ID (UUID) |
| run_id | TEXT NOT NULL | Parent run ID |
| total_trades | INTEGER | Total trades |
| wins | INTEGER | Winning trades |
| losses | INTEGER | Losing trades |
| draws | INTEGER | Break-even trades |
| avg_duration | TEXT | Average trade duration |
| best_pair | TEXT | Best performing pair |
| worst_pair | TEXT | Worst performing pair |
| raw_json | TEXT | Full summary as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_trade_summaries_run_id

**Relationships:** run_id → runs.id

### decision_results
Stores Part 06 decision results produced from already-parsed Part 05 evidence.

Decision rows are evidence and classification records only. The repository that writes this table does not run Freqtrade, call Ollama, send Discord messages, export strategies, modify strategy files, or approve strategies. Complex decision details are stored as JSON text so each decision can be explained and audited later.

Allowed Part 06 classifications are limited to:

- `rejected`
- `candidate`
- `promising`
- `validated`

Forbidden Part 06 outcomes such as `approved`, `exported`, `live_ready`, and `profitable_guaranteed` must not be stored in this table.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Decision result ID (UUID) |
| run_id | TEXT NOT NULL | Parent run ID |
| classification | TEXT NOT NULL | Part 06 classification |
| confidence_score | REAL | Evidence-strength score, not profitability probability |
| policy_name | TEXT NOT NULL | Decision policy name |
| risk_profile | TEXT | Risk profile used for threshold selection |
| timeframe | TEXT | Timeframe used for threshold selection |
| decision_json | TEXT NOT NULL | Full sanitized decision payload as JSON |
| gates_json | TEXT | Gate results as JSON |
| reasons_json | TEXT | Decision reasons as JSON |
| evidence_json | TEXT | Parsed evidence references and metric values as JSON |
| warnings_json | TEXT | Non-blocking warnings as JSON |
| blocking_failures_json | TEXT | Blocking failure codes/messages as JSON |
| normalized_result_artifact_path | TEXT | Normalized Part 05 artifact path used as evidence |
| created_at | TEXT NOT NULL | Decision timestamp |

**Indexes:** idx_decision_results_run_id, idx_decision_results_classification, idx_decision_results_created_at, idx_decision_results_policy_name

**Relationships:** run_id → runs.id

### run_logs
Detailed logging for run execution.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Log entry ID (UUID) |
| run_id | TEXT | Associated run ID |
| stage_key | TEXT | Associated stage |
| level | TEXT NOT NULL | Log level (debug, info, warning, error, critical) |
| source | TEXT NOT NULL | Log source |
| message | TEXT NOT NULL | Log message |
| details_json | TEXT | Additional details as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_run_logs_run_id, idx_run_logs_stage_key, idx_run_logs_level, idx_run_logs_created_at

**Relationships:** run_id → runs.id

### retry_history
Stores retry attempt information for failed runs.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Retry ID (UUID) |
| run_id | TEXT NOT NULL | Original failed run ID |
| parent_run_id | TEXT | Parent run ID |
| attempt_number | INTEGER NOT NULL | Retry attempt number |
| reason | TEXT NOT NULL | Reason for retry |
| proposed_fix_json | TEXT | Proposed fix as JSON |
| applied_fix_json | TEXT | Applied fix as JSON |
| status | TEXT NOT NULL | Retry status (proposed, approved, applied, failed, rejected, skipped) |
| error_message | TEXT | Error message if failed |
| created_at | TEXT NOT NULL | Creation timestamp |
| completed_at | TEXT | Completion timestamp |

**Indexes:** idx_retry_history_run_id, idx_retry_history_parent_run_id

**Relationships:** 
- run_id → runs.id
- parent_run_id → runs.id

### audit_logs
Audit trail for important system actions.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Audit entry ID (UUID) |
| run_id | TEXT | Associated run ID |
| action_type | TEXT NOT NULL | Action type |
| actor | TEXT NOT NULL | Actor (user, system, ai_assistant, ai_strategy_designer, ai_repair_agent) |
| approved | INTEGER NOT NULL DEFAULT 0 | Whether action was approved |
| description | TEXT NOT NULL | Action description |
| before_json | TEXT | State before action |
| after_json | TEXT | State after action |
| changed_files_json | TEXT | List of changed files |
| rollback_path | TEXT | Path to rollback data |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_audit_logs_run_id, idx_audit_logs_action_type, idx_audit_logs_created_at

**Relationships:** run_id → runs.id

## Part 08 Tables (Optimization Pipeline)

### optimization_runs

Stores optimization run metadata and configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Optimization run ID (UUID) |
| parent_run_id | TEXT | Parent run ID for retry chains |
| baseline_run_id | TEXT | Baseline run ID for comparison |
| optimized_run_id | TEXT | Optimized backtest run ID |
| strategy_name | TEXT NOT NULL | Strategy name |
| timeframe | TEXT NOT NULL | Timeframe |
| pairs_json | TEXT NOT NULL | Trading pairs as JSON |
| exchange | TEXT NOT NULL | Exchange name |
| risk_profile | TEXT | Risk profile |
| status | TEXT NOT NULL | Run status (pending, running, completed, failed_controlled, confirmation_required) |
| result_status | TEXT | Result status (not_improved, improved, optimization_candidate, optimization_promising, optimization_rejected, overfit_suspected, invalid_optimization) |
| best_trial_id | TEXT | Best trial ID |
| epochs_requested | INTEGER | Requested hyperopt epochs |
| epochs_completed | INTEGER | Completed hyperopt epochs |
| spaces_json | TEXT | Hyperopt spaces as JSON |
| policy_json | TEXT | Hyperopt policy as JSON |
| request_json | TEXT | Full request as JSON |
| comparison_json | TEXT | Baseline vs optimized comparison as JSON |
| report_artifact_path | TEXT | Path to optimization report artifact |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Indexes:** idx_optimization_runs_strategy_name, idx_optimization_runs_status, idx_optimization_runs_result_status, idx_optimization_runs_created_at

**Relationships:**
- parent_run_id → runs.id
- baseline_run_id → runs.id
- optimized_run_id → runs.id
- best_trial_id → optimization_trials.id

### optimization_trials

Stores every optimization trial for complete traceability.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Trial ID (UUID) |
| optimization_run_id | TEXT NOT NULL | Parent optimization run ID |
| trial_number | INTEGER NOT NULL | Trial sequence number |
| status | TEXT NOT NULL | Trial status (completed, failed, ignored, best, selected_for_validation, rejected) |
| is_best | INTEGER NOT NULL DEFAULT 0 | Whether this is the best trial |
| is_selected_for_validation | INTEGER NOT NULL DEFAULT 0 | Whether selected for optimized backtest |
| params_json | TEXT NOT NULL | Full parameters as JSON |
| buy_params_json | TEXT | Buy parameters as JSON |
| sell_params_json | TEXT | Sell parameters as JSON |
| roi_params_json | TEXT | ROI parameters as JSON |
| stoploss_params_json | TEXT | Stoploss parameters as JSON |
| trailing_params_json | TEXT | Trailing parameters as JSON |
| metrics_json | TEXT | Trial metrics as JSON |
| loss_score | REAL | Loss score from hyperopt |
| profit_total | REAL | Total profit |
| profit_factor | REAL | Profit factor |
| expectancy | REAL | Trade expectancy |
| max_drawdown | REAL | Maximum drawdown |
| trade_count | INTEGER | Total trade count |
| win_rate | REAL | Win rate |
| rejection_reason | TEXT | Reason if trial was rejected |
| failure_reason | TEXT | Reason if trial failed |
| artifact_paths_json | TEXT | Trial artifact paths as JSON |
| raw_trial_json | TEXT | Raw hyperopt trial data as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_optimization_trials_run_id, idx_optimization_trials_trial_number, idx_optimization_trials_is_best, idx_optimization_trials_status

**Relationships:** optimization_run_id → optimization_runs.id

**Important:** Every trial is persisted, not just the best trial. This enables frontend inspection of the complete optimization history and analysis of parameter space exploration.

## Data Storage Strategy

### What is Stored in SQLite

- **Metadata:** Run configurations, strategy metadata, artifact metadata
- **Metrics:** Numerical metrics and KPIs
- **Decision Evidence:** Part 06 decision results, gate outcomes, reasons, and evidence references
- **Status:** Run status, stage status, strategy status
- **Logs:** System events, run logs, audit trail
- **References:** File paths to artifacts stored in filesystem
- **Relationships:** Foreign keys linking related entities

### What is Stored in Filesystem

- **Strategy Files:** .py strategy files (freqtrade_workspace/user_data/strategies/)
- **Strategy Configs:** .json parameter files (freqtrade_workspace/user_data/strategies/)
- **Backtest Results:** Raw Freqtrade backtest output (freqtrade_workspace/user_data/backtest_results/)
- **Hyperopt Results:** Raw Freqtrade hyperopt output (freqtrade_workspace/user_data/hyperopt_results/)
- **Charts:** Plot files (freqtrade_workspace/user_data/plot/)
- **Export Packages:** Complete export bundles (exports/)
- **Run Artifacts:** Per-run artifact directories (artifacts/runs/{run_id}/)
- **Normalized Backtest Results:** Parsed backtest result JSON (artifacts/runs/{run_id}/normalized/backtest_result.normalized.json)

### What is Intentionally Not Stored in SQLite

- **Large Binary Data:** No file content stored in database
- **Market Data:** Raw OHLCV data not stored (managed by Freqtrade)
- **Trade Lists:** Individual trade details stored in Freqtrade results, not duplicated
- **Parser Decisions:** Approval, rejection, profitability classification, and trading readiness are not stored by the Part 05 parser
- **Strategy Code:** Strategy source code stored in filesystem, referenced by path
- **Secrets:** Secrets stored in .env file only, never in database

### Part 05 Parser Persistence Notes

The backtest result parser persists evidence only:

- Aggregate metrics go to `metrics_snapshots`.
- Pair evidence goes to `pair_results`.
- Aggregate trade counts go to `trade_summaries`.
- Quality flags go to audit evidence and normalized artifacts.
- Parser activity goes to `run_logs` and `audit_logs`.
- The normalized artifact is registered in `artifacts` as `metrics_json`.

The parser does not change run status, strategy classification, or approval fields.

### Part 06 Decision Persistence Notes

The Part 06 persistence layer stores decision results only after parsed evidence already exists:

- Decision rows go to `decision_results`.
- Full decision payloads are stored in `decision_json`.
- Gate results, reasons, evidence, warnings, and blocking failures are also stored in dedicated JSON columns for efficient retrieval.
- Secret-like keys are redacted before JSON is persisted.
- The decision repository does not update `runs.classification`; service-level logic will own that in a later implementation step.
- The decision repository does not approve or export strategies and does not write forbidden Part 06 outcomes.

## Part 08 Tables (Optimization Pipeline)

### optimization_runs
Stores optimization run lifecycle data and configuration.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Optimization run ID (UUID) |
| parent_run_id | TEXT | Parent run ID for retry chains |
| baseline_run_id | TEXT | Baseline run ID for comparison |
| optimized_run_id | TEXT | Optimized backtest run ID |
| strategy_name | TEXT NOT NULL | Strategy name |
| timeframe | TEXT NOT NULL | Timeframe |
| pairs_json | TEXT NOT NULL | Trading pairs as JSON |
| exchange | TEXT NOT NULL | Exchange name |
| risk_profile | TEXT | Risk profile (conservative, balanced, aggressive) |
| status | TEXT NOT NULL | Optimization status (pending, running, completed, failed_controlled, confirmation_required) |
| result_status | TEXT | Result status (not_improved, improved, optimization_candidate, optimization_promising, optimization_rejected, overfit_suspected, invalid_optimization) |
| best_trial_id | TEXT | Best trial ID |
| epochs_requested | INTEGER | Number of hyperopt epochs requested |
| epochs_completed | INTEGER | Number of hyperopt epochs completed |
| spaces_json | TEXT | Hyperopt spaces as JSON |
| policy_json | TEXT | Hyperopt policy as JSON |
| request_json | TEXT | Original request as JSON |
| comparison_json | TEXT | Baseline vs optimized comparison as JSON |
| report_artifact_path | TEXT | Path to optimization report artifact |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Indexes:** idx_optimization_runs_strategy_name, idx_optimization_runs_status, idx_optimization_runs_result_status, idx_optimization_runs_created_at

**Relationships:**
- parent_run_id → runs.id
- baseline_run_id → runs.id
- optimized_run_id → runs.id
- best_trial_id → optimization_trials.id

### optimization_trials
Stores individual optimization trial data for every trial (not just best).

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Trial ID (UUID) |
| optimization_run_id | TEXT NOT NULL | Parent optimization run ID |
| trial_number | INTEGER NOT NULL | Trial sequence number |
| status | TEXT NOT NULL | Trial status (completed, failed, ignored, best, selected_for_validation, rejected) |
| is_best | INTEGER NOT NULL DEFAULT 0 | Whether this is the best trial (0/1) |
| is_selected_for_validation | INTEGER NOT NULL DEFAULT 0 | Whether selected for validation (0/1) |
| params_json | TEXT NOT NULL | Full parameter set as JSON |
| buy_params_json | TEXT | Buy parameters as JSON |
| sell_params_json | TEXT | Sell parameters as JSON |
| roi_params_json | TEXT | ROI parameters as JSON |
| stoploss_params_json | TEXT | Stoploss parameters as JSON |
| trailing_params_json | TEXT | Trailing parameters as JSON |
| metrics_json | TEXT | Trial metrics as JSON |
| loss_score | REAL | Loss score from hyperopt |
| profit_total | REAL | Total profit |
| profit_factor | REAL | Profit factor |
| expectancy | REAL | Trade expectancy |
| max_drawdown | REAL | Maximum drawdown |
| trade_count | INTEGER | Total trade count |
| win_rate | REAL | Win rate |
| rejection_reason | TEXT | Reason if trial was rejected |
| failure_reason | TEXT | Reason if trial failed |
| artifact_paths_json | TEXT | Trial artifact paths as JSON |
| raw_trial_json | TEXT | Raw trial data from hyperopt as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_optimization_trials_run_id, idx_optimization_trials_trial_number, idx_optimization_trials_is_best, idx_optimization_trials_status

**Relationships:** optimization_run_id → optimization_runs.id

**Important:** Every trial is persisted, not just the best trial. This enables full analysis of the optimization search space.

### Part 08 Trial Persistence Notes

The Part 08 persistence layer stores optimization trials with complete parameter space coverage:

- All trials go to `optimization_trials`, regardless of whether they are selected as best.
- Full parameter sets (buy, sell, ROI, stoploss, trailing) are stored in dedicated JSON columns.
- Trial metrics (loss score, profit, drawdown, trade count, win rate, expectancy) are stored as structured columns.
- Rejection and failure reasons are persisted for analysis.
- The `is_best` flag identifies the best trial, but all trials remain queryable.
- Raw trial data from hyperopt is preserved in `raw_trial_json` for debugging.
- Trial-specific artifacts are tracked in `artifact_paths_json`.

The optimization repository does not run Hyperopt, parse results, or select best trials directly. Service-level logic will own these operations in later implementation steps.

## Part 13 Tables (Validation Evidence Layer)

Part 13 adds persistence for deeper validation evidence. These tables store validation run metadata and evidence summaries only. They do not run Freqtrade, call AI services, approve strategies, export strategies, or synthesize evidence.

### validation_runs

Stores one aggregate validation workflow record.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Validation run ID (UUID) |
| source_type | TEXT NOT NULL | Source type (`strategy`, `baseline_run`, `optimization_run`, `optimized_run`) |
| source_run_id | TEXT | Source run or optimization identifier, when applicable |
| strategy_name | TEXT NOT NULL | Strategy under validation |
| timeframe | TEXT NOT NULL | Freqtrade timeframe |
| pairs_json | TEXT NOT NULL | Trading pairs as JSON |
| exchange | TEXT NOT NULL | Exchange name |
| risk_profile | TEXT | Risk profile (`conservative`, `balanced`, `aggressive`) |
| status | TEXT NOT NULL | Validation workflow status |
| decision_status | TEXT | Aggregate validation decision status |
| timerange | TEXT | Requested or source timerange |
| oos_timerange | TEXT | Derived or requested OOS timerange |
| wfo_config_json | TEXT | WFO configuration as JSON |
| policy_json | TEXT | Validation policy as JSON |
| request_json | TEXT | Original validation request as JSON |
| decision_json | TEXT | Aggregate validation decision as JSON |
| summary_json | TEXT | Frontend-safe validation summary as JSON |
| report_artifact_path | TEXT | Project-relative validation report artifact path |
| created_at | TEXT NOT NULL | Creation timestamp |
| updated_at | TEXT NOT NULL | Last update timestamp |

**Indexes:** idx_validation_runs_strategy_name, idx_validation_runs_status, idx_validation_runs_decision_status, idx_validation_runs_created_at

### validation_evidence

Stores OOS, WFO, robustness, sensitivity, and aggregate-decision evidence records for a validation run.

| Column | Type | Description |
|--------|------|-------------|
| id | TEXT PRIMARY KEY | Evidence ID (UUID) |
| validation_run_id | TEXT NOT NULL | Parent validation run ID |
| evidence_type | TEXT NOT NULL | Evidence type (`oos`, `wfo_window`, `wfo_summary`, `robustness`, `sensitivity`, `validation_decision`) |
| status | TEXT NOT NULL | Evidence status or validation decision status |
| window_index | INTEGER | WFO window index, when applicable |
| timerange | TEXT | Evidence timerange |
| metrics_json | TEXT | Parsed metrics summary as JSON |
| decision_json | TEXT | Per-evidence decision summary as JSON |
| issues_json | TEXT | Issues and blocking reasons as JSON |
| warnings_json | TEXT | Warnings as JSON |
| artifact_paths_json | TEXT | Project-relative artifact paths as JSON |
| created_at | TEXT NOT NULL | Creation timestamp |

**Indexes:** idx_validation_evidence_run_id, idx_validation_evidence_type, idx_validation_evidence_status, idx_validation_evidence_window_index

### Part 13 Persistence Notes

- `validation_runs` owns the aggregate state and final decision payload.
- `validation_evidence` owns per-check evidence for OOS, WFO windows, robustness, sensitivity, and validation decisions.
- JSON columns are deserialized by `ValidationRepository` into frontend-ready keys such as `pairs`, `metrics`, `decision`, `issues`, `warnings`, and `artifact_paths`.
- Evidence records may reference child run artifacts by project-relative path, but raw stdout/stderr contents are not stored in these schema contracts.
- Prompt 2 adds persistence only; execution services and API routes are planned for later prompts.

## Entity Relationships

```
runs (1) ----< (N) run_stages
runs (1) ----< (N) metrics_snapshots
runs (1) ----< (N) pair_results
runs (1) ----< (1) trade_summaries
runs (1) ----< (N) decision_results
runs (1) ----< (N) run_logs
runs (1) ----< (N) artifacts
runs (1) ----< (N) retry_history
runs (1) ----< (N) audit_logs
runs (1) ----< (N) retry_history (as parent_run_id)

strategies (1) ----< (N) strategy_versions
strategies (1) ----< (N) artifacts
strategies (1) ----< (N) runs (via strategy_id)

strategy_versions (N) ----< (1) runs (via created_from_run_id)

optimization_runs (1) ----< (N) optimization_trials
optimization_runs (N) ----< (1) runs (as parent_run_id)
optimization_runs (N) ----< (1) runs (as baseline_run_id)
optimization_runs (N) ----< (1) runs (as optimized_run_id)
optimization_runs (N) ----< (1) optimization_trials (as best_trial_id)

validation_runs (1) ----< (N) validation_evidence
validation_runs (N) ----< (1) runs (as source_run_id, when source_type is baseline_run or optimized_run)
validation_runs (N) ----< (1) optimization_runs (as source_run_id, when source_type is optimization_run)
```

## Index Strategy

Indexes are created for:
- **Foreign Keys:** All foreign key columns have indexes
- **Query Patterns:** Common query filters (status, created_at, type)
- **Sorting:** Timestamp columns for chronological queries
- **Uniqueness:** Unique constraints for (run_id, stage_key), (strategy_id, version_number), (run_id, pair)
- **Optimization:** Strategy name, status, result status, trial number, best trial flag
- **Validation:** Strategy name, status, decision status, evidence type, evidence status, WFO window index

## Migration Strategy

- **Idempotent:** All migrations use CREATE TABLE IF NOT EXISTS and CREATE INDEX IF NOT EXISTS
- **Backward Compatible:** Part 02 tables remain unchanged
- **Version Tracked:** Schema version stored in app_meta table
- **Safe Re-runs:** Can run init-db.py multiple times without errors

## Schema Evolution

Future schema changes will:
1. Add new migration functions
2. Use ALTER TABLE for column additions (with defaults)
3. Create new tables with IF NOT EXISTS
4. Update schema_version in app_meta
5. Provide data migration scripts if needed

## Performance Considerations

- **WAL Mode:** SQLite Write-Ahead Logging for better concurrency
- **Foreign Keys:** Enabled for referential integrity
- **Indexes:** Strategic indexes for common queries
- **JSON Storage:** JSON stored as TEXT, parsed in application layer
- **Connection Pooling:** Managed by application, not database

## Security Considerations

- **Local Access Only:** Database file protected by filesystem permissions
- **No Secrets:** Secrets never stored in database
- **Audit Trail:** All important actions logged
- **Input Validation:** Application-level validation before database writes
