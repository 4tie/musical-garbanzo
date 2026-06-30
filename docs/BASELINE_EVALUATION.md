# Baseline Evaluation CLI

## Purpose

The baseline evaluation CLI provides a safe command-line way to run the complete Part 07 baseline pipeline with a real strategy, real data, real backtest, real parser, and real decision.

This tool evaluates existing Freqtrade strategies through a controlled pipeline that:
- Validates the strategy exists and is safe
- Generates a backtest-only Freqtrade config
- Checks local market data availability
- Downloads missing data only when explicitly allowed
- Runs a real Freqtrade backtest only when confirmed
- Parses the captured backtest result
- Evaluates the parsed evidence with deterministic decision gates
- Saves stage progress and final report artifacts

## Request Fields

The CLI accepts the following arguments:

### Required Arguments

- `--strategy` - Existing Freqtrade strategy name (e.g., `HERSmokeStrategy`)
- `--pair` - Trading pair (can be repeated, e.g., `--pair BTC/USDT --pair ETH/USDT`)
- `--timeframe` - Freqtrade timeframe (e.g., `5m`, `1h`, `4h`)

### Optional Arguments

- `--exchange` - Exchange name (default: `binance`)
- `--days` - Historical days to evaluate (default: `30`)
- `--timerange` - Optional Freqtrade timerange (e.g., `20240101-20241231`)
- `--risk-profile` - Decision risk profile (default: `balanced`, choices: `conservative`, `balanced`, `aggressive`)
- `--stake-currency` - Stake currency (default: `USDT`)
- `--stake-amount` - Stake amount (default: `unlimited`)
- `--max-open-trades` - Maximum open trades (default: `3`)
- `--notes` - Optional user notes

### Confirmation Flags

- `--download-missing-data` - Allow downloading missing market data (requires `--user-confirmed`)
- `--user-confirmed` - User has confirmed real execution (required for backtest and data download)
- `--apply-decision-to-run` - Apply decision classification to run (default: `True`)

## CLI Command

### Basic Example

```bash
python scripts/run-baseline-evaluation.py \
  --strategy HERSmokeStrategy \
  --pair BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --risk-profile balanced
```

### Full Example with Confirmation

```bash
python scripts/run-baseline-evaluation.py \
  --strategy HERSmokeStrategy \
  --pair BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --risk-profile balanced \
  --download-missing-data \
  --user-confirmed \
  --apply-decision-to-run
```

### Multiple Pairs

```bash
python scripts/run-baseline-evaluation.py \
  --strategy HERSmokeStrategy \
  --pair BTC/USDT \
  --pair ETH/USDT \
  --pair BNB/USDT \
  --timeframe 5m \
  --days 30 \
  --risk-profile balanced \
  --user-confirmed
```

## Expected Smoke Result

When running with the smoke strategy (`HERSmokeStrategy`), the expected result is:

- **Pipeline completes** - All 10 stages execute successfully
- **Classification is `rejected`** - The smoke strategy is designed to fail decision gates
- **Final marker**: `REAL_BASELINE_EVALUATION_PASSED`

Note: `REAL_BASELINE_EVALUATION_PASSED` indicates the pipeline completed successfully, not that the strategy was approved. Strategy rejection is a valid and expected outcome for the smoke strategy.

## Pipeline Stage List

The baseline evaluation pipeline consists of 10 stages:

1. **run_setup** - Create HER run and initialize baseline stages
2. **strategy_validation** - Validate strategy exists and is safe to use
3. **config_generation** - Generate backtest-only Freqtrade config
4. **data_check** - Check local market data availability
5. **data_download** - Download missing market data (if allowed and confirmed)
6. **baseline_backtest** - Run real Freqtrade backtest (if confirmed)
7. **result_parsing** - Parse captured backtest result
8. **decision_evaluation** - Evaluate parsed evidence with decision gates
9. **baseline_report** - Generate baseline evaluation report
10. **completion** - Mark pipeline as completed

## Pipeline Success vs Strategy Rejection

It's important to distinguish between:

- **Pipeline success** - All stages completed without errors
- **Strategy rejection** - The decision gates determined the strategy is not viable

A pipeline can complete successfully (status: `completed`) while the strategy is rejected (classification: `rejected`). This is the expected and correct behavior for strategies that don't meet the decision criteria.

The final marker `REAL_BASELINE_EVALUATION_PASSED` indicates pipeline success, not strategy approval.

## Artifact Paths

The pipeline generates the following artifacts:

- **Backtest config** - `artifacts/runs/{run_id}/config.json`
- **Backtest results** - `artifacts/runs/{run_id}/backtest_results.json`
- **Parsed metrics** - `artifacts/runs/{run_id}/metrics.json`
- **Decision report** - `artifacts/runs/{run_id}/decision_report.md`
- **Baseline report** - `artifacts/runs/{run_id}/baseline_report.md`

All artifact paths are project-relative and stored in the `artifacts/runs/` directory.

## Safety Rules

The CLI script follows strict safety rules:

### What the Script Does NOT Do

- Does not call Ollama
- Does not send Discord messages
- Does not approve strategies
- Does not export strategies
- Does not start live trading
- Does not start dry-run trading bot loops
- Does not create fake metrics
- Does not create fake backtest output
- Does not directly run unsafe Freqtrade commands

### What the Script Does

- Only runs real Freqtrade backtesting through `BaselineEvaluationService`
- Only runs backtest when `--user-confirmed` is present
- Only downloads data when both `--download-missing-data` and `--user-confirmed` are present
- Uses controlled failure handling with specific error codes
- Returns frontend-ready structured results
- Logs all stage progress with timestamps

## Output Format

The script prints a structured result including:

```
================================================================================
BASELINE EVALUATION RESULT
================================================================================
Run ID: {run_id}
Strategy: {strategy_name}
Pairs: {pairs}
Timeframe: {timeframe}
Exchange: {exchange}
Risk Profile: {risk_profile}
Status: {status}
Classification: {classification}
Confidence Score: {confidence_score}

Key Metrics:
  Trade Count: {trade_count}
  Profit Factor: {profit_factor}
  Expectancy: {expectancy}
  Max Drawdown: {max_drawdown}

Quality Flags:
  - {flag}

Artifacts:
  - {path}

Stage Summary:
  ✓ {stage_name}: {status}
      {message}

Warnings:
  - {warning}

Errors:
  - {error}

Next Actions:
  - {action}
================================================================================

REAL_BASELINE_EVALUATION_PASSED
================================================================================
```

## Exit Codes

The script returns the following exit codes:

- `0` - Pipeline completed successfully
- `1` - Confirmation required (add `--user-confirmed` to proceed)
- `2` - Controlled failure (retryable error)
- `3` - Other status
- `4` - System failure (unexpected error)

## Troubleshooting

### Confirmation Required

If you see `REAL_BASELINE_EVALUATION_CONFIRMATION_REQUIRED`, add the `--user-confirmed` flag:

```bash
python scripts/run-baseline-evaluation.py \
  --strategy HERSmokeStrategy \
  --pair BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --user-confirmed
```

### Data Download Required

If data is missing and you want to download it, add both flags:

```bash
python scripts/run-baseline-evaluation.py \
  --strategy HERSmokeStrategy \
  --pair BTC/USDT \
  --timeframe 5m \
  --days 30 \
  --download-missing-data \
  --user-confirmed
```

### Strategy Not Found

If the strategy is not found, ensure:
- The strategy exists in your Freqtrade user_data/strategies directory
- The strategy name matches exactly (case-sensitive)
- The strategy is a valid Freqtrade strategy file

### Backtest Failed

If the backtest fails, check:
- The strategy is valid and can be loaded by Freqtrade
- Data is available for the specified pairs and timeframe
- The Freqtrade config is valid
- Check the stage results for specific error codes

### Decision Rejection

If the strategy is rejected, this is expected behavior for strategies that don't meet the decision criteria. Review:
- The decision report artifact
- The quality flags
- The metrics to understand why the strategy was rejected

## Integration with API

The CLI script uses the same `BaselineEvaluationService` as the API endpoints. The results are identical whether you use the CLI or the API.

- API: `POST /api/baseline/evaluate`
- CLI: `python scripts/run-baseline-evaluation.py`

Both use the same request schema, service logic, and result format.
