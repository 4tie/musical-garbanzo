# Hyperopt Safety Policy

## Overview

This document defines the safety policy for Freqtrade Hyperopt execution in HER Part 08. The policy ensures that hyperopt optimization is conducted safely without risking live trading, data exposure, or system compromise.

## Allowed Commands

HER allows only the following Freqtrade hyperopt-related commands:

- `freqtrade hyperopt` - Run hyperopt optimization
- `freqtrade hyperopt-list` - List hyperopt results
- `freqtrade hyperopt-show` - Show specific hyperopt result details

These commands are added to the Part 08 allowlist in addition to the Part 04 commands:
- `create-userdir`
- `show-config`
- `list-strategies`
- `list-data`
- `download-data`
- `backtesting`

## Forbidden Commands

HER explicitly blocks the following Freqtrade commands:

- `freqtrade trade` - Live trading execution
- `freqtrade webserver` - Web server (could enable live trading)
- `freqtrade edge` - Edge command (could enable live trading)
- `freqtrade install-ui` - UI installation (could enable webserver)

Additionally, the command runner blocks:
- Shell operators (`&&`, `;`, `|`, `>`, `<`, `` ` ``, `$()`)
- Environment dump commands (`env`, `printenv`, `set`, `export`)
- Live intent markers (`live`, `order`, `orders`, `forcebuy`, `force-buy`, `forcesell`, `force-sell`, `cancel-open-orders`)
- Secret markers in commands (`token`, `secret`, `password`, `api_key`, `private_key`, etc.)

## Confirmation Rules

### User Confirmation Required

User confirmation is required before the following operations:

1. **Hyperopt Execution** - `user_confirmed=True` must be set before running hyperopt
2. **Data Download** - Both `download_missing_data=True` and `user_confirmed=True` must be set before downloading market data
3. **Optimized Backtest** - `user_confirmed=True` must be set before running the optimized backtest with best parameters

If `user_confirmed=False`, the service layer must stop before execution and return a controlled failure with clear messaging.

### Controlled Failure Messaging

When confirmation is required but not provided, return:
- Status: `confirmation_required`
- Error message: Clear explanation of what requires confirmation
- Next actions: Instructions for user to enable confirmation

## Max Epochs

### Default Epochs by Risk Profile

- **Conservative**: 25 epochs
- **Balanced**: 50 epochs
- **Aggressive**: 100 epochs

### Maximum Epochs by Risk Profile

- **Conservative**: 100 epochs
- **Balanced**: 200 epochs
- **Aggressive**: 300 epochs

### Epoch Validation

- Requests exceeding `max_epochs` are capped to the policy maximum
- A warning is issued when epochs are capped
- Policy validation occurs before hyperopt execution

## Allowed Spaces

### Default Allowed Spaces

By default, only the following spaces are allowed for optimization:

- `buy` - Buy signal parameters
- `sell` - Sell signal parameters

### Locked Spaces

The following spaces are locked by default and cannot be optimized without explicit policy override:

- `roi` - ROI table optimization
- `stoploss` - Stoploss optimization
- `trailing` - Trailing stop optimization
- `protection` - Protection mechanisms

### Space Validation

- Requests for locked spaces are rejected with a warning
- Locked spaces are removed from the normalized spaces list
- If no valid spaces remain, defaults to `["buy", "sell"]`

### Space Override

To enable locked spaces, the policy must be explicitly configured:

```python
policy.allow_roi_optimization = True
policy.allow_stoploss_optimization = True
policy.allow_trailing_optimization = True
```

## Minimum Trade Thresholds

### Base Thresholds by Risk Profile

- **Conservative**: 50 trades minimum
- **Balanced**: 30 trades minimum
- **Aggressive**: 20 trades minimum

### Timeframe Adjustments

Minimum trade thresholds are adjusted based on timeframe (shorter timeframes require more trades):

| Timeframe | Multiplier |
|-----------|------------|
| 1m        | 2.0x       |
| 3m        | 1.5x       |
| 5m        | 1.2x       |
| 15m       | 1.0x       |
| 30m       | 0.9x       |
| 1h        | 0.8x       |
| 2h        | 0.7x       |
| 4h        | 0.6x       |
| 6h        | 0.5x       |
| 12h       | 0.4x       |
| 1d        | 0.3x       |

### Minimum Guarantee

Regardless of risk profile and timeframe, the minimum trade threshold is never less than 10 trades.

### Zero Trade Policy

- `stop_on_zero_trades=True` by default
- Hyperopt runs that produce zero trades are considered invalid evidence
- Such trials are marked as failed and excluded from best trial selection

## Timeout Configuration

### Default Timeouts by Risk Profile

- **Conservative**: 1800 seconds (30 minutes)
- **Balanced**: 3600 seconds (1 hour)
- **Aggressive**: 7200 seconds (2 hours)

### Timeout Behavior

- Commands exceeding timeout are terminated
- Result marked as `timed_out=True`
- Partial output is captured if available
- Service layer handles timeout as controlled failure

## Max Optimized Parameters

### Default Limits

- **Conservative**: 4 parameters maximum
- **Balanced**: 6 parameters maximum
- **Aggressive**: 8 parameters maximum

### Parameter Count Detection

Parameter count detection is based on the hyperopt space definition:
- Each optimized parameter in the strategy counts toward the limit
- Nested or complex parameters may be counted as one
- Policy validation warns if parameter count appears to exceed limit

## Command Safety

### Command Construction

Hyperopt commands are constructed with only safe arguments:

```bash
freqtrade hyperopt \
  --config <config_path> \
  --strategy <strategy_name> \
  --spaces <spaces> \
  --epochs <epochs>
```

### Excluded Parameters

The following are NEVER included in hyperopt commands:

- `--dry-run` (not used by hyperopt)
- Live trading parameters
- Exchange API keys
- Position sizing parameters
- Leverage parameters
- Futures parameters

### Command Logging

The following metadata is logged for each hyperopt execution:

- Executable path
- Config path
- Strategy name
- Spaces
- Epochs
- Run ID
- Working directory
- Exit code
- Duration
- Stdout artifact path
- Stderr artifact path

### Secret Redaction

Secrets are NEVER logged:
- API keys are redacted from command args
- Secrets are redacted from stdout/stderr
- Config file secrets are not extracted
- Environment variables are not logged

## Why Hyperopt Result is Not Final Proof

Hyperopt results are not considered final proof of strategy effectiveness for several reasons:

### 1. Overfitting Risk

Hyperopt optimizes parameters for historical data, which can lead to:
- Curve fitting to specific historical patterns
- Poor performance on unseen data
- Over-optimization for noise rather than signal

### 2. Single Data Set

Hyperopt uses a single historical dataset:
- No walk-forward analysis
- No out-of-sample validation
- No cross-validation across time periods

### 3. Limited Scope

Hyperopt optimizes only what it's told to optimize:
- May miss important parameters
- May optimize local optima
- May not consider parameter interactions

### 4. Backtest vs Reality

Backtest results differ from live trading:
- No slippage in backtest
- No latency in backtest
- No market impact in backtest
- No emotional factors in backtest

## Why Optimized Backtest Must Run After Best Params

An optimized backtest with the best hyperopt parameters is required because:

### 1. Validation

- Confirms the hyperopt result is reproducible
- Validates parameters work correctly
- Ensures no hyperopt-specific artifacts

### 2. Full Metrics

- Hyperopt may use simplified objective function
- Optimized backtest provides full metrics suite
- Enables decision engine evaluation

### 3. Baseline Comparison

- Provides comparable metrics to baseline
- Enables meaningful improvement assessment
- Supports decision classification

### 4. Evidence Quality

- Creates separate artifact for optimized result
- Enables independent analysis
- Supports audit trail

### 5. Safety

- Isolates hyperopt from production backtest
- Enables separate risk assessment
- Provides controlled validation step

## Policy Enforcement

### Service Layer

The `HyperoptPolicyService` enforces policy at the service layer:

1. Validates request against policy
2. Normalizes spaces according to policy
3. Issues warnings for policy violations
4. Caps epochs to policy maximum
5. Adjusts min trades based on timeframe

### Command Runner Layer

The `FreqtradeCommandRunner` enforces safety at the command layer:

1. Validates command against allowlist
2. Blocks forbidden commands
3. Redacts secrets from logs
4. Enforces timeout limits
5. Captures stdout/stderr safely

### Hyperopt Runner Layer

The `FreqtradeHyperoptRunner` enforces safety at the execution layer:

1. Constructs only safe command arguments
2. Never includes live trading parameters
3. Logs metadata without secrets
4. Captures artifacts safely
5. Handles timeouts gracefully

## Policy Summary

### Conservative Policy

- Max epochs: 100
- Default epochs: 25
- Allowed spaces: buy, sell
- Locked spaces: roi, stoploss, trailing, protection
- Max parameters: 4
- Timeout: 30 minutes
- Min trades: 50+ (timeframe-adjusted)
- ROI/stoploss/trailing: Disabled

### Balanced Policy

- Max epochs: 200
- Default epochs: 50
- Allowed spaces: buy, sell
- Locked spaces: roi, stoploss, trailing, protection
- Max parameters: 6
- Timeout: 1 hour
- Min trades: 30+ (timeframe-adjusted)
- ROI/stoploss/trailing: Disabled

### Aggressive Policy

- Max epochs: 300
- Default epochs: 100
- Allowed spaces: buy, sell
- Locked spaces: roi, stoploss, trailing, protection
- Max parameters: 8
- Timeout: 2 hours
- Min trades: 20+ (timeframe-adjusted)
- ROI/stoploss/trailing: Disabled

## Safety Checklist

Before hyperopt execution, verify:

- [ ] User has confirmed execution (`user_confirmed=True`)
- [ ] Epochs are within policy limits
- [ ] Spaces are allowed and not locked
- [ ] Strategy exists in Freqtrade workspace
- [ ] Config file is safe (no secrets, no live trading)
- [ ] Market data is available or download is confirmed
- [ ] Timeout is set appropriately
- [ ] Working directory is correct
- [ ] Command runner allowlist includes hyperopt
- [ ] Secrets are redacted from logs
- [ ] Artifact capture is configured

## References

- Part 08 Optimization Pipeline Plan
- Freqtrade Hyperopt Documentation
- HER Security Guidelines
- HER Command Safety Policy
