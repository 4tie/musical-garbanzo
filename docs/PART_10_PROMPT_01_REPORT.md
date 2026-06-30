# Part 10 Prompt 01 Report: Read-Only Planning and Action API Contract Review

## Status: COMPLETED

All action API endpoints have been reviewed and documented. Frontend API structure has been inspected. UI flows have been planned. API gaps and risks have been identified.

## Files Inspected

### Frontend API Structure
- `frontend/src/lib/api/client.ts` - API client with GET methods, error handling, timeout support
- `frontend/src/lib/api/baseline.ts` - Baseline API helpers (GET only)
- `frontend/src/lib/api/optimization.ts` - Optimization API helpers (GET only)
- `frontend/src/lib/api/errors.ts` - Error handling utilities
- `frontend/src/lib/api/types.ts` - TypeScript type definitions
- `frontend/src/lib/api/adapters.ts` - Data adapters
- `frontend/src/lib/api/index.ts` - API exports

### Backend Action Endpoints
- `backend/app/api/v1/routers/baseline.py` - Baseline evaluation router with POST /api/baseline/evaluate
- `backend/app/api/v1/routers/optimization.py` - Optimization router with POST /api/optimization/run
- `backend/app/schemas/baseline.py` - Baseline request/response schemas
- `backend/app/schemas/optimization.py` - Optimization request/response schemas

### Backend Services (Referenced)
- `backend/app/services/baseline_evaluation_service.py` - Baseline evaluation service (referenced in router)
- `backend/app/services/optimization_pipeline_service.py` - Optimization pipeline service (referenced in router)

## Action Endpoints Reviewed

### Baseline Evaluation Endpoints

#### POST /api/baseline/evaluate
- **Method**: POST
- **Request Schema**: BaselineEvaluationRequest
- **Required Fields**: strategy_name, pairs, timeframe
- **Optional Fields**: exchange, days, timerange, risk_profile, stake_currency, stake_amount, max_open_trades, trading_mode, download_missing_data, user_confirmed, apply_decision_to_run, force_parse, notes
- **Confirmation Field**: user_confirmed (must be true for real execution)
- **Response Schema**: BaselineEvaluationResult
- **Response Shape**: Includes success, run_id, status, classification, confidence_score, strategy_name, pairs, timeframe, exchange, risk_profile, metrics, decision, quality_flags, stage_results, artifact_paths, warnings, errors, next_actions
- **Sync vs Async**: Synchronous (blocking operation)
- **Status Polling Endpoint**: GET /api/baseline/runs/{run_id}/status
- **Possible Controlled Failures**: Strategy validation, data availability, data download, backtest execution, result parsing, decision evaluation
- **Expected Frontend Behavior**: Validate input, show confirmation, set user_confirmed=true, send POST, show loading, display result, route to detail page on success

#### GET /api/baseline/runs/{run_id}/status
- **Method**: GET
- **Response Schema**: BaselineStatusResponse
- **Response Shape**: Includes run_id, status, classification, current_stage, stage_results, metrics, decision, warnings, errors
- **Expected Frontend Behavior**: Poll for progress updates

#### GET /api/baseline/runs/{run_id}
- **Method**: GET
- **Response Schema**: dict[str, Any]
- **Response Shape**: Includes run_id, status, classification, confidence_score, mode, created_at, updated_at, stages, metrics, decision, artifacts, warnings, errors
- **Expected Frontend Behavior**: Navigate to this page after successful evaluation

#### GET /api/baseline/runs/{run_id}/report
- **Method**: GET
- **Response Schema**: dict[str, Any]
- **Response Shape**: Includes run_id, artifact_id, artifact_type, description, file_path, sha256, size_bytes, created_at
- **Expected Frontend Behavior**: Display report metadata in detail page

### Optimization Endpoints

#### POST /api/optimization/run
- **Method**: POST
- **Request Schema**: OptimizationRequest
- **Required Fields**: strategy_name, pairs, timeframe
- **Optional Fields**: exchange, days, timerange, risk_profile, baseline_run_id, run_baseline_first, download_missing_data, user_confirmed, epochs, spaces, max_open_trades, stake_currency, stake_amount, apply_decision_to_run, notes
- **Confirmation Field**: user_confirmed (must be true for real execution)
- **Response Schema**: OptimizationStartResponse
- **Response Shape**: Includes run_id, status, message
- **HTTP Status**: 202 Accepted
- **Sync vs Async**: Synchronous (blocking operation despite 202 status)
- **Status Polling Endpoint**: GET /api/optimization/runs/{optimization_run_id}/status
- **Possible Controlled Failures**: Strategy validation, baseline reference, hyperopt policy validation, data availability, data download, hyperopt execution, hyperopt result parsing, optimized backtest, optimized result parsing, decision evaluation, comparison, report generation
- **Expected Frontend Behavior**: Validate input, show confirmation, set user_confirmed=true, send POST, show loading, display result, route to detail page on success

#### GET /api/optimization/runs/{optimization_run_id}/status
- **Method**: GET
- **Response Schema**: OptimizationStatusResponse
- **Response Shape**: Includes run_id, status, current_stage (null), stage_progress (null), epochs_completed, epochs_total, trials_completed, trials_total (null), message, error_code, created_at, updated_at
- **Expected Frontend Behavior**: Poll for progress updates

#### GET /api/optimization/runs/{optimization_run_id}
- **Method**: GET
- **Response Schema**: OptimizationRunDetail
- **Response Shape**: Includes run, stages (empty array), best_trial, comparison, artifact_paths
- **Expected Frontend Behavior**: Navigate to this page after successful optimization

#### GET /api/optimization/runs/{optimization_run_id}/trials
- **Method**: GET
- **Query Parameters**: limit, offset, status
- **Response Schema**: OptimizationTrial[]
- **Expected Frontend Behavior**: Display trials in optimization detail page

#### GET /api/optimization/runs/{optimization_run_id}/best-trial
- **Method**: GET
- **Response Schema**: OptimizationTrial
- **Expected Frontend Behavior**: Display best trial in optimization detail page

#### GET /api/optimization/runs/{optimization_run_id}/comparison
- **Method**: GET
- **Response Schema**: OptimizationComparison
- **Response Shape**: Includes optimization_run_id, baseline_run_id, optimized_run_id, best_trial_id, baseline_metrics, optimized_metrics, deltas, classifications, result_status, improvement_summary, warnings, overfit_suspected, created_at
- **Expected Frontend Behavior**: Display comparison in optimization detail page

#### GET /api/optimization/runs/{optimization_run_id}/report
- **Method**: GET
- **Response Schema**: dict[str, Any]
- **Response Shape**: Includes optimization_run_id, report_artifact_path, status, report
- **Expected Frontend Behavior**: Display report in optimization detail page

### Freqtrade Helper Endpoints
- **Status**: Not yet inspected in this prompt. Will be reviewed in subsequent prompts if needed for UI discovery.

## Request/Response Contract Summary

### Baseline Evaluation Contract
- **POST /api/baseline/evaluate** accepts BaselineEvaluationRequest with user_confirmed flag
- Returns BaselineEvaluationResult with full run details including run_id, status, classification, metrics, decision, stage_results
- Synchronous execution - blocks until complete
- Requires explicit user confirmation (user_confirmed=true)
- Supports data download confirmation (download_missing_data=true with user_confirmed=true)

### Optimization Contract
- **POST /api/optimization/run** accepts OptimizationRequest with user_confirmed flag
- Returns OptimizationStartResponse with run_id, status, message
- Synchronous execution - blocks until complete (despite 202 status)
- Requires explicit user confirmation (user_confirmed=true)
- Supports optional baseline reuse (baseline_run_id)
- Supports hyperopt configuration (epochs, spaces)

### Status Polling Contract
- **Baseline**: GET /api/baseline/runs/{run_id}/status returns current_stage, stage_results, metrics, decision
- **Optimization**: GET /api/optimization/runs/{optimization_run_id}/status returns current_stage (null), stage_progress (null), epochs_completed, trials_completed
- Both endpoints support progress tracking for long-running operations

## Required UI Flows

### 1. Start Baseline Evaluation Flow
- Entry points: Baseline list page, Dashboard
- Form modal/page with required fields (strategy_name, pairs, timeframe) and optional fields
- Confirmation modal with request summary and warning
- Set user_confirmed=true after user confirms
- Send POST request
- Show loading state during execution
- Display result (success or controlled failure)
- Route to /baseline/{run_id} on success
- Show ControlledFailureBanner on failure

### 2. Start Optimization Flow
- Entry points: Optimization list page, Dashboard, Baseline detail page
- Form modal/page with required fields (strategy_name, pairs, timeframe) and optional fields (epochs, spaces, baseline_run_id)
- Confirmation modal with request summary and warning
- Set user_confirmed=true after user confirms
- Send POST request
- Show loading state during execution
- Display result (success or controlled failure)
- Route to /optimization/{optimization_run_id} on success
- Show ControlledFailureBanner on failure

### 3. Confirmation Modal
- Request summary display
- Warning message about resource-intensive operation
- Estimated time/resource usage
- Confirmation checkbox
- Confirm and Cancel buttons
- Keyboard accessibility (Escape to cancel, Enter to confirm)

### 4. Request Validation
- Required fields must be non-empty
- Strategy name must be valid string
- Pairs must be non-empty list
- Timeframe must be valid string
- Epochs must be positive integer (max 200)
- Risk profile must be one of: conservative, balanced, aggressive
- Spaces must be subset of allowed values
- user_confirmed must be true before sending

### 5. Action Progress Panel
- Loading spinner/skeleton
- Current stage display
- Progress bar (if stage progress available)
- Estimated time remaining
- Cancel button (if supported by backend)

### 6. Status Polling
- Poll status endpoint every 2-5 seconds
- Update progress display
- Stop when status is completed/failed
- Handle network errors gracefully
- Implement exponential backoff on failures

### 7. Controlled Failure Display
- ControlledFailureBanner component (already exists from Part 09)
- Error details display
- Next actions list
- Retry option (if applicable)
- Navigate to detail page (if run was created)

### 8. Success Routing
- On baseline success: navigate to /baseline/{run_id}
- On optimization success: navigate to /optimization/{optimization_run_id}
- Show success toast/notification
- Update runs list to include new run
- Scroll to top of detail page

## API Gaps/Risks

### API Gaps

1. **No POST client method** - Frontend API client only has GET methods (apiPost needs to be added)
2. **No list strategies endpoint** - No backend endpoint to list available strategies for dropdown
3. **No pair/data availability endpoint** - No backend endpoint to check data availability for UI
4. **Synchronous execution** - Both POST endpoints are synchronous, which may cause timeout issues for long-running operations
5. **No current_stage in optimization status** - Optimization status response has current_stage=null (TODO in backend)
6. **No stage_progress in optimization status** - Optimization status response has stage_progress=null (TODO in backend)
7. **No trials_total in optimization status** - Optimization status response has trials_total=null (TODO in backend)
8. **No stages in optimization detail** - Optimization detail response has stages=[] (TODO in backend)

### Frontend Gaps

1. **No POST API client** - Need to add apiPost method to client.ts
2. **No action API clients** - Need to add startBaselineEvaluation and startOptimization functions
3. **No form components** - Need to build form components for baseline and optimization
4. **No confirmation modal** - Need to build reusable confirmation modal
5. **No progress panel** - Need to build progress display component
6. **No request validators** - Need to build request validation utilities
7. **No strategy selector** - Need to build strategy selection component
8. **No pair selector** - Need to build pair selection component
9. **No timeframe selector** - Need to build timeframe selection component

### Backend Gaps (Optional Fixes)

1. **Async execution** - Consider making POST endpoints async to avoid timeout issues
2. **Stage tracking** - Implement current_stage and stage_progress in optimization status
3. **Strategy listing** - Add endpoint to list available strategies
4. **Data availability** - Add endpoint to check data availability for UI
5. **Better error messages** - Normalize error messages across all endpoints

### Risks

1. **Timeout Risk** - Synchronous execution may timeout for long-running operations
2. **No Progress Tracking** - Without async execution, progress tracking is limited
3. **No Strategy Discovery** - Users must manually enter strategy names
4. **No Data Discovery** - Users cannot check data availability before starting
5. **Form Complexity** - Forms have many fields, may overwhelm users
6. **Validation Mismatch** - Frontend validation may not match backend validation exactly
7. **Controlled Failure Confusion** - Users may not understand controlled failures vs system failures

## Whether Backend Changes Are Needed Before UI

**NO** - Backend changes are not strictly required before building the UI. The existing backend endpoints are functional and can be used as-is.

**However**, the following backend improvements would enhance the UI experience:

1. **Async execution** - Making POST endpoints async would enable better progress tracking and avoid timeout issues
2. **Stage tracking** - Implementing current_stage and stage_progress in optimization status would enable better progress display
3. **Strategy listing** - Adding an endpoint to list available strategies would improve UX
4. **Data availability** - Adding an endpoint to check data availability would improve UX

These improvements can be addressed in subsequent prompts or parts if needed. For now, the UI can be built with the existing synchronous endpoints and manual strategy/pair input.

## Whether Prompt 2 Can Continue

**YES** - Prompt 2 can continue. The action API contracts have been fully reviewed and documented. The required UI flows have been planned. The API gaps and risks have been identified. The implementation plan is ready.

Prompt 2 will focus on adding POST API client methods to the frontend, which is the next logical step in building the safe run controls.
