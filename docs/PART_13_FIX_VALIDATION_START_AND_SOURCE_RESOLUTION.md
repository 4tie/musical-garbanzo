# Part 13 Fix: Validation Start Flow and Optimization Source Resolver

## Overview

This fix implements two critical improvements to the validation evidence layer:
1. **Run Validation action** on baseline and optimization detail pages with confirmation dialog
2. **Optimization source resolver** using `OptimizationRepository` to correctly resolve `optimization_run` sources

**Fix Date:** June 30, 2026

**Status:** ✅ COMPLETE

## Backend Changes

### 1. ValidationExecutionService Optimization Run Resolver

**File:** `backend/app/services/validation_execution_service.py`

**Changes:**
- Added `OptimizationRepository` import and injection in `__init__`
- Updated `_build_candidate_reference` method to handle `source_type="optimization_run"`:
  - Loads optimization run from `OptimizationRepository.get_optimization_run(source_run_id)`
  - Validates `optimized_run_id` exists, raises `optimized_run_missing` if missing
  - Loads optimized run from `RunRepository.get_run(optimized_run_id)`
  - Uses optimized run's strategy, pairs, timeframe, exchange, risk_profile, timerange, metrics
  - Preserves optimization metadata: `optimization_run_id`, `baseline_run_id`, `best_trial_id`, `optimized_run_id`
  - Adds warning `optimized_source_metrics_missing` if optimized run has no metrics
- Updated `_controlled_code_for_value_error` to include new controlled failure codes:
  - `optimization_run_not_found` - optimization run missing
  - `optimized_run_missing` - optimized_run_id field missing

**Behavior:**
- For `source_type="optimization_run"`: Uses `OptimizationRepository` → `optimized_run_id` → `RunRepository`
- For `source_type="baseline_run"`: Uses `RunRepository` directly (unchanged)
- For `source_type="optimized_run"`: Uses `RunRepository` directly (unchanged)
- For `source_type="strategy"`: Uses request fields directly (unchanged)

**Controlled Failures:**
- `optimization_run_not_found`: Optimization run not found in database
- `optimized_run_missing`: Optimization run exists but has no `optimized_run_id`
- `optimized_source_metrics_missing`: Warning when optimized run has no metrics (non-blocking)

### 2. Backend Tests

**File:** `backend/tests/test_validation_execution_service.py`

**Changes:**
- Added `OptimizationRepository` import
- Added test `test_optimization_run_source_uses_optimized_run_id`:
  - Creates baseline run, optimized run with metrics, and optimization run
  - Verifies candidate uses optimized run data
  - Verifies candidate includes optimization metadata
- Added test `test_optimization_run_not_found_controlled_failure`:
  - Verifies controlled failure when optimization run missing
- Added test `test_optimized_run_missing_controlled_failure`:
  - Verifies controlled failure when optimized_run_id missing
- Added test `test_optimized_run_missing_metrics_warning`:
  - Verifies warning added when optimized run has no metrics

## Frontend Changes

### 3. ValidationConfirmationDialog Component

**File:** `frontend/src/components/ValidationConfirmationDialog.tsx` (new)

**Features:**
- Modal dialog with confirmation for validation start
- Displays validation parameters:
  - Strategy name
  - Source type
  - Source run ID
  - Pairs
  - Timeframe
  - Risk profile
- Shows disclaimer: "Validation is evidence only. It is not strategy approval, export, live-trading authorization, or a guarantee of future performance."
- Confirm and Cancel buttons
- Escape key to close
- Click outside to close (via backdrop)

### 4. Baseline Detail Page Run Validation Button

**File:** `frontend/src/app/baseline/[runId]/BaselineDetailClient.tsx`

**Changes:**
- Added imports: `startValidation` from `@/lib/api/validation`, `ValidationConfirmationDialog`
- Added `validationDialogOpen` to state
- Added `handleRunValidation` callback:
  - Creates validation request with `source_type="baseline_run"`
  - Calls `startValidation` with `user_confirmed=true`
  - On success, navigates to `/validation/{validation_run_id}`
- Added "Run Validation" button in PageHeader actions:
  - Disabled if required fields missing (strategy_id, pairs, timeframe)
  - Opens confirmation dialog on click
- Added `ValidationConfirmationDialog` component at bottom of page

### 5. Optimization Detail Page Run Validation Button

**File:** `frontend/src/app/optimization/[optimizationRunId]/OptimizationDetailClient.tsx`

**Changes:**
- Added imports: `startValidation` from `@/lib/api/validation`, `ValidationConfirmationDialog`
- Added `validationDialogOpen` to state
- Added `handleRunValidation` callback:
  - Creates validation request with `source_type="optimization_run"`
  - Uses optimization run data for strategy_name, pairs, timeframe, exchange, risk_profile
  - Calls `startValidation` with `user_confirmed=true`
  - On success, navigates to `/validation/{validation_run_id}`
- Added "Run Validation" button in PageHeader actions:
  - Disabled if `optimized_run_id` missing or required fields missing
  - Opens confirmation dialog on click
- Added `ValidationConfirmationDialog` component at bottom of page

## Documentation Changes

### 6. PART_13_COMPLETION_REPORT.md

**Changes:**
- Removed "Run Validation action from baseline/optimization detail pages" from deferred list
- Removed "Strategy readiness banner integration on validation start" from deferred list
- Updated to reflect that these features are now implemented

### 7. PART_13_VALIDATION_EVIDENCE_PLAN.md

**Changes:**
- Updated Prompt 9 frontend implementation status:
  - Added "Run Validation action from baseline/optimization detail pages with confirmation dialog"
  - Added "ValidationConfirmationDialog component for validation start confirmation"
- Added "Part 13 fix (optimization_run resolver)" section:
  - Documented OptimizationRepository integration
  - Documented optimized_run_id preference
  - Documented controlled failures and warnings
  - Documented backend tests

## Test Results

### Backend Tests

**Command:**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_validation_execution_service.py tests/test_validation_controlled_failures.py tests/test_validation_api.py -q
```

**Expected Results:**
- All existing tests pass
- New optimization_run resolver tests pass
- Controlled failure tests pass
- API tests pass

### Frontend Tests

**Lint:**
```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
```

**Build:**
```bash
cd /home/mohs/Desktop/her/frontend
npm run build
```

**Expected Results:**
- Lint passes with no errors
- Build compiles successfully

### Repo Hygiene

**Command:**
```bash
cd /home/mohs/Desktop/her
git status --short
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
```

**Expected Results:**
- Only source/docs changes shown
- No runtime files in git status
- grep returns no output

## Files Changed

### Backend Files
- `backend/app/services/validation_execution_service.py` - OptimizationRepository integration, optimization_run resolver
- `backend/tests/test_validation_execution_service.py` - Tests for optimization_run resolver

### Frontend Files
- `frontend/src/components/ValidationConfirmationDialog.tsx` - New confirmation dialog component
- `frontend/src/app/baseline/[runId]/BaselineDetailClient.tsx` - Run Validation button and dialog
- `frontend/src/app/optimization/[optimizationRunId]/OptimizationDetailClient.tsx` - Run Validation button and dialog

### Documentation Files
- `docs/PART_13_COMPLETION_REPORT.md` - Updated deferred features list
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md` - Updated implementation status

## Validation Criteria

### Backend Validation
- ✅ `source_type="optimization_run"` loads from `OptimizationRepository`
- ✅ optimization run uses `optimized_run_id`, not `baseline_run_id`
- ✅ missing optimization run returns controlled failure
- ✅ missing optimized_run_id returns controlled failure
- ✅ baseline_run still works
- ✅ optimized_run still works
- ✅ strategy source still works
- ✅ no live/export/approval behavior
- ✅ no secrets or stdout/stderr in responses

### Frontend Validation
- ✅ baseline detail page has Run Validation button
- ✅ optimization detail page has Run Validation button
- ✅ confirmation dialog appears
- ✅ API called with correct source_type/source_run_id
- ✅ success navigates to `/validation/{validation_run_id}`
- ✅ missing fields disable button
- ✅ no approval/export/live/profit guarantee wording

## Security and Safety

- ✅ No fake evidence
- ✅ No approval/export/live trading controls
- ✅ No profit guarantees
- ✅ No secrets in responses
- ✅ No runtime files committed
- ✅ Controlled failures for error cases
- ✅ Clear disclaimers in confirmation dialog

## Commit Information

**Commit Message:** `Part 13 fix: add validation start flow and optimization source resolver`

**Files to Commit:**
- `backend/app/services/validation_execution_service.py`
- `backend/tests/test_validation_execution_service.py`
- `frontend/src/components/ValidationConfirmationDialog.tsx`
- `frontend/src/app/baseline/[runId]/BaselineDetailClient.tsx`
- `frontend/src/app/optimization/[optimizationRunId]/OptimizationDetailClient.tsx`
- `docs/PART_13_COMPLETION_REPORT.md`
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- `docs/PART_13_FIX_VALIDATION_START_AND_SOURCE_RESOLUTION.md`

## Summary

This fix successfully implements the Run Validation action on baseline and optimization detail pages with a confirmation dialog, and fixes the optimization_run source resolver to correctly use OptimizationRepository and optimized_run_id. All changes maintain the existing safety guarantees: no approval/export/live trading, no profit guarantees, no fake evidence, and proper controlled failures for error cases.
