# Freqtrade Backtest Runner

## Overview

HER runs controlled Freqtrade backtests using the `FreqtradeBacktestRunner`. This service executes backtests, captures raw outputs, and registers artifacts without parsing performance metrics or making profitability decisions.

## Runner Purpose

The backtest runner is responsible for:
- Executing Freqtrade backtest commands safely
- Capturing raw stdout/stderr output
- Discovering and registering backtest artifacts
- Writing logs to persistent storage
- Recording audit entries for traceability
- **Not** parsing performance metrics (done in later parts)
- **Not** classifying strategies (done in later parts)
- **Not** making profitability decisions (done in later parts)

## Exact Command Shape

The backtest runner builds the following command:

```bash
freqtrade backtesting \
  --config <config_path> \
  --userdir <freqtrade_workspace/user_data> \
  --strategy <strategy_name> \
  --timeframe <timeframe> \
  --export trades \
  --backtest-directory <artifacts/runs/{run_id}/raw_freqtrade/backtest_results>
```

### Optional Arguments

If `timerange` is provided:
```bash
--timerange <timerange>
```

If `pairs` are provided:
```bash
--pairs <pair1,pair2,...>
```

If custom `backtest_directory` is provided:
```bash
--backtest-directory <custom_directory>
```

### Export Options

- `none` - No export
- `trades` - Export trades (default)
- `signals` - Export signals

## User Confirmation Rule

**Critical:** HER never runs backtests silently. User confirmation is required:

### Validation Layer

Request schema validation:
```python
user_confirmed: bool = Field(False, description="User must confirm to run real backtest")

@field_validator("user_confirmed")
@classmethod
def validate_user_confirmed(cls, v: bool) -> bool:
    if not v:
        raise ValueError("user_confirmed must be true to run real backtest")
    return v
```

### Runtime Layer

Service runtime check:
```python
if not request.user_confirmed:
    return FreqtradeBacktestResult(
        success=False,
        blocked=True,
        error="User confirmation required",
    )
```

### Why This Rule Exists

1. **Prevent unintended execution** - Backtests can be resource-intensive
2. **Cost awareness** - Users should control when compute resources are used
3. **Transparency** - Users should be aware of all backtest operations
4. **Audit trail** - Explicit confirmation creates clear audit trail
5. **Safety** - Prevents accidental backtest runs

## Artifact Paths

### Backtest Output Directory

```
artifacts/runs/{run_id}/raw_freqtrade/backtest_results/
```

This directory contains:
- `backtest-result.json` - Freqtrade backtest results
- `trades.csv` - Trade history
- Other Freqtrade output files

### Log Files

```
artifacts/runs/{run_id}/raw_freqtrade/
├── stdout.log  # Backtest stdout
└── stderr.log  # Backtest stderr
```

### Artifact Registration

The runner registers artifacts with the following types:
- `backtest_raw` - Raw backtest output files
- `log_file` - Stdout/stderr log files
- `freqtrade_config` - Config file used for backtest

All artifacts are stored with project-relative paths for easy access.

## Result Discovery

The runner discovers backtest outputs by:

1. **Timestamp filtering** - Only includes files created after backtest started
2. **Recursive scanning** - Scans entire backtest directory tree
3. **File metadata** - Captures size and creation time
4. **Error handling** - Skips files that can't be accessed

### Discovery Process

```python
def discover_backtest_outputs(backtest_directory, started_at):
    artifacts = []
    for file_path in backtest_directory.rglob("*"):
        if file_path.is_file():
            file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
            if file_time >= started_at:
                artifacts.append(...)
    return artifacts
```

## What Is Not Parsed Yet

The backtest runner does **not** parse:

### Performance Metrics

- Total profit
- Profit factor
- Sharpe ratio
- Max drawdown
- Win rate
- Average trade duration

These metrics are parsed in later parts by dedicated metric parsers.

### Trade Analysis

- Trade-by-breakdown
- Entry/exit analysis
- Pair performance
- Timeframe performance

These analyses are done in later parts by dedicated analyzers.

### Strategy Classification

- Profitable vs unprofitable
- Risk levels
- Strategy types
- Performance tiers

These classifications are done in later parts by dedicated classifiers.

### Why Not Parse Here?

1. **Separation of concerns** - Execution vs analysis
2. **Flexibility** - Different analysis methods for different needs
3. **Testability** - Easier to test execution separately
4. **Reusability** - Raw outputs can be re-analyzed
5. **Incremental development** - Add analysis features incrementally

## Why Profitability Is Not Decided in Part 04

Profitability decisions are complex and require:

### Multiple Data Points

- Performance metrics
- Risk metrics
- Market conditions
- Strategy parameters
- Historical context

### Statistical Analysis

- Significance testing
- Confidence intervals
- Outlier detection
- Trend analysis

### Domain Expertise

- Trading knowledge
- Risk tolerance
- Market understanding
- Strategy context

### Risk Assessment

- Drawdown analysis
- Volatility metrics
- Correlation analysis
- Stress testing

### Why Defer to Later Parts

1. **Focus on execution** - Part 04 focuses on safe execution
2. **Proper analysis tools** - Later parts have dedicated analyzers
3. **User input** - Later parts can incorporate user preferences
4. **AI integration** - Later parts can use AI for classification
5. **Validation** - Later parts can validate results against benchmarks

## Schemas

### FreqtradeBacktestRequest

```python
{
    "run_id": "uuid",
    "config_path": "/path/to/config.json",
    "strategy_name": "MyStrategy",
    "timeframe": "1h",
    "timerange": "20240101-20240131",  # Optional
    "pairs": ["BTC/USDT", "ETH/USDT"],  # Optional
    "export": "trades",  # none, trades, signals
    "backtest_directory": "/custom/path",  # Optional
    "user_confirmed": true,  # Required
    "timeout_seconds": 1800
}
```

### FreqtradeBacktestResult

```python
{
    "run_id": "uuid",
    "success": true,
    "blocked": false,
    "exit_code": 0,
    "stdout": "Backtest output...",
    "stderr": "",
    "duration_seconds": 45.2,
    "backtest_directory": "/path/to/backtest_results",
    "artifacts": [FreqtradeBacktestArtifact, ...],
    "error": null,
    "errors": [],
    "warnings": []
}
```

### FreqtradeBacktestArtifact

```python
{
    "artifact_type": "backtest_raw",
    "path": "/path/to/artifact",
    "size_bytes": 1024,
    "created_at": "2024-01-01T00:00:00"
}
```

## Validation Rules

### Request Validation

- `run_id` must be provided
- `config_path` must be provided
- `strategy_name` must be valid class-name style (alphanumeric with underscores)
- `timeframe` must be provided
- `export` must be one of: none, trades, signals
- `user_confirmed` must be true

### Runtime Validation

- Freqtrade must be configured
- Strategy must exist
- Config file must exist
- User data directory must exist

## Error Handling

The backtest runner handles errors gracefully:

- **Freqtrade not configured** - Returns blocked status with error
- **Strategy not found** - Returns blocked status with error
- **Data missing** - Returns controlled failure with suggestion to download data
- **Command timeout** - Returns timed out status with partial output
- **File system errors** - Returns error without crashing
- **Artifact registration errors** - Logs error but continues

## Security Considerations

1. **No silent execution** - User confirmation required
2. **No live trading** - Only backtesting mode
3. **No dry_run false** - Config ensures dry_run true
4. **No forbidden commands** - Never uses 'trade' command
5. **Controlled subprocess** - Uses safe command runner
6. **Audit logging** - All backtests logged
7. **Path validation** - Prevents directory traversal attacks

## Logging

### Run Logs

The runner creates run logs for:
- Backtest command started
- Backtest command completed/failed
- Duration information
- Error information

Logs are stored in the database and can be queried via the logs API.

### Audit Logs

The runner creates audit logs for:
- Backtest command execution
- Strategy used
- Timeframe used
- Success/failure status
- Duration

Audit logs provide traceability for all backtest operations.

## Testing

The backtest runner is comprehensively tested in `backend/tests/test_freqtrade_backtest_runner.py`:

- Command construction
- Confirmation required
- Invalid strategy name rejected
- Invalid export rejected
- Backtest directory created
- Artifact registration with sample files
- Missing Freqtrade controlled failure
- Missing strategy controlled failure
- Forbidden command never used
- No metrics classification
- Stdout/stderr log writing
- Backtest success
- Backtest failure
- Logs and audit recorded
- Custom backtest directory
- Default export trades
- Export signals
- Export none

## Future Extensions

Future parts may add:

- Performance metric parsing
- Trade analysis
- Strategy classification
- Profitability assessment
- Risk analysis
- Benchmark comparison
- Multi-strategy backtesting
- Parameter optimization
