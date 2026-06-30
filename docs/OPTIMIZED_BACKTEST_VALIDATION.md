# Optimized Backtest Validation

## Why Hyperopt Result is Not Enough

HER does not trust Hyperopt output alone for several critical reasons:

1. **Hyperopt metrics are in-sample**: Hyperopt evaluates parameters on the same data used for optimization, leading to overfitting. The best trial in Hyperopt may perform poorly on out-of-sample data.

2. **Hyperopt uses simplified evaluation**: Hyperopt typically focuses on a single metric (e.g., profit) without considering the full decision criteria required for production readiness.

3. **No decision engine evaluation**: Hyperopt does not apply HER's decision engine criteria (risk profile, drawdown limits, trade quality, etc.).

4. **No controlled failure handling**: Hyperopt may produce results that would be rejected by HER's safety checks.

5. **No artifact normalization**: Hyperopt output is not normalized to HER's standard artifact format.

Therefore, HER must run a separate optimized backtest with the best trial parameters to validate the optimization result before considering it for approval.

## Best Params Materialization Flow

The `StrategyParamsMaterializer` safely materializes best trial parameters:

1. **Input**: Best trial ID, trial number, strategy name, and params dictionary (buy, sell, roi, stoploss, trailing)

2. **Validation**: 
   - Required sections (buy, sell) must be present and non-empty
   - Optional sections (roi, stoploss, trailing) must be dictionaries if present

3. **Materialization**:
   - Creates run-owned directory: `artifacts/runs/{optimization_run_id}/optimized_params/`
   - Writes params file: `{strategy_name}.json`
   - Never overwrites original strategy file
   - Never overwrites original strategy sidecar JSON

4. **Content**:
   ```json
   {
     "strategy_name": "MyStrategy",
     "source_trial_id": "trial-456",
     "source_trial_number": 42,
     "params": { ... },
     "buy_params": { ... },
     "sell_params": { ... },
     "roi_params": { ... },
     "stoploss_params": { ... },
     "trailing_params": { ... },
     "created_at": "2026-06-30T01:00:00Z",
     "warning": "This is validation materialization, not approved export. Do not use for live trading without explicit approval."
   }
   ```

5. **Artifact Registration**: Registers the params artifact in the artifact repository with metadata (trial_id, trial_number, strategy_name)

## Temporary Workspace Behavior

If Freqtrade requires params sidecar next to the strategy file:

1. **Create run-owned temporary workspace**: `artifacts/runs/{optimization_run_id}/temp_strategy_workspace/`

2. **Copy strategy file safely**: Copies the original strategy file to the temporary workspace without modifying the original

3. **Place params JSON next to copied strategy**: Places the materialized params JSON in the temporary workspace

4. **Use temporary workspace for backtest**: Configures Freqtrade to use the temporary workspace for the optimized backtest

5. **Never modify original**: The original strategy file in the user's strategies directory remains untouched

## Optimized Backtest Flow

The `OptimizedBacktestService` orchestrates the optimized backtest validation:

1. **Prepare optimized strategy workspace**: Calls `StrategyParamsMaterializer` to materialize params safely

2. **Generate optimized backtest config**: Uses `FreqtradeConfigGenerator` to create a backtest config

3. **Create separate HER run**: Creates a new run with name "Optimized Backtest - {strategy_name}" linked to the optimization run

4. **Run backtest**: Calls `FreqtradeBacktestRunner` to execute the optimized backtest

5. **Parse optimized result**: Calls `BacktestResultLoader` to parse the backtest output into normalized format

6. **Evaluate optimized decision**: Calls `DecisionService` to apply decision criteria to the optimized result

7. **Update optimization run**: Links the optimized run ID to the optimization run

8. **Return comprehensive result**: Returns optimized_run_id, config_path, params_artifact_path, backtest_artifacts, normalized_artifact_path, decision_artifact_path, classification, confidence_score, metrics, warnings, errors

## Safety Rules

1. **Never modify original strategy**: Original strategy file is never overwritten or modified

2. **Never export approved strategy**: Optimized params are marked as validation materialization, not approved export

3. **Never treat best params as live-ready**: The warning in the params artifact explicitly states this is not for live trading

4. **Never skip optimized backtest**: The optimized backtest is always run to validate Hyperopt results

5. **Never skip parse/decision**: The result is always parsed and evaluated through the decision engine

6. **No fake metrics**: All metrics come from real Freqtrade backtest execution

7. **No approval/export/live wording**: Service output never contains approval, export, or live trading terminology

8. **No secrets in params artifact**: Params artifact contains no API keys, secrets, or sensitive information

## Artifacts Generated

1. **Params artifact**: `artifacts/runs/{optimization_run_id}/optimized_params/{strategy_name}.json`
   - Contains materialized parameters with source trial info
   - Registered in artifact repository

2. **Backtest artifacts**: Raw Freqtrade backtest output files
   - Stored in run-specific backtest directory
   - Registered in artifact repository

3. **Normalized artifact**: Parsed and normalized backtest result
   - Standard HER format with metrics, pair results, trade summary
   - Registered in artifact repository

4. **Decision artifact**: Decision engine evaluation result
   - Classification, confidence score, warnings
   - Registered in artifact repository

## Frontend Display Notes

The frontend should display optimized backtest results with:

1. **Clear labeling**: Mark as "Optimized Backtest (Validation)" to distinguish from baseline

2. **Source trial info**: Display source trial ID and trial number for traceability

3. **Warning banner**: Show the validation materialization warning prominently

4. **Classification**: Display decision classification (validated, candidate, rejected, etc.)

5. **Comparison**: Show side-by-side comparison with baseline metrics

6. **Artifact links**: Provide links to params artifact, backtest artifacts, normalized artifact, decision artifact

7. **No approval buttons**: Do not provide approval/export buttons for optimized results (that comes later in the pipeline)

## Controlled Failure Handling

The optimized backtest service implements controlled failure handling:

1. **Backtest failure**: If backtest fails, stops before parse/decision, returns error with artifacts list

2. **Parse failure**: If parsing fails, stops before decision, returns error with backtest artifacts

3. **Decision failure**: If decision evaluation fails, returns error with all prior artifacts

4. **Missing best trial**: Returns controlled failure before any execution

5. **Invalid params**: Returns controlled failure before backtest execution

Each failure returns a structured response with:
- optimized_run_id (if created)
- optimized_config_path
- params_artifact_path
- backtest_artifacts (if any)
- normalized_artifact_path (if any)
- decision_artifact_path (if any)
- classification (null on failure)
- confidence_score (null on failure)
- metrics (empty on failure)
- warnings (if any)
- errors (list of error messages)
