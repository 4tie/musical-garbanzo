# Part 12 Prompt 1 Report: Backend Readiness Gate Planning

## Files Inspected

### Strategy Workspace Service
- **File:** `backend/app/services/strategy_workspace_service.py`
- **Key findings:**
  - Contains `get_strategy()` method that returns `StrategyDetail` with readiness state
  - Contains `resolve_strategy_for_run()` method (line 114-121) that returns strategy detail for run usage
  - Readiness computed via `_compute_readiness()` method
  - Service already has safety pattern inspection and params completeness checks
  - Uses `StrategyWorkspaceUtils` for file operations and validation

### Baseline Router
- **File:** `backend/app/api/v1/routers/baseline.py`
- **Key findings:**
  - Run start endpoint: `POST /api/baseline/evaluate` (line 25-70)
  - Request schema: `BaselineEvaluationRequest` with `strategy_name: str` field
  - Currently creates `BaselineEvaluationService` and calls `evaluate()`
  - No existing strategy readiness check
  - Error handling uses FastAPI `HTTPException` with simple detail messages

### Optimization Router
- **File:** `backend/app/api/v1/routers/optimization.py`
- **Key findings:**
  - Run start endpoint: `POST /api/optimization/run` (line 36-117)
  - Request schema: `OptimizationRequest` with `strategy_name: str` field
  - Currently validates request fields and user_confirmed
  - Creates `OptimizationPipelineService` and calls `run_optimization()`
  - No existing strategy readiness check
  - Error handling uses FastAPI `HTTPException` with simple detail messages

### Strategy Workspace Router
- **File:** `backend/app/api/v1/routers/strategy_workspace.py`
- **Key findings:**
  - Shows pattern for strategy workspace service usage
  - Has helper functions like `_raise_for_detail_errors()` for error handling
  - Returns structured `StrategyDetail` responses
  - Uses HTTPException for unsafe paths and missing strategies

### Baseline Schema
- **File:** `backend/app/schemas/baseline.py`
- **Key findings:**
  - `BaselineEvaluationRequest` requires `strategy_name` field
  - Field validation ensures non-empty strategy_name
  - Response includes success, status, run_id, and next_actions

### Optimization Schema
- **File:** `backend/app/schemas/optimization.py`
- **Key findings:**
  - `OptimizationRequest` requires `strategy_name` field
  - Field validation ensures non-empty strategy_name
  - Response includes run_id, status, and message

### Strategy Schemas
- **File:** `backend/app/schemas/strategies.py`
- **Key findings:**
  - `StrategyReadiness` enum defines: ready, warning, missing_sidecar, invalid, parse_error, unsafe
  - `StrategyDetail` contains readiness, issues, warnings
  - `StrategyIssue` has code, severity, message, details
  - Existing patterns for structured error responses

### Test Files
- **File:** `backend/tests/test_baseline_api.py`
  - Shows pattern for testing baseline endpoints with mocked services
  - Tests validation, error responses, and clean frontend data
- **File:** `backend/tests/test_optimization_api.py`
  - Shows pattern for testing optimization endpoints with mocked services
  - Tests validation, error responses, and request rejection
- **File:** `backend/tests/test_strategy_workspace_api.py`
  - Shows pattern for testing strategy workspace endpoints
  - Tests listing, detail retrieval, and error handling

## Backend Start Points Found

### Baseline Run Start
- **Endpoint:** `POST /api/baseline/evaluate`
- **Router:** `backend/app/api/v1/routers/baseline.py:25-70`
- **Strategy field:** `request.strategy_name` (from `BaselineEvaluationRequest`)
- **Current behavior:** No readiness check, proceeds directly to service call

### Optimization Run Start
- **Endpoint:** `POST /api/optimization/run`
- **Router:** `backend/app/api/v1/routers/optimization.py:36-117`
- **Strategy field:** `request.strategy_name` (from `OptimizationRequest`)
- **Current behavior:** No readiness check, proceeds directly to service call

## Exact Request Fields for Strategy Name

### Baseline
```python
class BaselineEvaluationRequest(BaseModel):
    strategy_name: str = Field(..., description="Existing Freqtrade strategy name")
```

### Optimization
```python
class OptimizationRequest(BaseModel):
    strategy_name: str = Field(..., description="Strategy name in Freqtrade workspace")
```

Both use `strategy_name` as a required string field.

## Current Error Response Style

Current routers use FastAPI's `HTTPException` with simple detail strings:

```python
raise HTTPException(status_code=400, detail="Invalid or unsafe strategy name")
raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
raise HTTPException(status_code=500, detail="Baseline evaluation failed. Check run logs for details.")
```

No structured error codes, no next_actions, no issue details.

## Gating Design Decision

### Approach: Dedicated Gate Service

**Decision:** Implement a dedicated `strategy_readiness_gate.py` service

**Rationale:**
1. **Reusability:** Single service can be called from both baseline and optimization routers
2. **Centralization:** Logic in one place, easier to maintain and test
3. **Consistency:** Ensures both routers use identical readiness checking logic
4. **Pattern alignment:** Follows existing service layer pattern for business logic
5. **Separation:** Separates gating logic from workspace inspection logic
6. **Testability:** Easier to unit test service function than router decorators

**Alternative considered but rejected:**
- Router guard/decorator: Would require duplicating logic or complex dependency injection
- Direct router validation: Would duplicate code between baseline and optimization routers
- Adding to StrategyWorkspaceService: Would mix concerns (inspection vs gating)

### Implementation Design

**Note:** A `strategy_readiness_gate.py` service file already exists from previous work. It will be reviewed and potentially updated during Prompt 2 implementation.

**Service functions (existing to be reviewed):**
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

**Integration pattern:**
```python
# At the start of each run endpoint
from app.services.strategy_readiness_gate import assert_strategy_ready_for_run
assert_strategy_ready_for_run(request.strategy_name, run_type="baseline")
```

## Blocked Response Contract

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

**Design decisions:**
- Structured error code for frontend handling
- Full strategy detail for debugging
- Issues array with specific problem codes
- Next actions array to guide user resolution
- Warnings array preserved from strategy detail

## Docs Created

1. **docs/PART_12_READINESS_GATING_PLAN.md**
   - Complete implementation plan
   - Design rationale and approach decision
   - Step-by-step implementation guide
   - Testing strategy
   - Edge case handling
   - Success criteria

2. **docs/PART_12_PROMPT_01_REPORT.md** (this file)
   - Files inspected and findings
   - Backend start points identified
   - Gating design decision
   - Blocked response contract
   - Current error response patterns

## Validation Status

**Not yet run** - Runtime behavior unchanged per prompt requirements

**Planned validation:**
```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_strategy_workspace_utils.py tests/test_strategy_workspace_service.py tests/test_strategy_workspace_api.py tests/test_strategy_import_api.py -q
```

## Readiness for Prompt 2

**Status:** Ready to continue

**Prerequisites met:**
- ✅ Code inspection completed
- ✅ Backend start points identified
- ✅ Request fields documented
- ✅ Error response patterns reviewed
- ✅ Gating approach designed
- ✅ Blocked response contract defined
- ✅ Implementation plan documented
- ✅ No runtime changes made

**Next steps (Prompt 2):**
1. Implement blocked response schema
2. Implement service function
3. Integrate into baseline router
4. Integrate into optimization router
5. Add comprehensive tests
6. Validate with existing test suite
