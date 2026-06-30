# Part 10 Safe Run Controls Plan

## Part 10 Scope

Part 10 adds safe run controls to the read-only Mission Control Dashboard built in Part 09. The user can start baseline evaluations and optimization pipelines from the frontend with explicit confirmation, validation, and progress tracking.

### What Part 10 Adds

- Start Baseline Evaluation flow from frontend
- Start Safe Optimization flow from frontend
- Request validation before sending to backend
- Confirmation modal before execution
- Status polling and progress display
- Controlled failure display and recovery UX
- Success routing to detail pages
- Frontend API clients for POST endpoints

### What Part 10 Does NOT Add

- Live trading controls
- Exchange order placement
- Freqtrade `trade` or `webserver` commands
- Strategy approval
- Export approved strategy
- Send strategy to exchange
- AI repair
- Ollama calls
- Discord actions
- Profit guarantees
- Fake successful runs
- Fake metrics
- Fake charts
- Hidden execution
- Automatic execution on page load

## Non-Goals

- Backend pipeline changes (backend is already complete from Parts 07-08)
- New Freqtrade integration beyond existing Part 04-08 services
- AI/LLM integration
- Discord integration
- Live trading system
- Exchange integration
- Strategy export system
- Approval workflow beyond existing decision gates

## Action API Contract Map

### Baseline Evaluation

#### POST /api/baseline/evaluate

**Method**: POST

**URL**: `/api/baseline/evaluate`

**Request Schema**: `BaselineEvaluationRequest`

**Required Fields**:
- `strategy_name` (string) - Existing Freqtrade strategy name
- `pairs` (list[string]) - Pairs to evaluate
- `timeframe` (string) - Freqtrade timeframe

**Optional Fields**:
- `exchange` (string, default: "binance") - Exchange name
- `days` (int, default: 30) - Historical days to evaluate
- `timerange` (string, optional) - Optional Freqtrade timerange
- `risk_profile` (string, default: "balanced") - Decision risk profile (conservative, balanced, aggressive)
- `stake_currency` (string, default: "USDT") - Stake currency
- `stake_amount` (float | string, default: "unlimited") - Stake amount
- `max_open_trades` (int, default: 3) - Maximum open trades
- `trading_mode` (string, default: "spot") - Trading mode (only "spot" allowed)
- `download_missing_data` (bool, default: false) - Whether missing data may be downloaded
- `user_confirmed` (bool, default: false) - **Confirmation field** - must be true for real execution
- `apply_decision_to_run` (bool, default: true) - Apply decision classification to run
- `force_parse` (bool, default: true) - Replace previous parsed evidence for this run
- `notes` (string, optional) - Optional user notes

**Response Schema**: `BaselineEvaluationResult`

**Response Shape**:
```typescript
{
  success: boolean
  run_id: string | null
  status: string
  classification: string | null
  confidence_score: float | null
  strategy_name: string
  pairs: string[]
  timeframe: string
  exchange: string
  risk_profile: string
  metrics: object
  decision: object
  quality_flags: string[]
  stage_results: BaselineStageResult[]
  artifact_paths: string[]
  warnings: string[]
  errors: string[]
  next_actions: string[]
}
```

**Sync vs Async Behavior**: **Synchronous** - The endpoint runs the complete pipeline synchronously and returns the final result. This is a blocking operation that can take significant time.

**Status Polling Endpoint**: Not needed for synchronous execution, but status endpoint exists for progress tracking if needed: `GET /api/baseline/runs/{run_id}/status`

**Possible Controlled Failures**:
- Strategy validation failures
- Data availability failures
- Data download failures (if download_missing_data=true)
- Backtest execution failures
- Result parsing failures
- Decision evaluation failures
- Controlled failure from any stage

**Expected Frontend Behavior**:
1. Validate user input matches schema requirements
2. Show confirmation modal with request details
3. Set `user_confirmed=true` only after user confirms
4. Send POST request
5. Show loading state during synchronous execution
6. Display result (success or controlled failure)
7. Route to detail page on success
8. Show controlled failure banner on failure

#### GET /api/baseline/runs/{run_id}/status

**Method**: GET

**URL**: `/api/baseline/runs/{run_id}/status`

**Response Schema**: `BaselineStatusResponse`

**Response Shape**:
```typescript
{
  run_id: string
  status: string
  classification: string | null
  current_stage: string | null
  stage_results: BaselineStageResult[]
  metrics: object
  decision: object
  warnings: string[]
  errors: string[]
}
```

**Expected Frontend Behavior**: Poll this endpoint for progress updates if implementing async progress tracking.

#### GET /api/baseline/runs/{run_id}

**Method**: GET

**URL**: `/api/baseline/runs/{run_id}`

**Response Schema**: `dict[str, Any]`

**Response Shape**:
```typescript
{
  run_id: string
  status: string
  classification: string | null
  confidence_score: float | null
  mode: string
  created_at: string | null
  updated_at: string | null
  stages: object[]
  metrics: object
  decision: object
  artifacts: string[]
  warnings: string[]
  errors: string[]
}
```

**Expected Frontend Behavior**: Navigate to this page after successful baseline evaluation.

#### GET /api/baseline/runs/{run_id}/report

**Method**: GET

**URL**: `/api/baseline/runs/{run_id}/report`

**Response Schema**: `dict[str, Any]`

**Response Shape**:
```typescript
{
  run_id: string
  artifact_id: string
  artifact_type: string
  description: string
  file_path: string
  sha256: string
  size_bytes: number
  created_at: string | null
}
```

**Expected Frontend Behavior**: Display report metadata in detail page.

### Optimization

#### POST /api/optimization/run

**Method**: POST

**URL**: `/api/optimization/run`

**Request Schema**: `OptimizationRequest`

**Required Fields**:
- `strategy_name` (string) - Strategy name in Freqtrade workspace
- `pairs` (list[string]) - Trading pairs to optimize
- `timeframe` (string) - Timeframe for optimization

**Optional Fields**:
- `exchange` (string, default: "binance") - Exchange name
- `days` (int, default: 30) - Number of days of data
- `timerange` (string, optional) - Specific time range
- `risk_profile` (string, default: "balanced") - Risk profile (conservative, balanced, aggressive)
- `baseline_run_id` (string, optional) - Existing baseline run ID to reuse
- `run_baseline_first` (bool, default: true) - Run baseline before optimization
- `download_missing_data` (bool, default: false) - Download missing market data
- `user_confirmed` (bool, default: false) - **Confirmation field** - must be true for real execution
- `epochs` (int, default: 50) - Number of hyperopt epochs (max 200)
- `spaces` (list[string], default: ["buy", "sell"]) - Hyperopt spaces to optimize (allowed: buy, sell, roi, stoploss, trailing, protection)
- `max_open_trades` (int, default: 3) - Maximum open trades
- `stake_currency` (string, default: "USDT") - Stake currency
- `stake_amount` (float | string, default: "unlimited") - Stake amount
- `apply_decision_to_run` (bool, default: true) - Apply decision classification to run
- `notes` (string, optional) - Optional notes

**Response Schema**: `OptimizationStartResponse`

**Response Shape**:
```typescript
{
  run_id: string
  status: OptimizationStatus
  message: string
}
```

**HTTP Status**: 202 Accepted

**Sync vs Async Behavior**: **Synchronous** - The endpoint runs the complete pipeline synchronously and returns the final result. Despite returning 202, the execution is blocking.

**Status Polling Endpoint**: `GET /api/optimization/runs/{optimization_run_id}/status`

**Possible Controlled Failures**:
- Strategy validation failures
- Baseline reference failures (if run_baseline_first=true)
- Hyperopt policy validation failures
- Data availability failures
- Data download failures (if download_missing_data=true)
- Hyperopt execution failures
- Hyperopt result parsing failures
- Optimized backtest failures
- Optimized result parsing failures
- Decision evaluation failures
- Comparison failures
- Report generation failures

**Expected Frontend Behavior**:
1. Validate user input matches schema requirements
2. Show confirmation modal with request details
3. Set `user_confirmed=true` only after user confirms
4. Send POST request
5. Show loading state during synchronous execution
6. Display result (success or controlled failure)
7. Route to detail page on success
8. Show controlled failure banner on failure

#### GET /api/optimization/runs/{optimization_run_id}/status

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}/status`

**Response Schema**: `OptimizationStatusResponse`

**Response Shape**:
```typescript
{
  run_id: string
  status: OptimizationStatus
  current_stage: OptimizationStage | null
  stage_progress: dict[OptimizationStage, OptimizationStatus] | null
  epochs_completed: int | null
  epochs_total: int | null
  trials_completed: int | null
  trials_total: int | null
  message: string | null
  error_code: string | null
  created_at: datetime
  updated_at: datetime
}
```

**Expected Frontend Behavior**: Poll this endpoint for progress updates if implementing async progress tracking.

#### GET /api/optimization/runs/{optimization_run_id}

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}`

**Response Schema**: `OptimizationRunDetail`

**Response Shape**:
```typescript
{
  run: OptimizationRun
  stages: OptimizationStageResult[]
  best_trial: OptimizationTrial | null
  comparison: OptimizationComparison | null
  artifact_paths: string[]
}
```

**Expected Frontend Behavior**: Navigate to this page after successful optimization.

#### GET /api/optimization/runs/{optimization_run_id}/trials

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}/trials`

**Query Parameters**:
- `limit` (int, default: 100) - Maximum number of trials to return
- `offset` (int, default: 0) - Number of trials to skip
- `status` (string, optional) - Status filter

**Response Schema**: `OptimizationTrial[]`

**Expected Frontend Behavior**: Display trials in optimization detail page.

#### GET /api/optimization/runs/{optimization_run_id}/best-trial

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}/best-trial`

**Response Schema**: `OptimizationTrial`

**Expected Frontend Behavior**: Display best trial in optimization detail page.

#### GET /api/optimization/runs/{optimization_run_id}/comparison

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}/comparison`

**Response Schema**: `OptimizationComparison`

**Response Shape**:
```typescript
{
  optimization_run_id: string
  baseline_run_id: string | null
  optimized_run_id: string | null
  best_trial_id: string | null
  baseline_metrics: object | null
  optimized_metrics: object | null
  delta_profit_factor: float | null
  delta_expectancy: float | null
  delta_drawdown: float | null
  delta_trade_count: int | null
  baseline_classification: string | null
  optimized_classification: string | null
  result_status: OptimizationResultStatus | null
  improvement_summary: string | null
  warnings: string[]
  overfit_suspected: boolean
  created_at: datetime | null
}
```

**Expected Frontend Behavior**: Display comparison in optimization detail page.

#### GET /api/optimization/runs/{optimization_run_id}/report

**Method**: GET

**URL**: `/api/optimization/runs/{optimization_run_id}/report`

**Response Schema**: `dict[str, Any]`

**Response Shape**:
```typescript
{
  optimization_run_id: string
  report_artifact_path: string
  status: string
  report: object
}
```

**Expected Frontend Behavior**: Display report in optimization detail page.

### Freqtrade Helper Endpoints

**Status**: Not yet inspected in this prompt. Will be reviewed in subsequent prompts if needed for UI discovery.

## Planned UI Flows

### 1. Start Baseline Evaluation Flow

**Entry Points**:
- "Start Baseline Evaluation" button on Baseline list page
- "Start Baseline Evaluation" button on Dashboard

**Flow Steps**:
1. User clicks "Start Baseline Evaluation" button
2. Open Baseline Evaluation form modal/page
3. User fills in required fields:
   - Strategy name (dropdown or text input)
   - Pairs (text input or multi-select)
   - Timeframe (dropdown)
   - Optional: exchange, days, timerange, risk_profile, stake settings
4. User clicks "Continue" to review
5. Show confirmation modal with:
   - Request summary
   - Warning about resource-intensive operation
   - Estimated time (if available)
   - Confirmation checkbox
6. User confirms (sets user_confirmed=true)
7. Send POST request to `/api/baseline/evaluate`
8. Show loading state during execution
9. On success:
   - Display success message
   - Show run_id
   - Auto-navigate to `/baseline/{run_id}`
10. On controlled failure:
    - Display ControlledFailureBanner
    - Show error details
    - Provide next actions
11. On network error:
    - Display ErrorBanner
    - Provide retry option

### 2. Start Optimization Flow

**Entry Points**:
- "Start Optimization" button on Optimization list page
- "Start Optimization" button on Dashboard
- "Optimize this strategy" button on Baseline detail page

**Flow Steps**:
1. User clicks "Start Optimization" button
2. Open Optimization form modal/page
3. User fills in required fields:
   - Strategy name (dropdown or text input)
   - Pairs (text input or multi-select)
   - Timeframe (dropdown)
   - Optional: baseline_run_id (if reusing baseline), epochs, spaces, risk_profile, stake settings
4. User clicks "Continue" to review
5. Show confirmation modal with:
   - Request summary
   - Warning about resource-intensive operation
   - Estimated epochs and time
   - Confirmation checkbox
6. User confirms (sets user_confirmed=true)
7. Send POST request to `/api/optimization/run`
8. Show loading state during execution
9. On success:
   - Display success message
   - Show optimization_run_id
   - Auto-navigate to `/optimization/{optimization_run_id}`
10. On controlled failure:
    - Display ControlledFailureBanner
    - Show error details
    - Provide next actions
11. On network error:
    - Display ErrorBanner
    - Provide retry option

### 3. Confirmation Modal

**Purpose**: Explicit user confirmation before resource-intensive operations

**Components**:
- Request summary display
- Warning message about operation
- Estimated time/resource usage
- Confirmation checkbox
- Confirm and Cancel buttons
- Keyboard accessibility (Escape to cancel, Enter to confirm)

### 4. Request Validation

**Validation Rules**:
- Required fields must be non-empty
- Strategy name must be valid string
- Pairs must be non-empty list
- Timeframe must be valid string
- Epochs must be positive integer (max 200)
- Risk profile must be one of: conservative, balanced, aggressive
- Spaces must be subset of allowed values
- user_confirmed must be true before sending

**Validation Feedback**:
- Field-level error messages
- Form-level error summary
- Disable submit button until valid
- Show validation errors on blur/submit

### 5. Action Progress Panel

**Purpose**: Show progress during synchronous execution

**Components**:
- Loading spinner/skeleton
- Current stage display
- Progress bar (if stage progress available)
- Estimated time remaining
- Cancel button (if supported by backend)

**Behavior**:
- Show on request start
- Update during execution (if polling implemented)
- Hide on completion
- Show error on failure

### 6. Status Polling

**Purpose**: Track progress of long-running operations

**Behavior**:
- Poll status endpoint every 2-5 seconds
- Update progress display
- Stop when status is completed/failed
- Handle network errors gracefully
- Implement exponential backoff on failures

**Note**: Since both endpoints are synchronous, status polling may not be strictly necessary unless backend is updated to support async execution.

### 7. Controlled Failure Display

**Purpose**: Show controlled failures clearly without appearing as system crashes

**Components**:
- ControlledFailureBanner component (already exists from Part 09)
- Error details display
- Next actions list
- Retry option (if applicable)
- Navigate to detail page (if run was created)

**Behavior**:
- Use ControlledFailureBanner with appropriate title
- Show "This is not a system failure" message
- Display error_code and details
- Provide actionable next steps
- Distinguish from network errors

### 8. Success Routing

**Purpose**: Navigate user to appropriate detail page on success

**Behavior**:
- On baseline success: navigate to `/baseline/{run_id}`
- On optimization success: navigate to `/optimization/{optimization_run_id}`
- Show success toast/notification
- Update runs list to include new run
- Scroll to top of detail page

## Required Components

### New Components to Build

1. **BaselineEvaluationForm** - Form for baseline evaluation request (COMPLETED in Prompt 5 as /baseline page)
2. **OptimizationForm** - Form for optimization request (COMPLETED in Prompt 6 as /optimization page)
3. **ConfirmationModal** - Reusable confirmation modal (COMPLETED in Prompt 3 as ConfirmationDialog, ENHANCED in Prompt 9 with Escape key handler)
4. **ActionProgressPanel** - Progress display during execution (COMPLETED in Prompt 3, ENHANCED in Prompt 7 with runType, updatedAt, retry copy)
5. **RequestValidator** - Request validation utilities (COMPLETED in Prompt 2 as validators.ts)
6. **StrategySelector** - Strategy selection dropdown (COMPLETED in Prompt 3 as StrategySelect, ENHANCED in Prompt 4 with real endpoint)
7. **PairSelector** - Pair selection input (COMPLETED in Prompt 3 as PairInput, ENHANCED in Prompt 4 with validation)
8. **TimeframeSelector** - Timeframe selection dropdown (COMPLETED in Prompt 3 as TimeframeSelect, UPDATED in Prompt 4 with documented constants)
9. **RiskProfileSelector** - Risk profile dropdown (COMPLETED in Prompt 3 as RiskProfileSelect, UPDATED in Prompt 4 to match backend)
10. **DataAvailabilityPreview** - Data availability preview (COMPLETED in Prompt 3, ENHANCED in Prompt 4 with real endpoint)
11. **ValidationSummary** - Form validation summary (COMPLETED in Prompt 4)
12. **useRunPolling** - Reusable polling hook (COMPLETED in Prompt 7)
13. **ActionErrorDetails** - Error details display (COMPLETED in Prompt 3, ENHANCED in Prompt 8 with stage, error code, debug copy)
14. **RecoverySuggestions** - Recovery suggestion utilities (COMPLETED in Prompt 8)

### Existing Components to Reuse

1. **AppShell** - Layout shell
2. **PageHeader** - Page headers
3. **SectionCard** - Content sections
4. **Button** - Buttons
5. **StatusBadge** - Status indicators
6. **EmptyState** - Empty states
7. **ErrorBanner** - Error display
8. **ControlledFailureBanner** - Controlled failure display
9. **LoadingSkeleton** - Loading states
10. **Drawer** - Slide-out panels

### New API Clients to Build

1. **apiPost** - Generic POST method in client.ts (COMPLETED in Prompt 2)
2. **startBaselineEvaluation** - POST /api/baseline/evaluate (COMPLETED in Prompt 2)
3. **startOptimization** - POST /api/optimization/run (COMPLETED in Prompt 2)

### New Pages to Build

1. **Baseline Evaluation Page** - `/baseline/evaluate` or modal
2. **Optimization Page** - `/optimization/start` or modal

## Safety UX Rules

### Confirmation Requirements

1. **Explicit Confirmation** - No action starts without user confirmation
2. **Confirmation Checkbox** - User must check a box to confirm understanding
3. **Request Summary** - Show full request details before confirmation
4. **Warning Message** - Clear warning about resource-intensive operation
5. **No Silent Execution** - Never execute actions without user awareness

### Validation Requirements

1. **Frontend Validation** - Validate before sending to backend
2. **Field-Level Errors** - Show errors on individual fields
3. **Form-Level Errors** - Show summary of all errors
4. **Disable Submit** - Disable submit button until valid
5. **Clear Error Messages** - Human-readable error messages

### Error Handling Requirements

1. **Network Errors** - Show ErrorBanner with retry option
2. **Controlled Failures** - Show ControlledFailureBanner with next actions
3. **Validation Errors** - Show field-level errors
4. **Timeout Errors** - Show timeout message with retry option
5. **No Silent Failures** - Always show error to user

### Progress Display Requirements

1. **Loading State** - Show loading during execution
2. **Current Stage** - Show current stage if available
3. **Progress Bar** - Show progress if available
4. **Estimated Time** - Show estimated time if available
5. **Cancel Option** - Provide cancel if supported

### Success Display Requirements

1. **Success Message** - Show clear success message
2. **Run ID Display** - Show created run_id
3. **Auto-Navigation** - Navigate to detail page
4. **Update Lists** - Update runs list to include new run
5. **No False Success** - Never show success if operation failed

### Routing Requirements

1. **Detail Page Routing** - Navigate to appropriate detail page on success
2. **Back Button** - Support browser back button
3. **URL Updates** - Update URL on navigation
4. **Preserve State** - Preserve form state on navigation if needed
5. **Deep Linking** - Support direct links to detail pages

## Risk/Gap List

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

1. **No POST API client** - RESOLVED in Prompt 2: Added apiPost method to client.ts
2. **No action API clients** - RESOLVED in Prompt 2: Added startBaselineEvaluation and startOptimization functions
3. **No form components** - Need to build form components for baseline and optimization
4. **No confirmation modal** - Need to build reusable confirmation modal
5. **No progress panel** - Need to build progress display component
6. **No request validators** - RESOLVED in Prompt 2: Added request validation utilities in validators.ts
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

## Prompt-by-Prompt Implementation Plan

### Prompt 1 (Current)
- Inspect existing frontend API structure
- Inspect backend action endpoints
- Document action endpoint contracts
- Identify required UI flows
- Identify API gaps/risks
- Create PART_10_SAFE_RUN_CONTROLS_PLAN.md
- Create PART_10_PROMPT_01_REPORT.md

### Prompt 2
- Add apiPost method to frontend API client
- Add startBaselineEvaluation API client
- Add startOptimization API client
- Add TypeScript types for request schemas
- Test API clients with existing backend
- Create PART_10_PROMPT_02_REPORT.md

### Prompt 3
- Build ConfirmationModal component
- Build ActionProgressPanel component
- Build RequestValidator utilities
- Test components with mock data
- Create PART_10_PROMPT_03_REPORT.md

### Prompt 4
- Build BaselineEvaluationForm component
- Build StrategySelector component
- Build PairSelector component
- Build TimeframeSelector component
- Test form validation
- Create PART_10_PROMPT_04_REPORT.md

### Prompt 5
- Build OptimizationForm component
- Integrate with existing selectors
- Add epochs and spaces selection
- Test form validation
- Create PART_10_PROMPT_05_REPORT.md

### Prompt 6
- Add "Start Baseline Evaluation" buttons to Baseline page
- Add "Start Optimization" buttons to Optimization page
- Wire forms to API clients
- Implement confirmation flow
- Test end-to-end flow
- Create PART_10_PROMPT_06_REPORT.md

### Prompt 7
- Implement status polling (if needed)
- Implement progress display updates
- Handle controlled failures
- Implement success routing
- Test error scenarios
- Create PART_10_PROMPT_07_REPORT.md

### Prompt 8
- Polish form UX
- Add help text and tooltips
- Improve error messages
- Add keyboard shortcuts
- Test accessibility
- Create PART_10_PROMPT_08_REPORT.md

### Prompt 9
- Manual UI smoke test
- Test with real backend
- Test controlled failure scenarios
- Test success scenarios
- Fix any issues found
- Create PART_10_PROMPT_09_REPORT.md

### Prompt 10
- Final validation
- Update documentation
- Update PARTS_ROADMAP.md
- Create PART_10_COMPLETION_REPORT.md
- Commit and push
- Create PART_10_PROMPT_10_REPORT.md

## Known Limitations

1. **Synchronous Execution** - Both POST endpoints are synchronous, which may cause timeout issues for long-running operations. This is a backend limitation that may need to be addressed in a future part.

2. **No Strategy Discovery** - Users must manually enter strategy names. There is no backend endpoint to list available strategies for dropdown selection.

3. **No Data Discovery** - Users cannot check data availability before starting. There is no backend endpoint to check data availability for UI.

4. **Limited Progress Tracking** - Optimization status response has current_stage=null and stage_progress=null, limiting progress tracking capabilities.

5. **Form Complexity** - Forms have many fields, which may overwhelm users. This will be addressed with good UX design in later prompts.

6. **Validation Mismatch Risk** - Frontend validation may not match backend validation exactly. This will be mitigated by careful testing.

## Safety Confirmation

**CONFIRMED**: Part 10 will NOT add:
- Live trading controls
- Exchange order placement
- Freqtrade `trade` or `webserver` commands
- Strategy approval
- Export approved strategy
- Send strategy to exchange
- AI repair
- Ollama calls
- Discord actions
- Profit guarantees
- Fake successful runs
- Fake metrics
- Fake charts
- Hidden execution
- Automatic execution on page load

**CONFIRMED**: Part 10 will add:
- Safe baseline evaluation start flow
- Safe optimization start flow
- Explicit user confirmation
- Request validation
- Progress display
- Controlled failure display
- Success routing to detail pages
- Frontend API clients for POST endpoints
