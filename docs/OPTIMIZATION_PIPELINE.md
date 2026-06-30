# HER Optimization Pipeline

## Purpose

The HER Optimization Pipeline (Part 08) provides a safe way to optimize trading strategy parameters using Freqtrade Hyperopt. The pipeline:

1. Starts from an existing strategy
2. Runs baseline evaluation or reuses an existing baseline run
3. Runs safe Freqtrade Hyperopt with user confirmation
4. Persists every optimization trial (not just the best trial)
5. Extracts best parameters based on objective function
6. Re-tests best parameters with a real optimized backtest
7. Parses optimized backtest results
8. Runs decision engine on optimized results
9. Compares baseline vs optimized results
10. Produces an optimization report
11. Exposes frontend-ready APIs for optimization data

**Important:** This pipeline does NOT guarantee profitability, approve strategies, export strategies, run live trading, call Ollama, or send Discord messages. It optimizes parameters safely and validates whether optimization actually improved the baseline evidence.

## CLI Usage

### Basic Command

```bash
python scripts/run-optimization.py \
  --strategy HERHyperoptSmokeStrategy \
  --pair BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --risk-profile balanced \
  --epochs 20 \
  --spaces buy,sell \
  --download-missing-data \
  --user-confirmed \
  --apply-decision-to-run \
  --run-baseline-first
```

### Arguments

- `--strategy` (required) - Strategy name to optimize
- `--pair` (repeatable) - Trading pair (e.g., --pair BTC/USDT --pair ETH/USDT)
- `--pairs` (alternative) - Comma-separated trading pairs (e.g., BTC/USDT,ETH/USDT)
- `--timeframe` (required) - Timeframe (e.g., 1h, 4h, 1d)
- `--exchange` (default: binance) - Exchange name
- `--days` (default: 30) - Number of days of data
- `--timerange` (optional) - Specific time range
- `--risk-profile` (default: balanced) - Risk profile (conservative, balanced, aggressive)
- `--epochs` (default: 50) - Number of hyperopt epochs
- `--spaces` (default: buy,sell) - Comma-separated hyperopt spaces
- `--download-missing-data` - Download missing market data (requires --user-confirmed)
- `--user-confirmed` - Confirm resource-intensive operations (Hyperopt, backtest, data download)
- `--apply-decision-to-run` (default: True) - Apply decision classification to run
- `--baseline-run-id` (optional) - Existing baseline run ID to reuse
- `--run-baseline-first` (default: True) - Run baseline before optimization

### Output

The script prints:

- optimization_run_id
- baseline_run_id
- optimized_run_id
- strategy_name
- pairs
- timeframe
- status
- result_status
- trials_count
- best_trial_id
- best_trial_number
- optimized_classification
- baseline_metrics
- optimized_metrics
- comparison summary (delta_profit_factor, delta_expectancy, delta_drawdown, delta_trade_count, improvement_summary)
- report_path
- API endpoints to inspect later
- warnings
- errors

### Final Markers

- `REAL_OPTIMIZATION_PIPELINE_PASSED` - Pipeline completed successfully
- `REAL_OPTIMIZATION_PIPELINE_FAILED_CONTROLLED` - Pipeline failed with controlled error
- `REAL_OPTIMIZATION_PIPELINE_CONFIRMATION_REQUIRED` - Pipeline requires user confirmation

## Request Fields

The `OptimizationRequest` schema includes:

- `strategy_name` - Strategy name in Freqtrade workspace
- `pairs` - Trading pairs to optimize
- `timeframe` - Timeframe for optimization
- `exchange` - Exchange name (default: binance)
- `days` - Number of days of data (default: 30)
- `timerange` - Specific time range (optional)
- `risk_profile` - Risk profile (conservative, balanced, aggressive)
- `baseline_run_id` - Existing baseline run ID to reuse (optional)
- `run_baseline_first` - Run baseline before optimization (default: True)
- `download_missing_data` - Download missing market data (default: False)
- `user_confirmed` - User confirmation for resource-intensive operations (default: False)
- `epochs` - Number of hyperopt epochs (default: 50)
- `spaces` - Hyperopt spaces to optimize (default: buy, sell)
- `max_open_trades` - Maximum open trades (default: 3)
- `stake_currency` - Stake currency (default: USDT)
- `stake_amount` - Stake amount (default: unlimited)
- `apply_decision_to_run` - Apply decision classification to run (default: True)
- `notes` - Optional notes

## Stages

The optimization pipeline consists of 17 stages:

1. **optimization_setup** - Create optimization run and initialize stages
2. **baseline_reference** - Establish baseline reference (run new or link existing)
3. **hyperopt_policy_validation** - Validate hyperopt configuration is safe
4. **hyperopt_config_generation** - Generate Freqtrade hyperopt config
5. **data_check** - Check local market data availability
6. **data_download** - Download missing market data (if allowed and confirmed)
7. **hyperopt_execution** - Run Freqtrade hyperopt (requires user confirmation)
8. **hyperopt_result_parsing** - Parse hyperopt results and extract trial data
9. **trial_persistence** - Persist every trial to database
10. **best_trial_selection** - Select best trial based on objective function
11. **optimized_config_generation** - Generate config with best parameters
12. **optimized_backtest** - Run real backtest with best parameters (requires user confirmation)
13. **optimized_result_parsing** - Parse optimized backtest results
14. **optimized_decision_evaluation** - Run decision engine on optimized results
15. **baseline_vs_optimized_comparison** - Compare metrics and classifications
16. **optimization_report** - Generate comprehensive optimization report
17. **completion** - Mark pipeline as completed

## All-Trial Persistence

**Important:** Every trial is persisted to the database, not just the best trial. This enables full analysis of the optimization search space.

### Trial Data Stored

For every trial, the pipeline persists:

- trial_number - Sequential trial number (1, 2, 3, ...)
- status - Trial status (completed, failed, ignored, best, selected_for_validation, rejected)
- full parameter set used - All parameters (buy, sell, ROI, stoploss, trailing)
- buy_params - Buy signal parameters
- sell_params - Sell signal parameters
- roi_params - ROI parameters if present
- stoploss_params - Stoploss parameters if present
- trailing_params - Trailing stop parameters if present
- loss_score - Loss score from hyperopt objective function
- profit_metrics - Profit, profit factor, net profit, etc.
- drawdown_metrics - Max drawdown, average drawdown, etc.
- trade_count - Total number of trades
- win_rate - Win rate percentage
- expectancy - Trade expectancy if available
- pair_results - Per-pair results if available
- is_best_trial - Whether this is the best trial
- rejection_reason - Why trial was not selected
- artifact_paths - Trial-specific artifact paths
- created_at - Timestamp

### Trial History API

- `GET /api/optimization/runs/{optimization_run_id}/trials` - Returns all trials (not just best trial)
- `GET /api/optimization/runs/{optimization_run_id}/trials/{trial_id}` - Returns full trial details with parameters

## Best Trial Selection

Best trial selection is based on:

1. **Objective function** - Primary metric from hyperopt (e.g., profit, Sharpe, profit factor)
2. **Trade count threshold** - Minimum trades required
3. **Drawdown limit** - Maximum acceptable drawdown
4. **Consistency** - Prefer consistent performance across pairs

### Tie-breaking

- Higher trade count
- Lower drawdown
- More recent trial

### Best Trial API

- `GET /api/optimization/runs/{optimization_run_id}/best-trial` - Returns the best trial

## Optimized Backtest Validation

The pipeline validates best parameters with a real optimized backtest:

1. Generate optimized config with best parameters
2. Validate config is safe and valid
3. Run optimized backtest with best parameters
4. Capture raw backtest outputs
5. Parse optimized backtest results
6. Extract normalized metrics
7. Run decision engine on optimized results
8. Compare to baseline metrics
9. Determine if optimization improved results
10. Generate optimization comparison report

### Comparison Metrics

The pipeline compares:

- Profit metrics - Net profit, profit factor, expectancy
- Risk metrics - Max drawdown, average drawdown, Sharpe ratio
- Trade metrics - Trade count, win rate, average win/loss
- Classification - Baseline vs optimized classification
- Confidence score - Baseline vs optimized confidence

### Improvement Criteria

Improvement is determined by:

- Higher profit factor
- Higher expectancy
- Lower drawdown
- Higher win rate
- Better classification
- Higher confidence score

## Baseline vs Optimized Comparison

### Comparison Structure

The comparison includes:

- Request summary - Strategy, pairs, timeframe, exchange
- Baseline results - Baseline metrics, classification, confidence
- Optimized results - Optimized metrics, classification, confidence
- Metric deltas - Absolute and percentage changes
- Classification change - Whether classification improved
- Trial summary - Total trials, best trial number, improvement rate
- Recommendation - Whether to use optimized parameters

### Comparison Logic

The pipeline determines improvement by:

1. Primary metric improvement - Profit factor or expectancy improved
2. Risk improvement - Drawdown reduced or maintained
3. Classification improvement - Better classification achieved
4. Consistency - Improvement across multiple metrics
5. Statistical significance - Sufficient trade count for confidence

### Recommendation Levels

- Strong improvement - Clear improvement across metrics
- Moderate improvement - Some improvement, mixed results
- No improvement - Optimized results similar or worse than baseline
- Degradation - Optimized results worse than baseline

### Comparison API

- `GET /api/optimization/runs/{optimization_run_id}/comparison` - Returns baseline vs optimized comparison

## Frontend-Ready APIs

### Optimization Run Endpoints

- `POST /api/optimization/run` - Start optimization pipeline (requires user_confirmed=true)
- `GET /api/optimization/runs` - List optimization runs with pagination and status filter
- `GET /api/optimization/runs/{optimization_run_id}` - Get full optimization run detail
- `GET /api/optimization/runs/{optimization_run_id}/status` - Get lightweight status for polling
- `GET /api/optimization/runs/{optimization_run_id}/report` - Get optimization report artifact metadata

### Trial Endpoints

- `GET /api/optimization/runs/{optimization_run_id}/trials` - List all trials for an optimization run
- `GET /api/optimization/runs/{optimization_run_id}/trials/{trial_id}` - Get full trial details with parameters
- `GET /api/optimization/runs/{optimization_run_id}/best-trial` - Get the best trial

### Comparison Endpoints

- `GET /api/optimization/runs/{optimization_run_id}/comparison` - Get baseline vs optimized comparison

### Frontend-Ready Response Format

List responses include:
- Trial summary with key metrics
- Trial status and rejection reasons
- Best trial flag
- Parameter summaries
- Comparison deltas

Detail responses include:
- Full parameter sets
- Complete metrics
- Pair results
- Trade summary
- Artifact paths
- Stage history

All responses:
- Properly serialized datetime fields
- No secrets exposed
- No raw stack traces
- No approval/export/live wording
- Clean error messages with specific error codes

## Safety Rules

### What the Pipeline Does NOT Do

- Does not call Ollama
- Does not send Discord messages
- Does not approve strategies
- Does not export strategies
- Does not start live trading
- Does not start dry-run trading bot loops
- Does not guarantee profitability
- Does not claim optimization will improve results
- Does not use unsafe Freqtrade commands
- Does not bypass user confirmation requirements

### What the Pipeline Does

- Runs safe Freqtrade hyperopt with user confirmation
- Persists every optimization trial for transparency
- Validates best parameters with real backtest
- Compares optimized vs baseline objectively
- Provides frontend-ready trial data
- Uses controlled failure messaging
- Sanitizes secrets in logs and configs
- Requires user confirmation for resource-intensive operations

### User Confirmation Requirements

- Hyperopt execution requires `user_confirmed=true`
- Data download requires both `download_missing_data=true` and `user_confirmed=true`
- Optimized backtest requires `user_confirmed=true`

### Secret Protection

- No hardcoded secrets in optimization code
- Config generator sanitizes secrets in responses
- Exchange keys empty in generated configs
- Secret sanitization in logs and audit records
- No secrets in API responses

## Troubleshooting

### Common Issues

**Pipeline fails with "confirmation_required" error:**
- Ensure `--user-confirmed` flag is set
- Check that resource-intensive operations are confirmed

**Hyperopt fails to execute:**
- Verify strategy exists in Freqtrade workspace
- Check that strategy has hyperoptable parameters
- Ensure data is available or use `--download-missing-data`

**No trials persisted:**
- Check hyperopt execution completed successfully
- Verify hyperopt results are accessible
- Check trial persistence stage logs

**Best trial not selected:**
- Verify trials were persisted successfully
- Check that at least one trial completed successfully
- Review trial rejection reasons

**Optimized backtest fails:**
- Verify best trial parameters are valid
- Check that config generation succeeded
- Ensure data is available for optimized backtest

**Comparison not available:**
- Verify both baseline and optimized backtests completed
- Check that decision evaluation succeeded
- Review comparison stage logs

### Debugging

1. Check pipeline status: `GET /api/optimization/runs/{optimization_run_id}/status`
2. Review stage results in run detail
3. Check trial list for trial status and rejection reasons
4. Review comparison for detailed metrics
5. Check logs for specific error messages

### Logs and Artifacts

Pipeline artifacts are stored in:
- `artifacts/runs/{optimization_run_id}/optimization/` - Optimization-specific artifacts
- `artifacts/runs/{optimization_run_id}/optimized_params/` - Optimized parameters
- `artifacts/runs/{optimization_run_id}/raw_freqtrade/hyperopt_results/` - Raw hyperopt outputs
- `artifacts/runs/{optimized_run_id}/raw_freqtrade/backtest_results/` - Raw backtest outputs
- `artifacts/runs/{optimized_run_id}/normalized/` - Normalized results
- `artifacts/runs/{optimized_run_id}/decisions/` - Decision results
