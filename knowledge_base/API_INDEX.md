# HER API Index

Complete reference for every backend endpoint. Built from inspecting FastAPI routers and frontend API clients. Use this before writing any code that touches an API route.

**Base URL:** `http://localhost:8000` (local) or `http://0.0.0.0:8000` (Replit backend workflow)

All endpoints except `/health` are prefixed with `/api` or `/api/v1`.

---

## Mismatches & Gaps (Flagged)

| Issue | Detail |
|---|---|
| Frontend calls `/api/freqtrade/strategies` | No such endpoint in router; router has `/api/v1/freqtrade/status` and `/api/v1/freqtrade/workspace` |
| Frontend calls `/api/freqtrade/data` (GET) | No GET data endpoint in router; router has `POST /data/check` and `POST /data/download` |
| Frontend calls `/api/baseline/runs/{id}/report` | Not confirmed in router; router has evaluate, `runs/{id}`, `runs/{id}/status` |
| Frontend calls `/api/decisions/runs/{runId}/latest` | Not confirmed in router; decisions router may expose this via a different path |
| Frontend calls `/api/runs/{runId}/decision` | Convenience route not confirmed in runs router; may be handled by decisions router |
| Frontend calls `/api/optimization/runs/{id}/best-trial` and `/comparison` as separate GETs | Backend combines in detail endpoint; may be separate convenience routes |

---

## Domain: System

### `GET /health`
- **Purpose:** Lightweight liveness check
- **Response:** `{ status: "healthy", version: string }`
- **Frontend client:** `system.ts → fetchHealth()`
- **Used by:** Dashboard, AppShell header

### `GET /api/system/status`
- **Purpose:** Full system component status (Freqtrade, DB, Ollama)
- **Response:** `{ freqtrade: {...}, database: {...}, ollama: {...} }`
- **Frontend client:** `system.ts → fetchSystemStatus()`
- **Used by:** Dashboard System Overview cards

### `GET /api/settings/public`
- **Purpose:** Non-sensitive public configuration values
- **Response:** `{ backend_port, frontend_port, app_env, ... }`
- **Frontend client:** `system.ts → fetchPublicSettings()`
- **Used by:** Settings page

---

## Domain: Runs

Prefix: `/api/v1/runs`

### `GET /api/runs`
- **Purpose:** List runs with optional filters
- **Query params:** `status`, `classification`, `strategy_id`, `limit`, `offset`
- **Response:** `RunListItem[]`
  - `id`, `name`, `mode`, `status`, `classification`, `strategy_id`, `parent_run_id`, `is_demo`, `created_at`, `updated_at`, `started_at`, `completed_at`
- **Frontend client:** `runs.ts → listRuns()`
- **Used by:** Runs page, Dashboard

### `POST /api/runs`
- **Purpose:** Create a new run record
- **Body:** `RunCreate` — `strategy_id`, `mode`, `config_override?`
- **Response:** `RunRead` (full run object)
- **Frontend client:** Not called directly from UI (pipelines create runs internally)

### `GET /api/runs/{run_id}`
- **Purpose:** Get full run detail
- **Response:** `RunRead`
- **Frontend client:** `runs.ts → getRun(runId)`
- **Used by:** Baseline detail, Optimization detail, Journey page

### `PATCH /api/runs/{run_id}`
- **Purpose:** Update run fields
- **Body:** `RunUpdate` — `status?`, `classification?`, `failure_reason?`
- **Response:** `RunRead`
- **Frontend client:** Not called directly from UI

### `POST /api/runs/{run_id}/status`
- **Purpose:** Update run status atomically
- **Body:** `RunStatusUpdate` — `status`, `failure_reason?`
- **Response:** `RunRead`
- **Frontend client:** Not called directly from UI (used internally by pipelines)

### `POST /api/runs/{run_id}/start`
- **Purpose:** Mark run as started (sets `started_at`, transitions to `running`)
- **Response:** `RunRead`
- **Frontend client:** Not called directly from UI

### `POST /api/runs/{run_id}/complete`
- **Purpose:** Mark run as completed
- **Query params:** `status`, `classification`
- **Response:** `RunRead`
- **Frontend client:** Not called directly from UI

### `POST /api/runs/{run_id}/fail`
- **Purpose:** Mark run as failed with reason
- **Body:** `RunFailRequest` — `failure_type`, `reason`
- **Response:** `RunRead`
- **Frontend client:** Not called directly from UI

### `GET /api/runs/{run_id}/stages`
- **Purpose:** List all pipeline stages for a run
- **Response:** `RunStage[]`
  - `id`, `run_id`, `stage_key`, `stage_name`, `order_index`, `status`, `started_at`, `completed_at`, `duration_ms`, `input_json`, `output_json`, `error_json`, `logs_summary`
- **Frontend client:** `runs.ts → listRunStages(runId)`
- **Used by:** Baseline detail (stage progress), LiveRunPanel

### `GET /api/runs/{run_id}/stages/{stage_key}`
- **Purpose:** Get a specific stage detail
- **Response:** `RunStage`
- **Frontend client:** `runs.ts → getRunStage(runId, stageKey)`

### `GET /api/runs/{run_id}/logs`
- **Purpose:** Retrieve stage and run logs
- **Response:** log entries array
- **Frontend client:** `runs.ts → getRunLogs(runId)`
- **Used by:** Baseline detail logs section

### `GET /api/runs/{run_id}/retry-history`
- **Purpose:** List retry attempts for a run
- **Response:** retry history entries
- **Frontend client:** `runs.ts → getRetryHistory(runId)`

### `GET /api/runs/{run_id}/metrics`
- **Purpose:** List metrics snapshots for a run
- **Response:** `MetricsSnapshot[]`
- **Frontend client:** `results.ts → getRunMetrics(runId)`
- **Used by:** Baseline detail, Results page

### `GET /api/runs/{run_id}/metrics/latest`
- **Purpose:** Get most recent metrics snapshot
- **Response:** `MetricsSnapshot`
- **Frontend client:** `results.ts → getLatestMetrics(runId)`

### `GET /api/runs/{run_id}/pair-results`
- **Purpose:** Per-pair performance breakdown
- **Response:** pair performance array
- **Frontend client:** `results.ts → listPairResults(runId)`

### `GET /api/runs/{run_id}/trade-summary`
- **Purpose:** Trade-level statistics aggregation
- **Response:** trade summary object
- **Frontend client:** `results.ts → getTradeSummary(runId)`

### `GET /api/runs/{run_id}/result-quality`
- **Purpose:** Quality flags for parsed backtest result
- **Response:** quality flags object
- **Frontend client:** `results.ts → getResultQuality(runId)`

---

## Domain: Strategies

Prefix: `/api/v1/strategies`

### `GET /api/strategies`
- **Purpose:** List all registered strategies
- **Query params:** `status?`, `source_type?`
- **Response:** `StrategyListItem[]`
- **Frontend client:** `strategies.ts → listStrategies()`
- **Used by:** Strategy Library, Journey page selector, StrategySelect component

### `POST /api/strategies`
- **Purpose:** Register a new strategy record
- **Body:** `StrategyCreate` — `name`, `source_type`
- **Response:** `StrategyRead`

### `GET /api/strategies/{strategy_id}`
- **Purpose:** Get strategy detail
- **Response:** `StrategyRead`
- **Frontend client:** `strategies.ts → getStrategy(name)`
- **Used by:** Strategy detail page

### `PATCH /api/strategies/{strategy_id}`
- **Purpose:** Update strategy metadata
- **Body:** `StrategyUpdate` — `status?`, metadata fields
- **Response:** `StrategyRead`

### `POST /api/strategies/{strategy_id}/archive`
- **Purpose:** Archive a strategy (soft delete)
- **Response:** `StrategyRead`

### `GET /api/strategies/{strategy_id}/versions`
- **Purpose:** List all versions of a strategy
- **Response:** `StrategyVersionListItem[]`
- **Frontend client:** Not directly called from UI pages

### `POST /api/strategies/{strategy_id}/versions`
- **Purpose:** Create a new strategy version snapshot
- **Body:** `StrategyVersionCreate` — `version_number`, `code_hash`
- **Response:** `StrategyVersionRead`

---

## Domain: Strategy Workspace

Prefix: `/api/strategy_workspace`

### `GET /api/strategy_workspace/strategies`
- **Purpose:** List strategies with workspace metadata (readiness, params)
- **Query params:** `readiness?`, `search?`, `limit?`
- **Response:** `StrategySummary[]`
- **Frontend client:** `strategies.ts → listStrategies()` (may call workspace variant)
- **Used by:** Strategy Lab page, Workspace selector

### `POST /api/strategy_workspace/strategies/import`
- **Purpose:** Import an existing Freqtrade strategy file into HER
- **Body:** `StrategyImportRequest` — `strategy_name`, `file_path`
- **Response:** `StrategyImportResult`
- **Frontend client:** `strategies.ts → importStrategy()`

### `GET /api/strategy_workspace/strategies/{name}/params`
- **Purpose:** Get strategy parameters summary
- **Response:** `StrategyParamsSummary`
- **Frontend client:** `strategies.ts → getStrategyParams(name)`
- **Used by:** Strategy detail page, Optimization form

### `POST /api/strategy_workspace/strategies/{name}/validate`
- **Purpose:** Run readiness gate check on a strategy
- **Response:** `StrategyDetail` — includes readiness issues list
- **Frontend client:** `strategies.ts → validateStrategy(name)`
- **Used by:** Strategy detail page, pre-run checks

---

## Domain: Baseline

Prefix: `/api/v1/baseline`

### `POST /api/baseline/evaluate`
- **Purpose:** Launch a full baseline evaluation pipeline
- **Body:** `BaselineEvaluationRequest`
  - `strategy_name` (required)
  - `pairs` (required)
  - `user_confirmed: true` (required — blocks execution if false)
  - `timeframe?`, `timerange?`, `risk_profile?`
- **Response:** `BaselineEvaluationResult` — `run_id`, `status`, `metrics?`
- **Execution flag:** Triggers Freqtrade CLI subprocess
- **Frontend client:** `baseline.ts → startBaselineEvaluation()`
- **Used by:** Baseline page (form submit)

### `GET /api/baseline/runs/{run_id}`
- **Purpose:** Full baseline run detail (stages, metrics, decision, artifacts)
- **Response:** `dict` with `run`, `stages`, `metrics`, `decision`, `artifacts`
- **Frontend client:** `baseline.ts → getBaselineRunDetail(runId)`
- **Used by:** Baseline detail page

### `GET /api/baseline/runs/{run_id}/status`
- **Purpose:** Current stage and metrics snapshot for polling
- **Response:** `BaselineStatusResponse` — `current_stage`, `stage_results`, `metrics`
- **Frontend client:** `baseline.ts → getBaselineStatus(runId)`
- **Used by:** LiveRunPanel (via useRunPolling), Baseline detail

---

## Domain: Optimization

Prefix: `/api/v1/optimization`

### `POST /api/optimization/run`
- **Purpose:** Launch Hyperopt optimization pipeline
- **Body:** `OptimizationRequest`
  - `strategy_name` (required)
  - `pairs` (required)
  - `timeframe` (required, validated)
  - `epochs` (required, validated range)
  - `user_confirmed: true` (required)
  - `spaces?`, `risk_profile?`, `baseline_run_id?`
- **Response:** `OptimizationStartResponse` — `run_id`, `optimization_run_id`, `status`
- **Execution flag:** Triggers Freqtrade hyperopt subprocess
- **Frontend client:** `optimization.ts → startOptimization()`
- **Used by:** Optimizer page (form submit)

### `GET /api/optimization/runs`
- **Purpose:** List optimization runs
- **Query params:** `limit?`, `offset?`, `status?`
- **Response:** `OptimizationRunListItem[]`
- **Frontend client:** `optimization.ts → listOptimizationRuns()`
- **Used by:** Runs page, Dashboard, Journey page

### `GET /api/optimization/runs/{id}`
- **Purpose:** Full optimization run detail
- **Response:** `OptimizationRunDetail` — `best_trial`, `comparison`, `artifact_paths`, `trials_summary`
- **Frontend client:** `optimization.ts → getOptimizationRunDetail(id)`
- **Used by:** Optimization detail page

### `GET /api/optimization/runs/{id}/status`
- **Purpose:** Current status for polling
- **Response:** `OptimizationStatusResponse` — `epochs_completed`, `trials_completed`, `current_stage`
- **Frontend client:** `optimization.ts → getOptimizationStatus(id)`
- **Used by:** LiveRunPanel

### `GET /api/optimization/runs/{id}/trials`
- **Purpose:** List all trials for an optimization run
- **Query params:** `limit?`, `offset?`, `status?`
- **Response:** `OptimizationTrial[]`
  - `id`, `trial_number`, `status`, `is_best`, `params_json`, `metrics_json`, `loss_score`, `profit_factor`, `max_drawdown`, `trade_count`, `win_rate`
- **Frontend client:** `optimization.ts → listOptimizationTrials(id)`
- **Used by:** Optimization detail (trials chart + table)

### `GET /api/optimization/runs/{id}/report`
- **Purpose:** Retrieve optimization run report artifact (JSON)
- **Response:** report content dict
- **Frontend client:** `optimization.ts → getOptimizationReport(id)`

---

## Domain: Validation

Prefix: `/api/v1/validation`

### `POST /api/validation/run`
- **Purpose:** Launch full validation pipeline (OOS + WFO + robustness)
- **Body:** `ValidationRequest`
  - `strategy_name` (required)
  - `pairs` (required)
  - `timeframe` (required)
  - `user_confirmed: true` (required)
  - `oos_timerange?`, `wfo_config?`, `source_run_id?`
- **Response:** `ValidationRunResponse` — `run_id`, `validation_run_id`, `decision_status`
- **Execution flag:** Triggers multiple Freqtrade CLI calls
- **Frontend client:** `validation.ts → startValidationRun()`

### `GET /api/validation/runs`
- **Purpose:** List validation runs
- **Query params:** `status?`, `decision_status?`, `strategy_name?`
- **Response:** `ValidationRunAPIListItem[]`
- **Frontend client:** `validation.ts → listValidationRuns()`
- **Used by:** Validation list page, Journey page

### `GET /api/validation/runs/{id}`
- **Purpose:** Full validation run detail with grouped evidence
- **Response:** `dict` with `run`, `evidence` (grouped by OOS/WFO/robustness), `summary`
- **Frontend client:** `validation.ts → getValidationRun(id)`
- **Used by:** Validation detail page

### `GET /api/validation/runs/{id}/status`
- **Purpose:** Current stage and evidence count for polling
- **Response:** `ValidationStatusResponse` — `current_stage`, `evidence_count`, `errors`
- **Frontend client:** `validation.ts → getValidationStatus(id)`
- **Used by:** LiveRunPanel

### `GET /api/validation/runs/{id}/evidence`
- **Purpose:** All evidence items for a validation run, grouped by type
- **Response:** `dict` — `oos: ValidationEvidence[]`, `wfo: ValidationEvidence[]`, `robustness: ValidationEvidence[]`
- **Frontend client:** `validation.ts → getValidationEvidence(id)`
- **Used by:** Validation detail (OOS card, WFO card, Robustness card)

---

## Domain: Results

Prefix: `/api/v1/results`

### `POST /api/results/backtest/{run_id}/parse`
- **Purpose:** Trigger backtest result parsing for a run
- **Response:** parse status
- **Execution flag:** Reads Freqtrade output files

### `GET /api/results/backtest/{run_id}`
- **Purpose:** Combined backtest results (metrics + trades + quality)
- **Response:** `BacktestCombinedResult`
- **Frontend client:** `results.ts → getBacktestResults(runId)`
- **Used by:** Baseline detail (full results section)

### `GET /api/results/backtest/{run_id}/quality`
- **Purpose:** Quality flags for a backtest result
- **Response:** quality flags object
- **Frontend client:** `results.ts → getResultQuality(runId)`

---

## Domain: Decisions

Prefix: `/api/v1/decisions`

### `GET /api/decisions/policies`
- **Purpose:** List available decision policies (conservative, balanced, aggressive)
- **Response:** policy list
- **Frontend client:** `decisions.ts → listPolicies()`

### `GET /api/decisions/policies/{name}`
- **Purpose:** Get a specific policy's gate thresholds
- **Response:** policy detail with gate configurations
- **Frontend client:** `decisions.ts → getPolicy(name)`

### `GET /api/decisions/runs/{run_id}`
- **Purpose:** Get all decision results for a run
- **Response:** `DecisionResult[]`
- **Frontend client:** `decisions.ts → getRunDecision(runId)`

### `GET /api/decisions/runs/{run_id}/latest`
- **Purpose:** Most recent decision result for a run
- **Response:** `DecisionResult`
- **Frontend client:** `decisions.ts → getLatestRunDecision(runId)`
- **Used by:** Dashboard, Baseline detail, Journey page

### `POST /api/decisions/runs/{run_id}/evaluate`
- **Purpose:** Re-evaluate a run through the decision engine
- **Response:** `DecisionResult`
- **Frontend client:** Not called directly from UI (used internally by pipelines)

---

## Domain: Freqtrade

Prefix: `/api/v1/freqtrade`

### `GET /api/v1/freqtrade/status`
- **Purpose:** Check Freqtrade CLI availability and version
- **Response:** `{ executable_available: bool, version: string, allowed_commands: string[] }`
- **Frontend client:** `freqtrade.ts → getFreqtradeStatus()`
- **Used by:** System status, Settings page

### `GET /api/v1/freqtrade/workspace`
- **Purpose:** Validate Freqtrade workspace structure
- **Response:** `{ valid: bool, user_data_dir: string, config_dir: string, issues: string[] }`
- **Frontend client:** `freqtrade.ts → getFreqtradeWorkspace()`

### `POST /api/v1/freqtrade/config/backtest`
- **Purpose:** Generate a Freqtrade backtest config file
- **Body:** `ConfigBacktestRequest` — `strategy`, `pairs`, `timeframe`
- **Response:** `{ config_path: string, artifact_id: string }`
- **Execution flag:** Writes config file to disk

### `POST /api/v1/freqtrade/data/check`
- **Purpose:** Check historical data availability for given pairs/timerange
- **Body:** `FreqtradeDataCheckRequest` — `pairs`, `timerange`, `timeframe`
- **Response:** `FreqtradeDataCheckResult` — per-pair data availability
- **Frontend client:** `freqtrade.ts → checkData()`
- **Used by:** DataAvailabilityPreview component

### `POST /api/v1/freqtrade/data/download`
- **Purpose:** Download historical data for given pairs
- **Body:** `FreqtradeDataDownloadRequest` — includes `user_confirmed: true`
- **Response:** `FreqtradeDataDownloadResult`
- **Execution flag:** Triggers Freqtrade download-data subprocess

### `POST /api/v1/freqtrade/backtest`
- **Purpose:** Execute a raw Freqtrade backtest (low-level, used internally by pipeline)
- **Body:** `FreqtradeBacktestRequest` — includes `user_confirmed: true`
- **Response:** `FreqtradeBacktestResult`
- **Execution flag:** Triggers Freqtrade backtesting subprocess

---

## Domain: Artifacts, Metrics, Logs

### `GET /api/artifacts`
- **Purpose:** List all registered artifacts
- **Frontend client:** `artifacts.ts → listArtifacts()`

### `GET /api/artifacts/{id}`
- **Purpose:** Get a single artifact record
- **Frontend client:** `artifacts.ts → getArtifact(id)`

### `GET /api/runs/{run_id}/artifacts`
- **Purpose:** List artifacts for a specific run
- **Frontend client:** `artifacts.ts → listRunArtifacts(runId)`
- **Used by:** Baseline detail artifacts section

### `GET /api/audit-logs`
- **Purpose:** Query audit log entries
- **Frontend client:** `artifacts.ts → listAuditLogs()`
