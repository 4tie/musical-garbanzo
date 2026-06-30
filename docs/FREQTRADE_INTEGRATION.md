# Freqtrade Integration

This document describes the HER Part 04 Freqtrade integration boundary. Part 04 connects HER to a local Freqtrade installation for safe detection, workspace validation, config generation, data checks, and controlled backtesting later in the part.

## Freqtrade Paths

HER reads Freqtrade settings from environment variables:

| Setting | Default |
| --- | --- |
| `FREQTRADE_PATH` | empty |
| `FREQTRADE_USER_DATA_DIR` | `./freqtrade_workspace/user_data` |
| `FREQTRADE_CONFIG_DIR` | `./freqtrade_workspace/config` |
| `FREQTRADE_DEFAULT_CONFIG` | `./freqtrade_workspace/config/config.generated.json` |
| `FREQTRADE_DEFAULT_EXCHANGE` | `binance` |
| `FREQTRADE_DEFAULT_TRADING_MODE` | `spot` |
| `FREQTRADE_DEFAULT_STAKE_CURRENCY` | `USDT` |
| `FREQTRADE_DEFAULT_TIMEFRAME` | `5m` |
| `FREQTRADE_REAL_SMOKE_ENABLED` | `false` |

Runtime outputs must remain local and uncommitted.

## Workspace Structure

HER expects this local workspace:

```text
freqtrade_workspace/
├── config/
│   ├── config.backtest.example.json
│   ├── config.dryrun.example.json
│   └── config.generated.example.json
└── user_data/
    ├── strategies/
    ├── data/
    ├── backtest_results/
    ├── hyperopt_results/
    ├── hyperopts/
    ├── plot/
    └── logs/
```

The workspace service may create missing directories. It never deletes user data, erases downloaded market data, or overwrites strategy files.

## Detection Behavior

HER detects Freqtrade in this order:

1. If `FREQTRADE_PATH` is set, HER uses that value.
2. If `FREQTRADE_PATH` is empty, HER tries to resolve `freqtrade` from PATH.
3. Detection may run only `freqtrade --version`.
4. Missing or failing Freqtrade returns a controlled status with user action required.

Detection does not run backtests, download data, import strategy logic, start a bot loop, or expose secrets.

## Setting FREQTRADE_PATH

If Freqtrade is installed outside PATH, set the executable path in `.env`:

```bash
FREQTRADE_PATH=/usr/local/bin/freqtrade
```

If Freqtrade is available in PATH, either leave `FREQTRADE_PATH` empty or set:

```bash
FREQTRADE_PATH=freqtrade
```

Check detection safely:

```bash
source .venv/bin/activate
python scripts/test-freqtrade.py
```

## Allowed Commands

Part 04 allows only these command forms:

- `freqtrade --version`
- `freqtrade create-userdir`
- `freqtrade show-config`
- `freqtrade list-strategies`
- `freqtrade list-data`
- `freqtrade download-data`
- `freqtrade backtesting`

Prompt 2 implements detection and workspace services only. It may run `--version`; it does not run the other commands yet.

## Forbidden Commands

Part 04 forbids:

- `freqtrade trade`
- `freqtrade webserver`
- Any live trading command.
- Any dry-run bot loop.
- Any command that can place exchange orders.
- Any command that modifies exchange state.
- Any command that exposes secrets.
- Any command outside the allowlist.

## Why Live Trading Is Forbidden In Part 04

Part 04 is an integration foundation for safe local validation. It is not a deployment or trading automation phase. Live trading and dry-run bot loops create operational risk, can expose secrets, and do not belong in the backend/database and backtest validation flow being built here.

HER must first prove controlled detection, workspace validation, config generation, data checks, raw artifact capture, and real backtest execution before any future trading-mode discussion.

## Config Generator

HER generates safe Freqtrade backtest configurations using the `FreqtradeConfigGenerator` service.

### Generated Config Path

Configs are written to:
```
freqtrade_workspace/config/runs/{run_id}.backtest.json
```

### Safety Rules

- **Never includes exchange API keys** - `exchange.key` and `exchange.secret` are always empty
- **Never reads secrets from `.env`** - Configs are generated without accessing environment variables
- **Always sets `dry_run: true`** - Hardcoded, cannot be overridden
- **Validates for secret-like keys** - Rejects configs with secret markers in any field
- **Registers as artifact** - Each config is tracked as an artifact for traceability

### Config Schema

Generated configs include:
- Trading settings (max_open_trades, stake_currency, dry_run_wallet)
- Strategy settings (strategy name, timeframe, optional timerange)
- Exchange settings (name, empty key/secret, pair whitelist)
- Data settings (pairlists, dataformat_ohlcv, user_data_dir)

See `docs/FREQTRADE_CONFIG_GENERATOR.md` for detailed documentation.

## Strategy Detection

HER detects and validates Freqtrade strategies using the `FreqtradeStrategyService`.

### Strategy Directory

Strategies are located in:
```
freqtrade_workspace/user_data/strategies/
```

### Detection Methods

HER provides two strategy detection methods:

1. **File scanning** - Lists `.py` files in strategies directory (fallback)
2. **Freqtrade command** - Uses `freqtrade list-strategies` for validated detection

### Safety Rules

- **Only inspects files under strategies directory** - Path validation prevents traversal
- **Does not import arbitrary strategy code** - No code execution in Part 04
- **Prefers Freqtrade list-strategies** - For actual Freqtrade visibility
- **Fallback to file listing** - If Freqtrade not configured, marks `freqtrade_visible=false`
- **No strategy execution** - Strategies are only detected, not run
- **No file modification** - Service only reads, never writes

### Sidecar JSON Detection

For each strategy file (e.g., `MyStrategy.py`):
- Checks for sidecar `MyStrategy.json`
- Missing sidecar generates warning (not fatal)
- Later parts can generate sidecar files

### Validation

- Path validation (must be within strategies directory)
- Name validation (alphanumeric with underscores/hyphens)
- File existence validation
- Freqtrade visibility validation (if Freqtrade configured)

See `docs/FREQTRADE_STRATEGY_INTEGRATION.md` for detailed documentation.

## Data Management

HER checks data availability and downloads missing market data using the `FreqtradeDataService`.

### Data Directory

Candle data is stored in:
```
freqtrade_workspace/user_data/data/
```

### Data Check

HER uses two methods to check data availability:

1. **Freqtrade list-data** - Uses `freqtrade list-data --userdir <user_data>` for accurate detection
2. **Local file discovery** - Scans data directory as fallback

### Data Download

HER can download missing data using `freqtrade download-data`:

- Requires explicit user confirmation (`user_confirmed = true`)
- Requires Freqtrade to be configured
- Requires pairs, timeframes, and either days or timerange
- Never uses `--erase` flag (prevents data deletion)
- Captures stdout/stderr
- Records run logs and audit logs if `run_id` provided

### Safety Rules

- **Never downloads silently** - User confirmation required at validation and runtime
- **Never uses --erase** - Prevents accidental data deletion
- **No fake data** - Only real data from Freqtrade
- **Controlled failure** - Missing Freqtrade returns blocked status
- **Audit trail** - All downloads logged when `run_id` provided

See `docs/FREQTRADE_DATA_MANAGEMENT.md` for detailed documentation.

## Backtest Runner

HER runs controlled Freqtrade backtests using the `FreqtradeBacktestRunner`.

### Backtest Command

HER uses `freqtrade backtesting` with the following command:

```bash
freqtrade backtesting \
  --config <config_path> \
  --userdir <freqtrade_workspace/user_data> \
  --strategy <strategy_name> \
  --timeframe <timeframe> \
  --export trades \
  --backtest-directory <artifacts/runs/{run_id}/raw_freqtrade/backtest_results>
```

Optional arguments:
- `--timerange <timerange>` for specific time range
- `--pairs <pairs>` for specific trading pairs
- `--export <none|trades|signals>` for export type

### Artifact Capture

HER captures backtest outputs:
- Backtest result files (JSON, CSV)
- Stdout/stderr logs
- Config file used

Artifacts are registered with types:
- `backtest_raw` - Raw backtest outputs
- `log_file` - Stdout/stderr logs
- `freqtrade_config` - Config file

### Safety Rules

- **Never runs silently** - User confirmation required at validation and runtime
- **Never uses 'trade' command** - Only 'backtesting' command
- **Never sets dry_run false** - Config ensures dry_run true
- **No metrics parsing** - Raw outputs only, analysis done in later parts
- **No profitability decisions** - Classification done in later parts
- **Audit trail** - All backtests logged with run logs and audit logs

### What Is Not Done Here

- Performance metric parsing (done in later parts)
- Strategy classification (done in later parts)
- Profitability assessment (done in later parts)
- Trade analysis (done in later parts)

See `docs/FREQTRADE_BACKTEST_RUNNER.md` for detailed documentation.

## API Endpoints

HER exposes safe backend API endpoints for Freqtrade operations.

### Read-Only Endpoints

- `GET /api/freqtrade/status` - Get Freqtrade status and configuration
- `GET /api/freqtrade/version` - Get Freqtrade version
- `GET /api/freqtrade/workspace` - Get Freqtrade workspace status
- `GET /api/freqtrade/strategies` - List available strategies
- `GET /api/freqtrade/strategies/{strategy_name}` - Get specific strategy status
- `GET /api/freqtrade/data` - Get data directory overview

### Action Endpoints

- `POST /api/freqtrade/config/backtest` - Generate safe backtest config (does not run backtest)
- `POST /api/freqtrade/data/check` - Check data availability (does not download data)
- `POST /api/freqtrade/data/download` - Run real Freqtrade download-data (requires user confirmation)
- `POST /api/freqtrade/backtest` - Run real Freqtrade backtest (requires user confirmation)

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

### Integration with Part 03 Repositories

When request includes `run_id`:
- Run logs are written to the run log repository
- Audit logs are written to the audit log repository
- Artifacts are registered when config/backtest files are produced

### Mounting

Endpoints are mounted under both:
- `/api/freqtrade/...` (preferred)
- `/api/v1/freqtrade/...` (for compatibility)

See `docs/API_CONTRACTS.md` for detailed API documentation with request/response examples.

## Later Real Smoke Validation

Later in Part 04, HER will add a real smoke validation script. That script will:

- Detect Freqtrade.
- Validate the workspace.
- List strategies.
- Check local data availability.
- Download missing data only with an explicit opt-in flag.
- Generate a safe backtest config.
- Run one controlled real backtest only when prerequisites are met.
- Capture raw artifacts and logs.
- Report unavailable prerequisites without fabricating success.

Unit tests may mock command construction and failures, but final Part 04 readiness requires a real configured Freqtrade smoke validation.
