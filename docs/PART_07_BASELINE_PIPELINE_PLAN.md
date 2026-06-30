# Part 07 Baseline Evaluation Pipeline Plan

## Purpose

Part 07 builds a safe baseline evaluation workflow for an existing Freqtrade strategy. It connects the completed Part 04 Freqtrade integration, Part 05 backtest parser, and Part 06 decision engine into one traceable orchestration path.

The pipeline evaluates one already-existing strategy end to end:

1. Create a HER run.
2. Validate the selected strategy exists and is visible to the local Freqtrade workspace.
3. Generate a safe backtest-only Freqtrade config.
4. Check local market data availability.
5. Download missing market data only when explicitly allowed.
6. Run a real Freqtrade backtest only when explicitly confirmed.
7. Parse the captured real backtest result.
8. Evaluate the parsed evidence with deterministic decision gates.
9. Save stage progress and final report artifacts.
10. Expose API and CLI access for the same workflow.

Core rule:

```text
AI suggests. Backend validates. Freqtrade tests. HER decides.
```

## Implementation Status: COMPLETED (Prompt 6)

The baseline evaluation pipeline is now fully implemented with API endpoints and CLI script as of Prompt 6. The following components are complete:

### Completed Components

**Service Layer:**
- `backend/app/services/baseline_evaluation_service.py` - Main orchestration service with all 10 stages
- Reuses existing Part 04 services: FreqtradeStrategyService, FreqtradeConfigGenerator, FreqtradeDataService, FreqtradeBacktestRunner
- Reuses existing Part 05 services: BacktestResultParser
- Reuses existing Part 06 services: DecisionService
- Implements controlled failure handling with no unhandled exceptions
- Tracks all stages with timestamps, messages, warnings, and errors
- **NEW (Prompt 4):** Added controlled failure helper methods: `_start_stage`, `_complete_stage`, `_fail_stage`, `_confirmation_required`, `_add_run_log`, `_add_audit_log`, `_get_error_message`
- **NEW (Prompt 4):** All failures use specific error codes with user-facing messages
- **NEW (Prompt 4):** Stage results include error_code field for frontend integration
- **NEW (Prompt 4):** Error messages provide next_actions for user guidance

**Schema Layer:**
- `backend/app/schemas/baseline.py` - Already existed with comprehensive contracts
- BaselineEvaluationRequest with full validation
- BaselineStageResult for stage tracking
- **NEW (Prompt 4):** Added error_code field to BaselineStageResult for controlled failure tracking
- BaselineEvaluationResult for final results
- BaselineStatusResponse for status queries

**Repository Layer:**
- `backend/app/repositories/runs.py` - Updated with baseline_evaluation mode support
- `backend/app/repositories/run_stages.py` - Added create_baseline_stages() and mark_stage_waiting() methods
- Added "completed" status to RUN_STATUSES
- Added "baseline_evaluation" to RUN_MODES

**Test Layer:**
- `backend/tests/test_baseline_evaluation_service.py` - Comprehensive unit tests with mocks
- Tests all acceptance criteria from Prompt 3
- Tests controlled failure scenarios
- Tests confirmation requirement scenarios
- Tests stage tracking
- Tests no Ollama/Discord calls
- Tests no approval/export classification emission
- **NEW (Prompt 4):** `backend/tests/test_baseline_controlled_failures.py` - Comprehensive controlled failure tests
- **NEW (Prompt 4):** Tests all error codes have user-facing messages and next_actions
- **NEW (Prompt 4):** Tests confirmation-required download and backtest paths
- **NEW (Prompt 4):** Tests rejected decision still returns pipeline success
- **NEW (Prompt 4):** Tests failed stages store error codes and frontend-ready data
- **NEW (Prompt 4):** Tests no stack traces in responses
- **NEW (Prompt 4):** Tests no secrets in errors/details
- **NEW (Prompt 5):** `backend/tests/test_baseline_api.py` - Comprehensive API endpoint tests
- **NEW (Prompt 5):** Tests OpenAPI includes Baseline Evaluation tag
- **NEW (Prompt 5):** Tests evaluate endpoint accepts valid request
- **NEW (Prompt 5):** Tests evaluate endpoint rejects invalid request
- **NEW (Prompt 5):** Tests confirmation required response is clean
- **NEW (Prompt 5):** Tests get run status returns frontend-ready data
- **NEW (Prompt 5):** Tests get report missing returns controlled 404
- **NEW (Prompt 5):** Tests no secrets in response
- **NEW (Prompt 5):** Tests endpoint does not expose raw stdout/stderr content by default
- **NEW (Prompt 5):** Tests no approved/export/live/profit guarantee wording

**Constants:**
- `backend/app/core/constants.py` - Updated with baseline pipeline stages and statuses
- **NEW (Prompt 4):** Added BASELINE_ERROR_CODES list with 14 specific error codes
- **NEW (Prompt 4):** Added BASELINE_ERROR_MESSAGES mapping with user-facing messages and next_actions for each error code

**API Layer:**
- **NEW (Prompt 5):** `backend/app/api/v1/routers/baseline.py` - Baseline evaluation API router
- **NEW (Prompt 5):** POST /api/baseline/evaluate - Evaluate baseline through complete pipeline
- **NEW (Prompt 5):** GET /api/baseline/runs/{run_id} - Get full baseline run summary
- **NEW (Prompt 5):** GET /api/baseline/runs/{run_id}/status - Get lightweight status
- **NEW (Prompt 5):** GET /api/baseline/runs/{run_id}/report - Get baseline report artifact
- **NEW (Prompt 5):** Router mounted under /api and /api/v1 in main.py
- **NEW (Prompt 5):** Clean error responses with no stack traces or secrets
- **NEW (Prompt 5):** Synchronous execution (no background workers in Part 07)

**Documentation:**
- **NEW (Prompt 5):** `docs/API_CONTRACTS.md` - Updated with baseline API endpoint documentation
- **NEW (Prompt 5):** Includes request example with HERSmokeStrategy
- **NEW (Prompt 5):** Documents all four baseline endpoints with examples
- **NEW (Prompt 5):** Documents error behavior and confirmation requirements
- **NEW (Prompt 6):** `docs/BASELINE_EVALUATION.md` - Comprehensive CLI documentation
- **NEW (Prompt 6):** Includes CLI command examples and expected smoke result
- **NEW (Prompt 6):** Documents pipeline stages, safety rules, and troubleshooting

**CLI Layer:**
- **NEW (Prompt 6):** `scripts/run-baseline-evaluation.py` - CLI script for real baseline evaluation
- **NEW (Prompt 6):** Accepts all required and optional CLI arguments
- **NEW (Prompt 6):** Requires --user-confirmed for real execution
- **NEW (Prompt 6):** Prints structured output with key metrics and stage summary
- **NEW (Prompt 6):** Returns appropriate exit codes based on status
- **NEW (Prompt 6):** Follows all safety rules (no Ollama, Discord, approval, export, live trading)

**CLI Safety Tests:**
- **NEW (Prompt 6):** `backend/tests/test_baseline_real_script_safety.py` - Comprehensive safety tests
- **NEW (Prompt 6):** Tests script exists and imports BaselineEvaluationService
- **NEW (Prompt 6):** Tests script requires --user-confirmed for real execution
- **NEW (Prompt 6):** Tests script does not call Ollama or Discord
- **NEW (Prompt 6):** Tests script does not contain approval/export logic
- **NEW (Prompt 6):** Tests script does not create fake metrics
- **NEW (Prompt 6):** Tests script does not directly run unsafe Freqtrade commands
- **NEW (Prompt 6):** Tests script contains expected final markers
- **NEW (Prompt 6):** AST parsing tests to verify no forbidden imports

### Remaining Work (Future Prompts)

- Frontend integration (Prompt 7)
- Real Freqtrade validation tests (Prompt 8)

## Readiness Verification

Part 04 Freqtrade integration files verified:

- `backend/app/services/freqtrade_backtest_runner.py`
- `backend/app/services/freqtrade_config_generator.py`
- `backend/app/services/freqtrade_data_service.py`
- `backend/app/services/freqtrade_strategy_service.py`
- `backend/app/services/freqtrade_command_runner.py`
- `scripts/freqtrade-real-smoke-test.py`

Part 05 parser and metrics files verified:

- `backend/app/services/backtest_result_parser.py`
- `backend/app/services/backtest_metrics_extractor.py`
- `backend/app/services/backtest_pair_trade_parser.py`
- `backend/app/services/result_quality_service.py`
- `scripts/parse-real-smoke-backtest.py`

Part 06 decision files verified:

- `backend/app/services/decision_engine.py`
- `backend/app/services/decision_policy.py`
- `backend/app/services/decision_service.py`
- `backend/app/repositories/decisions.py`
- `backend/app/api/v1/routers/decisions.py`
- `scripts/evaluate-real-smoke-decision.py`
- `backend/tests/conftest.py`
- `backend/tests/test_pytest_database_isolation.py`
- `docs/PART_06_COMPLETION_REPORT.md`

Required context docs reviewed:

- `docs/PART_06_COMPLETION_REPORT.md`
- `docs/RUN_LIFECYCLE.md`
- `docs/API_CONTRACTS.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/EVIDENCE_AND_TRACEABILITY.md`
- `docs/FREQTRADE_INTEGRATION.md`
- `docs/BACKTEST_RESULT_PARSER.md`
- `docs/DECISION_ENGINE.md`
- `docs/PARTS_ROADMAP.md`

## Existing Services To Reuse

Part 07 should orchestrate existing components instead of duplicating their logic.

Run and stage tracking:

- `RunsRepository`
- `RunStagesRepository`
- existing run and stage API contracts

Strategy validation:

- `FreqtradeStrategyService`

Backtest config generation:

- `FreqtradeConfigGenerator`

Data check and optional download:

- `FreqtradeDataService`

Real backtest execution:

- `FreqtradeBacktestRunner`
- `FreqtradeCommandRunner`

Result parsing:

- `BacktestResultParser`
- `BacktestMetricsExtractor`
- `BacktestPairTradeParser`
- `ResultQualityService`

Decision evaluation:

- `DecisionPolicyService`
- `DecisionEngine`
- `DecisionService`
- `DecisionRepository`

Traceability:

- artifact repository
- run logs repository
- audit logs repository

## Baseline Evaluation Flow

The Part 07 orchestration should run in this order:

1. `run_setup`: create or load the HER run and persist requested inputs.
2. `strategy_validation`: verify strategy name/path, workspace containment, sidecar state, and Freqtrade visibility where available.
3. `config_generation`: generate and register a safe backtest config for the run.
4. `data_check`: inspect local data for requested exchange, pairs, timeframe, and timerange.
5. `data_download`: download missing data only when allowed by confirmation flags.
6. `baseline_backtest`: run real `freqtrade backtesting` only when explicitly confirmed.
7. `result_parsing`: parse captured raw backtest outputs into normalized persisted evidence.
8. `decision_evaluation`: evaluate parsed evidence and persist the decision result.
9. `baseline_report`: assemble a frontend-ready report from run, stage, artifact, parser, and decision evidence.
10. `completion`: mark the pipeline complete or failed with a controlled reason.

No stage may skip its safety checks. A later stage must not infer success from an earlier stage unless the earlier stage wrote an explicit passed status and expected evidence.

## Stage List

Part 07 stage keys:

- `run_setup`
- `strategy_validation`
- `config_generation`
- `data_check`
- `data_download`
- `baseline_backtest`
- `result_parsing`
- `decision_evaluation`
- `baseline_report`
- `completion`

Stage status values should follow the existing run-stage contract:

- `pending`
- `running`
- `passed`
- `failed`
- `skipped`
- `waiting`

Part 07 also defines a pipeline-level status contract for baseline response envelopes:

- `pending`
- `running`
- `completed`
- `failed_controlled`
- `confirmation_required`

Baseline evaluation modes:

- `real`

No fake or mock baseline mode exists.

Suggested stage behavior:

| Stage | Success Output | Controlled Stop Conditions |
| --- | --- | --- |
| `run_setup` | run id, persisted request | invalid input, missing required fields |
| `strategy_validation` | strategy metadata and visibility | missing strategy, invalid path, not visible to Freqtrade |
| `config_generation` | config artifact path | invalid config input, secret-like config value |
| `data_check` | availability result | missing required pairs/timeframe/timerange evidence |
| `data_download` | download command artifact/logs or skipped status | missing data with no confirmation, download disabled |
| `baseline_backtest` | raw Freqtrade output artifacts | confirmation missing, command failure, no structured output |
| `result_parsing` | normalized artifact and parsed DB rows | no parseable output, parser errors, unusable quality |
| `decision_evaluation` | decision result and decision artifact | missing parsed metrics, policy error |
| `baseline_report` | report payload/artifact | missing required evidence references |
| `completion` | final run status and stage summary | previous failed or waiting stage |

## Required Inputs

Minimum required inputs:

- `strategy_name` or existing strategy identifier.
- `exchange`, defaulting to the configured local default when omitted.
- `trading_mode`, defaulting to `spot` unless configured otherwise.
- `pairs`, one or more Freqtrade pair strings.
- `timeframe`.
- `timerange` or an equivalent bounded historical window.
- `risk_profile` for decision thresholds.
- `user_confirmed`.
- `download_missing_data`.

Optional inputs:

- `run_id` for resuming or re-evaluating an existing run.
- `run_name`.
- `force_parse`.
- `force_decision`.
- `apply_decision_to_run`.
- `config_overrides` limited to safe backtest-only fields.
- report format selector for CLI output.

## Schema Contract

Part 07 adds `backend/app/schemas/baseline.py` as the request and response contract for future baseline orchestration.

`BaselineEvaluationRequest` fields:

- `strategy_name`
- `pairs`
- `timeframe`
- `exchange`
- `days`
- `timerange`
- `risk_profile`
- `stake_currency`
- `stake_amount`
- `max_open_trades`
- `trading_mode`
- `download_missing_data`
- `user_confirmed`
- `apply_decision_to_run`
- `force_parse`
- `notes`

Request validation rules:

- `strategy_name` is required and must not be blank.
- `pairs` must not be empty.
- `timeframe` is required and must not be blank.
- `days` must be positive when provided.
- `risk_profile` must be `conservative`, `balanced`, or `aggressive`.
- `trading_mode` currently supports only `spot`.
- `download_missing_data=true` with `user_confirmed=false` is schema-valid, but service orchestration must stop before download.

Response schemas:

- `BaselineStageResult`: one safe stage summary with project-relative artifact paths.
- `BaselineEvaluationResult`: frontend-ready final or partial baseline report.
- `BaselineStatusResponse`: current run status, current stage, stage results, metrics, decision summary, warnings, and errors.

API-safe response rules:

- No secrets.
- No raw stdout or stderr content by default.
- No arbitrary full local absolute artifact paths.
- Artifact paths should be project-relative.
- Metrics and decision payloads should be summaries suitable for frontend display.

## Expected Outputs

The pipeline should return frontend-ready data without requiring the frontend to stitch together raw backend internals.

Expected response/report fields:

- `run_id`
- `status`
- `classification`
- `current_stage`
- `stages`
- `strategy`
- `config_artifact`
- `data_availability`
- `data_download`
- `backtest`
- `parse_result`
- `decision`
- `artifacts`
- `logs_summary`
- `warnings`
- `blocking_failures`
- `next_actions`

Expected persisted evidence:

- run row and stage rows in SQLite
- generated config artifact metadata
- raw Freqtrade output artifact metadata
- normalized parser artifact
- metrics snapshot
- pair results
- trade summary
- decision row
- decision artifact
- run logs
- audit logs

## Controlled Failure Behavior

Part 07 must prefer explicit controlled stops over ambiguous failure states.

Controlled stops should:

- update the current stage to `failed` or `waiting`
- set the run status to `failed_controlled` or `waiting_for_confirmation`
- store a clear `failure_reason`
- preserve all evidence collected so far
- avoid classifying strategy quality when the failure is environmental or data-related
- avoid deleting raw artifacts or market data

Required controlled outcomes:

- missing strategy: stop at `strategy_validation`
- invalid strategy path: stop at `strategy_validation`
- config validation failure: stop at `config_generation`
- missing market data and `download_missing_data=false`: stop at `data_check` or set `data_download` to `waiting`
- missing market data and `user_confirmed=false`: stop before any download command
- backtest requested with `user_confirmed=false`: stop before any backtest command
- Freqtrade command failure: stop at the command stage and retain stdout/stderr
- no parseable structured output: stop at `result_parsing`
- parsed metrics missing: stop at `decision_evaluation`

Data availability issues are system or setup failures, not strategy rejections.

## Explicit Confirmation Rules

Running real Freqtrade or downloading market data requires:

```json
{
  "user_confirmed": true
}
```

Downloading missing data also requires:

```json
{
  "download_missing_data": true
}
```

If `user_confirmed=false`, Part 07 must stop with a controlled failure or confirmation-required status before any Freqtrade command that downloads data or runs backtesting.

If `download_missing_data=false`, Part 07 must not download data even when `user_confirmed=true`.

Allowed behavior without confirmation:

- create a run
- validate strategy metadata
- generate a safe local config
- check data availability
- report that confirmation is required

Forbidden behavior without confirmation:

- `freqtrade download-data`
- `freqtrade backtesting`
- any command that can fetch market data
- any command that can execute a test run against Freqtrade beyond safe read-only checks

## API Plan

Part 07 should add a small orchestration API rather than forcing clients to call every lower-level endpoint manually.

Proposed endpoints under both `/api` and `/api/v1`:

- `POST /baseline-evaluations`
- `GET /baseline-evaluations/{run_id}`
- `POST /baseline-evaluations/{run_id}/resume`
- `GET /baseline-evaluations/{run_id}/report`

`POST /baseline-evaluations` should:

- validate the request
- create a run when no `run_id` is supplied
- initialize the Part 07 stages
- execute only stages allowed by confirmation flags
- return the latest pipeline status and report payload

`GET /baseline-evaluations/{run_id}` should:

- return run status, stage status, current stage, and available evidence references

`POST /baseline-evaluations/{run_id}/resume` should:

- continue from a waiting or controlled failure state when the new request provides required confirmation or corrected inputs
- never repeat real Freqtrade commands unless explicitly confirmed again

`GET /baseline-evaluations/{run_id}/report` should:

- return the final or partial frontend-ready baseline report
- include missing-evidence warnings when the report is incomplete

The API should continue exposing existing lower-level routes for advanced/manual workflows:

- run APIs
- run stage APIs
- Freqtrade config/data/backtest APIs
- results parse APIs
- decision APIs

## CLI Plan

Part 07 should add a CLI script for local repeatability and smoke validation:

```bash
python scripts/evaluate-baseline-strategy.py \
  --strategy SmokeTestStrategy \
  --pairs BTC/USDT \
  --timeframe 5m \
  --timerange 20240101-20240131 \
  --risk-profile balanced \
  --user-confirmed \
  --download-missing-data
```

Suggested CLI behavior:

- default to dry planning and read-only checks unless execution flags are present
- require `--user-confirmed` before download or backtest
- require `--download-missing-data` before missing data download
- print a compact stage summary
- print the final classification only after parsing and decision evaluation succeed
- write or reference the same report artifact used by the API

Useful CLI modes:

- `--plan-only`: validate inputs and show what would run
- `--check-data-only`: stop after data availability
- `--parse-only --run-id <id>`: parse existing raw backtest outputs
- `--decision-only --run-id <id>`: evaluate already parsed evidence
- `--json`: emit machine-readable status/report JSON

## Real Validation Plan

Part 07 real validation should be incremental:

1. Unit tests for pipeline request validation and confirmation gates.
2. Unit tests for stage status transitions and controlled failures.
3. Integration tests using fake command runners only for no-execution paths.
4. API tests for confirmation-required responses.
5. CLI safety tests proving no Freqtrade command runs without confirmation.
6. A real local smoke run only when explicitly invoked with confirmation.

Real validation command should be separate from normal tests and should not run silently in CI or ordinary local pytest:

```bash
python scripts/evaluate-baseline-strategy.py \
  --strategy SmokeTestStrategy \
  --pairs BTC/USDT \
  --timeframe 5m \
  --timerange 20240101-20240131 \
  --risk-profile balanced \
  --user-confirmed \
  --download-missing-data
```

## Prompt 4 Completion Summary

**Status:** COMPLETED

**Files Created/Updated:**
1. `backend/app/services/baseline_evaluation_service.py` - Main orchestration service with controlled failure helpers (1,390 lines)
2. `backend/tests/test_baseline_evaluation_service.py` - Comprehensive unit tests (931 lines)
3. `backend/tests/test_baseline_controlled_failures.py` - Controlled failure behavior tests (NEW - 450 lines)
4. `backend/app/repositories/runs.py` - Updated with baseline_evaluation mode support
5. `backend/app/repositories/run_stages.py` - Added baseline-specific methods
6. `backend/app/core/constants.py` - Added baseline pipeline constants and error messages
7. `backend/app/schemas/baseline.py` - Added error_code field to BaselineStageResult
8. `docs/PART_07_BASELINE_PIPELINE_PLAN.md` - Updated with Prompt 4 completion status
9. `docs/RUN_LIFECYCLE.md` - Updated with baseline evaluation controlled failure details
10. `docs/EVIDENCE_AND_TRACEABILITY.md` - Updated with baseline error code tracking

**Service Orchestration Summary:**
The BaselineEvaluationService successfully orchestrates all 10 required stages:
1. Run Setup - Creates run with baseline_evaluation mode and baseline-specific stages
2. Strategy Validation - Validates strategy exists, safe path, and Freqtrade visibility
3. Config Generation - Generates safe backtest config using existing FreqtradeConfigGenerator
4. Data Check - Checks data availability using existing FreqtradeDataService
5. Data Download - Downloads missing data only when allowed and confirmed
6. Baseline Backtest - Runs real backtest only when user confirmed
7. Result Parsing - Parses results using existing BacktestResultParser
8. Decision Evaluation - Evaluates decisions using existing DecisionService
9. Baseline Report - Creates comprehensive report artifact
10. Completion - Sets final run status and classification

**Stage Tracking Summary:**
- Each stage is recorded in run_stages table with status, timestamps, messages
- Stage statuses: pending, running, passed, failed, waiting
- Pipeline statuses: pending, running, completed, failed_controlled, confirmation_required
- All stages track warnings, errors, artifact paths, and details
- Stage results are returned in BaselineEvaluationResult.stage_results

**Controlled Failure Summary:**
- No unhandled exceptions leak to final response
- All exceptions are caught and result in failed_controlled status
- Each stage has explicit failure handling with error_data and logs_summary
- Run logs and audit logs are saved on failures
- Failed stages stop pipeline progression
- Confirmation required stages stop pipeline and wait for user input
- **NEW (Prompt 4):** All failures use specific error codes from BASELINE_ERROR_CODES
- **NEW (Prompt 4):** Error codes map to user-facing messages with next_actions
- **NEW (Prompt 4):** Stage results include error_code field for frontend integration
- **NEW (Prompt 4):** No stack traces in API-safe responses
- **NEW (Prompt 4):** No secrets in errors or details
- **NEW (Prompt 4):** Rejected classification does not mean pipeline failure

**Test Results:**
All acceptance criteria tests implemented:
- Missing strategy -> failed_controlled ✓
- Missing data + download disabled -> failed_controlled ✓
- Missing data + download true + user_confirmed false -> confirmation_required ✓
- user_confirmed false blocks backtest ✓
- Successful mocked flow calls parser and decision service ✓
- Failed backtest stops before parse ✓
- Failed parse stops before decision ✓
- Decision rejected still means pipeline success if evaluation completed ✓
- Stage results are recorded ✓
- Report artifact path generated ✓
- No Ollama/Discord calls ✓
- No approval/export classification emitted ✓
- **NEW (Prompt 4):** All error codes have user-facing messages and next_actions ✓
- **NEW (Prompt 4):** Confirmation-required download path tested ✓
- **NEW (Prompt 4):** Confirmation-required backtest path tested ✓
- **NEW (Prompt 4):** Rejected decision still returns pipeline success ✓
- **NEW (Prompt 4):** Failed stages store error codes ✓
- **NEW (Prompt 4):** No stack traces in responses ✓
- **NEW (Prompt 4):** No secrets in errors/details ✓
- **NEW (Prompt 4):** Frontend-ready stage data tested ✓

**Service Reuse:**
The service successfully reuses existing Part 04, 05, and 06 services:
- FreqtradeStrategyService (Part 04)
- FreqtradeConfigGenerator (Part 04)
- FreqtradeDataService (Part 04)
- FreqtradeBacktestRunner (Part 04)
- BacktestResultParser (Part 05)
- DecisionService (Part 06)
- RunRepository (existing)
- RunStageRepository (existing)
- ArtifactRepository (existing)
- RunLogRepository (existing)
- AuditLogRepository (existing)

**No Duplication:**
- No Freqtrade command logic duplicated
- No parser logic duplicated
- No decision logic duplicated
- All orchestration is coordinated through existing service APIs

**Next Steps:**
- Prompt 5: API endpoints implementation
- Prompt 6: Frontend integration
- Prompt 7: Real Freqtrade validation tests

Expected real validation evidence:

- run created
- all Part 07 stages visible
- safe config artifact written
- data checked and optionally downloaded only when allowed
- real Freqtrade backtest raw outputs captured
- parser emits normalized artifact
- decision result persisted
- final report references all evidence
- runtime DB and artifacts remain local and uncommitted

## Security Rules

Part 07 must preserve existing safety boundaries:

- local-only execution
- no cloud services
- no exchange order placement
- no live trading
- no dry-run bot loops
- no Freqtrade `trade`
- no Freqtrade `webserver`
- no secret exposure in configs, logs, audit records, artifacts, or API responses
- no fake result as readiness proof
- no hidden download or backtest command
- no deletion of market data or raw artifacts
- no `--erase` data download behavior
- no strategy approval
- no strategy export
- no profitability guarantees

## Non-Goals

Part 07 must not implement:

- strategy generation
- strategy repair
- Hyperopt
- walk-forward analysis
- out-of-sample validation
- robustness checks
- strategy approval
- strategy export
- live trading
- dry-run bot loops
- Ollama calls
- Discord notifications

## Documentation Notes

`docs/PARTS_ROADMAP.md` currently labels Part 07 as frontend app shell work. This prompt defines Part 07 as the Baseline Evaluation Pipeline. The implementation prompt should either update the roadmap numbering or explicitly treat this plan as the current Part 07 backend orchestration scope.

## Acceptance Criteria For This Planning Step

- Part 04, Part 05, and Part 06 readiness verified.
- `docs/PART_07_BASELINE_PIPELINE_PLAN.md` exists.
- Part 07 scope is clear.
- Non-goals are explicit.
- Stage names are documented.
- Confirmation rules are documented.
- No Freqtrade execution is required or performed.
- No implementation code is changed.
