# HER API Contracts

This document describes the API contracts for HER backend endpoints.

## Base URL

```
http://127.0.0.1:8000/api
```

`/api` is the preferred Part 03 API prefix. Existing `/api/v1` routes remain mounted for compatibility.

## Authentication

Currently, HER is a local-only application with no authentication. This may change in future versions.

## Common Response Codes

- `200 OK` - Request successful
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request data
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

## Error Response Format

All API errors use the same safe JSON envelope. Stack traces and raw exceptions are not returned.

```json
{
  "error": true,
  "type": "validation_error",
  "message": "Human readable message",
  "details": {}
}
```

Standard error types:
- `validation_error` - Invalid request data or invalid domain value
- `not_found` - Requested resource does not exist
- `conflict` - Request conflicts with existing state
- `system_error` - Unexpected backend failure
- `http_error` - Other HTTP error

## Pagination And Filtering

List endpoints use query parameters for filtering and pagination. Current Part 03 list endpoints return arrays directly and accept:
- `limit` - maximum number of rows, usually default `50` or `100`
- `offset` - number of rows to skip, default `0`
- domain filters such as `status`, `classification`, `strategy_id`, `run_id`, `artifact_type`, `stage_key`, `level`, or `action_type`

`PaginatedResponse` exists as a shared schema for future endpoints that need total counts without changing each item model.

## Part 07 Baseline Evaluation Contract

Part 07 defines the schema and stage contract for baseline evaluation of an existing strategy. This section documents the request and response payloads before orchestration endpoints are implemented.

Baseline evaluation mode:

- `real`

No fake or mock baseline evaluation mode exists.

Baseline pipeline stages:

1. `run_setup`
2. `strategy_validation`
3. `config_generation`
4. `data_check`
5. `data_download`
6. `baseline_backtest`
7. `result_parsing`
8. `decision_evaluation`
9. `baseline_report`
10. `completion`

Baseline pipeline statuses:

- `pending`
- `running`
- `completed`
- `failed_controlled`
- `confirmation_required`

### Baseline Evaluation Request

Future Part 07 orchestration endpoints should accept `BaselineEvaluationRequest`.

```json
{
  "strategy_name": "SmokeTestStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "days": 30,
  "timerange": null,
  "risk_profile": "balanced",
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "max_open_trades": 3,
  "trading_mode": "spot",
  "download_missing_data": false,
  "user_confirmed": false,
  "apply_decision_to_run": true,
  "force_parse": true,
  "notes": null
}
```

Validation rules:

- `strategy_name` is required and must not be blank.
- `pairs` must contain at least one non-blank pair.
- `timeframe` is required and must not be blank.
- `days` must be positive when provided.
- `risk_profile` must be `conservative`, `balanced`, or `aggressive`.
- `trading_mode` currently supports only `spot`.
- `download_missing_data=true` with `user_confirmed=false` is schema-valid, but the service must stop before any download.

### Baseline Stage Result

Each stage summary uses `BaselineStageResult`.

```json
{
  "stage_name": "run_setup",
  "status": "completed",
  "started_at": "2026-06-29T20:00:00Z",
  "completed_at": "2026-06-29T20:00:01Z",
  "duration_seconds": 1.0,
  "message": "Run created",
  "warnings": [],
  "errors": [],
  "artifact_paths": ["artifacts/runs/run-123/setup.json"],
  "details": {}
}
```

Artifact paths must be project-relative. Baseline API responses must not include secrets, full raw stdout/stderr content, or arbitrary absolute local paths.

### Baseline Evaluation Result

`BaselineEvaluationResult` is the frontend-ready final or partial report envelope.

```json
{
  "success": true,
  "run_id": "run-123",
  "status": "completed",
  "classification": "rejected",
  "confidence_score": 40.0,
  "strategy_name": "SmokeTestStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "risk_profile": "balanced",
  "metrics": {},
  "decision": {},
  "quality_flags": [],
  "stage_results": [],
  "artifact_paths": [],
  "warnings": [],
  "errors": [],
  "next_actions": []
}
```

### Baseline Status Response

`BaselineStatusResponse` is the polling/status envelope for an existing baseline evaluation run.

```json
{
  "run_id": "run-123",
  "status": "running",
  "classification": null,
  "current_stage": "data_check",
  "stage_results": [],
  "metrics": {},
  "decision": {},
  "warnings": [],
  "errors": []
}
```

Part 07 schemas define contracts only. They do not run Freqtrade, download data, parse outputs, evaluate decisions, call Ollama, send Discord messages, approve strategies, or export strategies.

## Part 08 Optimization Contract

Part 08 defines the schema and API contract for optimization of an existing strategy. This section documents the request and response payloads before orchestration endpoints are implemented.

Optimization pipeline stages:

1. `optimization_setup`
2. `baseline_reference`
3. `hyperopt_policy_validation`
4. `hyperopt_config_generation`
5. `data_check`
6. `data_download`
7. `hyperopt_execution`
8. `hyperopt_result_parsing`
9. `trial_persistence`
10. `best_trial_selection`
11. `optimized_config_generation`
12. `optimized_backtest`
13. `optimized_result_parsing`
14. `optimized_decision_evaluation`
15. `baseline_vs_optimized_comparison`
16. `optimization_report`
17. `completion`

Optimization pipeline statuses:

- `pending`
- `running`
- `completed`
- `failed_controlled`
- `confirmation_required`

Optimization result statuses:

- `not_improved`
- `improved`
- `optimization_candidate`
- `optimization_promising`
- `optimization_rejected`
- `overfit_suspected`
- `invalid_optimization`

Optimization trial statuses:

- `completed`
- `failed`
- `ignored`
- `best`
- `selected_for_validation`
- `rejected`

### Optimization Request

Future Part 08 orchestration endpoints should accept `OptimizationRequest`.

```json
{
  "strategy_name": "HERSmokeStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "days": 30,
  "timerange": null,
  "risk_profile": "balanced",
  "baseline_run_id": null,
  "run_baseline_first": true,
  "download_missing_data": false,
  "user_confirmed": false,
  "epochs": 50,
  "spaces": ["buy", "sell"],
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "apply_decision_to_run": true,
  "notes": null
}
```

Validation rules:

- `strategy_name` is required and must not be blank.
- `pairs` must contain at least one non-blank pair.
- `timeframe` is required and must not be blank.
- `epochs` must be greater than 0 and cannot exceed 200.
- `spaces` must only contain allowed values: buy, sell, roi, stoploss, trailing, protection.
- `risk_profile` must be `conservative`, `balanced`, or `aggressive`.
- `user_confirmed` can be false, but the service must stop before Hyperopt execution and optimized backtest execution.
- `download_missing_data=true` with `user_confirmed=false` is schema-valid, but the service must stop before data download.

### Hyperopt Policy

`HyperoptPolicy` defines safety constraints for hyperopt execution.

```json
{
  "max_epochs": 200,
  "default_epochs": 50,
  "allowed_spaces": ["buy", "sell"],
  "locked_spaces": ["roi", "stoploss", "trailing", "protection"],
  "max_optimized_parameters": 6,
  "allow_roi_optimization": false,
  "allow_stoploss_optimization": false,
  "allow_trailing_optimization": false,
  "timeout_seconds": 3600,
  "min_trades": 10,
  "stop_on_zero_trades": true,
  "notes": null
}
```

Default policy enforces safe defaults:
- Default epochs: 50
- Max epochs: 200
- Allowed spaces: buy, sell only
- Locked spaces: roi, stoploss, trailing, protection
- ROI, stoploss, and trailing optimization disabled by default
- Timeout: 3600 seconds (1 hour)
- Stop on zero trades: true

### Optimization Stage Result

Each stage summary uses `OptimizationStageResult`.

```json
{
  "stage_name": "optimization_setup",
  "status": "completed",
  "started_at": "2026-06-30T20:00:00Z",
  "completed_at": "2026-06-30T20:00:01Z",
  "duration_seconds": 1.0,
  "message": "Optimization run created",
  "error_code": null,
  "warnings": [],
  "errors": [],
  "artifact_paths": ["artifacts/runs/run-123/setup.json"],
  "details": {}
}
```

### Optimization Trial

`OptimizationTrial` represents a single hyperopt trial.

```json
{
  "id": "trial-123",
  "optimization_run_id": "opt-run-123",
  "trial_number": 1,
  "status": "completed",
  "is_best": false,
  "is_selected_for_validation": false,
  "params": {"buy": {"rsi": 30}, "sell": {"rsi": 70}},
  "buy_params": {"rsi": 30},
  "sell_params": {"rsi": 70},
  "roi_params": null,
  "stoploss_params": null,
  "trailing_params": null,
  "metrics": {"profit_total": 100.0, "profit_factor": 1.5},
  "loss_score": 0.5,
  "profit_total": 100.0,
  "profit_factor": 1.5,
  "expectancy": 0.6,
  "max_drawdown": 10.0,
  "trade_count": 50,
  "win_rate": 0.6,
  "rejection_reason": null,
  "failure_reason": null,
  "artifact_paths": [],
  "raw_trial": {},
  "created_at": "2026-06-30T20:00:05Z"
}
```

**Important:** Every trial is persisted, not just the best trial. This enables full analysis of the optimization search space.

### Optimization Run

`OptimizationRun` represents the complete optimization run.

```json
{
  "id": "opt-run-123",
  "parent_run_id": null,
  "baseline_run_id": "run-123",
  "optimized_run_id": "run-124",
  "strategy_name": "HERSmokeStrategy",
  "timeframe": "5m",
  "pairs": ["BTC/USDT"],
  "exchange": "binance",
  "risk_profile": "balanced",
  "status": "completed",
  "result_status": "improved",
  "best_trial_id": "trial-45",
  "epochs_requested": 50,
  "epochs_completed": 50,
  "spaces": ["buy", "sell"],
  "policy": {"max_epochs": 200, "default_epochs": 50},
  "request": {"user_confirmed": true},
  "comparison": {"profit_improvement": 15.5},
  "report_artifact_path": "artifacts/runs/opt-run-123/report.md",
  "created_at": "2026-06-30T20:00:00Z",
  "updated_at": "2026-06-30T20:30:00Z"
}
```

### Optimization Comparison

`OptimizationComparison` compares baseline vs optimized results.

```json
{
  "baseline_run_id": "run-123",
  "optimized_run_id": "run-124",
  "baseline_metrics": {"profit_total": 100.0, "profit_factor": 1.5},
  "optimized_metrics": {"profit_total": 115.5, "profit_factor": 1.6},
  "improvement": {"profit_total": 15.5, "profit_factor": 0.1},
  "improvement_percentage": {"profit_total": 15.5, "profit_factor": 6.7},
  "baseline_classification": "rejected",
  "optimized_classification": "candidate",
  "is_improvement": true,
  "notes": "Optimization improved profit by 15.5%"
}
```

### Optimization Result

`OptimizationResult` is the frontend-ready final or partial report envelope.

```json
{
  "success": true,
  "run_id": "opt-run-123",
  "status": "completed",
  "result_status": "improved",
  "strategy_name": "HERSmokeStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "risk_profile": "balanced",
  "baseline_run_id": "run-123",
  "optimized_run_id": "run-124",
  "best_trial_id": "trial-45",
  "epochs_completed": 50,
  "comparison": {},
  "report_artifact_path": "artifacts/runs/opt-run-123/report.md",
  "stage_results": [],
  "trials": [],
  "warnings": [],
  "errors": [],
  "next_actions": []
}
```

### Optimization Status Response

`OptimizationStatusResponse` is the polling/status envelope for an existing optimization run.

```json
{
  "run_id": "opt-run-123",
  "status": "running",
  "result_status": null,
  "current_stage": "hyperopt_execution",
  "epochs_completed": 25,
  "epochs_requested": 50,
  "stage_results": [],
  "trials": [],
  "warnings": [],
  "errors": []
}
```

Part 08 schemas define contracts only. They do not run Hyperopt, run Freqtrade, download data, parse outputs, evaluate decisions, call Ollama, send Discord messages, approve strategies, or export strategies.

### Optimization API Endpoints

#### Start Optimization

**POST** `/api/optimization/run`

Start optimization pipeline for an existing strategy.

**Request Body:** `OptimizationRequest`

```json
{
  "strategy_name": "HERSmokeStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "days": 30,
  "risk_profile": "balanced",
  "baseline_run_id": null,
  "run_baseline_first": true,
  "download_missing_data": false,
  "user_confirmed": true,
  "epochs": 50,
  "spaces": ["buy", "sell"],
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "apply_decision_to_run": true,
  "notes": null
}
```

**Response:** `202 Accepted`

```json
{
  "run_id": "opt-run-123",
  "status": "completed",
  "message": "Optimization pipeline completed with status: completed"
}
```

**Behavior:**
- Requires `user_confirmed=true` before Hyperopt execution
- Requires both `download_missing_data=true` and `user_confirmed=true` before data download
- Requires `user_confirmed=true` before optimized backtest execution
- Does not call Ollama
- Does not send Discord messages
- Does not approve/export strategies
- This endpoint may take time because it can run Hyperopt and backtests
- Synchronous local execution is used (no background workers in Part 08)

**Error Response:** `400 Bad Request`

```json
{
  "detail": "user_confirmed=true is required before Hyperopt/backtest execution"
}
```

**Error Response:** `500 Internal Server Error`

```json
{
  "detail": "Optimization pipeline failed: [truncated error message]"
}
```

---

#### List Optimization Runs

**GET** `/api/optimization/runs`

List optimization runs with optional filtering and pagination.

**Query Parameters:**
- `limit` - Maximum number of runs to return (default: 100)
- `offset` - Number of runs to skip (default: 0)
- `status` - Filter by status (optional)

**Response:** `200 OK`

```json
[
  {
    "id": "opt-run-123",
    "strategy_name": "HERSmokeStrategy",
    "timeframe": "5m",
    "pairs": ["BTC/USDT"],
    "exchange": "binance",
    "status": "completed",
    "result_status": "improved",
    "epochs_requested": 50,
    "epochs_completed": 50,
    "best_trial_id": "trial-45",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:30:00Z"
  }
]
```

---

#### Get Optimization Run

**GET** `/api/optimization/runs/{optimization_run_id}`

Return full optimization run detail including run metadata, stages, trials, comparison, and artifacts.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Response:** `200 OK`

```json
{
  "run": {
    "id": "opt-run-123",
    "parent_run_id": null,
    "baseline_run_id": "run-123",
    "optimized_run_id": "run-124",
    "strategy_name": "HERSmokeStrategy",
    "timeframe": "5m",
    "pairs": ["BTC/USDT"],
    "exchange": "binance",
    "risk_profile": "balanced",
    "status": "completed",
    "result_status": "improved",
    "best_trial_id": "trial-45",
    "epochs_requested": 50,
    "epochs_completed": 50,
    "spaces": ["buy", "sell"],
    "policy": { ... },
    "request": { ... },
    "comparison": { ... },
    "report_artifact_path": "artifacts/runs/opt-run-123/report.md",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-01T00:30:00Z"
  },
  "stages": [],
  "best_trial": { ... },
  "comparison": { ... },
  "artifact_paths": [],
  "warnings": [],
  "errors": []
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

---

#### Get Optimization Status

**GET** `/api/optimization/runs/{optimization_run_id}/status`

Return lightweight status for polling optimization progress.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Response:** `200 OK`

```json
{
  "run_id": "opt-run-123",
  "status": "running",
  "current_stage": null,
  "stage_progress": null,
  "epochs_completed": 25,
  "epochs_total": 50,
  "trials_completed": 25,
  "trials_total": null,
  "message": null,
  "error_code": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:15:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

---

#### Get Optimization Report

**GET** `/api/optimization/runs/{optimization_run_id}/report`

Return optimization report artifact metadata if it exists.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Response:** `200 OK`

```json
{
  "optimization_run_id": "opt-run-123",
  "report_artifact_path": "artifacts/runs/opt-run-123/optimization/optimization_report.json",
  "status": "available"
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization report not available for run {optimization_run_id}"
}
```

---

#### Get Optimization Trials

**GET** `/api/optimization/runs/{optimization_run_id}/trials`

Return all trials for an optimization run (not just best trial).

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Query Parameters:**
- `limit` - Maximum number of trials to return (default: 100)
- `offset` - Number of trials to skip (default: 0)
- `status` - Filter by trial status (optional)

**Response:** `200 OK`

```json
[
  {
    "id": "trial-123",
    "optimization_run_id": "opt-run-123",
    "trial_number": 1,
    "status": "completed",
    "is_best": false,
    "is_selected_for_validation": false,
    "params": {"buy": {"rsi": 30}, "sell": {"rsi": 70}},
    "buy_params": {"rsi": 30},
    "sell_params": {"rsi": 70},
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": {"profit_total": 100.0, "profit_factor": 1.5},
    "loss_score": 0.5,
    "profit_total": 100.0,
    "profit_factor": 1.5,
    "expectancy": 0.6,
    "max_drawdown": 10.0,
    "trade_count": 50,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": {},
    "created_at": "2024-01-01T00:00:05Z"
  }
]
```

**Important:** This endpoint returns all trials, not just the best trial, enabling full analysis of the optimization search space.

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

---

#### Get Optimization Trial Detail

**GET** `/api/optimization/runs/{optimization_run_id}/trials/{trial_id}`

Return full trial details including complete parameters and metrics.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID
- `trial_id` - Trial UUID

**Response:** `200 OK`

```json
{
  "trial": {
    "id": "trial-123",
    "optimization_run_id": "opt-run-123",
    "trial_number": 1,
    "status": "completed",
    "is_best": false,
    "is_selected_for_validation": false,
    "params": {"buy": {"rsi": 30}, "sell": {"rsi": 70}},
    "buy_params": {"rsi": 30},
    "sell_params": {"rsi": 70},
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": {"profit_total": 100.0, "profit_factor": 1.5},
    "loss_score": 0.5,
    "profit_total": 100.0,
    "profit_factor": 1.5,
    "expectancy": 0.6,
    "max_drawdown": 10.0,
    "trade_count": 50,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": {},
    "created_at": "2024-01-01T00:00:05Z"
  },
  "artifact_paths": []
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

```json
{
  "detail": "Trial {trial_id} not found"
}
```

---

#### Get Best Trial

**GET** `/api/optimization/runs/{optimization_run_id}/best-trial`

Return the best trial for an optimization run.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Response:** `200 OK`

```json
{
  "id": "trial-45",
  "optimization_run_id": "opt-run-123",
  "trial_number": 45,
  "status": "best",
  "is_best": true,
  "is_selected_for_validation": true,
  "params": {"buy": {"rsi": 35}, "sell": {"rsi": 65}},
  "buy_params": {"rsi": 35},
  "sell_params": {"rsi": 65},
  "roi_params": null,
  "stoploss_params": null,
  "trailing_params": null,
  "metrics": {"profit_total": 115.5, "profit_factor": 1.6},
  "loss_score": 0.3,
  "profit_total": 115.5,
  "profit_factor": 1.6,
  "expectancy": 0.65,
  "max_drawdown": 8.0,
  "trade_count": 52,
  "win_rate": 0.65,
  "rejection_reason": null,
  "failure_reason": null,
  "artifact_paths": [],
  "raw_trial": {},
  "created_at": "2024-01-01T00:20:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

```json
{
  "detail": "No best trial found for optimization run {optimization_run_id}"
}
```

---

#### Get Optimization Comparison

**GET** `/api/optimization/runs/{optimization_run_id}/comparison`

Return baseline vs optimized comparison for an optimization run.

**Path Parameters:**
- `optimization_run_id` - Optimization run UUID

**Response:** `200 OK`

```json
{
  "optimization_run_id": "opt-run-123",
  "baseline_run_id": "run-123",
  "optimized_run_id": "run-124",
  "best_trial_id": "trial-45",
  "baseline_metrics": {"profit_total": 100.0, "profit_factor": 1.5},
  "optimized_metrics": {"profit_total": 115.5, "profit_factor": 1.6},
  "delta_profit_factor": 0.1,
  "delta_expectancy": 0.05,
  "delta_drawdown": -2.0,
  "delta_trade_count": 2,
  "baseline_classification": "promising",
  "optimized_classification": "validated",
  "result_status": "improved",
  "improvement_summary": "Optimized strategy shows improvement in profit factor and expectancy",
  "warnings": [],
  "overfit_suspected": false,
  "created_at": "2024-01-01T00:30:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Optimization run {optimization_run_id} not found"
}
```

```json
{
  "detail": "Comparison not available for optimization run {optimization_run_id}"
}
```

### Baseline Evaluation API Endpoints

#### Evaluate Baseline

**POST** `/api/baseline/evaluate`

Evaluate an existing strategy baseline through the complete baseline evaluation pipeline.

**Request Body:** `BaselineEvaluationRequest`

```json
{
  "strategy_name": "HERSmokeStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "days": 30,
  "risk_profile": "balanced",
  "download_missing_data": true,
  "user_confirmed": true,
  "apply_decision_to_run": true
}
```

**Response:** `200 OK`

Returns `BaselineEvaluationResult` with the evaluation results.

**Behavior:**
- Calls `BaselineEvaluationService.evaluate`
- Requires `user_confirmed=true` before real Freqtrade backtest
- Requires both `download_missing_data=true` and `user_confirmed=true` before data download
- Does not call Ollama
- Does not send Discord messages
- Does not approve/export strategies
- This endpoint may take time because it can run a real Freqtrade backtest
- Synchronous local execution is used (no background workers in Part 07)

**Error Response:** `500 Internal Server Error`

```json
{
  "detail": "Baseline evaluation failed. Check run logs for details."
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/baseline/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "strategy_name": "HERSmokeStrategy",
    "pairs": ["BTC/USDT"],
    "timeframe": "5m",
    "exchange": "binance",
    "days": 30,
    "risk_profile": "balanced",
    "download_missing_data": true,
    "user_confirmed": true
  }'
```

---

#### Get Baseline Run

**GET** `/api/baseline/runs/{run_id}`

Return full baseline run summary including run metadata, stages, latest metrics, latest decision, artifacts, and warnings/errors.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
{
  "run_id": "run-123",
  "status": "completed",
  "classification": "candidate",
  "confidence_score": 0.75,
  "mode": "real",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:10:00Z",
  "stages": [
    {
      "stage_name": "run_setup",
      "status": "passed",
      "started_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:00:01Z",
      "duration_ms": 1000,
      "message": "Run created",
      "error_data": null
    }
  ],
  "metrics": {"profit": 100},
  "decision": {"classification": "candidate", "confidence_score": 0.75},
  "artifacts": ["artifacts/runs/run-123/report.md"],
  "warnings": [],
  "errors": []
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Run {run_id} not found"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/baseline/runs/{run_id}
```

---

#### Get Baseline Status

**GET** `/api/baseline/runs/{run_id}/status`

Return lightweight status for a baseline evaluation run including run_id, status, classification, current_stage, stage_results, and warnings/errors.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

Returns `BaselineStatusResponse`.

```json
{
  "run_id": "run-123",
  "status": "running",
  "classification": null,
  "current_stage": "data_check",
  "stage_results": [
    {
      "stage_name": "run_setup",
      "status": "completed",
      "started_at": "2024-01-01T00:00:00Z",
      "completed_at": "2024-01-01T00:00:01Z",
      "duration_seconds": 1.0,
      "message": "Run created",
      "error_code": null,
      "warnings": [],
      "errors": [],
      "artifact_paths": [],
      "details": {}
    }
  ],
  "metrics": {},
  "decision": {},
  "warnings": [],
  "errors": []
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Run {run_id} not found"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/baseline/runs/{run_id}/status
```

---

#### Get Baseline Report

**GET** `/api/baseline/runs/{run_id}/report`

Return baseline report artifact metadata if it exists.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
{
  "run_id": "run-123",
  "artifact_id": "artifact-uuid",
  "artifact_type": "report_md",
  "description": "Baseline evaluation report",
  "file_path": "artifacts/runs/run-123/baseline_report.md",
  "sha256": "abc123...",
  "size_bytes": 1024,
  "created_at": "2024-01-01T00:10:00Z"
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Baseline report not found for run {run_id}"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/baseline/runs/{run_id}/report
```

### Error Behavior

All baseline API endpoints return clean errors without stack traces or secrets:

- **Run not found** - 404 with clean message
- **Report not found** - 404 with clean message
- **Invalid request** - 422 validation error
- **Confirmation required** - 200 with status `confirmation_required` and next_actions
- **Controlled pipeline failure** - 200 with status `failed_controlled` and error details

No stack traces, secrets, or raw stdout/stderr bodies are exposed by default.

## Part 08 Optimization Pipeline Contract

Part 08 defines the schema and API contract for optimization pipeline execution. This section documents the request and response payloads for optimization endpoints.

Optimization pipeline stages:

1. `optimization_setup`
2. `baseline_reference`
3. `hyperopt_policy_validation`
4. `hyperopt_config_generation`
5. `data_check`
6. `data_download`
7. `hyperopt_execution`
8. `hyperopt_result_parsing`
9. `trial_persistence`
10. `best_trial_selection`
11. `optimized_config_generation`
12. `optimized_backtest`
13. `optimized_result_parsing`
14. `optimized_decision_evaluation`
15. `baseline_vs_optimized_comparison`
16. `optimization_report`
17. `completion`

Optimization pipeline statuses:

- `pending`
- `running`
- `completed`
- `failed_controlled`
- `confirmation_required`

Optimization result statuses:

- `not_improved`
- `improved`
- `optimization_candidate`
- `optimization_promising`
- `optimization_rejected`
- `overfit_suspected`
- `invalid_optimization`

Optimization trial statuses:

- `completed`
- `failed`
- `ignored`
- `best`
- `selected_for_validation`
- `rejected`

### Optimization Request

Optimization endpoints accept `OptimizationRequest`.

```json
{
  "strategy_name": "TestStrategy",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "days": 30,
  "timerange": null,
  "risk_profile": "balanced",
  "baseline_run_id": null,
  "run_baseline_first": true,
  "download_missing_data": false,
  "user_confirmed": false,
  "epochs": 50,
  "spaces": ["buy", "sell"],
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "apply_decision_to_run": true,
  "notes": null
}
```

**Validation Rules:**
- `strategy_name` required, non-empty
- `pairs` required, non-empty list
- `timeframe` required, non-empty
- `epochs` must be > 0 and <= 200
- `spaces` must be from allowed values: buy, sell, roi, stoploss, trailing, protection
- `risk_profile` must be: conservative, balanced, or aggressive
- `user_confirmed` can be false, but service stops before hyperopt/backtest execution

### Hyperopt Policy

Default hyperopt policy configuration:

```json
{
  "max_epochs": 200,
  "default_epochs": 50,
  "allowed_spaces": ["buy", "sell"],
  "locked_spaces": ["roi", "stoploss", "trailing", "protection"],
  "max_optimized_parameters": 6,
  "allow_roi_optimization": false,
  "allow_stoploss_optimization": false,
  "allow_trailing_optimization": false,
  "timeout_seconds": 3600,
  "min_trades": 10,
  "stop_on_zero_trades": true,
  "notes": null
}
```

### Optimization Endpoints

#### List Optimization Runs

**GET** `/api/optimization/runs`

List all optimization runs with optional filters.

**Query Parameters:**
- `strategy_name` (optional) - Filter by strategy name
- `status` (optional) - Filter by status
- `result_status` (optional) - Filter by result status
- `limit` (optional, default: 50, max: 200) - Maximum number of results

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "strategy_name": "TestStrategy",
    "timeframe": "5m",
    "pairs": ["BTC/USDT"],
    "exchange": "binance",
    "status": "completed",
    "result_status": "improved",
    "epochs_requested": 50,
    "epochs_completed": 50,
    "best_trial_id": "trial-uuid",
    "created_at": "2026-06-30T00:00:00Z",
    "updated_at": "2026-06-30T01:00:00Z"
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/optimization/runs
curl http://127.0.0.1:8000/api/optimization/runs?status=completed
curl http://127.0.0.1:8000/api/optimization/runs?result_status=improved
```

---

#### Get Optimization Run

**GET** `/api/optimization/runs/{run_id}`

Get detailed information about an optimization run.

**Response:** `200 OK`

```json
{
  "id": "uuid",
  "parent_run_id": null,
  "baseline_run_id": "baseline-uuid",
  "optimized_run_id": "optimized-uuid",
  "strategy_name": "TestStrategy",
  "timeframe": "5m",
  "pairs": ["BTC/USDT"],
  "exchange": "binance",
  "risk_profile": "balanced",
  "status": "completed",
  "result_status": "improved",
  "best_trial_id": "trial-uuid",
  "epochs_requested": 50,
  "epochs_completed": 50,
  "spaces": ["buy", "sell"],
  "policy": { ... },
  "request": { ... },
  "comparison": { ... },
  "report_artifact_path": "artifacts/runs/uuid/optimization/optimization_report.json",
  "created_at": "2026-06-30T00:00:00Z",
  "updated_at": "2026-06-30T01:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Run not found

---

#### Start Optimization

**POST** `/api/optimization/evaluate`

Start a new optimization pipeline.

**Request Body:** `OptimizationRequest`

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "status": "pending",
  "result_status": null,
  "stages": [],
  "best_trial": null,
  "comparison": null,
  "artifact_paths": [],
  "warnings": [],
  "errors": [],
  "message": "Optimization pipeline started",
  "error_code": null,
  "created_at": "2026-06-30T00:00:00Z",
  "completed_at": null
}
```

**Confirmation Required Response:**
If `user_confirmed=false` and confirmation is needed:

```json
{
  "run_id": "uuid",
  "status": "confirmation_required",
  "message": "Hyperopt execution requires user confirmation. Set user_confirmed=true to proceed.",
  "error_code": "confirmation_required_for_hyperopt",
  "next_actions": ["Set user_confirmed=true in request", "Review hyperopt parameters", "Confirm and retry"]
}
```

---

#### Get Optimization Status

**GET** `/api/optimization/runs/{run_id}/status`

Get current status of an optimization run.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "status": "running",
  "current_stage": "hyperopt_execution",
  "stage_progress": {
    "optimization_setup": "completed",
    "baseline_reference": "completed",
    "hyperopt_policy_validation": "completed",
    "hyperopt_config_generation": "completed",
    "data_check": "completed",
    "hyperopt_execution": "running"
  },
  "epochs_completed": 25,
  "epochs_total": 50,
  "trials_completed": 25,
  "trials_total": 50,
  "message": "Hyperopt execution in progress",
  "error_code": null,
  "created_at": "2026-06-30T00:00:00Z",
  "updated_at": "2026-06-30T00:30:00Z"
}
```

---

#### List Trials

**GET** `/api/optimization/runs/{run_id}/trials`

List all trials for an optimization run.

**Query Parameters:**
- `status` (optional) - Filter by trial status
- `is_best` (optional) - Filter by best trial flag (true/false)
- `limit` (optional, default: 100, max: 500) - Maximum number of results

**Response:** `200 OK`

```json
[
  {
    "id": "trial-uuid-1",
    "optimization_run_id": "run-uuid",
    "trial_number": 1,
    "status": "completed",
    "is_best": false,
    "is_selected_for_validation": false,
    "params": { "buy": { "rsi": 30 }, "sell": { "rsi": 70 } },
    "buy_params": { "rsi": 30 },
    "sell_params": { "rsi": 70 },
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": { "profit_total": 100.0, "profit_factor": 1.5 },
    "loss_score": 0.5,
    "profit_total": 100.0,
    "profit_factor": 1.5,
    "expectancy": 0.02,
    "max_drawdown": -0.15,
    "trade_count": 50,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": null,
    "created_at": "2026-06-30T00:10:00Z"
  },
  {
    "id": "trial-uuid-2",
    "optimization_run_id": "run-uuid",
    "trial_number": 2,
    "status": "best",
    "is_best": true,
    "is_selected_for_validation": true,
    "params": { "buy": { "rsi": 35 }, "sell": { "rsi": 65 } },
    "buy_params": { "rsi": 35 },
    "sell_params": { "rsi": 65 },
    "metrics": { "profit_total": 150.0, "profit_factor": 1.8 },
    "loss_score": 0.3,
    "profit_total": 150.0,
    "profit_factor": 1.8,
    "trade_count": 60,
    "win_rate": 0.65,
    "created_at": "2026-06-30T00:15:00Z"
  }
]
```

**Important:** Every trial is persisted, not just the best trial. This enables frontend inspection of the complete optimization history.

---

#### Get Best Trial

**GET** `/api/optimization/runs/{run_id}/trials/best`

Get the best trial for an optimization run.

**Response:** `200 OK`

```json
{
  "id": "trial-uuid",
  "optimization_run_id": "run-uuid",
  "trial_number": 25,
  "status": "best",
  "is_best": true,
  "is_selected_for_validation": true,
  "params": { "buy": { "rsi": 35 }, "sell": { "rsi": 65 } },
  "buy_params": { "rsi": 35 },
  "sell_params": { "rsi": 65 },
  "metrics": { "profit_total": 200.0, "profit_factor": 2.0 },
  "loss_score": 0.2,
  "profit_total": 200.0,
  "profit_factor": 2.0,
  "trade_count": 75,
  "win_rate": 0.7,
  "created_at": "2026-06-30T00:25:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Run not found or no best trial exists

---

#### Get Comparison

**GET** `/api/optimization/runs/{run_id}/comparison`

Get baseline vs optimized comparison.

**Response:** `200 OK`

```json
{
  "optimization_run_id": "run-uuid",
  "baseline_run_id": "baseline-uuid",
  "optimized_run_id": "optimized-uuid",
  "baseline_metrics": {
    "profit_total": 100.0,
    "profit_factor": 1.5,
    "max_drawdown": -0.15,
    "trade_count": 50,
    "win_rate": 0.6
  },
  "optimized_metrics": {
    "profit_total": 200.0,
    "profit_factor": 2.0,
    "max_drawdown": -0.12,
    "trade_count": 75,
    "win_rate": 0.7
  },
  "metric_deltas": {
    "profit_total": 100.0,
    "profit_factor": 0.5,
    "max_drawdown": 0.03,
    "trade_count": 25,
    "win_rate": 0.1
  },
  "baseline_classification": "rejected",
  "optimized_classification": "candidate",
  "baseline_confidence": 0.3,
  "optimized_confidence": 0.6,
  "classification_improved": true,
  "recommendation": "improved",
  "trial_summary": {
    "total_trials": 50,
    "best_trial_number": 25,
    "improvement_rate": 0.5
  },
  "created_at": "2026-06-30T01:00:00Z"
}
```

---

#### Get Optimization Report

**GET** `/api/optimization/runs/{run_id}/report`

Get the optimization report artifact.

**Response:** `200 OK`

```json
{
  "run_id": "run-uuid",
  "strategy_name": "TestStrategy",
  "timeframe": "5m",
  "pairs": ["BTC/USDT"],
  "request_summary": { ... },
  "stage_summary": [ ... ],
  "trial_summary": {
    "total_trials": 50,
    "completed_trials": 48,
    "failed_trials": 2,
    "best_trial_number": 25
  },
  "best_trial": { ... },
  "comparison": { ... },
  "artifact_paths": [ ... ],
  "warnings": [ ... ],
  "errors": [ ... ],
  "created_at": "2026-06-30T01:00:00Z"
}
```

**Error Responses:**
- `404 Not Found` - Run not found or report not generated

---

#### Get Optimization Artifacts

**GET** `/api/optimization/runs/{run_id}/artifacts`

List all artifacts for an optimization run.

**Response:** `200 OK`

```json
[
  {
    "id": "artifact-uuid",
    "artifact_type": "hyperopt_raw",
    "path": "artifacts/runs/run-uuid/hyperopt/hyperopt_results.json",
    "description": "Hyperopt results",
    "created_at": "2026-06-30T00:20:00Z"
  },
  {
    "id": "artifact-uuid-2",
    "artifact_type": "report_md",
    "path": "artifacts/runs/run-uuid/optimization/optimization_report.json",
    "description": "Optimization report",
    "created_at": "2026-06-30T01:00:00Z"
  }
]
```

---

#### Get Optimization Stages

**GET** `/api/optimization/runs/{run_id}/stages`

Get stage progress for an optimization run.

**Response:** `200 OK`

```json
[
  {
    "stage_name": "optimization_setup",
    "status": "completed",
    "started_at": "2026-06-30T00:00:00Z",
    "completed_at": "2026-06-30T00:00:05Z",
    "duration_seconds": 0.05,
    "message": "Optimization setup completed",
    "error_code": null,
    "warnings": [],
    "errors": [],
    "artifact_paths": [],
    "details": {}
  },
  {
    "stage_name": "hyperopt_execution",
    "status": "running",
    "started_at": "2026-06-30T00:05:00Z",
    "completed_at": null,
    "duration_seconds": null,
    "message": "Hyperopt execution in progress",
    "error_code": null,
    "warnings": [],
    "errors": [],
    "artifact_paths": [],
    "details": {
      "epochs_completed": 25,
      "epochs_total": 50
    }
  }
]
```

### Optimization Error Handling

All optimization API endpoints return clean errors without stack traces or secrets:

- **Run not found** - 404 with clean message
- **Trial not found** - 404 with clean message
- **Report not found** - 404 with clean message
- **Invalid request** - 422 validation error
- **Confirmation required** - 200 with status `confirmation_required` and next_actions
- **Controlled pipeline failure** - 200 with status `failed_controlled` and error details

No stack traces, secrets, or raw stdout/stderr bodies are exposed by default.

## Runs API

### Run Modes

Allowed run modes:
- `upload_strategy` - Upload and validate an existing strategy
- `generate_strategy` - Generate a new strategy with AI
- `repair_strategy` - Repair a broken strategy
- `optimize_strategy` - Optimize strategy parameters
- `manual_test` - Manual testing mode

### Run Statuses

Allowed run statuses:
- `created` - Run created, not started
- `queued` - Run queued for execution
- `running` - Run is currently executing
- `waiting_for_confirmation` - Awaiting user confirmation
- `failed_controlled` - Failed with controlled error (retryable)
- `failed_system` - Failed with system error (not retryable)
- `rejected` - Run rejected by decision engine
- `candidate` - Passed initial validation
- `promising` - Shows promising results
- `validated` - Fully validated
- `approved` - Approved for export
- `exported` - Successfully exported
- `cancelled` - Cancelled by user

### Classifications

Allowed classification values:
- `rejected` - Strategy rejected
- `candidate` - Strategy is a candidate
- `promising` - Strategy shows promise
- `validated` - Strategy validated
- `approved` - Strategy approved

### Endpoints

#### List Runs

**GET** `/api/runs`

List all runs with optional filters.

**Query Parameters:**
- `status` (optional) - Filter by status
- `classification` (optional) - Filter by classification
- `strategy_id` (optional) - Filter by strategy ID
- `limit` (optional, default: 50, max: 500) - Maximum number of results
- `offset` (optional, default: 0) - Offset for pagination

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "name": "Test Run",
    "mode": "generate_strategy",
    "status": "created",
    "classification": null,
    "strategy_id": null,
    "parent_run_id": null,
    "is_demo": false,
    "created_at": "2026-06-28T05:00:00Z",
    "updated_at": "2026-06-28T05:00:00Z",
    "started_at": null,
    "completed_at": null
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/runs
curl http://127.0.0.1:8000/api/runs?status=running
curl http://127.0.0.1:8000/api/runs?limit=10&offset=20
```

---

#### Create Run

**POST** `/api/runs`

Create a new run.

**Request Body:**
```json
{
  "name": "Test Run",
  "mode": "generate_strategy",
  "strategy_id": "uuid (optional)",
  "parent_run_id": "uuid (optional)",
  "exchange": "binance (optional)",
  "quote_currency": "USDT (optional)",
  "trading_mode": "spot (optional)",
  "timeframe": "1h (optional)",
  "pairs": ["BTC/USDT", "ETH/USDT"] (optional),
  "timerange": "20240101-20241231 (optional)",
  "risk_profile": "moderate (optional)",
  "analysis_depth": "standard (optional)",
  "is_demo": false (optional, default: false)
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "name": "Test Run",
  "mode": "generate_strategy",
  "status": "created",
  "classification": null,
  "strategy_id": null,
  "parent_run_id": null,
  "exchange": "binance",
  "quote_currency": "USDT",
  "trading_mode": "spot",
  "timeframe": "1h",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timerange": "20240101-20241231",
  "risk_profile": "moderate",
  "analysis_depth": "standard",
  "is_demo": false,
  "failure_reason": null,
  "created_at": "2026-06-28T05:00:00Z",
  "updated_at": "2026-06-28T05:00:00Z",
  "started_at": null,
  "completed_at": null
}
```

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid mode: 'invalid_mode'. Allowed values: upload_strategy, generate_strategy, repair_strategy, optimize_strategy, manual_test"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Run",
    "mode": "generate_strategy",
    "pairs": ["BTC/USDT"],
    "timeframe": "1h"
  }'
```

---

#### Get Run

**GET** `/api/runs/{run_id}`

Get detailed information about a specific run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
{
  "id": "uuid",
  "name": "Test Run",
  "mode": "generate_strategy",
  "status": "running",
  "classification": null,
  "strategy_id": null,
  "parent_run_id": null,
  "exchange": "binance",
  "quote_currency": "USDT",
  "trading_mode": "spot",
  "timeframe": "1h",
  "pairs": ["BTC/USDT"],
  "timerange": "20240101-20241231",
  "risk_profile": "moderate",
  "analysis_depth": "standard",
  "is_demo": false,
  "failure_reason": null,
  "created_at": "2026-06-28T05:00:00Z",
  "updated_at": "2026-06-28T05:01:00Z",
  "started_at": "2026-06-28T05:01:00Z",
  "completed_at": null
}
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Run {run_id} not found"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/runs/{run_id}
```

---

#### Update Run

**PATCH** `/api/runs/{run_id}`

Update specific fields of a run.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "name": "Updated Name" (optional),
  "exchange": "binance" (optional),
  "quote_currency": "USDT" (optional),
  "trading_mode": "spot" (optional),
  "timeframe": "4h" (optional),
  "pairs": ["BTC/USDT", "ETH/USDT"] (optional),
  "timerange": "20240101-20241231" (optional),
  "risk_profile": "aggressive" (optional),
  "analysis_depth": "deep" (optional)
}
```

**Response:** `200 OK`

Returns the updated run object (same format as GET run).

**Error Response:** `404 Not Found`

```json
{
  "detail": "Run {run_id} not found"
}
```

**Example:**
```bash
curl -X PATCH http://127.0.0.1:8000/api/runs/{run_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "timeframe": "4h"
  }'
```

---

#### Update Run Status

**POST** `/api/runs/{run_id}/status`

Update the status of a run.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "status": "running",
  "failure_reason": "Error message" (optional, for failed statuses)
}
```

**Response:** `200 OK`

Returns the updated run object.

**Behavior:**
- When status becomes `running`, `started_at` is set automatically
- When status becomes a terminal status (`failed_controlled`, `failed_system`, `rejected`, `exported`, `cancelled`), `completed_at` is set automatically
- `updated_at` is always updated

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid status: 'invalid_status'. Allowed values: created, queued, running, ..."
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/status \
  -H "Content-Type: application/json" \
  -d '{
    "status": "running"
  }'
```

---

#### Update Run Classification

**POST** `/api/runs/{run_id}/classification`

Set the classification of a run.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "classification": "candidate"
}
```

**Response:** `200 OK`

Returns the updated run object.

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid classification: 'invalid_classification'. Allowed values: rejected, candidate, promising, validated, approved"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/classification \
  -H "Content-Type: application/json" \
  -d '{
    "classification": "promising"
  }'
```

---

#### Start Run

**POST** `/api/runs/{run_id}/start`

Mark a run as started.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:** None

**Response:** `200 OK`

Returns the updated run object with status `running` and `started_at` set.

**Note:** This does not execute the actual pipeline - it only updates the state.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/start
```

---

#### Complete Run

**POST** `/api/runs/{run_id}/complete`

Mark a run as completed.

**Path Parameters:**
- `run_id` - Run UUID

**Query Parameters:**
- `status` (optional) - Final status (defaults to `candidate`)
- `classification` (optional) - Classification to set

**Response:** `200 OK`

Returns the updated run object with `completed_at` set.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/complete?classification=promising
```

---

#### Fail Run

**POST** `/api/runs/{run_id}/fail`

Mark a run as failed.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "failure_type": "controlled",
  "reason": "Failure reason description"
}
```

**Response:** `200 OK`

Returns the updated run object with status `failed_controlled` or `failed_system` and `completed_at` set.

**Failure Types:**
- `controlled` - Controlled failure (retryable) → status becomes `failed_controlled`
- `system` - System failure (not retryable) → status becomes `failed_system`

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/fail \
  -H "Content-Type: application/json" \
  -d '{
    "failure_type": "controlled",
    "reason": "Backtest failed due to insufficient data"
  }'
```

## Run Stages API

### Stage Statuses

Allowed stage statuses:
- `pending` - Stage not started
- `running` - Stage currently executing
- `passed` - Stage completed successfully
- `failed` - Stage failed
- `skipped` - Stage skipped
- `waiting` - Stage waiting for input

### Default Run Stages

When a run is created, the following default stages are automatically created:

1. **run_setup** (order: 1) - Run Setup
2. **preflight_checks** (order: 2) - Preflight Checks
3. **strategy_normalization** (order: 3) - Strategy Normalization
4. **pair_timeframe_selection** (order: 4) - Pair and Timeframe Selection
5. **data_availability** (order: 5) - Data Availability Check
6. **baseline_backtest** (order: 6) - Baseline Backtest
7. **initial_decision** (order: 7) - Initial Decision
8. **hyperopt** (order: 8) - Hyperopt Optimization
9. **walk_forward_oos** (order: 9) - Walk-Forward Out-of-Sample
10. **robustness** (order: 10) - Robustness Analysis
11. **final_classification** (order: 11) - Final Classification
12. **export** (order: 12) - Export Strategy
13. **notification** (order: 13) - Notification

### Endpoints

#### List Stages

**GET** `/api/runs/{run_id}/stages`

List all stages for a run, ordered by execution order.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "stage_key": "run_setup",
    "stage_name": "Run Setup",
    "order_index": 1,
    "status": "proposed",
    "started_at": null,
    "completed_at": null,
    "duration_ms": null,
    "input": null,
    "output": null,
    "error": null,
    "logs_summary": null,
    "created_at": "2026-06-28T05:00:00Z",
    "updated_at": "2026-06-28T05:00:00Z"
  }
]
```

**Error Response:** `404 Not Found`

```json
{
  "detail": "Run {run_id} not found"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/runs/{run_id}/stages
```

---

#### Get Stage

**GET** `/api/runs/{run_id}/stages/{stage_key}`

Get a specific stage for a run.

**Path Parameters:**
- `run_id` - Run UUID
- `stage_key` - Stage key (e.g., "run_setup")

**Response:** `200 OK`

Returns the stage object (same format as list response).

**Error Response:** `404 Not Found`

```json
{
  "detail": "Stage {stage_key} not found for run {run_id}"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/runs/{run_id}/stages/run_setup
```

---

#### Start Stage

**POST** `/api/runs/{run_id}/stages/{stage_key}/start`

Start a stage.

**Path Parameters:**
- `run_id` - Run UUID
- `stage_key` - Stage key

**Request Body:**
```json
{
  "input_data": {"key": "value"} (optional)
}
```

**Response:** `200 OK`

Returns the updated stage object with status `running` and `started_at` set.

**Note:** This does not execute the actual stage logic - it only updates the state.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/stages/run_setup/start \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {"pairs": ["BTC/USDT"]}
  }'
```

---

#### Complete Stage

**POST** `/api/runs/{run_id}/stages/{stage_key}/complete`

Complete a stage.

**Path Parameters:**
- `run_id` - Run UUID
- `stage_key` - Stage key

**Request Body:**
```json
{
  "output_data": {"result": "success"} (optional),
  "logs_summary": "Completed successfully" (optional)
}
```

**Response:** `200 OK`

Returns the updated stage object with status `passed`, `completed_at` set, and `duration_ms` calculated.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/stages/run_setup/complete \
  -H "Content-Type: application/json" \
  -d '{
    "output_data": {"metrics": {"profit": 100}},
    "logs_summary": "Stage completed successfully"
  }'
```

---

#### Fail Stage

**POST** `/api/runs/{run_id}/stages/{stage_key}/fail`

Fail a stage.

**Path Parameters:**
- `run_id` - Run UUID
- `stage_key` - Stage key

**Request Body:**
```json
{
  "error_data": {"error": "test error"} (optional),
  "logs_summary": "Failed due to error" (optional)
}
```

**Response:** `200 OK`

Returns the updated stage object with status `failed`, `completed_at` set, and `duration_ms` calculated.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/stages/run_setup/fail \
  -H "Content-Type: application/json" \
  -d '{
    "error_data": {"exception": "ValueError", "message": "Invalid input"},
    "logs_summary": "Stage failed due to validation error"
  }'
```

---

#### Skip Stage

**POST** `/api/runs/{run_id}/stages/{stage_key}/skip`

Skip a stage.

**Path Parameters:**
- `run_id` - Run UUID
- `stage_key` - Stage key

**Query Parameters:**
- `reason` (optional) - Reason for skipping

**Response:** `200 OK`

Returns the updated stage object with status `skipped` and `completed_at` set.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/stages/run_setup/skip?reason="Not needed for this run"
```

---

#### Reset Stages

**POST** `/api/runs/{run_id}/stages/reset`

Reset all stages for a run to pending status.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
{
  "message": "Reset 13 stages for run {run_id}",
  "count": 13
}
```

**Behavior:**
- Resets all stages to `pending` status
- Clears `started_at`, `completed_at`, `duration_ms`
- Clears `input`, `output`, `error` data
- Updates `updated_at` timestamp

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/runs/{run_id}/stages/reset
```

## Strategies API

### Strategy Source Types

Allowed strategy source types:
- `generated` - Created by AI through AutoQuant pipeline
- `uploaded` - Uploaded by user from existing file
- `repaired` - Repaired from a failed strategy
- `manual` - Manually created by user
- `imported` - Imported from another HER-compatible source
- `demo` - Safe placeholder data for frontend/API development

### Strategy Directions

Allowed strategy directions:
- `long` - Long-only strategies
- `short` - Short-only strategies
- `both` - Both long and short
- `unknown` - Direction not specified

### Strategy Statuses

Allowed strategy statuses:
- `draft` - Initial state, not yet validated
- `active` - Validated and ready for use
- `archived` - No longer in use but kept for history

### Endpoints

#### List Strategies

**GET** `/api/strategies`

List all strategies with optional filters.

**Query Parameters:**
- `status` (optional) - Filter by status
- `source_type` (optional) - Filter by source type
- `limit` (optional, default: 50, max: 500) - Maximum number of results
- `offset` (optional, default: 0) - Offset for pagination

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "name": "MyStrategy",
    "source_type": "generated",
    "status": "draft",
    "direction": "both",
    "timeframe": "1h",
    "current_version_id": "uuid",
    "is_demo": false,
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/strategies
curl "http://127.0.0.1:8000/api/strategies?status=active&source_type=generated"
```

---

#### Create Strategy

**POST** `/api/strategies`

Create a new strategy.

**Request Body:**
```json
{
  "name": "MyStrategy",
  "class_name": "MyStrategy",
  "source_type": "generated",
  "timeframe": "1h",
  "direction": "both",
  "file_path": null,
  "params_path": null,
  "status": "draft",
  "is_demo": false
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "name": "MyStrategy",
  "class_name": "MyStrategy",
  "source_type": "generated",
  "timeframe": "1h",
  "direction": "both",
  "file_path": null,
  "params_path": null,
  "status": "draft",
  "current_version_id": null,
  "is_demo": false,
  "created_at": "2026-06-28T05:00:00Z",
  "updated_at": "2026-06-28T05:00:00Z"
}
```

**Error Response:** `400 Bad Request`

```json
{
  "error": true,
  "type": "validation_error",
  "message": "Invalid source_type: 'invalid'. Allowed values: uploaded, generated, repaired, manual, imported, demo",
  "details": {}
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/strategies \
  -H "Content-Type: application/json" \
  -d '{
    "name": "MyStrategy",
    "source_type": "generated",
    "timeframe": "1h"
  }'
```

---

#### Get Strategy

**GET** `/api/strategies/{strategy_id}`

Get detailed information about a specific strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Response:** `200 OK`

Returns the strategy object (same format as create response).

**Error Response:** `404 Not Found`

```json
{
  "detail": "Strategy {strategy_id} not found"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/strategies/{strategy_id}
```

---

#### Update Strategy

**PATCH** `/api/strategies/{strategy_id}`

Update specific fields of a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Request Body:**
```json
{
  "name": "Updated Name",
  "timeframe": "4h",
  "status": "active"
}
```

**Response:** `200 OK`

Returns the updated strategy object.

**Error Response:** `404 Not Found`

```json
{
  "detail": "Strategy {strategy_id} not found"
}
```

**Example:**
```bash
curl -X PATCH http://127.0.0.1:8000/api/strategies/{strategy_id} \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Name",
    "status": "active"
  }'
```

---

#### Archive Strategy

**POST** `/api/strategies/{strategy_id}/archive`

Archive a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Response:** `200 OK`

Returns the updated strategy object with status `archived`.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/strategies/{strategy_id}/archive
```

---

#### List Strategy Versions

**GET** `/api/strategies/{strategy_id}/versions`

List all versions for a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "version_number": 2,
    "py_path": "/path/to/strategy_v2.py",
    "json_path": "/path/to/strategy_v2.json",
    "is_current": true,
    "code_hash": "abc123",
    "created_from_run_id": "uuid",
    "notes": "Optimized parameters",
    "created_at": "2026-06-28T05:00:00Z"
  },
  {
    "id": "uuid",
    "version_number": 1,
    "py_path": "/path/to/strategy_v1.py",
    "json_path": "/path/to/strategy_v1.json",
    "is_current": false,
    "code_hash": "def456",
    "created_from_run_id": null,
    "notes": "Initial version",
    "created_at": "2026-06-28T04:00:00Z"
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/strategies/{strategy_id}/versions
```

---

#### Create Strategy Version

**POST** `/api/strategies/{strategy_id}/versions`

Create a new strategy version.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Request Body:**
```json
{
  "strategy_id": "uuid",
  "version_number": 2,
  "py_path": "/path/to/strategy_v2.py",
  "json_path": "/path/to/strategy_v2.json",
  "spec": {"indicators": ["RSI", "MACD"]},
  "params": {"stoploss": -0.1, "roi": {"0": 0.1}},
  "code_hash": "abc123",
  "created_from_run_id": "uuid",
  "notes": "Optimized parameters"
}
```

**Response:** `201 Created`

```json
{
  "id": "uuid",
  "strategy_id": "uuid",
  "version_number": 2,
  "py_path": "/path/to/strategy_v2.py",
  "json_path": "/path/to/strategy_v2.json",
  "spec": {"indicators": ["RSI", "MACD"]},
  "params": {"stoploss": -0.1, "roi": {"0": 0.1}},
  "code_hash": "abc123",
  "created_from_run_id": "uuid",
  "notes": "Optimized parameters",
  "is_current": false,
  "created_at": "2026-06-28T05:00:00Z"
}
```

**Note:** If `version_number` is not provided, it will be auto-incremented from the latest version. If it's version 1, it automatically becomes the current version.

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/strategies/{strategy_id}/versions \
  -H "Content-Type: application/json" \
  -d '{
    "spec": {"indicators": ["RSI", "MACD"]},
    "notes": "New version with RSI indicator"
  }'
```

---

#### Get Current Version

**GET** `/api/strategies/{strategy_id}/current-version`

Get the current version for a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Response:** `200 OK`

Returns the current version object (same format as create version response).

**Error Response:** `404 Not Found`

```json
{
  "detail": "No current version set for strategy {strategy_id}"
}
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/strategies/{strategy_id}/current-version
```

---

#### Set Current Version

**POST** `/api/strategies/{strategy_id}/current-version/{version_id}`

Set the current version for a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID
- `version_id` - Version UUID

**Response:** `200 OK`

Returns the updated strategy object with `current_version_id` updated.

**Error Response:** `404 Not Found`

```json
{
  "detail": "Version {version_id} not found"
}
```

**Example:**
```bash
curl -X POST http://127.0.0.1:8000/api/strategies/{strategy_id}/current-version/{version_id}
```

## Artifacts API

### Artifact Types

Allowed artifact types:
- `strategy_py` - Strategy Python code file
- `strategy_json` - Strategy parameters JSON file
- `strategy_spec` - Strategy specification
- `freqtrade_config` - Freqtrade configuration snapshot
- `backtest_raw` - Raw backtest output reference
- `hyperopt_raw` - Raw hyperopt output reference
- `metrics_json` - Metrics JSON artifact
- `report_md` - Markdown report artifact
- `export_package` - Export package reference
- `log_file` - Log file reference
- `chart` - Chart or image artifact
- `other` - Other file types

### Endpoints

#### List Artifacts

**GET** `/api/artifacts`

List all artifacts with optional filters.

**Query Parameters:**
- `run_id` (optional) - Filter by run ID
- `strategy_id` (optional) - Filter by strategy ID
- `artifact_type` (optional) - Filter by artifact type
- `limit` (optional, default: 50, max: 500) - Maximum number of results
- `offset` (optional, default: 0) - Offset for pagination

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "strategy_id": "uuid",
    "artifact_type": "strategy_py",
    "file_path": "/path/to/strategy.py",
    "description": "Generated strategy",
    "sha256": "abc123...",
    "size_bytes": 1024,
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

**Example:**
```bash
curl http://127.0.0.1:8000/api/artifacts
curl "http://127.0.0.1:8000/api/artifacts?run_id={run_id}"
```

---

#### Create Artifact

**POST** `/api/artifacts`

Create a new artifact.

**Request Body:**
```json
{
  "run_id": "uuid",
  "strategy_id": "uuid",
  "artifact_type": "strategy_py",
  "file_path": "/path/to/strategy.py",
  "description": "Generated strategy",
  "sha256": "abc123...",
  "size_bytes": 1024
}
```

**Response:** `201 Created`

Returns the created artifact object.

**Error Response:** `400 Bad Request`

```json
{
  "detail": "Invalid artifact_type: 'invalid'. Allowed values: strategy_py, strategy_json, ..."
}
```

---

#### Get Artifact

**GET** `/api/artifacts/{artifact_id}`

Get a specific artifact by ID.

**Path Parameters:**
- `artifact_id` - Artifact UUID

**Response:** `200 OK`

Returns the artifact object.

**Error Response:** `404 Not Found`

---

#### List Run Artifacts

**GET** `/api/runs/{run_id}/artifacts`

List all artifacts for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

Returns list of artifacts for the run.

---

#### List Strategy Artifacts

**GET** `/api/strategies/{strategy_id}/artifacts`

List all artifacts for a strategy.

**Path Parameters:**
- `strategy_id` - Strategy UUID

**Response:** `200 OK`

Returns list of artifacts for the strategy.

## Metrics API

### Endpoints

#### List Metric Snapshots

**GET** `/api/runs/{run_id}/metrics`

List all metric snapshots for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "stage_key": "baseline_backtest",
    "net_profit": 0.184,
    "profit_factor": 1.35,
    "max_drawdown": 12.1,
    "sharpe": 1.12,
    "calmar": 1.44,
    "win_rate": 54.2,
    "trade_count": 120,
    "expectancy": 0.42,
    "avg_win": 2.1,
    "avg_loss": -1.3,
    "raw_json": {"profit": 100, "trades": 50},
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

---

#### Get Latest Metric Snapshot

**GET** `/api/runs/{run_id}/metrics/latest`

Get the latest metric snapshot for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

Returns the latest metric snapshot.

**Error Response:** `404 Not Found`

---

#### Create Metric Snapshot

**POST** `/api/runs/{run_id}/metrics`

Create a new metric snapshot.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "stage_key": "baseline_backtest",
  "net_profit": 0.184,
  "profit_factor": 1.35,
  "max_drawdown": 12.1,
  "trade_count": 120,
  "expectancy": 0.42,
  "raw_json": {"profit": 100, "trades": 50}
}
```

**Response:** `201 Created`

Returns the created metric snapshot.

---

#### List Pair Results

**GET** `/api/runs/{run_id}/pair-results`

List all pair results for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "pair": "BTC/USDT",
    "net_profit": 0.092,
    "profit_factor": 1.35,
    "max_drawdown": 12.1,
    "trade_count": 44,
    "win_rate": 54.0,
    "expectancy": 0.4,
    "raw_json": {"profit": 50},
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

---

#### Create Pair Result

**POST** `/api/runs/{run_id}/pair-results`

Create a new pair result.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "pair": "BTC/USDT",
  "net_profit": 0.092,
  "profit_factor": 1.35,
  "max_drawdown": 12.1,
  "trade_count": 44,
  "win_rate": 54.0,
  "expectancy": 0.4,
  "raw_json": {"profit": 50}
}
```

**Response:** `201 Created`

Returns the created pair result.

---

#### Get Trade Summary

**GET** `/api/runs/{run_id}/trade-summary`

Get the trade summary for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
{
  "id": "uuid",
  "run_id": "uuid",
  "total_trades": 50,
  "wins": 30,
  "losses": 20,
  "draws": 0,
  "avg_duration": "1h30m",
  "best_pair": "BTC/USDT",
  "worst_pair": "ETH/USDT",
  "raw_json": {},
  "created_at": "2026-06-28T05:00:00Z"
}
```

**Error Response:** `404 Not Found`

---

#### Create Trade Summary

**POST** `/api/runs/{run_id}/trade-summary`

Create a new trade summary.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "total_trades": 50,
  "wins": 30,
  "losses": 20,
  "draws": 0,
  "avg_duration": "1h30m",
  "best_pair": "BTC/USDT",
  "worst_pair": "ETH/USDT"
}
```

**Response:** `201 Created`

Returns the created trade summary.

## Results API

### Purpose

The Results API exposes parsed backtest evidence produced by the Part 05 parser pipeline.

It does not:

- Run Freqtrade.
- Download market data.
- Call Ollama.
- Send Discord messages.
- Approve or reject strategies.
- Claim profitability.
- Change run status or strategy classification.

### Endpoints

#### Parse Captured Backtest Outputs

**POST** `/api/results/backtest/{run_id}/parse`

Parse already captured raw Freqtrade outputs for a run and save normalized evidence.

Mounted under both:

- `/api/results/backtest/{run_id}/parse`
- `/api/v1/results/backtest/{run_id}/parse`

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "force": false
}
```

`force=true` deletes previous metric snapshots for the run before saving the current parse result. Pair results are upserted and trade summary is replaced.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "success": true,
  "normalized_result_path": "artifacts/runs/{run_id}/normalized/backtest_result.normalized.json",
  "warnings": [],
  "errors": [],
  "saved_records": {
    "metric_snapshot": {"id": "uuid"},
    "pair_results": [{"id": "uuid"}],
    "trade_summary": {"id": "uuid"},
    "quality_audit": {"id": "uuid"}
  }
}
```

If no raw outputs exist, the endpoint returns `200 OK` with `success=false` and quality flags such as `missing_backtest_file`. This is a controlled parser failure, not a fake success.

**Error Response:** `404 Not Found`

Returned when the run does not exist.

---

#### Get Combined Parsed Backtest Result

**GET** `/api/results/backtest/{run_id}`

Return the latest combined parsed result:

- Latest metrics snapshot.
- Pair results.
- Trade summary.
- Latest quality report.
- Normalized artifact path.
- Warnings for missing sections.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "latest_metrics": {
    "net_profit": 10.0,
    "profit_factor": 1.4,
    "trade_count": 3
  },
  "pair_results": [],
  "trade_summary": null,
  "quality_report": null,
  "normalized_result_path": null,
  "warnings": ["pair_results_missing"]
}
```

---

#### Get Result Quality

**GET** `/api/results/backtest/{run_id}/quality`

Return the latest parser quality report for a run.

Compatibility route:

**GET** `/api/runs/{run_id}/result-quality`

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "parse_quality": "warning",
  "flags": [
    {
      "code": "too_few_trades",
      "severity": "warning",
      "message": "Parsed result has fewer trades than the configured minimum.",
      "details": {"trade_count": 3, "min_trades": 20}
    }
  ],
  "warnings": [],
  "errors": [],
  "is_usable_for_metrics": true,
  "is_usable_for_decision": true
}
```

`is_usable_for_decision` means enough parsed evidence exists for a future decision engine. It does not mean approved, profitable, exportable, or trading-ready.

**Error Response:** `404 Not Found`

Returned when no quality report exists for the run.

---

#### Get Normalized Result Artifact

**GET** `/api/results/backtest/{run_id}/normalized`

Return the normalized parsed result JSON artifact.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "metrics": {},
  "pair_results": [],
  "trade_summary": {},
  "quality_flags": [],
  "parser_metadata": {},
  "source_files": [
    "artifacts/runs/{run_id}/raw_freqtrade/backtest_results/backtest-result.json"
  ],
  "created_at": "2026-06-28T00:00:00Z"
}
```

**Error Response:** `404 Not Found`

Returned when the normalized artifact has not been written or is missing on disk.

### Existing Metrics Routes

The Results API keeps existing Part 03 metrics endpoints working:

- `GET /api/runs/{run_id}/metrics/latest`
- `GET /api/runs/{run_id}/pair-results`
- `GET /api/runs/{run_id}/trade-summary`

These routes are also mounted under `/api/v1`.

## Decisions API

### Purpose

The Decisions API exposes Part 06 decision results derived from already-parsed Part 05 evidence.

Decision persistence and APIs are separate from the Results parser. Decision endpoints must not:

- Run Freqtrade.
- Download market data.
- Call Ollama.
- Send Discord messages.
- Approve strategies.
- Export strategies.
- Modify strategy files.
- Claim future profitability.

Allowed Part 06 classifications:

- `rejected`
- `candidate`
- `promising`
- `validated`

Forbidden Part 06 outcomes:

- `approved`
- `exported`
- `live_ready`
- `profitable_guaranteed`

### Decision Schemas

Decision results include:

- `classification` - One allowed Part 06 classification.
- `confidence_score` - Evidence-strength score, not profitability probability.
- `policy_name` - One configured decision policy.
- `risk_profile` and `timeframe` - Threshold context used by the future decision service.
- `gates` - Acceptance-gate results.
- `reasons` - Explainable decision reasons.
- `evidence` - Parsed Part 05 metrics and artifact references.
- `warnings` - Non-blocking warning messages.
- `blocking_failures` - Blocking failure codes/messages.
- `next_actions` - Suggested next workflow actions.

Decision gate statuses:

- `passed`
- `failed`
- `warning`
- `not_applicable`
- `insufficient_data`

Decision reason severities:

- `info`
- `warning`
- `blocking`

Decision policy names:

- `default_conservative`
- `default_balanced`
- `default_aggressive`

### Endpoints

All Decisions API endpoints are mounted under both `/api` and `/api/v1`.

#### List Decision Policies

**GET** `/api/decisions/policies`

Return available deterministic decision policy summaries.

**Response:** `200 OK`

```json
[
  {
    "policy_name": "default_balanced",
    "display_name": "Balanced Decision Policy",
    "description": "Balanced baseline acceptance thresholds for already-parsed backtest evidence.",
    "allowed_classifications": ["rejected", "candidate", "promising", "validated"],
    "gate_names": ["minimum_trades_gate"],
    "risk_profile": "balanced",
    "timeframe": "1h",
    "thresholds": {
      "min_trades": 60,
      "candidate_profit_factor": 1.1
    },
    "notes": []
  }
]
```

#### Get Decision Policy

**GET** `/api/decisions/policies/{policy_name}`

Return one policy with full thresholds.

**Error Response:** `404 Not Found`

```json
{
  "error": true,
  "type": "not_found",
  "message": "Decision policy default_unknown not found",
  "details": {}
}
```

#### Evaluate Run Decision

**POST** `/api/decisions/runs/{run_id}/evaluate`

Evaluate already-parsed backtest evidence and persist a decision result.

This endpoint requires Part 05 parsed metrics to already exist. It does not run Freqtrade, parse raw output, call Ollama, send Discord messages, approve strategies, or export strategies.

**Request Body:**
```json
{
  "policy_name": "default_balanced",
  "risk_profile": "balanced",
  "timeframe": "1h",
  "apply_to_run": true,
  "force": false
}
```

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "success": true,
  "decision": {
    "run_id": "uuid",
    "classification": "rejected",
    "confidence_score": 18.0
  },
  "saved_decision_id": "uuid",
  "decision_report_path": "artifacts/runs/{run_id}/decisions/decision_result.json",
  "run_updated": true,
  "classification": "rejected",
  "confidence_score": 18.0,
  "policy_name": "default_balanced",
  "gates": [],
  "reasons": [],
  "warnings": [],
  "blocking_failures": [],
  "next_actions": []
}
```

Controlled missing-metrics response:

```json
{
  "run_id": "uuid",
  "success": false,
  "decision": null,
  "saved_decision_id": null,
  "decision_report_path": null,
  "run_updated": false,
  "errors": [
    "parsed_metrics_missing",
    "Parsed metrics are missing. Run the Part 05 parse endpoint or script first."
  ],
  "next_actions": ["Run the Part 05 parse endpoint or script first."]
}
```

Missing run response:

```json
{
  "error": true,
  "type": "not_found",
  "message": "Run {run_id} not found",
  "details": {}
}
```

#### List Run Decisions

**GET** `/api/decisions/runs/{run_id}`

Return all saved decisions for a run, newest first.

#### Get Latest Run Decision

**GET** `/api/decisions/runs/{run_id}/latest`

Return the latest saved decision result for a run.

Missing decision response:

```json
{
  "error": true,
  "type": "not_found",
  "message": "No decision found for run {run_id}",
  "details": {}
}
```

#### Backtest Decision Compatibility Route

**GET** `/api/results/backtest/{run_id}/decision`

Return the latest saved decision for a run.

#### Run Decision Compatibility Route

**GET** `/api/runs/{run_id}/decision`

Return the latest saved decision for run detail UI pages.

### Safety Notes

Decision API responses are sanitized to avoid deployment-oriented wording in user-facing decision payloads. Persisted decisions still retain the full traceable result in `decision_results` and the decision report artifact.

## Logs API

### Log Levels

Allowed log levels:
- `info` - Informational messages
- `warning` - Warning messages
- `error` - Error messages
- `debug` - Debug messages
- `critical` - Critical failures that need immediate attention

### Log Sources

Allowed log sources:
- `system` - System-generated logs
- `ai` - AI-generated logs
- `freqtrade` - Freqtrade logs
- `user` - User-generated logs

### Endpoints

#### List Run Logs

**GET** `/api/runs/{run_id}/logs`

List log entries for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Query Parameters:**
- `stage_key` (optional) - Filter by stage key
- `level` (optional) - Filter by log level
- `limit` (optional, default: 100, max: 1000) - Maximum number of results
- `offset` (optional, default: 0) - Offset for pagination

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "level": "info",
    "source": "system",
    "message": "Strategy generated successfully",
    "stage_key": "generate",
    "details": {"indicators": ["RSI"]},
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

**Note:** Secret-like values in details are automatically sanitized (replaced with `[REDACTED]`).

---

#### Add Log

**POST** `/api/runs/{run_id}/logs`

Add a log entry.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "level": "info",
  "source": "system",
  "message": "Strategy generated successfully",
  "stage_key": "generate",
  "details": {"indicators": ["RSI"]}
}
```

**Response:** `201 Created`

Returns the created log entry.

**Error Response:** `400 Bad Request`

## Retry History API

### Retry Statuses

Allowed retry statuses:
- `proposed` - Retry or repair option has been proposed
- `approved` - Proposed retry or repair has been approved
- `applied` - Approved retry or repair has been applied
- `failed` - Retry or repair failed
- `rejected` - Proposed retry or repair was rejected
- `skipped` - Retry or repair was intentionally skipped

### Endpoints

#### List Retry History

**GET** `/api/runs/{run_id}/retry-history`

List retry history for a run.

**Path Parameters:**
- `run_id` - Run UUID

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "parent_run_id": "uuid",
    "attempt_number": 1,
    "reason": "Strategy failed to load",
    "stage_key": "backtest",
    "status": "applied",
    "error_message": "Strategy failed to load",
    "proposed_fix": {"fix": "correct syntax"},
    "applied_fix": {"fix": "corrected syntax"},
    "created_at": "2026-06-28T05:00:00Z",
    "completed_at": "2026-06-28T05:05:00Z"
  }
]
```

---

#### Create Retry Entry

**POST** `/api/runs/{run_id}/retry-history`

Create a retry history entry.

**Path Parameters:**
- `run_id` - Run UUID

**Request Body:**
```json
{
  "parent_run_id": "uuid",
  "attempt_number": 1,
  "reason": "Strategy failed to load",
  "stage_key": "backtest",
  "status": "proposed",
  "error_message": "Strategy failed to load",
  "proposed_fix": {"fix": "correct syntax"}
}
```

**Response:** `201 Created`

Returns the created retry entry.

---

#### Complete Retry

**POST** `/api/retry-history/{retry_id}/complete`

Complete a retry entry.

**Path Parameters:**
- `retry_id` - Retry UUID

**Request Body:**
```json
{
  "status": "applied",
  "applied_fix": {"fix": "corrected syntax"},
  "error_message": null
}
```

**Response:** `200 OK`

Returns the updated retry entry.

**Error Response:** `404 Not Found`

## Audit Logs API

### Audit Actors

Allowed audit actors:
- `user` - User actions
- `system` - System actions
- `ai_assistant` - General assistant actions
- `ai_strategy_designer` - Strategy design assistant actions
- `ai_repair_agent` - Repair assistant actions

### Endpoints

#### List Audit Logs

**GET** `/api/audit-logs`

List audit logs with optional filters.

**Query Parameters:**
- `run_id` (optional) - Filter by run ID
- `action_type` (optional) - Filter by action type
- `limit` (optional, default: 100, max: 1000) - Maximum number of results
- `offset` (optional, default: 0) - Offset for pagination

**Response:** `200 OK`

```json
[
  {
    "id": "uuid",
    "run_id": "uuid",
    "actor": "ai_assistant",
    "action_type": "create",
    "description": "Created strategy draft",
    "target_type": "strategy",
    "target_id": "uuid",
    "before": null,
    "after": {"name": "MyStrategy"},
    "changed_files": ["strategy.py"],
    "rollback_path": null,
    "approved": true,
    "notes": "Generated by AI",
    "created_at": "2026-06-28T05:00:00Z"
  }
]
```

---

#### Create Audit Log

**POST** `/api/audit-logs`

Create an audit log entry.

**Request Body:**
```json
{
  "run_id": "uuid",
  "actor": "ai_assistant",
  "action_type": "create",
  "description": "Created strategy draft",
  "target_type": "strategy",
  "target_id": "uuid",
  "before": null,
  "after": {"name": "MyStrategy"},
  "changed_files": ["strategy.py"],
  "rollback_path": null,
  "approved": true,
  "notes": "Generated by AI"
}
```

**Response:** `201 Created`

Returns the created audit log entry.

**Error Response:** `400 Bad Request`

## System API

### Health Check

**GET** `/health`

Check if the backend is running.

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "app_name": "HER",
  "version": "0.3.0"
}
```

### System Status

**GET** `/api/system/status`

Get comprehensive system status.

**Response:** `200 OK`

```json
{
  "backend": "healthy",
  "database": "healthy",
  "database_path": "/path/to/data/her.db",
  "freqtrade": "configured",
  "ollama": "configured",
  "discord": "disabled",
  "docs_foundation_detected": true,
  "project_version": "0.3.0",
  "project_root": "/path/to/her",
  "freqtrade_user_data_dir": "/path/to/freqtrade_workspace/user_data",
  "frontend_port": 3000,
  "backend_port": 8000
}
```

## Freqtrade API

The Freqtrade API provides endpoints for Freqtrade status, workspace, strategy detection, data management, config generation, and backtesting.

### Endpoints

#### Get Freqtrade Status

**GET** `/api/freqtrade/status`

Get Freqtrade status and configuration.

**Response:** `200 OK`

```json
{
  "configured": false,
  "executable_available": false,
  "version": null,
  "workspace_valid": false,
  "allowed_commands": ["version", "list-data", "list-strategies", "backtesting"],
  "forbidden_commands": ["trade", "webserver"],
  "real_smoke_enabled": false,
  "warnings": [],
  "error": null
}
```

**Error Response:** `200 OK` (always returns, even if Freqtrade not configured)

---

#### Get Freqtrade Version

**GET** `/api/freqtrade/version`

Get Freqtrade version.

**Response:** `200 OK`

```json
{
  "version": "2024.1",
  "available": true,
  "error": null
}
```

**Controlled Failure (Freqtrade not configured):**

```json
{
  "version": null,
  "available": false,
  "error": "Freqtrade not configured"
}
```

---

#### Get Freqtrade Workspace

**GET** `/api/freqtrade/workspace`

Get Freqtrade workspace status.

**Response:** `200 OK`

```json
{
  "valid": true,
  "user_data_dir": "/path/to/freqtrade_workspace/user_data",
  "config_dir": "/path/to/freqtrade_workspace/config",
  "missing_dirs": [],
  "created_dirs": [],
  "user_action_required": null,
  "error": null
}
```

---

#### List Strategies

**GET** `/api/freqtrade/strategies`

List available strategies (file-visible and Freqtrade-visible when possible).

**Response:** `200 OK`

```json
{
  "strategies": [
    {
      "strategy_name": "MyStrategy",
      "file_path": "/path/to/strategies/MyStrategy.py",
      "exists": true,
      "freqtrade_visible": true,
      "has_sidecar_json": true,
      "sidecar_path": "/path/to/strategies/MyStrategy.json"
    }
  ],
  "source": "local",
  "error": null
}
```

---

#### Get Strategy Details

**GET** `/api/freqtrade/strategies/{strategy_name}`

Get specific strategy status.

**Path Parameters:**
- `strategy_name` - Strategy name

**Response:** `200 OK`

```json
{
  "strategy": {
    "strategy_name": "MyStrategy",
    "file_path": "/path/to/strategies/MyStrategy.py",
    "exists": true,
    "freqtrade_visible": true,
    "has_sidecar_json": true,
    "sidecar_path": "/path/to/strategies/MyStrategy.json"
  },
  "error": null
}
```

**Error Response:** `200 OK` (strategy not found returns null strategy with error)

---

#### Get Data Overview

**GET** `/api/freqtrade/data`

Get data directory overview.

**Query Parameters:**
- `exchange` (optional) - Filter by exchange
- `trading_mode` (optional) - Filter by trading mode
- `timeframe` (optional) - Filter by timeframe

**Response:** `200 OK`

```json
{
  "data_dir": "/path/to/freqtrade_workspace/user_data/data",
  "exists": true,
  "pairs_count": 10,
  "error": null
}
```

---

#### Generate Backtest Config

**POST** `/api/freqtrade/config/backtest`

Generate safe backtest config. Does not run backtest.

**Request Body:**
```json
{
  "run_id": "uuid (optional)",
  "config_path": "/path/to/config.json (optional)",
  "strategy_name": "MyStrategy",
  "timeframe": "1h",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timerange": "20240101-20240131",
  "stake_currency": "USDT",
  "stake_amount": 100,
  "dry_run": true
}
```

**Response:** `200 OK`

```json
{
  "success": true,
  "config_path": "/path/to/config.json",
  "artifact_id": "uuid",
  "error": null
}
```

**Error Response:** `200 OK` (returns success=false with error message)

---

#### Check Data Availability

**POST** `/api/freqtrade/data/check`

Check data availability. Does not download data.

**Request Body:**
```json
{
  "run_id": "uuid (optional)",
  "config_path": "/path/to/config.json (optional)",
  "exchange": "binance",
  "trading_mode": "spot",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timeframe": "1h",
  "timerange": "20240101-20240131",
  "show_timerange": true
}
```

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "pairs": [
    {
      "pair": "BTC/USDT",
      "exists": true,
      "file_path": "/path/to/data/BTC_USDT-1h-feather.parquet",
      "timerange": "20240101-20240131",
      "timeframe": "1h"
    }
  ],
  "source": "freqtrade",
  "freqtrade_visible": true,
  "error": null,
  "errors": [],
  "warnings": []
}
```

---

#### Download Data

**POST** `/api/freqtrade/data/download`

Run real Freqtrade `download-data`. Requires user confirmation.

**Request Body:**
```json
{
  "run_id": "uuid (optional)",
  "config_path": "/path/to/config.json (optional)",
  "exchange": "binance",
  "trading_mode": "spot",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timeframes": ["1h", "4h"],
  "days": 30,
  "timerange": null,
  "data_format_ohlcv": "feather",
  "user_confirmed": true
}
```

**Confirmation Rule:** `user_confirmed` must be `true` or request is rejected with `400 Bad Request`.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "success": true,
  "blocked": false,
  "exit_code": 0,
  "stdout": "Data downloaded successfully",
  "stderr": "",
  "duration_seconds": 45.2,
  "error": null,
  "errors": [],
  "warnings": []
}
```

**Controlled Failure (Freqtrade not configured):**

```json
{
  "run_id": "uuid",
  "success": false,
  "blocked": true,
  "exit_code": null,
  "stdout": "",
  "stderr": "",
  "duration_seconds": 0.0,
  "error": "Freqtrade is not configured",
  "errors": ["Freqtrade is not configured"],
  "warnings": []
}
```

**Error Response:** `400 Bad Request` (validation error, e.g., user_confirmed=false)

```json
{
  "detail": "user_confirmed must be true to run real download"
}
```

---

#### Run Backtest

**POST** `/api/freqtrade/backtest`

Run real Freqtrade backtest. Requires user confirmation.

**Request Body:**
```json
{
  "run_id": "uuid",
  "config_path": "/path/to/config.json",
  "strategy_name": "MyStrategy",
  "timeframe": "1h",
  "timerange": "20240101-20240131",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "export": "trades",
  "backtest_directory": null,
  "user_confirmed": true,
  "timeout_seconds": 1800
}
```

**Confirmation Rule:** `user_confirmed` must be `true` or request is rejected with `400 Bad Request`.

**Response:** `200 OK`

```json
{
  "run_id": "uuid",
  "success": true,
  "blocked": false,
  "exit_code": 0,
  "stdout": "Backtest completed successfully",
  "stderr": "",
  "duration_seconds": 120.5,
  "backtest_directory": "/path/to/backtest_results",
  "artifacts": [
    {
      "artifact_type": "backtest_raw",
      "path": "/path/to/backtest-result.json",
      "size_bytes": 1024,
      "created_at": "2024-01-01T00:00:00"
    }
  ],
  "error": null,
  "errors": [],
  "warnings": []
}
```

**Controlled Failure (Freqtrade not configured):**

```json
{
  "run_id": "uuid",
  "success": false,
  "blocked": true,
  "exit_code": null,
  "stdout": "",
  "stderr": "",
  "duration_seconds": 0.0,
  "backtest_directory": null,
  "artifacts": [],
  "error": "Freqtrade is not configured",
  "errors": ["Freqtrade is not configured"],
  "warnings": []
}
```

**Error Response:** `400 Bad Request` (validation error, e.g., user_confirmed=false or invalid strategy name)

```json
{
  "detail": "user_confirmed must be true to run real backtest"
}
```

### Confirmation Rules

Both data download and backtest endpoints require explicit user confirmation:

1. **Validation Layer:** Schema validation rejects `user_confirmed=false` with `400 Bad Request`
2. **Runtime Layer:** Service checks `user_confirmed=true` before execution

This prevents silent execution of resource-intensive operations.

### Controlled Failures

API endpoints return controlled failures for common scenarios:

- **Freqtrade not configured** - Returns `200 OK` with `blocked=true` and error message
- **Strategy not found** - Returns `200 OK` with `blocked=true` and error message
- **Data missing** - Returns `200 OK` with suggestion to download data
- **Command blocked** - Returns `200 OK` with `blocked=true` and error message
- **Command timeout** - Returns `200 OK` with `timed_out=true` and partial output

Stack traces are never exposed in API responses.

### Error Handling

All endpoints return consistent error responses:

```json
{
  "detail": "Error message describing what went wrong"
}
```

Common error scenarios:
- `400 Bad Request` - Invalid input data, validation errors
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Unexpected server error

## Pagination

List endpoints support pagination using `limit` and `offset` parameters:

- `limit` - Maximum number of items to return (default: 50, max: 500)
- `offset` - Number of items to skip (default: 0)

Example:
```bash
curl "http://127.0.0.1:8000/api/runs?limit=10&offset=20"
```

This returns items 21-30.

## Filtering

List endpoints support filtering by various fields using query parameters:

```bash
curl "http://127.0.0.1:8000/api/runs?status=running&classification=promising"
```

## Part 08 Optimization Pipeline API

### Overview

The optimization pipeline API provides endpoints for managing hyperopt-based strategy optimization, including run management, trial listing, best trial identification, and baseline vs optimized comparison.

### Base URL

```
http://127.0.0.1:8000/api/optimization
```

### Optimization Stages

Optimization runs progress through these stages:
- `optimization_setup` - Initial setup and validation
- `baseline_reference` - Baseline run reference
- `hyperopt_policy_validation` - Policy validation
- `hyperopt_config_generation` - Config generation
- `data_check` - Data availability check
- `data_download` - Data download if needed
- `hyperopt_execution` - Hyperopt execution
- `hyperopt_result_parsing` - Result parsing
- `trial_persistence` - Trial persistence
- `best_trial_selection` - Best trial selection
- `optimized_config_generation` - Optimized config generation
- `optimized_backtest` - Optimized backtest
- `optimized_result_parsing` - Optimized result parsing
- `optimized_decision_evaluation` - Decision evaluation
- `baseline_vs_optimized_comparison` - Comparison
- `optimization_report` - Report generation
- `completion` - Completion

### Optimization Statuses

- `pending` - Run is queued
- `running` - Run is in progress
- `completed` - Run completed successfully
- `failed_controlled` - Run failed with controlled error
- `confirmation_required` - User confirmation needed

### Optimization Result Statuses

- `not_improved` - Optimization did not improve over baseline
- `improved` - Optimization improved over baseline
- `optimization_candidate` - Optimization is a candidate
- `optimization_promising` - Optimization is promising
- `optimization_rejected` - Optimization rejected
- `overfit_suspected` - Overfitting suspected
- `invalid_optimization` - Invalid optimization

### Optimization Trial Statuses

- `completed` - Trial completed successfully
- `failed` - Trial failed
- `ignored` - Trial ignored
- `best` - Trial marked as best
- `selected_for_validation` - Trial selected for validation
- `rejected` - Trial rejected by policy

### Endpoints

#### POST /api/optimization/run

Start an optimization pipeline run.

**Request:**
```json
{
  "strategy_name": "MyStrategy",
  "pairs": ["BTC/USDT", "ETH/USDT"],
  "timeframe": "1h",
  "exchange": "binance",
  "days": 30,
  "timerange": "20240101-20240201",
  "risk_profile": "balanced",
  "baseline_run_id": null,
  "run_baseline_first": true,
  "download_missing_data": false,
  "user_confirmed": false,
  "epochs": 50,
  "spaces": ["buy", "sell"],
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "apply_decision_to_run": true,
  "notes": null
}
```

**Response (202 Accepted):**
```json
{
  "run_id": "opt-run-123",
  "status": "pending",
  "message": "Optimization run queued"
}
```

**Error Response (501 Not Implemented):**
```json
{
  "detail": "Optimization pipeline service not yet implemented. Use the repository directly for trial persistence."
}
```

**Validation Rules:**
- `strategy_name`: Required, non-empty string
- `pairs`: Required, non-empty list of trading pairs
- `timeframe`: Required, non-empty string
- `epochs`: Must be > 0 and <= 200
- `spaces`: Must be subset of ["buy", "sell", "roi", "stoploss", "trailing", "protection"]
- `risk_profile`: Must be one of ["conservative", "balanced", "aggressive"]

#### GET /api/optimization/runs

List all optimization runs.

**Query Parameters:**
- `limit` - Maximum number of runs to return (default: 100)
- `offset` - Number of runs to skip (default: 0)
- `status` - Optional status filter

**Response (200 OK):**
```json
[
  {
    "id": "opt-run-123",
    "strategy_name": "MyStrategy",
    "timeframe": "1h",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "exchange": "binance",
    "status": "completed",
    "result_status": "improved",
    "epochs_requested": 50,
    "epochs_completed": 50,
    "best_trial_id": "trial-456",
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  }
]
```

#### GET /api/optimization/runs/{optimization_run_id}

Get full optimization run detail.

**Response (200 OK):**
```json
{
  "run": {
    "id": "opt-run-123",
    "parent_run_id": null,
    "baseline_run_id": "run-789",
    "optimized_run_id": "run-999",
    "strategy_name": "MyStrategy",
    "timeframe": "1h",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "exchange": "binance",
    "risk_profile": "balanced",
    "status": "completed",
    "result_status": "improved",
    "best_trial_id": "trial-456",
    "epochs_requested": 50,
    "epochs_completed": 50,
    "spaces": ["buy", "sell"],
    "policy": {
      "max_epochs": 200,
      "default_epochs": 50,
      "allowed_spaces": ["buy", "sell"],
      "locked_spaces": ["roi", "stoploss", "trailing", "protection"],
      "max_optimized_parameters": 6,
      "allow_roi_optimization": false,
      "allow_stoploss_optimization": false,
      "allow_trailing_optimization": false,
      "timeout_seconds": 3600,
      "min_trades": 10,
      "stop_on_zero_trades": true
    },
    "request": {},
    "comparison": {},
    "report_artifact_path": null,
    "created_at": "2024-01-15T10:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z"
  },
  "stages": [],
  "best_trial": {
    "id": "trial-456",
    "optimization_run_id": "opt-run-123",
    "trial_number": 25,
    "status": "best",
    "is_best": true,
    "is_selected_for_validation": false,
    "params": {},
    "buy_params": {},
    "sell_params": {},
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": {},
    "loss_score": 0.15,
    "profit_total": 150.5,
    "profit_factor": 2.5,
    "expectancy": 0.05,
    "max_drawdown": -10.2,
    "trade_count": 45,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": null,
    "created_at": "2024-01-15T11:30:00Z"
  },
  "comparison": {
    "optimization_run_id": "opt-run-123",
    "baseline_run_id": "run-789",
    "optimized_run_id": "run-999",
    "baseline_metrics": {},
    "optimized_metrics": {},
    "metric_deltas": {},
    "baseline_classification": "promising",
    "optimized_classification": "validated",
    "baseline_confidence": 0.75,
    "optimized_confidence": 0.85,
    "classification_improved": true,
    "recommendation": "Use optimized strategy",
    "trial_summary": {},
    "created_at": "2024-01-15T12:00:00Z"
  },
  "artifact_paths": []
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/status

Get lightweight optimization run status.

**Response (200 OK):**
```json
{
  "run_id": "opt-run-123",
  "status": "running",
  "current_stage": "hyperopt_execution",
  "stage_progress": {
    "optimization_setup": "completed",
    "baseline_reference": "completed",
    "hyperopt_execution": "running"
  },
  "epochs_completed": 25,
  "epochs_total": 50,
  "trials_completed": 25,
  "trials_total": 50,
  "message": "Hyperopt execution in progress",
  "error_code": null,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T11:30:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/trials

List all trials for an optimization run.

**Query Parameters:**
- `limit` - Maximum number of trials to return (default: 100)
- `offset` - Number of trials to skip (default: 0)
- `status` - Optional status filter

**Response (200 OK):**
```json
[
  {
    "id": "trial-456",
    "optimization_run_id": "opt-run-123",
    "trial_number": 25,
    "status": "best",
    "is_best": true,
    "is_selected_for_validation": false,
    "params": {},
    "buy_params": {},
    "sell_params": {},
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": {},
    "loss_score": 0.15,
    "profit_total": 150.5,
    "profit_factor": 2.5,
    "expectancy": 0.05,
    "max_drawdown": -10.2,
    "trade_count": 45,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": null,
    "created_at": "2024-01-15T11:30:00Z"
  }
]
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/trials/{trial_id}

Get full trial details.

**Response (200 OK):**
```json
{
  "trial": {
    "id": "trial-456",
    "optimization_run_id": "opt-run-123",
    "trial_number": 25,
    "status": "best",
    "is_best": true,
    "is_selected_for_validation": false,
    "params": {},
    "buy_params": {},
    "sell_params": {},
    "roi_params": null,
    "stoploss_params": null,
    "trailing_params": null,
    "metrics": {},
    "loss_score": 0.15,
    "profit_total": 150.5,
    "profit_factor": 2.5,
    "expectancy": 0.05,
    "max_drawdown": -10.2,
    "trade_count": 45,
    "win_rate": 0.6,
    "rejection_reason": null,
    "failure_reason": null,
    "artifact_paths": [],
    "raw_trial": null,
    "created_at": "2024-01-15T11:30:00Z"
  },
  "artifact_paths": []
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/best-trial

Get the best trial for an optimization run.

**Response (200 OK):**
```json
{
  "id": "trial-456",
  "optimization_run_id": "opt-run-123",
  "trial_number": 25,
  "status": "best",
  "is_best": true,
  "is_selected_for_validation": false,
  "params": {},
  "buy_params": {},
  "sell_params": {},
  "roi_params": null,
  "stoploss_params": null,
  "trailing_params": null,
  "metrics": {},
  "loss_score": 0.15,
  "profit_total": 150.5,
  "profit_factor": 2.5,
  "expectancy": 0.05,
  "max_drawdown": -10.2,
  "trade_count": 45,
  "win_rate": 0.6,
  "rejection_reason": null,
  "failure_reason": null,
  "artifact_paths": [],
  "raw_trial": null,
  "created_at": "2024-01-15T11:30:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/comparison

Get baseline vs optimized comparison.

**Response (200 OK):**
```json
{
  "optimization_run_id": "opt-run-123",
  "baseline_run_id": "run-789",
  "optimized_run_id": "run-999",
  "baseline_metrics": {},
  "optimized_metrics": {},
  "metric_deltas": {},
  "baseline_classification": "promising",
  "optimized_classification": "validated",
  "baseline_confidence": 0.75,
  "optimized_confidence": 0.85,
  "classification_improved": true,
  "recommendation": "Use optimized strategy",
  "trial_summary": {},
  "created_at": "2024-01-15T12:00:00Z"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

#### GET /api/optimization/runs/{optimization_run_id}/report

Get optimization report artifact metadata.

**Response (200 OK):**
```json
{
  "optimization_run_id": "opt-run-123",
  "report_artifact_path": "artifacts/runs/opt-run-123/report.json",
  "status": "available"
}
```

**Error Response (404 Not Found):**
```json
{
  "detail": "Optimization run opt-run-123 not found"
}
```

### Security Considerations

- No secrets are exposed in optimization API responses
- No approved/export/live/profit guarantee wording in responses
- All parameter values are from hyperopt results, not user input
- Original strategy files are never overwritten
- Live trading commands are never allowed through optimization API

## Part 13 Validation Evidence Contract

Part 13 Prompt 2 defines backend constants, schemas, and database persistence for deeper validation evidence. It does not add HTTP routes yet and does not run Freqtrade.

Validation stages:

1. `validation_setup`
2. `candidate_reference`
3. `readiness_gate`
4. `oos_timerange_split`
5. `oos_backtest`
6. `oos_result_parsing`
7. `oos_decision`
8. `wfo_window_generation`
9. `wfo_window_execution`
10. `wfo_result_parsing`
11. `wfo_decision`
12. `robustness_checks`
13. `sensitivity_checks`
14. `validation_decision`
15. `validation_report`
16. `completion`

Validation workflow statuses:

- `pending`
- `running`
- `completed`
- `failed_controlled`
- `confirmation_required`

Validation decision statuses:

- `not_validated`
- `oos_failed`
- `oos_passed`
- `wfo_failed`
- `wfo_passed`
- `robustness_failed`
- `robustness_passed`
- `validated`
- `rejected`
- `validation_error`

### Validation Run Request

Future validation start endpoints should accept `ValidationRunRequest`.

```json
{
  "source_type": "strategy",
  "source_run_id": null,
  "strategy_name": "SmokeTestStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "risk_profile": "balanced",
  "timerange": null,
  "days": 90,
  "oos_ratio": 0.3,
  "wfo_enabled": true,
  "wfo_train_days": 60,
  "wfo_test_days": 15,
  "wfo_step_days": 15,
  "wfo_max_windows": 5,
  "robustness_enabled": true,
  "sensitivity_enabled": false,
  "download_missing_data": false,
  "user_confirmed": false,
  "notes": null
}
```

Validation rules:

- `strategy_name` is required and must not be blank.
- `pairs` must contain at least one non-blank pair.
- `timeframe` is required and must not be blank.
- `source_type` must be `strategy`, `baseline_run`, `optimization_run`, or `optimized_run`.
- `risk_profile` must be `conservative`, `balanced`, or `aggressive`.
- `oos_ratio` must be between `0.10` and `0.50`.
- WFO day/window values must be positive.
- `user_confirmed=false` is schema-valid, but future execution services must stop before real Freqtrade execution.

### Validation Evidence

`ValidationEvidence` is the persistence and frontend-safe shape for OOS, WFO, robustness, sensitivity, and aggregate-decision evidence.

```json
{
  "id": "evidence-1",
  "validation_run_id": "validation-run-1",
  "evidence_type": "oos",
  "status": "completed",
  "window_index": null,
  "timerange": "20250301-20250331",
  "metrics": {
    "profit_factor": 1.4,
    "trade_count": 22
  },
  "decision": {
    "classification": "candidate"
  },
  "issues": [],
  "warnings": ["low_trade_count_warning"],
  "artifact_paths": [
    "artifacts/runs/validation-run/oos/backtest_result.normalized.json"
  ],
  "created_at": "2026-06-30T10:00:00Z"
}
```

Evidence contracts intentionally omit raw stdout/stderr contents, approval fields, export fields, live-trading fields, and profit guarantees.

### Validation Detail Shape

Future detail endpoints should return a `ValidationRunDetail` style payload:

```json
{
  "run": {
    "id": "validation-run-1",
    "source_type": "strategy",
    "source_run_id": null,
    "strategy_name": "SmokeTestStrategy",
    "timeframe": "5m",
    "pairs": ["BTC/USDT"],
    "exchange": "binance",
    "risk_profile": "balanced",
    "status": "completed",
    "decision_status": "validated",
    "timerange": null,
    "oos_timerange": null,
    "report_artifact_path": "artifacts/runs/validation-run/validation/report.json",
    "created_at": "2026-06-30T10:00:00Z",
    "updated_at": "2026-06-30T10:05:00Z"
  },
  "evidence": [],
  "oos": null,
  "wfo": null,
  "robustness": [],
  "sensitivity": [],
  "decision": {
    "decision_status": "validated",
    "confidence_score": null,
    "policy_name": null,
    "reasons": [],
    "blocking_failures": [],
    "warnings": [],
    "next_actions": []
  },
  "summary": {
    "decision_status": "validated",
    "evidence_count": 3,
    "issues": [],
    "warnings": [],
    "next_actions": []
  },
  "artifact_paths": [
    "artifacts/runs/validation-run/validation/report.json"
  ],
  "warnings": [],
  "errors": []
}
```

Prompt 2 exposes this as a schema contract only. Validation routes are planned for later Part 13 prompts.

## Part 13 Validation Evidence API

Part 13 exposes validation evidence through backend API endpoints. These endpoints provide frontend-safe access to validation runs, evidence, and reports.

### Validation Run Request

POST `/api/validation/run` or `/api/v1/validation/run`

Request body:

```json
{
  "source_type": "strategy",
  "source_run_id": null,
  "strategy_name": "SmokeTestStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "risk_profile": "balanced",
  "timerange": null,
  "days": 90,
  "oos_ratio": 0.30,
  "wfo_enabled": true,
  "wfo_train_days": 60,
  "wfo_test_days": 15,
  "wfo_step_days": 15,
  "wfo_max_windows": 5,
  "robustness_enabled": true,
  "sensitivity_enabled": false,
  "download_missing_data": false,
  "user_confirmed": false,
  "notes": null
}
```

Response:

```json
{
  "validation_run_id": "validation-run-123",
  "status": "confirmation_required",
  "decision_status": null,
  "strategy_name": "SmokeTestStrategy",
  "pairs": ["BTC/USDT"],
  "timeframe": "5m",
  "exchange": "binance",
  "risk_profile": "balanced",
  "warnings": [],
  "errors": [],
  "next_actions": []
}
```

Requirements:
- `user_confirmed=true` required before real validation execution
- Strategy readiness enforced by backend gate
- Returns controlled failure for blocked strategies

### List Validation Runs

GET `/api/validation/runs` or `/api/v1/validation/runs`

Query parameters:
- `limit` (default: 50, max: 500)
- `offset` (default: 0)
- `status` (optional filter)
- `decision_status` (optional filter)
- `source_type` (optional filter)
- `strategy_name` (optional filter)

Response:

```json
[
  {
    "validation_run_id": "validation-run-123",
    "strategy_name": "SmokeTestStrategy",
    "source_type": "strategy",
    "source_run_id": null,
    "pairs": ["BTC/USDT"],
    "timeframe": "5m",
    "status": "completed",
    "decision_status": "validated",
    "created_at": "2026-06-30T10:00:00Z",
    "updated_at": "2026-06-30T10:05:00Z",
    "summary": {
      "decision_status": "validated",
      "evidence_count": 3,
      "warnings": [],
      "errors": [],
      "next_actions": []
    }
  }
]
```

### Get Validation Run Detail

GET `/api/validation/runs/{validation_run_id}` or `/api/v1/validation/runs/{validation_run_id}`

Response:

```json
{
  "run": {
    "validation_run_id": "validation-run-123",
    "source_type": "strategy",
    "source_run_id": null,
    "strategy_name": "SmokeTestStrategy",
    "pairs": ["BTC/USDT"],
    "timeframe": "5m",
    "exchange": "binance",
    "risk_profile": "balanced",
    "status": "completed",
    "decision_status": "validated",
    "timerange": null,
    "oos_timerange": null,
    "created_at": "2026-06-30T10:00:00Z",
    "updated_at": "2026-06-30T10:05:00Z"
  },
  "request": {
    "strategy_name": "SmokeTestStrategy",
    "pairs": ["BTC/USDT"],
    "timeframe": "5m"
  },
  "candidate_reference": {},
  "oos_summary": {
    "evidence_type": "oos",
    "status": "oos_passed",
    "timerange": "20240416-20240601",
    "metrics": {"trade_count": 40, "profit_factor": 1.4},
    "decision": {"decision_status": "oos_passed"}
  },
  "wfo_summary": {
    "evidence_type": "wfo_summary",
    "status": "wfo_passed",
    "pass_count": 4,
    "fail_count": 1
  },
  "robustness_summary": {
    "checks": [
      {
        "evidence_type": "robustness",
        "check_name": "parameter_stability",
        "status": "robustness_passed"
      }
    ],
    "count": 1
  },
  "sensitivity_summary": {
    "checks": [],
    "count": 0
  },
  "final_decision": {
    "decision_status": "validated",
    "reasons": [],
    "blocking_failures": [],
    "warnings": [],
    "next_actions": []
  },
  "report_path": "artifacts/runs/validation-run-123/validation/validation_report.json",
  "evidence": [],
  "warnings": [],
  "errors": [],
  "next_actions": [],
  "summary": {}
}
```

### Get Validation Status

GET `/api/validation/runs/{validation_run_id}/status` or `/api/v1/validation/runs/{validation_run_id}/status`

Response:

```json
{
  "validation_run_id": "validation-run-123",
  "status": "completed",
  "decision_status": "validated",
  "current_stage": null,
  "evidence_count": 3,
  "message": null,
  "completed_stages": [
    "validation_setup",
    "candidate_reference",
    "readiness_gate",
    "oos_timerange_split",
    "oos_backtest",
    "oos_result_parsing",
    "oos_decision",
    "wfo_window_generation",
    "wfo_window_execution",
    "wfo_result_parsing",
    "wfo_decision",
    "robustness_checks",
    "validation_decision",
    "validation_report",
    "completion"
  ],
  "failed_stage": null,
  "summary": {},
  "warnings": [],
  "errors": [],
  "created_at": "2026-06-30T10:00:00Z",
  "updated_at": "2026-06-30T10:05:00Z"
}
```

### Get Validation Evidence

GET `/api/validation/runs/{validation_run_id}/evidence` or `/api/v1/validation/runs/{validation_run_id}/evidence`

Response:

```json
{
  "validation_run_id": "validation-run-123",
  "evidence": [
    {
      "evidence_type": "oos",
      "status": "oos_passed",
      "timerange": "20240416-20240601",
      "metrics": {"trade_count": 40, "profit_factor": 1.4},
      "decision": {"decision_status": "oos_passed"}
    },
    {
      "evidence_type": "wfo_window",
      "window_index": 1,
      "timerange": "20240215-20240301",
      "status": "wfo_passed",
      "metrics": {"trade_count": 30, "profit_factor": 1.3}
    },
    {
      "evidence_type": "robustness",
      "status": "robustness_passed",
      "metrics": {"check": "stable"}
    }
  ],
  "oos": [...],
  "wfo_windows": [...],
  "wfo_summary": [...],
  "robustness": [...],
  "sensitivity": [...]
}
```

### Get Validation Report

GET `/api/validation/runs/{validation_run_id}/report` or `/api/v1/validation/runs/{validation_run_id}/report`

Response:

```json
{
  "validation_run_id": "validation-run-123",
  "report_artifact_path": "artifacts/runs/validation-run-123/validation/validation_report.json",
  "report": {
    "final_decision": {"decision_status": "validated"},
    "oos_result": {"status": "oos_passed"},
    "wfo_result": {"status": "wfo_passed"},
    "robustness_result": {"status": "robustness_passed"}
  }
}
```

### Error Behavior

All endpoints return clean, safe error responses:

- `404` for missing validation runs, evidence, or reports
- `400` for invalid request data
- `500` for system errors with sanitized messages
- No raw stack traces
- No secrets (api_key, password, token)
- No approval/export/live trading actions
- No profit guarantee wording

### Safety Guarantees

- No Ollama calls
- No Discord messages
- No live trading commands
- No strategy approval
- No strategy export
- No profit guarantees
- All evidence sanitized before frontend exposure
- Stdout/stderr stripped from responses
- Secrets redacted from responses

## Future Endpoints

The following endpoints will be added in future parts:

- Strategies API (`/api/strategies`)
- Artifacts API (`/api/artifacts`)
- Metrics API (`/api/metrics`)
- Audit Logs API (`/api/audit`)
