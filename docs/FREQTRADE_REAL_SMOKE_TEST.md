# Freqtrade Real Smoke Test

## Overview

The real smoke test validates HER's Freqtrade integration against a real Freqtrade installation, real data download, and real backtesting execution.

## What the Smoke Test Does

The smoke test performs the following steps:

1. **Environment Check**: Verifies Freqtrade executable is available and gets version
2. **Workspace Validation**: Confirms workspace directories and smoke strategy exist
3. **HER Run Creation**: Creates a real HER run record for tracking
4. **Config Generation**: Generates a safe backtest configuration for HERSmokeStrategy
5. **Data Download**: Downloads real candle data from Binance (BTC/USDT, 5m, 30 days)
6. **Data Verification**: Confirms data is available after download
7. **Backtest Execution**: Runs real Freqtrade backtesting with the smoke strategy
8. **Artifact Capture**: Registers config, logs, and backtest outputs as artifacts
9. **Status Update**: Marks the HER run as validated or failed

## What the Smoke Test Does NOT Prove

- **NOT a profitability test**: HERSmokeStrategy is intentionally simple and not profitable
- **NOT a strategy validation**: The strategy is for integration testing only
- **NOT financial advice**: Do not use this strategy for actual trading
- **NOT a complete system test**: Does not validate the full AutoQuant pipeline

## Why HERSmokeStrategy is Not Profitable

HERSmokeStrategy is designed solely for integration testing:

- Uses simple moving average crossover logic
- No risk management beyond basic stop loss
- No position sizing
- No market regime detection
- No feature engineering
- No optimization
- Intentionally naive parameters

**DO NOT use this strategy for live trading.**

## Required Environment Setup

### Prerequisites

1. **Freqtrade Installation**: Install Freqtrade or ensure it's in PATH
   ```bash
   pip install freqtrade
   ```

2. **Environment Variables**: Configure HER settings
   ```bash
   export FREQTRADE_PATH=/path/to/freqtrade  # Optional if in PATH
   export FREQTRADE_USER_DATA_DIR=/path/to/freqtrade_workspace/user_data
   export FREQTRADE_CONFIG_DIR=/path/to/freqtrade_workspace/config
   ```

3. **Workspace Structure**: Ensure the following exists:
   ```
   freqtrade_workspace/
   ├── user_data/
   │   └── strategies/
   │       ├── HERSmokeStrategy.py
   │       └── HERSmokeStrategy.json
   └── config/
       └── runs/
   ```

4. **Database**: HER SQLite database must be initialized

5. **Python Environment**: Activate HER virtual environment
   ```bash
   source .venv/bin/activate
   ```

## Running the Smoke Test

### Command

```bash
python scripts/freqtrade-real-smoke-test.py
```

### Expected Outputs

The script prints a detailed summary:

```
============================================================
  Step A: Environment and Version Check
============================================================
  Freqtrade Configured: Yes
  Executable: /usr/local/bin/freqtrade
  Version: 2024.1

============================================================
  Step B: Workspace Validation
============================================================
  Workspace Valid: True
  Smoke Strategy Path: /path/to/HERSmokeStrategy.py
  Smoke Strategy Exists: True
  Config Directory: /path/to/config
  Config Directory Exists: True

============================================================
  Step C: Create HER Run Record
============================================================
  Run ID: run-123
  Run Name: Real Freqtrade Smoke Test
  Run Status: running

============================================================
  Step D: Generate Smoke Config
============================================================
  Config Path: /path/to/config/runs/run-123.smoke.backtest.json
  Config Generated: True

============================================================
  Step E: Download Real Data
============================================================
  Exchange: binance
  Pair: BTC/USDT
  Timeframe: 5m
  Days: 30
  Data Format: feather
  Download Success: True
  Exit Code: 0

============================================================
  Step F: Verify Data
============================================================
  Data Available: True
  Data Path: /path/to/user_data/data/binance/BTC_USDT-5m-feather

============================================================
  Step G: Run Real Backtest
============================================================
  Strategy: HERSmokeStrategy
  Timeframe: 5m
  Export Type: trades
  Config Path: /path/to/config/runs/run-123.smoke.backtest.json
  Backtest Success: True
  Exit Code: 0
  Duration: 15000ms

============================================================
  Step H: Capture Artifacts
============================================================
  Artifacts Registered: 4
  Final Run Status: validated

============================================================
  Step I: Summary
============================================================
  Run ID: run-123
  Freqtrade Version: 2024.1
  Config Path: /path/to/config/runs/run-123.smoke.backtest.json
  Data Status: Success
  Backtest Exit Code: 0
  Backtest Duration: 15000ms
  Artifact Count: 4
  Final HER Run Status: validated

✓ REAL_SMOKE_PASSED
```

### Exit Codes

- `0`: Smoke test passed
- `1`: Freqtrade not configured
- `2`: Workspace validation failed
- `3`: Data download failed
- `4`: Backtest failed
- `5`: Unexpected error

## Common Failures

### Freqtrade Not Configured

**Error**: `REAL_SMOKE_PENDING: Freqtrade not configured`

**Cause**: Freqtrade executable not found in PATH or FREQTRADE_PATH not set

**Solution**:
- Install Freqtrade: `pip install freqtrade`
- Or set: `export FREQTRADE_PATH=/path/to/freqtrade`

### Workspace Validation Failed

**Error**: Workspace directories not valid or smoke strategy missing

**Cause**: Required directories or files don't exist

**Solution**:
- Create workspace structure
- Ensure HERSmokeStrategy.py exists in user_data/strategies/

### Data Download Failed

**Error**: `REAL_SMOKE_FAILED_DATA_DOWNLOAD`

**Cause**: Network issues, exchange rate limits, or invalid parameters

**Solution**:
- Check internet connection
- Verify Binance API is accessible
- Try reducing `days` parameter in the script

### Backtest Failed

**Error**: Backtest execution failed

**Cause**: Invalid config, strategy errors, or data issues

**Solution**:
- Check backtest logs in artifacts
- Verify strategy syntax
- Ensure data is valid

## Inspecting Artifacts

After the smoke test runs, artifacts are registered in the HER database:

1. **Config Artifact**: The generated Freqtrade config file
2. **Stdout Log**: Freqtrade command stdout
3. **Stderr Log**: Freqtrade command stderr
4. **Backtest Raw Files**: Freqtrade backtest output files

### Viewing Artifacts via API

```bash
# List artifacts for a run
curl http://127.0.0.1:8000/api/runs/{run_id}/artifacts

# Get specific artifact details
curl http://127.0.0.1:8000/api/artifacts/{artifact_id}
```

### Viewing Artifacts via Database

```bash
# Query artifacts table
sqlite3 backend/her.db "SELECT * FROM artifacts WHERE run_id = '{run_id}'"
```

### Viewing Files Directly

```bash
# View config
cat freqtrade_workspace/config/runs/{run_id}.smoke.backtest.json

# View logs
cat artifacts/runs/{run_id}/raw_freqtrade/backtest_results/stdout.log
cat artifacts/runs/{run_id}/raw_freqtrade/backtest_results/stderr.log
```

## Safety Guarantees

The smoke script is designed with strict safety measures:

- **Never runs live trading**: Does not execute `freqtrade trade`
- **Never runs webserver**: Does not execute `freqtrade webserver`
- **No exchange keys**: Does not use any API keys or secrets
- **Always dry run**: Sets `dry_run: true` in config
- **No data destruction**: Never uses `--erase` flag
- **No AI calls**: Does not call Ollama or any AI service
- **No Discord messages**: Does not send any notifications

## Integration with CI/CD

The smoke test can be integrated into CI/CD pipelines:

```yaml
# Example GitHub Actions step
- name: Run Freqtrade Smoke Test
  run: |
    source .venv/bin/activate
    python scripts/freqtrade-real-smoke-test.py
  env:
    FREQTRADE_PATH: /usr/local/bin/freqtrade
```

## Troubleshooting

### Permission Errors

If you encounter permission errors:

```bash
chmod +x scripts/freqtrade-real-smoke-test.py
```

### Module Import Errors

Ensure you're running from the project root:

```bash
cd /home/mohs/Desktop/her
python scripts/freqtrade-real-smoke-test.py
```

### Database Lock Errors

If the database is locked:

```bash
# Stop any running backend server
# Then retry the smoke test
```

## Next Steps After Smoke Test

If the smoke test passes:

1. HER's Freqtrade integration is validated
2. The pipeline can proceed to strategy development
3. Real backtesting can be used for strategy validation

If the smoke test fails:

1. Review the specific failure reason
2. Fix the underlying issue (Freqtrade, workspace, network)
3. Re-run the smoke test
4. Do not proceed with strategy development until integration is validated
