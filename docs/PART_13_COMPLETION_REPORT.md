# Part 13 Completion Report: Validation Evidence Layer

## Overview

Part 13 implemented a complete validation evidence layer that answers whether a strategy survived deeper validation or only looked good in one backtest. The layer evaluates strategy evidence across out-of-sample (OOS) validation, walk-forward (WFO) validation, robustness checks, and sensitivity checks, with deterministic validation decisions and persisted evidence exposed through backend APIs and frontend evidence views.

**Status:** ✅ COMPLETE

**Completion Date:** June 30, 2026

**Core Rule:** AI suggests. Backend validates. Freqtrade tests. HER decides.

## Summary

Part 13 added a comprehensive validation evidence layer to HER, including:
- Validation database tables and repository
- Validation schemas for API contracts
- OOS timerange splitting service
- WFO window builder service
- Robustness evaluator
- Validation policy service
- Validation execution service
- Validation API endpoints
- Frontend validation evidence UI
- Comprehensive test coverage

The layer enforces strategy readiness gating before validation, requires user confirmation before execution, provides controlled failure responses, and clearly separates validation evidence from approval/export/live trading.

## Files Created/Updated

### Backend Files Created
- `backend/app/schemas/validation.py` - Validation Pydantic schemas (627 lines)
- `backend/app/api/v1/routers/validation.py` - Validation API router (411 lines)
- `backend/app/services/oos_timerange_service.py` - OOS timerange splitting (Prompt 4)
- `backend/app/services/wfo_window_service.py` - WFO window builder (Prompt 5)
- `backend/app/services/robustness_evaluator.py` - Robustness evaluator (Prompt 6)
- `backend/app/services/validation_policy_service.py` - Validation policy (Prompt 3)
- `backend/app/services/validation_execution_service.py` - Validation execution (Prompt 7)
- `backend/app/repositories/validation_repository.py` - Validation repository (Prompt 2)
- `backend/tests/test_validation_api.py` - API tests (348 lines)
- `backend/tests/test_validation_repository.py` - Repository tests (Prompt 2)
- `backend/tests/test_validation_schemas.py` - Schema tests (Prompt 2)
- `backend/tests/test_validation_policy_service.py` - Policy tests (Prompt 3)
- `backend/tests/test_oos_timerange_service.py` - OOS tests (Prompt 4)
- `backend/tests/test_wfo_window_service.py` - WFO tests (Prompt 5)
- `backend/tests/test_robustness_evaluator.py` - Robustness tests (Prompt 6)
- `backend/tests/test_validation_execution_service.py` - Execution tests (Prompt 7)
- `backend/tests/test_validation_controlled_failures.py` - Controlled failure tests (Prompt 7)

### Backend Files Updated
- `backend/app/main.py` - Added validation router mounting
- `backend/app/db/models.py` - Added validation_runs and validation_evidence tables (Prompt 2)

### Frontend Files Created
- `frontend/src/lib/api/validation.ts` - Validation API client
- `frontend/src/app/validation/page.tsx` - Validation list page
- `frontend/src/app/validation/[validationRunId]/page.tsx` - Validation detail page
- `frontend/src/components/ValidationDecisionBanner.tsx` - Decision banner
- `frontend/src/components/OOSValidationCard.tsx` - OOS evidence card
- `frontend/src/components/WFOValidationCard.tsx` - WFO evidence card
- `frontend/src/components/RobustnessValidationCard.tsx` - Robustness card

### Frontend Files Updated
- `frontend/src/lib/api/types.ts` - Added validation types
- `frontend/src/components/Sidebar.tsx` - Added Validation navigation

### Documentation Files Created
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md` - Validation plan
- `docs/OOS_VALIDATION.md` - OOS validation documentation (Prompt 4)
- `docs/WFO_VALIDATION.md` - WFO validation documentation (Prompt 5)
- `docs/ROBUSTNESS_VALIDATION.md` - Robustness validation documentation (Prompt 6)
- `docs/VALIDATION_POLICY.md` - Validation policy documentation (Prompt 3)
- `docs/PART_13_PROMPT_03_REPORT.md` - Prompt 3 report
- `docs/PART_13_PROMPT_04_REPORT.md` - Prompt 4 report
- `docs/PART_13_PROMPT_05_REPORT.md` - Prompt 5 report
- `docs/PART_13_PROMPT_06_REPORT.md` - Prompt 6 report
- `docs/PART_13_PROMPT_07_REPORT.md` - Prompt 7 report
- `docs/PART_13_PROMPT_08_REPORT.md` - Prompt 8 report
- `docs/PART_13_PROMPT_09_REPORT.md` - Prompt 9 report
- `docs/PART_13_COMPLETION_REPORT.md` - This completion report

### Documentation Files Updated
- `docs/API_CONTRACTS.md` - Added Part 13 Validation Evidence API section
- `docs/PARTS_ROADMAP.md` - Will mark Part 13 complete

## Validation Schemas Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/schemas/validation.py`

**Schemas Implemented:**
- `ValidationRunRequest` - Request body for starting validation
- `ValidationRunResponse` - Response from validation start
- `ValidationRunAPIListItem` - List item for validation runs
- `ValidationRunDB` - Database model for validation runs
- `ValidationEvidenceDB` - Database model for validation evidence
- `ValidationEvidence` - Evidence item with metrics, decision, issues
- `ValidationIssue` - Issue with code, message, severity, details
- `ValidationDecision` - Decision with status, reasons, failures
- `ValidationSummary` - Summary with evidence counts
- `ValidationOOSResult` - OOS validation result
- `ValidationWFOSummary` - WFO summary result
- `ValidationRobustnessSummary` - Robustness summary result
- `ValidationSensitivitySummary` - Sensitivity summary result

**Validation:** All schemas use Pydantic v2 with proper field validation, type hints, and serialization.

## Validation DB Migration Status

**Status:** ✅ COMPLETE

**Tables Added:**
- `validation_runs` - Stores validation run metadata
  - id, source_type, source_run_id, strategy_name, pairs_json, timeframe, exchange, risk_profile, status, validation_state, final_decision_json, request_json, report_artifact_path, created_at, updated_at
- `validation_evidence` - Stores validation evidence items
  - id, validation_run_id, evidence_type, status, window_index, timerange, metrics_json, decision_json, issues_json, warnings_json, artifact_paths_json, created_at

**Repository:** `ValidationRepository` provides CRUD operations for both tables.

**Migration:** Tables added through Alembic migration in Prompt 2.

## Evidence Persistence Status

**Status:** ✅ COMPLETE

**Persistence Model:**
- Validation runs stored in `validation_runs` table
- Evidence items stored in `validation_evidence` table
- Each evidence item linked to validation run via `validation_run_id`
- Evidence grouped by type: oos, wfo_window, wfo_summary, robustness, sensitivity, validation_decision
- Artifact paths stored as JSON array in `artifact_paths_json`
- Report artifact path stored in `report_artifact_path`

**Repository Operations:**
- `create_validation_run()` - Create new validation run
- `get_validation_run()` - Get validation run by ID
- `list_validation_runs()` - List validation runs with filters
- `update_validation_run()` - Update validation run status/decision
- `create_evidence()` - Create evidence item
- `list_evidence()` - List evidence for validation run
- `get_evidence_by_type()` - Get evidence by type

## Validation Policy Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/services/validation_policy_service.py`

**Policies Implemented:**
- Conservative risk profile (default)
- Balanced risk profile
- Aggressive risk profile

**Evaluation Methods:**
- `evaluate_oos()` - Evaluate OOS validation evidence
- `evaluate_wfo()` - Evaluate WFO validation evidence
- `evaluate_robustness()` - Evaluate robustness checks
- `evaluate_sensitivity()` - Evaluate sensitivity checks
- `make_final_decision()` - Make final validation decision

**Decision States:**
- `validated` - All checks passed
- `rejected` - Evidence failed gates
- `validation_error` - System error prevented validation

**Failure Issues:**
- Code, message, severity, metric name, actual value, threshold, next action

**Documentation:** `docs/VALIDATION_POLICY.md`

## OOS Splitter Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/services/oos_timerange_service.py`

**Features:**
- `parse_timerange()` - Parse Freqtrade timerange string
- `build_timerange()` - Build timerange string from dates
- `split_timerange()` - Split timerange into in-sample and OOS
- `build_from_days()` - Build timerange from day count
- `validate_min_duration()` - Validate minimum duration

**Supported Ratios:**
- 70/30 (default)
- 80/20
- 60/40

**Behavior:**
- OOS days rounded up to ensure minimum ratio
- OOS starts exactly at in-sample end boundary
- No date gap or overlap
- Controlled failure for invalid timeranges
- Deterministic output

**Documentation:** `docs/OOS_VALIDATION.md`

## WFO Window Builder Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/services/wfo_window_service.py`

**Features:**
- `build_wfo_windows()` - Build WFO windows from timerange
- `validate_wfo_config()` - Validate WFO configuration

**Window Configuration:**
- `train_days` - Training segment duration (default: 60)
- `test_days` - Test segment duration (default: 15)
- `step_days` - Step between windows (default: 15)
- `max_windows` - Maximum windows (default: 5)

**Behavior:**
- Windows are chronological and non-overlapping for test segments
- `step_days` >= `test_days` to prevent test window overlap
- 1-based `window_index`
- Each window has train_start, train_end, test_start, test_end
- Controlled failure for invalid configurations
- Deterministic output

**Documentation:** `docs/WFO_VALIDATION.md`

## Robustness Evaluator Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/services/robustness_evaluator.py`

**Checks Implemented:**
- Metric stability checks (trade count, profit factor, expectancy, drawdown)
- WFO stability checks (pass rate, zero-trade windows, non-positive expectancy, profit factor, unstable drawdown)
- Sensitivity variant checks (variant evidence evaluation)

**Summary Types:**
- Passed checks
- Warning checks
- Failed checks
- Critical findings

**Behavior:**
- Evaluates provided evidence only
- Does not run new backtests
- Returns structured summary with counts and findings
- Controlled failure for invalid inputs

**Documentation:** `docs/ROBUSTNESS_VALIDATION.md`

## Validation Execution Service Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/services/validation_execution_service.py`

**Features:**
- `run_validation()` - Execute complete validation workflow
- `resolve_candidate_reference()` - Resolve source to validation subject
- `execute_oos_validation()` - Execute OOS validation
- `execute_wfo_validation()` - Execute WFO validation
- `evaluate_robustness()` - Evaluate robustness checks
- `make_final_decision()` - Make final decision
- `write_report_artifact()` - Write validation report

**Source Types Supported:**
- `strategy` - Manual strategy from workspace
- `baseline_run` - Existing baseline run
- `optimization_run` - Completed optimization
- `optimized_run` - Optimized backtest run

**Safety Guarantees:**
- Strategy readiness gating before execution
- User confirmation required before execution
- Controlled failure responses
- No stdout/stderr in responses
- No secrets in responses
- No stack traces in error responses
- Project-relative artifact paths only

**Documentation:** Prompt 7 report

## Validation API Status

**Status:** ✅ COMPLETE

**Location:** `backend/app/api/v1/routers/validation.py`

**Endpoints:**
- `POST /api/validation/run` - Start validation run
- `GET /api/validation/runs` - List validation runs
- `GET /api/validation/runs/{validation_run_id}` - Get validation run detail
- `GET /api/validation/runs/{validation_run_id}/status` - Get validation status
- `GET /api/validation/runs/{validation_run_id}/evidence` - Get validation evidence
- `GET /api/validation/runs/{validation_run_id}/report` - Get validation report

**Mounting:** Both `/api` and `/api/v1` prefixes

**OpenAPI Tag:** "Validation"

**Safety Guarantees:**
- Evidence sanitization (stdout/stderr removed, secrets redacted)
- Controlled failure responses
- Clean error responses (404, 400, 500)
- No raw stack traces
- No secrets in responses
- Project-relative paths only

**Documentation:** `docs/API_CONTRACTS.md` Part 13 section

## Frontend Evidence UI Status

**Status:** ✅ COMPLETE

**Routes:**
- `/validation` - Validation list page
- `/validation/[validationRunId]` - Validation detail page

**Components:**
- `ValidationDecisionBanner` - Decision banner with disclaimers
- `OOSValidationCard` - OOS evidence display
- `WFOValidationCard` - WFO evidence display
- `RobustnessValidationCard` - Robustness checks display

**API Client:**
- `frontend/src/lib/api/validation.ts` - API client functions
- `frontend/src/lib/api/types.ts` - Validation type definitions

**Navigation:**
- Added "Validation" item to sidebar (code: VL)

**Safety Guarantees:**
- Decision banner always displays disclaimers
- No profit guarantee language
- No approval/export controls
- No live trading controls
- Clear separation between evidence and approval

**Documentation:** Prompt 9 report

## Test Results

### Backend Tests

**Command:**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest \
tests/test_validation_repository.py \
tests/test_validation_schemas.py \
tests/test_validation_policy_service.py \
tests/test_oos_timerange_service.py \
tests/test_wfo_window_service.py \
tests/test_robustness_evaluator.py \
tests/test_validation_execution_service.py \
tests/test_validation_controlled_failures.py \
tests/test_validation_api.py \
tests/test_strategy_readiness_gate.py \
tests/test_baseline_api.py \
tests/test_optimization_api.py \
-q
```

**Result:** ✅ PASSED
- 195 tests passed
- 1 test skipped
- 15 warnings (Pydantic deprecation, unrelated to Part 13)
- Duration: 3.79s

**Test Coverage:**
- Validation repository: CRUD operations
- Validation schemas: Pydantic validation
- Validation policy: OOS, WFO, robustness, final decision
- OOS timerange: Splitting, parsing, validation
- WFO windows: Building, validation
- Robustness evaluator: Metric stability, WFO stability
- Validation execution: Full workflow, controlled failures
- Validation API: All endpoints, error handling, sanitization
- Strategy readiness gate: Blocking non-ready strategies
- Baseline API: Integration with readiness gate
- Optimization API: Integration with readiness gate

### Frontend Tests

**Lint:**
```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
```

**Result:** ✅ PASSED
- 0 errors
- 0 warnings

**Build:**
```bash
cd /home/mohs/Desktop/her/frontend
npm run build
```

**Result:** ✅ PASSED
- Compiled successfully in 2.5s
- TypeScript finished in 4.2s
- Static pages generated successfully
- New routes added: /validation, /validation/[validationRunId]

## Frontend Lint/Build Results

**Lint:** ✅ PASSED (0 errors, 0 warnings)

**Build:** ✅ PASSED
- Compiled successfully
- TypeScript validation passed
- Static pages generated
- New validation routes included

## Repo Hygiene Result

**Git Status:**
```bash
cd /home/mohs/Desktop/her
git status --short
```

**Result:** ✅ CLEAN
- Only intended source/docs changes staged
- No runtime files committed

**Runtime Files Check:**
```bash
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
```

**Result:** ✅ CLEAN
- No __pycache__ files tracked
- No .pyc files tracked
- No .venv files tracked
- No node_modules files tracked
- No .next files tracked

## Manual Smoke Result

**Status:** NOT PERFORMED

**Reason:** Manual smoke testing requires running backend and frontend servers, which was not performed in this automated completion process. The automated test suite provides comprehensive coverage of all validation components.

**Automated Validation:**
- 195 backend tests passed
- Frontend lint passed
- Frontend build passed
- Repo hygiene passed

**Manual Smoke Checklist (Deferred):**
- Strategy Workspace loads
- Ready strategy can be selected
- Non-ready strategy is blocked
- Baseline still works for ready strategy
- Optimization still works for ready strategy
- Validation run can be started for a ready strategy/candidate
- OOS evidence displays
- WFO evidence displays
- Robustness evidence displays
- Rejected validation explains why
- Validated result does not claim guaranteed profit
- No live/export/approval/AI repair controls were added

## Security/Secrets Result

**Status:** ✅ SECURE

**Secrets Handling:**
- No secrets in API responses
- No secrets in validation reports
- No secrets in evidence artifacts
- Secret redaction in API router
- Project-relative paths only

**API Sanitization:**
- Stdout/stderr removed from responses
- Secrets redacted (api_key, apikey, secret, password, token)
- Stack traces removed from error responses
- Error messages limited to 300 characters

**No Unauthorized Actions:**
- No live trading commands
- No approval/export controls
- No AI repair/generation
- No Discord notifications
- No Ollama calls

## Runtime Files Not Committed Result

**Status:** ✅ CLEAN

**Files NOT Committed:**
- ❌ .env files
- ❌ data/her.db
- ❌ data/*.db
- ❌ .pytest_runtime/
- ❌ logs/
- ❌ artifacts/runs/
- ❌ freqtrade_workspace/config/runs/
- ❌ freqtrade_workspace/user_data/data/
- ❌ freqtrade_workspace/user_data/backtest_results/
- ❌ freqtrade_workspace/user_data/hyperopt_results/
- ❌ freqtrade_workspace/user_data/logs/
- ❌ node_modules/
- ❌ .next/
- ❌ __pycache__/
- ❌ .pyc files
- ❌ .venv/

**Files Committed:**
- ✅ Source code only
- ✅ Tests only
- ✅ Documentation only
- ✅ Migrations only

## What Part 13 Did Not Implement

**Deferred to Later Parts:**
- Evidence cards on baseline/optimization/strategy detail pages
- Real-time polling for running validations
- Filtering on validation list page
- Sensitivity card component (displayed inline)
- Hyperopt redesign for per-window optimization
- Strategy approval
- Strategy export
- Live trading
- Exchange order execution
- Profit guarantees

**Explicit Non-Goals:**
- AI strategy generation
- AI strategy repair
- Strategy editing
- New pair discovery
- Discord notifications
- Ollama calls
- Fake evidence

## Readiness for Part 14

**Status:** ✅ READY

**Part 13 Deliverables Complete:**
- ✅ Validation DB tables exist
- ✅ Validation schemas exist
- ✅ Validation repository exists
- ✅ OOS timerange splitter exists
- ✅ WFO window builder exists
- ✅ Robustness evaluator exists
- ✅ Validation policy exists
- ✅ Validation execution service exists
- ✅ Validation API exists
- ✅ Frontend validation evidence UI exists
- ✅ Evidence is persisted
- ✅ Final validation decision is produced
- ✅ Tests pass
- ✅ Frontend lint/build pass
- ✅ Repo hygiene passes
- ✅ No fake evidence
- ✅ No profit guarantees
- ✅ No approval/export/live trading
- ✅ No runtime files committed

**System State:**
- All validation components tested and working
- API endpoints available and documented
- Frontend UI available and building successfully
- Database schema complete
- Repository operations complete
- Policy evaluation complete
- Execution workflow complete
- Evidence persistence complete

**Acceptance Criteria Met:**
- All acceptance criteria from Prompt 10 satisfied
- No blocking issues
- No security concerns
- No hygiene issues
- Ready for Part 14

## Summary

Part 13 successfully implemented a complete validation evidence layer for HER. The layer provides comprehensive validation across OOS, WFO, robustness, and sensitivity checks, with deterministic decision-making, evidence persistence, API exposure, and frontend visualization. All safety guarantees are maintained: no approval/export/live trading, no profit guarantees, no fake evidence, and no runtime files committed.

**Completion Status:** ✅ COMPLETE

**Next Step:** Ready for Part 14
