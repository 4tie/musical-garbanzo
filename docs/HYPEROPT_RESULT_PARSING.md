# Hyperopt Result Parsing Documentation

## Overview

The `HyperoptResultParser` service parses Freqtrade hyperopt output files and extracts all trials for persistence in the optimization pipeline. This ensures complete traceability of the optimization search space, not just the best trial.

## Automatic File Discovery

The parser automatically discovers hyperopt result files when no explicit file paths are provided. This enables real Part 08 validation without manual file injection.

### Discovery Locations (Priority Order)

1. **Run-specific hyperopt artifact directory**
   - Path: `{HER_ARTIFACTS_RUNS}/{run_id}/hyperopt/*.json`
   - Example: `/home/mohs/Desktop/her/artifacts/runs/opt-run-123/hyperopt/result.json`

2. **Run-specific artifact directory**
   - Path: `{HER_ARTIFACTS_RUNS}/{run_id}/*.json`
   - Example: `/home/mohs/Desktop/her/artifacts/runs/opt-run-123/result.json`

3. **Global Freqtrade hyperopt_results directory**
   - Path: `{FREQTRADE_HYPEROPT_RESULTS}/*.json`
   - Example: `/home/mohs/Desktop/her/freqtrade_workspace/user_data/hyperopt_results/result.json`

### Discovery Behavior

- **Deduplication:** Files discovered from multiple locations are deduplicated by path
- **Hidden files:** Files starting with `.` are excluded (e.g., `.last_result.json`)
- **Error handling:** If no files are discovered, a `ValueError` is raised with diagnostic information showing which locations were searched

### Discovery Error Example

If no files are found, the parser raises:

```
ValueError: No hyperopt result files discovered for run opt-run-123.
Searched locations:
  1. /home/mohs/Desktop/her/artifacts/runs/opt-run-123/hyperopt (exists: False)
  2. /home/mohs/Desktop/her/artifacts/runs/opt-run-123 (exists: False)
  3. /home/mohs/Desktop/her/freqtrade_workspace/user_data/hyperopt_results (exists: True)
Please ensure hyperopt has been executed and result files are available.
```

### Manual File Override

If `result_files` parameter is provided, automatic discovery is skipped and the provided files are used directly.

## Supported Result Shapes

The parser supports multiple Freqtrade output formats to handle different versions and configurations:

### 1. List of Trials

```json
[
  {
    "loss": 0.5,
    "buy_rsi": 30,
    "sell_rsi": 70,
    "metrics": {
      "profit_total": 100.0,
      "trade_count": 50
    }
  },
  {
    "loss": 0.3,
    "buy_rsi": 35,
    "sell_rsi": 65,
    "metrics": {
      "profit_total": 115.5,
      "trade_count": 52
    }
  }
]
```

### 2. Object with Results Key

```json
{
  "results": [
    {
      "loss": 0.5,
      "buy_rsi": 30,
      "metrics": {"profit_total": 100.0}
    }
  ],
  "best_result": {
    "loss": 0.3,
    "buy_rsi": 35,
    "metrics": {"profit_total": 115.5}
  }
}
```

### 3. Object with Trials Key

```json
{
  "trials": [
    {
      "loss": 0.5,
      "buy_rsi": 30,
      "metrics": {"profit_total": 100.0}
    }
  ]
}
```

### 4. Single Trial Object

```json
{
  "loss": 0.5,
  "buy_rsi": 30,
  "sell_rsi": 70,
  "metrics": {
    "profit_total": 100.0
  }
}
```

## Trial Persistence Rules

### All Trials Persisted

Every trial from the hyperopt result is persisted to the `optimization_trials` table, including:

- **Completed trials** - Trials that finished successfully
- **Failed trials** - Trials that encountered errors
- **Rejected trials** - Trials that fail policy thresholds
- **Ignored trials** - Incomplete or unusable trials

### Trial Data Fields

For each trial, the following fields are persisted:

| Field | Description |
|-------|-------------|
| `trial_number` | Sequential trial number (1, 2, 3, ...) |
| `status` | Trial status (completed, failed, ignored, best, selected_for_validation, rejected) |
| `params_json` | Full parameter set as JSON |
| `buy_params_json` | Buy signal parameters as JSON |
| `sell_params_json` | Sell signal parameters as JSON |
| `roi_params_json` | ROI parameters as JSON |
| `stoploss_params_json` | Stoploss parameters as JSON |
| `trailing_params_json` | Trailing parameters as JSON |
| `metrics_json` | Trial metrics as JSON |
| `loss_score` | Loss score from hyperopt |
| `profit_total` | Total profit |
| `profit_factor` | Profit factor |
| `expectancy` | Trade expectancy |
| `max_drawdown` | Maximum drawdown |
| `trade_count` | Total trade count |
| `win_rate` | Win rate |
| `rejection_reason` | Reason if trial was rejected |
| `failure_reason` | Reason if trial failed |
| `artifact_paths_json` | Trial artifact paths as JSON |
| `raw_trial_json` | Raw trial data from hyperopt as JSON |
| `is_best` | Whether this is the best trial (0/1) |
| `is_selected_for_validation` | Whether selected for validation (0/1) |

### Parameter Separation

The parser automatically separates parameters by space:

- `buy_rsi` → `params.buy.rsi`
- `sell_rsi` → `params.sell.rsi`
- `roi_t1` → `params.roi.t1`
- `stoploss_value` → `params.stoploss.value`
- `trailing_stop` → `params.trailing.stop`

If parameters are already separated (e.g., `params.buy.rsi`), they are preserved as-is.

## Best Trial Detection

The parser uses multiple methods to detect the best trial:

### 1. Explicit Best Result

If the result file contains a `best_result` key, that trial is marked as best:

```json
{
  "best_result": {
    "loss": 0.3,
    "buy_rsi": 35
  }
}
```

### 2. Lowest Loss Score

If no explicit best result, the trial with the lowest loss score is selected:

```python
best_trial = min(trials, key=lambda t: t.loss_score)
```

### 3. Metric Ranking Fallback

If loss scores are unavailable, the parser falls back to metric ranking (profit, profit factor, etc.).

### Best Trial Documentation

The parser output includes:
- `best_trial_id` - UUID of the best trial
- `best_trial_number` - Trial number of the best trial
- Detection method used (documented in parser output)

## Trial Status Classification

Trials are classified based on their raw data:

| Status | Condition |
|--------|-----------|
| `best` | Explicitly marked as best trial |
| `completed` | Trial has loss score and no errors |
| `failed` | Trial has error or failure reason |
| `rejected` | Trial completed but fails policy thresholds |
| `ignored` | Trial is incomplete or unusable |

### Policy-Based Rejection

When a `HyperoptPolicy` is provided, trials are checked against policy thresholds:

- **Minimum trades** - If `trade_count < policy.min_trades`, trial is rejected
- **Zero trades** - If `trade_count == 0` and `policy.stop_on_zero_trades`, trial is rejected

## Partial Trial History Warning

If the parser can only extract the best trial (e.g., from stdout fallback), it sets:

- `partial_trial_history = true`
- Warning: `full_trial_history_not_available`

This indicates that not all trials were available for parsing. The best trial is still persisted, but the frontend should display a warning that the full optimization history is not available.

## Parser Output

The `parse_and_persist_trials` method returns:

```python
{
  "trials_count": 50,              # Total trials parsed
  "persisted_trials_count": 48,    # Trials successfully persisted
  "best_trial_id": "trial-uuid",   # Best trial UUID
  "best_trial_number": 25,         # Best trial number
  "partial_trial_history": false,   # Whether full history is available
  "warnings": [],                   # Warning messages
  "errors": [],                     # Error messages
  "source_files": [                 # Source file paths
    "path/to/result1.json"
  ]
}
```

## Frontend API Implications

### Trial Listing Endpoint

The frontend can query all trials via:

```
GET /api/optimization/runs/{run_id}/trials
```

This returns all trials, not just the best trial, enabling:
- Full parameter space exploration visualization
- Analysis of failed/rejected trials
- Comparison of trial metrics across the search space

### Best Trial Endpoint

The best trial is available via:

```
GET /api/optimization/runs/{run_id}/trials/best
```

### Partial History Display

When `partial_trial_history = true`, the frontend should:
- Display a warning banner
- Show the best trial if available
- Indicate that full trial history is not available

## Error Handling

### Parse Errors

If a result file cannot be parsed:
- Error is logged to `errors` array
- Parsing continues with other files
- No trials are silently discarded

### Persistence Errors

If a trial cannot be persisted:
- Error is logged to `errors` array
- Trial is counted in `trials_count` but not `persisted_trials_count`
- `partial_trial_history` is set to `true`

## Testing

Test fixtures are located at:
- `backend/tests/fixtures/hyperopt/list_of_trials.json`
- `backend/tests/fixtures/hyperopt/object_with_results.json`
- `backend/tests/fixtures/hyperopt/object_with_trials.json`
- `backend/tests/fixtures/hyperopt/failed_trial.json`
- `backend/tests/fixtures/hyperopt/rejected_trial.json`
- `backend/tests/fixtures/hyperopt/separated_params.json`

Tests cover:
- Multiple result shape parsing
- Best trial detection
- Failed and rejected trial handling
- Parameter extraction and separation
- Metric extraction
- Full trial persistence (no silent discarding)
- Frontend-ready output serialization

## Implementation Notes

- The parser does not run Hyperopt or Freqtrade
- The parser does not call Ollama or send Discord messages
- The parser does not approve or export strategies
- All trials are persisted, not just the best trial
- Raw trial data is preserved in `raw_trial_json` for debugging
- Trial-specific artifacts are tracked in `artifact_paths_json`
