# Evidence and Traceability

## Purpose

The Evidence and Traceability system in HER provides comprehensive tracking of all run activities, artifacts, metrics, logs, retry attempts, and audit events. This system ensures that every action is recorded, every artifact is tracked, and every failure is visible. This transparency is critical for debugging, AI explanations, and user trust.

## Artifacts

**What are Artifacts?**

Artifacts are files generated during a run, such as:
- Strategy Python files (`.py`)
- Strategy parameter files (`.json`)
- Strategy specifications
- Backtest results
- Configuration files
- Any other output files

**Artifact Storage:**
- Artifacts are stored as file references in the database
- The database stores the file path, SHA256 hash, and size
- File paths are stored as project-relative paths when possible
- Artifacts can be linked to runs or strategies
- Artifact types are validated against allowed values such as `strategy_py`, `strategy_json`, `strategy_spec`, `freqtrade_config`, `backtest_raw`, `hyperopt_raw`, `metrics_json`, `report_md`, `export_package`, `log_file`, `chart`, and `other`

**Artifact Lifecycle:**
1. Created during a run (e.g., strategy generation, backtest)
2. Stored in the database with metadata
3. Can be retrieved by run ID or strategy ID
4. Provides traceability for all generated files

**Part 06 Decision Artifact:**

Decision evaluation writes a JSON report to:

`artifacts/runs/{run_id}/decisions/decision_result.json`

The artifact is registered with:

- `artifact_type`: `metrics_json`
- `description`: `Decision engine result`
- `run_id`: the evaluated run ID

The report contains the decision classification, confidence score, gates, reasons, evidence references, warnings, blocking failures, and next actions. It is not an export package and does not approve a strategy.

**Security:**
- Artifacts do not store secrets
- File content is not read or downloaded in Part 03
- Only metadata is stored in the database

## Metrics Snapshots

**What are Metrics Snapshots?**

Metrics snapshots capture the performance data from backtests and strategy evaluations. They include:
- Raw metrics data as JSON
- Profit/loss information
- Win rates
- Sharpe ratios
- Drawdown metrics
- Any other performance indicators

**Metrics Storage:**
- Stored as JSON in the database
- Multiple snapshots can exist per run (e.g., different timeframes)
- Latest snapshot can be retrieved quickly
- Raw JSON is stored as text and returned parsed

**Pair Results:**
- Individual pair performance data
- Stored per trading pair (e.g., BTC/USDT)
- Allows analysis of which pairs perform best

**Trade Summaries:**
- Aggregate trade statistics
- Total trades, profitable trades, losing trades
- Profit factor, total profit, total loss
- Provides high-level performance overview

**Important Notes:**
- Metrics are not used for strategy acceptance logic in Part 03
- Part 06 consumes parsed metrics as evidence for decision gates
- Demo metrics are accepted for testing
- Part 05 parses real Freqtrade results into normalized evidence

## Decision Results

Part 06 decision results are stored in `decision_results`.

Each row includes:

- Final safe classification: `rejected`, `candidate`, `promising`, or `validated`.
- Confidence score.
- Policy name, risk profile, and timeframe.
- Gate results.
- Decision reasons.
- Evidence references.
- Warnings and blocking failures.
- Normalized result artifact path when available.

The decision repository stores decision rows only. It does not update run classification. `DecisionService` owns the optional safe run classification update.

Forbidden Part 06 outcomes are not stored:

- `approved`
- `exported`
- `live_ready`
- `profitable_guaranteed`

## Run Logs

**What are Run Logs?**

Run logs provide a detailed timeline of events during a run. They include:
- Log level (info, warning, error, debug)
- Source (system, AI, freqtrade, user)
- Message content
- Associated stage key
- Additional details as JSON

**Log Storage:**
- Stored in the database with timestamps
- Can be filtered by run, stage, or level
- Details stored as JSON
- Logs are returned in descending order (newest first)

**Part 06 Decision Logs:**

Decision evaluation adds run logs with `source=decision_service` and `stage_key=decision_engine`:

- `decision_evaluation_started`
- `decision_evaluation_completed`

Completion details include classification, confidence score, and blocking failure count. Rejected decisions include a warning log clarifying that integration validation status and strategy decision classification are separate concepts.

**Secret Sanitization:**
HER automatically sanitizes secret-like values in log details to prevent accidental exposure:
- `token`
- `secret`
- `password`
- `api_key`
- `apikey`
- `private_key`

When these markers are detected in log detail keys, their values are replaced with `[REDACTED]`. Keys such as `access_token` and `refresh_token` are covered because they contain `token`.

**Example:**
```python
# Input details
{"api_key": "sk-1234567890", "user": "test"}

# Stored details
{"api_key": "[REDACTED]", "user": "test"}
```

**Security:**
- Secrets are never stored in logs
- Sanitization is recursive (handles nested dictionaries and lists)
- This is a safety net, not a replacement for proper secret management

## Retry History

**What is Retry History?**

Retry history tracks all retry attempts when a run fails or needs correction. It includes:
- Parent run ID (the original run)
- Stage where retry occurred
- Retry status (proposed, approved, applied, failed, rejected, skipped)
- Error message that triggered the retry
- Proposed fix (what AI suggests)
- Applied fix (what was actually done)
- Completion timestamp

**Retry Storage:**
- Stored in the database with full context
- Supports parent_run_id for tracking retry chains
- Proposed and applied fixes stored as JSON
- Prevents infinite loops (storage only, no execution logic)

**Retry Lifecycle:**
1. Run fails at a stage
2. Retry entry created with proposed fix
3. Retry approved or rejected by policy/user flow
4. Approved fix applied, failed, or skipped
5. History preserved for analysis

**Use Cases:**
- AI-driven error correction
- Manual retry with user changes
- Tracking what fixes work
- Learning from failures

## Audit Logs

**What are Audit Logs?**

Audit logs track all significant actions in the system for accountability and traceability. They include:
- Actor (system, AI, user)
- Action type (create, update, delete, approve, reject, etc.)
- Description
- Target type (strategy, run, config, etc.)
- Target ID
- State before action (before JSON)
- State after action (after JSON)
- Changed files list
- Rollback path when available
- Approval status
- Notes

**Audit Storage:**
- Stored in the database with timestamps
- Before/after states stored as JSON
- Changed files stored as JSON array
- Approval flag indicates if action was approved
- Can be filtered by run or action type
- Secret-like keys in before/after JSON are recursively redacted

**Audit Actors:**
- `system` - Automated system actions
- `user` - User-initiated actions
- `ai_assistant` - General assistant actions
- `ai_strategy_designer` - Strategy design assistant actions
- `ai_repair_agent` - Repair assistant actions

**Security:**
- Secrets are never stored in audit logs when they are under obvious secret-like keys
- Before/after states should still avoid sensitive data; redaction is a safety net
- Approved flag tracks human approval of AI actions

**Part 06 Decision Audit:**

Decision evaluation adds an audit log with:

- `actor`: `system`
- `action_type`: `decision_evaluation`
- `target_type`: `run`
- `target_id`: run ID
- `after`: full sanitized `DecisionResult`
- `approved`: `false`

This audit entry records what the decision engine concluded. It is not an approval workflow and does not authorize export or deployment.

## Part 07 Baseline Evaluation Artifacts

**Part 07 Baseline Report Artifact:**

Baseline evaluation writes a comprehensive JSON report to:

`artifacts/runs/{run_id}/baseline/baseline_evaluation_report.json`

The artifact is registered with:

- `artifact_type`: `report_md`
- `description`: `Baseline evaluation report`
- `run_id`: the evaluated run ID
- `metadata`: `{"stage": "baseline_report"}`

The report contains:
- Request summary (strategy, pairs, timeframe, exchange, risk profile)
- Stage summary (status, duration, message for each of the 10 stages)
- Decision summary (classification, confidence score, policy name)
- Artifact paths (all generated artifacts from the pipeline)
- Warnings and errors (aggregated from all stages)
- Next actions (from decision evaluation)
- Created timestamp

**Part 07 Stage Artifacts:**

Each stage in the baseline pipeline generates specific artifacts:

1. **Config Generation Stage:**
   - Freqtrade backtest config file
   - Path: `freqtrade_config/runs/{run_id}.backtest.json`
   - Registered as `freqtrade_config` type

2. **Baseline Backtest Stage:**
   - Raw Freqtrade backtest outputs
   - Path: `artifacts/runs/{run_id}/raw_freqtrade/backtest_results/`
   - Includes trades JSON, backtest results, and other Freqtrade outputs
   - Registered as `backtest_raw` type

3. **Result Parsing Stage:**
   - Normalized backtest result artifact
   - Path: `artifacts/runs/{run_id}/normalized/normalized_result.json`
   - Registered by Part 05 BacktestResultParser

4. **Decision Evaluation Stage:**
   - Decision result artifact
   - Path: `artifacts/runs/{run_id}/decisions/decision_result.json`
   - Registered by Part 06 DecisionService

**Part 07 Run Logs:**

Baseline evaluation adds run logs with `source=baseline_evaluation` for each stage:

- `run_setup` - Run creation and initialization
- `strategy_validation` - Strategy validation results
- `config_generation` - Config file generation
- `data_check` - Data availability check results
- `data_download` - Data download execution (if applicable)
- `baseline_backtest` - Backtest execution results
- `result_parsing` - Parsing completion and metrics
- `decision_evaluation` - Decision evaluation results
- `baseline_report` - Report generation
- `completion` - Pipeline completion

**Part 07 Audit Logs:**

Baseline evaluation adds audit logs:

- Run creation audit (actor: system, action: baseline_evaluation_started)
- Stage completion audits for each stage
- Final completion audit (actor: system, action: baseline_evaluation_completed)

**Part 07 Stage Tracking:**

All 10 baseline pipeline stages are tracked in `run_stages`:

- `run_setup` - Stage 1
- `strategy_validation` - Stage 2
- `config_generation` - Stage 3
- `data_check` - Stage 4
- `data_download` - Stage 5
- `baseline_backtest` - Stage 6
- `result_parsing` - Stage 7
- `decision_evaluation` - Stage 8
- `baseline_report` - Stage 9
- `completion` - Stage 10

Each stage records:
- Status (pending, running, passed, failed, waiting)
- Start and completion timestamps
- Duration in milliseconds
- Input data (request parameters)
- Output data (stage results)
- Error data (if failed) - includes error_code for controlled failures
- Logs summary

**Part 07 Controlled Failure Tracking:**

Baseline evaluation implements controlled failure behavior with specific error codes:

- `strategy_not_found` - Strategy not found in Freqtrade workspace
- `strategy_validation_failed` - Strategy name or structure validation failed
- `unsafe_strategy_path` - Strategy file path is outside allowed workspace
- `config_generation_failed` - Backtest configuration generation failed
- `data_missing` - Market data is missing
- `confirmation_required_for_download` - Data download requires user confirmation
- `confirmation_required_for_backtest` - Backtest execution requires user confirmation
- `data_download_failed` - Data download failed
- `backtest_failed` - Freqtrade backtest failed
- `backtest_artifacts_missing` - Backtest artifacts are missing
- `parse_failed` - Backtest result parsing failed
- `decision_failed` - Decision evaluation failed
- `baseline_report_failed` - Baseline report creation failed
- `unexpected_pipeline_error` - Unexpected pipeline error occurred

Each error code maps to:
- Short message (for UI display)
- User message (detailed explanation)
- Next actions (actionable guidance for user)

Error codes are stored in:
- `BaselineStageResult.error_code` field
- `run_stages.error_data` column
- Frontend responses for user guidance

**Part 07 Stage Result Structure:**

Each stage result includes frontend-ready data:
- `stage_name` - Stage identifier
- `status` - Stage status (completed, failed_controlled, confirmation_required)
- `message` - Human-readable status message
- `started_at` - ISO format timestamp
- `completed_at` - ISO format timestamp
- `duration_seconds` - Stage duration
- `error_code` - Specific error code (if failed or confirmation_required)
- `warnings` - List of warning messages
- `errors` - List of error messages (no stack traces)
- `artifact_paths` - List of project-relative artifact paths
- `details` - Additional stage-specific data (no secrets)

**Part 07 Evidence Chain:**

The baseline evaluation creates a complete evidence chain:

1. **Request Evidence:** Original evaluation request stored in run_setup stage input
2. **Strategy Evidence:** Strategy validation results in strategy_validation stage
3. **Config Evidence:** Generated config file and artifact registration
4. **Data Evidence:** Data check results and download logs
5. **Backtest Evidence:** Raw Freqtrade outputs and execution logs
6. **Parsed Evidence:** Normalized metrics, pair results, trade summary
7. **Decision Evidence:** Decision classification, gates, and reasons
8. **Report Evidence:** Comprehensive baseline report aggregating all evidence

This evidence chain ensures complete traceability from initial request to final decision, with all intermediate steps recorded and auditable.

## Part 08 Optimization Pipeline Artifacts

**Part 08 Optimization Report Artifact:**

Optimization pipeline writes a comprehensive JSON report to:

`artifacts/runs/{optimization_run_id}/optimization/optimization_report.json`

The artifact is registered with:

- `artifact_type`: `report_md`
- `description`: `Optimization pipeline report`
- `run_id`: the optimization run ID

The report contains:
- Request summary (strategy, pairs, timeframe, exchange, risk profile, epochs, spaces)
- Baseline run ID and summary
- Hyperopt policy validation results
- Hyperopt command metadata (without secrets)
- Trials summary (count, best trial ID)
- Best trial details (parameters, metrics)
- Optimized backtest summary (run ID, classification, confidence score)
- Optimized decision results
- Baseline vs optimized comparison (deltas, result status, improvement summary)
- Warnings and errors (aggregated from all stages)
- Artifact paths (all generated artifacts from the pipeline)
- Frontend display hints (what sections to show in UI)
- Created timestamp

**Part 08 Optimized Params Artifact:**

Best trial parameters are materialized safely to:

`artifacts/runs/{optimization_run_id}/optimized_params/{strategy_name}.json`

The artifact is registered with:

- `artifact_type`: `optimized_params`
- `description`: `Optimized params for {strategy_name} from trial {trial_id}`
- `run_id`: the optimization run ID

The params artifact contains:
- strategy_name
- source_trial_id
- source_trial_number
- params (full parameter dict)
- buy_params (separated buy parameters)
- sell_params (separated sell parameters)
- roi_params (separated ROI parameters)
- stoploss_params (separated stoploss parameters)
- trailing_params (separated trailing parameters)
- created_at timestamp
- warning: "This is validation materialization, not approved export. Do not use for live trading without explicit approval."

**Part 08 Stage Artifacts:**

Each stage in the optimization pipeline generates specific artifacts:

1. **Hyperopt Execution Stage:**
   - Raw Freqtrade hyperopt outputs
   - Path: `artifacts/runs/{optimization_run_id}/raw_freqtrade/hyperopt_results/`
   - Includes hyperopt results, trials JSON, and other Freqtrade outputs
   - Registered as `hyperopt_raw` type

2. **Optimized Backtest Stage:**
   - Raw Freqtrade backtest outputs for optimized backtest
   - Path: `artifacts/runs/{optimized_run_id}/raw_freqtrade/backtest_results/`
   - Registered as `backtest_raw` type

3. **Optimized Result Parsing Stage:**
   - Normalized backtest result artifact
   - Path: `artifacts/runs/{optimized_run_id}/normalized/normalized_result.json`
   - Registered by Part 05 BacktestResultLoader

4. **Optimized Decision Evaluation Stage:**
   - Decision result artifact
   - Path: `artifacts/runs/{optimized_run_id}/decisions/decision_result.json`
   - Registered by Part 06 DecisionService

**Part 08 Run Logs:**

Optimization pipeline adds run logs with `source=optimization_pipeline` for each stage:

- `optimization_setup` - Optimization run creation and initialization
- `baseline_reference` - Baseline run resolution or creation
- `hyperopt_policy_validation` - Policy validation results
- `hyperopt_config_generation` - Config file generation
- `data_check` - Data availability check results
- `data_download` - Data download execution (if applicable)
- `hyperopt_execution` - Hyperopt execution results
- `hyperopt_result_parsing` - Parsing completion and trial count
- `trial_persistence` - Trial persistence confirmation
- `best_trial_selection` - Best trial selection results
- `optimized_config_generation` - Optimized config generation
- `optimized_backtest` - Optimized backtest execution results
- `optimized_result_parsing` - Optimized parsing completion
- `optimized_decision_evaluation` - Optimized decision evaluation results
- `baseline_vs_optimized_comparison` - Comparison calculation results
- `optimization_report` - Report generation
- `completion` - Pipeline completion

**Part 08 Audit Logs:**

Optimization pipeline adds audit logs:

- Optimization run creation audit (actor: system, action: optimization_started)
- Stage completion audits for each stage
- Trial persistence audits (actor: system, action: trial_persisted)
- Best trial selection audit (actor: system, action: best_trial_selected)
- Final completion audit (actor: system, action: optimization_completed)

**Part 08 Stage Tracking:**

All 17 optimization pipeline stages are tracked in `optimization_stages`:

- `optimization_setup` - Stage 1
- `baseline_reference` - Stage 2
- `hyperopt_policy_validation` - Stage 3
- `hyperopt_config_generation` - Stage 4
- `data_check` - Stage 5
- `data_download` - Stage 6
- `hyperopt_execution` - Stage 7
- `hyperopt_result_parsing` - Stage 8
- `trial_persistence` - Stage 9
- `best_trial_selection` - Stage 10
- `optimized_config_generation` - Stage 11
- `optimized_backtest` - Stage 12
- `optimized_result_parsing` - Stage 13
- `optimized_decision_evaluation` - Stage 14
- `baseline_vs_optimized_comparison` - Stage 15
- `optimization_report` - Stage 16
- `completion` - Stage 17

Each stage records:
- Status (pending, running, completed, failed_controlled)
- Start and completion timestamps
- Duration in seconds
- Input data (request parameters)
- Output data (stage results)
- Error data (if failed) - includes error_code for controlled failures
- Logs summary

**Part 08 Controlled Failure Tracking:**

Optimization pipeline implements controlled failure behavior with specific error codes:

- `baseline_missing` - Baseline run not found or not provided
- `policy_rejected_request` - Hyperopt policy validation rejected the request
- `confirmation_required_for_hyperopt` - User confirmation required before Hyperopt execution
- `data_missing` - Market data is missing
- `hyperopt_failed` - Freqtrade hyperopt execution failed
- `hyperopt_result_missing` - Hyperopt result files are missing
- `no_trials_parsed` - No trials could be parsed from hyperopt results
- `best_trial_missing` - Best trial could not be selected
- `params_materialization_failed` - Optimized params materialization failed
- `optimized_backtest_failed` - Optimized backtest execution failed
- `optimized_parse_failed` - Optimized result parsing failed
- `optimized_decision_failed` - Optimized decision evaluation failed
- `comparison_failed` - Baseline vs optimized comparison failed
- `report_failed` - Optimization report creation failed
- `unexpected_optimization_error` - Unexpected pipeline error occurred

Each error code maps to:
- Short message (for UI display)
- User message (detailed explanation)
- Next actions (actionable guidance for user)

Error codes are stored in:
- `OptimizationStageResult.error_code` field
- Optimization run status updates
- Frontend responses for user guidance

**Part 08 Trial Persistence Evidence:**

Every trial from hyperopt is persisted in `optimization_trials`:

- Trial ID and trial number
- Optimization run ID
- Status (completed, failed, ignored, best, selected_for_validation, rejected)
- Parameters (full params dict, separated buy/sell/roi/stoploss/trailing)
- Metrics (profit_total, profit_factor, expectancy, max_drawdown, trade_count, win_rate)
- Loss score (for hyperopt optimization)
- Rejection/failure reasons
- Artifact paths (trial-specific artifacts)
- Raw trial data (original hyperopt output)
- Created timestamp

This ensures complete trial history is available for:
- Selecting the best trial
- Analyzing parameter space exploration
- Understanding why certain trials were rejected
- Comparing trial performance
- Debugging hyperopt issues

**Part 08 Comparison Evidence:**

Baseline vs optimized comparison is stored in `optimization_runs.comparison_json`:

- Baseline run ID and metrics
- Optimized run ID and metrics
- Best trial ID
- Metric deltas (profit_factor, expectancy, drawdown, trade_count)
- Baseline and optimized classifications
- Result status (improved, not_improved, optimization_candidate, optimization_rejected, overfit_suspected, invalid_optimization)
- Improvement summary (human-readable delta summary)
- Warnings list
- Overfit suspicion flag
- Created timestamp

This comparison evidence provides:
- Clear before/after metrics
- Quantified improvement or degradation
- Classification consistency check
- Overfit detection
- Decision support for approval workflows

**Part 08 Evidence Chain:**

The optimization pipeline creates a complete evidence chain:

1. **Request Evidence:** Original optimization request stored in optimization_setup stage input
2. **Baseline Evidence:** Baseline run resolution and metrics
3. **Policy Evidence:** Hyperopt policy validation results
4. **Config Evidence:** Generated hyperopt config file
5. **Data Evidence:** Data check results and download logs
6. **Hyperopt Evidence:** Raw hyperopt outputs and execution logs
7. **Trial Evidence:** All persisted trials with parameters and metrics
8. **Best Trial Evidence:** Selected best trial with full details
9. **Params Evidence:** Materialized optimized params artifact
10. **Optimized Backtest Evidence:** Raw optimized backtest outputs
11. **Optimized Parsed Evidence:** Normalized optimized metrics
12. **Optimized Decision Evidence:** Optimized decision classification
13. **Comparison Evidence:** Baseline vs optimized comparison
14. **Report Evidence:** Comprehensive optimization report aggregating all evidence

This evidence chain ensures complete traceability from initial optimization request to final comparison, with all intermediate steps recorded and auditable. Every trial is preserved, every decision is documented, and the complete parameter space exploration is available for analysis.

## Why HER Must Never Hide Failures

**Transparency Principle:**

HER is designed to be transparent about all failures. This is critical for several reasons:

1. **Trust:** Users need to trust that the system is honest about what works and what doesn't.
2. **Debugging:** Failures provide valuable information for fixing issues.
3. **Learning:** Understanding failures helps improve the system.
4. **Accountability:** Every action should be traceable to its source.

**How HER Achieves This:**

1. **Run Logs:** Every event is logged with full context.
2. **Retry History:** All retry attempts are tracked with proposed and applied fixes.
3. **Audit Logs:** All actions are recorded with before/after states.
4. **Stage Status:** Each stage's status is visible (pending, running, passed, failed).
5. **Error Messages:** Errors are stored with full details (sanitized for secrets).

**No Silent Failures:**
- If a stage fails, the status is explicitly set to "failed"
- Error messages are stored in the database
- Retry history shows what went wrong and how it was addressed
- Audit logs show who/what caused the failure

## How These Tables Support UI Stage Cards and AI Explanations

**UI Stage Cards:**

The frontend uses these tables to display rich stage cards:

1. **Stage Status:** From `run_stages` table (pending, running, passed, failed)
2. **Logs:** From `run_logs` table filtered by stage_key
3. **Artifacts:** From `artifacts` table filtered by run_id
4. **Metrics:** From `metrics_snapshots` and related tables
5. **Retry History:** From `retry_history` table for failed stages

**Example Stage Card Data:**
```
Stage: Backtest
Status: Failed
Logs: 3 entries (1 error, 2 info)
Artifacts: backtest_raw.json
Retry History: 1 retry attempted
Error: "Strategy failed to load"
```

**AI Explanations:**

AI uses these tables to generate explanations:

1. **Logs:** Understand what happened during the run
2. **Retry History:** See what fixes were attempted
3. **Metrics:** Analyze performance data
4. **Audit Logs:** Understand what actions were taken
5. **Artifacts:** Review generated files

**Example AI Explanation:**
```
The backtest stage failed because the strategy had a syntax error.
A retry was attempted with a proposed fix to correct the syntax.
The retry passed with improved metrics (profit: +15%).
The strategy was then approved for use.
```

**Traceability Chain:**

The complete traceability chain for any action:
1. **Run** → The overall execution context
2. **Stages** → Individual steps in the run
3. **Logs** → Detailed events during stages
4. **Artifacts** → Files generated
5. **Metrics** → Performance data
6. **Retry History** → Corrections and fixes
7. **Audit Logs** → Who did what and when

This chain allows complete reconstruction of any run for debugging, analysis, or explanation.

## Future Enhancements

In future parts, the evidence and traceability system will:
- Parse real Freqtrade backtest results
- Calculate derived metrics from raw data
- Generate visual reports from metrics
- Integrate with Discord for real-time notifications
- Support advanced filtering and search
- Provide export functionality for audit trails
- Integrate with AI for automated failure analysis
