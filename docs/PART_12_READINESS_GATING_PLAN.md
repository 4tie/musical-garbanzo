# Part 12: Backend Strategy Readiness Gating Plan

## Overview

Implement backend enforcement of strategy readiness before baseline and optimization runs can start. The API must prevent execution when strategies are not structurally ready, regardless of frontend warnings.

## Current State Analysis

### Backend Start Points

**Baseline Run Start**
- Endpoint: `POST /api/baseline/evaluate`
- Router: `backend/app/api/v1/routers/baseline.py` (lines 25-70)
- Schema: `BaselineEvaluationRequest`
- Strategy field: `strategy_name: str` (required)

**Optimization Run Start**
- Endpoint: `POST /api/optimization/run`
- Router: `backend/app/api/v1/routers/optimization.py` (lines 36-117)
- Schema: `OptimizationRequest`
- Strategy field: `strategy_name: str` (required)

### Readiness States (from Part 11)

**Allowed for run execution:**
- `ready` - Strategy is structurally complete and safe
- `warning` - Strategy has minor issues but can still run

**Blocked from run execution:**
- `missing_sidecar` - Sidecar JSON file is missing
- `invalid` - Strategy structure is invalid
- `parse_error` - Python syntax or JSON parsing error
- `unsafe` - Security or path safety issues

### Existing Error Response Patterns

Current routers use FastAPI's `HTTPException` with:
- Status codes: 400 (bad request), 404 (not found), 500 (server error)
- Simple `detail` field with error message
- No structured error codes or next actions

Example from baseline.py:
```python
raise HTTPException(status_code=400, detail="Invalid or unsafe strategy name")
```

## Implementation Design

### Gating Approach: Dedicated Gate Service

**Decision:** Implement a dedicated `strategy_readiness_gate.py` service

**Rationale:**
1. Reusable across both baseline and optimization routers
2. Centralized logic for easier maintenance and testing
3. Follows existing pattern of service layer for business logic
4. Better than router guards for complex validation logic
5. Separates gating logic from workspace inspection logic

### New Service (Prompt 2 - COMPLETED)

**Location:** `backend/app/services/strategy_readiness_gate.py`

**Functions implemented:**
```python
def assert_strategy_ready_for_run(
    strategy_name: str,
    run_type: str = "baseline",
    workspace_service: Optional[StrategyWorkspaceService] = None,
) -> StrategyReadinessGateResult:
    """
    Assert that a strategy is ready for baseline or optimization run execution.

    This function performs static validation only - it does not execute strategy code,
    run Freqtrade, modify files, or auto-fix anything.

    Returns StrategyReadinessGateResult with allowed=True if strategy is ready.
    Raises HTTPException with structured StrategyReadinessBlockedError if not ready.
    """

def check_strategy_readiness(
    strategy_name: str,
    workspace_service: Optional[StrategyWorkspaceService] = None,
) -> StrategyReadinessGateResult:
    """
    Check strategy readiness without raising exceptions.

    This is a non-asserting version that returns the result regardless of readiness state.
    Useful for checking readiness without blocking execution.
    """
```

### Blocked Response Contract

**Status Code:** 400 (Bad Request)

**Response Body:**
```json
{
  "error": true,
  "code": "strategy_not_ready",
  "message": "Strategy is not ready for validation.",
  "strategy_name": "ExampleStrategy",
  "readiness": "missing_sidecar",
  "issues": [
    {
      "code": "sidecar_missing",
      "severity": "error",
      "message": "Sidecar JSON file not found",
      "details": {}
    }
  ],
  "warnings": [],
  "next_actions": [
    "Open Strategy Workspace",
    "Inspect strategy readiness issues",
    "Fix the strategy or sidecar JSON manually",
    "Revalidate before starting baseline or optimization"
  ]
}
```

### Router Integration Points

**Baseline Router (`baseline.py`):**
```python
@router.post("/baseline/evaluate", response_model=BaselineEvaluationResult)
def evaluate_baseline(request: BaselineEvaluationRequest) -> BaselineEvaluationResult:
    # NEW: Check strategy readiness before service call
    from app.services.strategy_readiness_gate import assert_strategy_ready_for_run
    assert_strategy_ready_for_run(request.strategy_name, run_type="baseline")
    
    # Existing service call continues...
    service = BaselineEvaluationService(...)
    result = service.evaluate(request)
    return result
```

**Optimization Router (`optimization.py`):**
```python
@router.post("/optimization/run", response_model=OptimizationStartResponse, status_code=202)
async def start_optimization(request: OptimizationRequest) -> OptimizationStartResponse:
    # NEW: Check strategy readiness before service call
    from app.services.strategy_readiness_gate import assert_strategy_ready_for_run
    assert_strategy_ready_for_run(request.strategy_name, run_type="optimization")
    
    # Existing validation continues...
    if not request.strategy_name or not request.pairs or not request.timeframe:
        raise HTTPException(status_code=400, detail="...")
    
    # Existing service call continues...
    pipeline_service = OptimizationPipelineService(...)
    result = pipeline_service.run_optimization(request)
    return result
```

### New Schema for Blocked Response (Prompt 2 - COMPLETED)

**Location:** `backend/app/schemas/strategies.py`

**Schemas implemented:**
```python
class StrategyReadinessGateResult(BaseModel):
    """Result of strategy readiness gate check for run execution."""
    strategy_name: str
    readiness: StrategyReadiness
    allowed: bool
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    message: str
    next_actions: list[str] = Field(default_factory=list)


class StrategyReadinessBlockedError(BaseModel):
    """Structured error response when strategy readiness blocks run execution."""
    error: bool = True
    code: str = "strategy_not_ready"
    message: str = "Strategy is not ready for validation."
    strategy_name: str
    readiness: StrategyReadiness
    issues: list[StrategyIssue] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    next_actions: list[str] = Field(
        default_factory=lambda: [
            "Open Strategy Workspace",
            "Inspect strategy readiness issues",
            "Fix the strategy or sidecar JSON manually",
            "Revalidate before starting baseline or optimization"
        ]
    )
```

## Implementation Steps

### Step 1: Review Existing Blocked Response Schema (Prompt 2 - COMPLETED)
- ✅ Reviewed `StrategyReadinessGateResult` in `backend/app/schemas/strategies.py`
- ✅ Reviewed `StrategyReadinessBlockedError` in `backend/app/schemas/strategies.py`
- ✅ Schemas include all required fields per contract
- ✅ No updates needed

### Step 2: Review Existing Service Function (Prompt 2 - COMPLETED)
- ✅ Reviewed `backend/app/services/strategy_readiness_gate.py`
- ✅ Reviewed `assert_strategy_ready_for_run()` function
- ✅ Reviewed `check_strategy_readiness()` function (non-asserting version)
- ✅ Functions use `StrategyWorkspaceService` to get strategy detail
- ✅ Functions check readiness against allowed/blocked states
- ✅ Functions raise HTTPException with structured response if blocked
- ✅ Functions return result if ready
- ✅ No updates needed

### Step 3: Review Existing Unit Tests (Prompt 2 - COMPLETED)
- ✅ Reviewed `backend/tests/test_strategy_readiness_gate.py`
- ✅ Verified ready allowed test
- ✅ Verified warning allowed test
- ✅ Verified missing_sidecar blocked test
- ✅ Verified invalid blocked test
- ✅ Verified parse_error blocked test
- ✅ Verified unsafe blocked test
- ✅ Verified missing strategy blocked test
- ✅ Verified unsafe strategy name blocked test
- ✅ Verified strategy file not executed test
- ✅ All required tests present and passing

### Step 4: Integrate into Baseline Router (Prompt 3 - COMPLETED)
- ✅ Added readiness check at start of `evaluate_baseline()` endpoint
- ✅ Imported gate service and called `assert_strategy_ready_for_run()`
- ✅ Kept existing error handling
- ✅ Gate check happens before service initialization

### Step 5: Integrate into Optimization Router (Prompt 4 - COMPLETED)
- ✅ Added readiness check at start of `start_optimization()` endpoint
- ✅ Imported gate service and called `assert_strategy_ready_for_run()`
- ✅ Kept existing error handling
- ✅ Gate check happens before service initialization

### Step 6: Add Integration Tests (Prompt 3 - COMPLETED for baseline)
- ✅ Test baseline router blocks non-ready strategies
- ✅ Test baseline router allows ready strategies
- ✅ Test baseline router allows warning strategies
- ✅ Test blocked response structure matches contract
- ✅ Test each blocked readiness state
- ✅ Test blocked baseline does not start execution
- ✅ Test blocked response includes next_actions

### Step 7: Add Optimization Integration Tests (Prompt 4 - COMPLETED)
- ✅ Test optimization router blocks non-ready strategies
- ✅ Test optimization router allows ready strategies
- ✅ Test optimization router allows warning strategies
- ✅ Test blocked response structure matches contract
- ✅ Test each blocked readiness state
- ✅ Test blocked optimization does not start execution
- ✅ Test blocked optimization does not start baseline-first
- ✅ Test blocked response includes next_actions

### Step 8: Add Frontend Blocked Readiness UX (Prompt 5 - COMPLETED)
- ✅ Added strategy_not_ready error kind to ApiErrorKind
- ✅ Added isStrategyReadinessBlockedPayload detection in API client
- ✅ Created StrategyReadinessBlockedBanner component
- ✅ Added blocked readiness state to baseline page
- ✅ Added blocked readiness state to optimization page
- ✅ Integrated banner display in baseline page
- ✅ Integrated banner display in optimization page
- ✅ Added strategy detail link to banner
- ✅ Frontend lint passes
- ✅ Frontend build passes

## Testing Strategy

### Unit Tests
- Test `assert_strategy_ready_for_run()` with each readiness state
- Test blocked response structure
- Test HTTPException raising

### Integration Tests
- Test baseline endpoint with blocked strategies
- Test optimization endpoint with blocked strategies
- Test successful runs with ready strategies
- Test successful runs with warning strategies

### Test Fixtures
- Reuse existing strategy workspace fixtures
- Create strategies in each readiness state
- Mock service calls where appropriate

## Edge Cases

1. **Strategy not found**: Handled by gate service - returns HTTPException with readiness=unsafe
2. **Unsafe strategy name**: Handled by gate service - returns HTTPException with readiness=unsafe
3. **Service initialization failure**: Handled by gate service - returns HTTPException with structured error
4. **Readiness check failure**: Handled by gate service - returns HTTPException with structured error
5. **Workspace errors**: Converted to HTTPException with structured blocked response

## Validation Commands

**Prompt 2 (COMPLETED):**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_strategy_readiness_gate.py tests/test_strategy_workspace_utils.py tests/test_strategy_workspace_service.py -q
# Result: 37 passed
```

**Prompt 3 (COMPLETED):**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_baseline_api.py tests/test_strategy_readiness_gate.py -q
# Result: 32 passed, 1 skipped
```

**Prompt 4 (COMPLETED):**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_optimization_api.py tests/test_strategy_readiness_gate.py -q
# Result: 53 passed
```

## Non-Goals (Explicitly Out of Scope)

- AI strategy repair
- AI strategy generation
- Strategy editing
- Params editing
- Export functionality
- Approval workflows
- Live trading
- OOS/WFO/robustness testing
- Auto-fix functionality
- Exchange orders
- Profitability claims

## Success Criteria

1. Backend prevents baseline runs when strategy readiness is blocked
2. Backend prevents optimization runs when strategy readiness is blocked
3. Backend allows baseline runs when strategy readiness is ready or warning
4. Backend allows optimization runs when strategy readiness is ready or warning
5. Blocked response matches specified contract
6. Existing tests pass
7. New tests cover gating logic
8. No frontend changes required (backend enforcement only)
