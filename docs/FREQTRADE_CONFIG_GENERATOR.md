# Freqtrade Config Generator

## Overview

The Freqtrade Config Generator creates safe Freqtrade configuration files for backtesting only. It ensures that generated configs never contain exchange API keys, secrets, or live trading settings.

## Config Purpose

Generated configs are used exclusively for:
- Backtesting strategies against historical data
- Validating strategy performance
- Testing strategy logic without financial risk
- Smoke testing Freqtrade integration

Configs are **never** used for:
- Live trading
- Dry-run bot loops
- Exchange order execution
- Production deployments

## Generated Config Path

Configs are written to:

```
freqtrade_workspace/config/runs/{run_id}.backtest.json
```

Each run gets its own isolated config file, enabling:
- Parallel backtesting without conflicts
- Config artifact tracking per run
- Historical config inspection
- Debugging specific run configurations

## Safe Fields

The following fields are included in generated configs:

### Trading Settings
- `max_open_trades` - Maximum concurrent trades (default: 3)
- `stake_currency` - Currency for trading (default: USDT)
- `stake_amount` - Amount to stake (default: "unlimited")
- `dry_run` - Always set to `true`
- `dry_run_wallet` - Simulated wallet balance (default: 10000)
- `cancel_open_orders_on_exit` - Clean up on exit (default: true)
- `trading_mode` - Trading mode: spot, futures, or margin (default: spot)

### Strategy Settings
- `strategy` - Strategy class name
- `timeframe` - Candle timeframe (e.g., 1h, 5m)
- `timerange` - Optional backtest timerange (e.g., 20240101-20240131)

### Exchange Settings
- `exchange.name` - Exchange name (e.g., binance)
- `exchange.key` - Always empty string
- `exchange.secret` - Always empty string
- `exchange.pair_whitelist` - Trading pairs
- `exchange.pair_blacklist` - Always empty array

### Data Settings
- `pairlists` - Static pair list configuration
- `dataformat_ohlcv` - OHLCV data format (default: feather)
- `user_data_dir` - Freqtrade user data directory path

## Forbidden Fields

The following fields are **never** included in generated configs:

- Exchange API keys (`exchange.key` is always empty)
- Exchange API secrets (`exchange.secret` is always empty)
- Telegram tokens (`telegram.token` is never set)
- Real API server credentials. `api_server.jwt_secret_key` uses a fixed disabled-API placeholder only because current Freqtrade schema requires a minimum-length value even when the API server is disabled.
- Any secret-like values in additional config
- Live trading settings
- `dry_run = false` (always enforced to `true`)

## No Secrets Rule

**Critical:** The config generator enforces a strict no-secrets policy:

1. **Never reads secrets from `.env`** - Configs are generated without accessing environment variables
2. **Never accepts secrets in requests** - Request validation rejects secret-like keys
3. **Validates output** - Generated configs are validated before writing
4. **Sanitizes responses** - API responses redact any secret-like values
5. **Uses only non-credential placeholders where Freqtrade requires one** - The disabled API server JWT placeholder is not read from `.env`, is not a real secret, and is redacted from API responses.

### Secret Markers

Keys containing these markers are rejected:
- `api_key` / `apikey`
- `secret`
- `password`
- `token`
- `private_key`
- `app_secret`
- `discord_token`
- `exchange_key`
- `jwt_secret_key`

## Dry Run True Rule

**Critical:** `dry_run` is always set to `true` and cannot be overridden:

```python
config["dry_run"] = True  # Hardcoded, never from request
```

This ensures:
- No real money can be traded
- No exchange orders can be placed
- Backtesting is isolated from live markets
- Strategy testing is safe

## Pair Whitelist Rule

Pairs must be provided in the request and are included in the config:

```python
"exchange": {
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": []
}
```

Validation rules:
- Pairs list must not be empty
- Pairs must be valid trading pair format (e.g., BTC/USDT)
- Pair blacklist is always empty (no filtering in backtesting)

## How Config Is Used by Backtesting

When a run reaches the backtesting stage:

1. Config generator creates `freqtrade_workspace/config/runs/{run_id}.backtest.json`
2. Config is registered as an artifact for traceability
3. Freqtrade command runner executes:
   ```bash
   freqtrade backtesting --config freqtrade_workspace/config/runs/{run_id}.backtest.json
   ```
4. Backtest results are captured as artifacts
5. Config file remains available for inspection

## Request Schema

### FreqtradeBacktestConfigRequest

```python
{
    "run_id": "uuid",                    # Required
    "exchange": "binance",               # Default from settings
    "trading_mode": "spot",              # Default: spot
    "stake_currency": "USDT",            # Default: USDT
    "stake_amount": "unlimited",         # Default: unlimited
    "dry_run_wallet": 10000.0,           # Default: 10000
    "max_open_trades": 3,                # Default: 3
    "pairs": ["BTC/USDT", "ETH/USDT"],  # Required, non-empty
    "timeframe": "1h",                   # Required, non-empty
    "timerange": "20240101-20240131",   # Optional
    "strategy_name": "MyStrategy",       # Required, safe class-name style
    "data_format_ohlcv": "feather",      # Default: feather
    "cancel_open_orders_on_exit": true,  # Default: true
    "additional_safe_config": {}          # Optional, no secrets allowed
}
```

### Validation Rules

- `pairs` must not be empty
- `strategy_name` must be alphanumeric with underscores/hyphens only
- `timeframe` must not be empty
- `trading_mode` must be one of: spot, futures, margin
- `additional_safe_config` must not contain secret-like keys

## Response Schema

### FreqtradeBacktestConfigResult

```python
{
    "run_id": "uuid",
    "config_path": "freqtrade_workspace/config/runs/{run_id}.backtest.json",
    "config": { /* sanitized config */ },
    "artifact_id": "uuid",
    "success": true,
    "error": null
}
```

## Example Config

```json
{
  "max_open_trades": 3,
  "stake_currency": "USDT",
  "stake_amount": "unlimited",
  "dry_run": true,
  "dry_run_wallet": 10000.0,
  "cancel_open_orders_on_exit": true,
  "trading_mode": "spot",
  "timeframe": "1h",
  "timerange": "20240101-20240131",
  "exchange": {
    "name": "binance",
    "key": "",
    "secret": "",
    "pair_whitelist": ["BTC/USDT", "ETH/USDT"],
    "pair_blacklist": []
  },
  "pairlists": [
    {
      "method": "StaticPairList"
    }
  ],
  "dataformat_ohlcv": "feather",
  "user_data_dir": "./freqtrade_workspace/user_data",
  "strategy": "MyStrategy"
}
```

## Artifact Registration

Each generated config is registered as an artifact:

- `artifact_type`: `freqtrade_config`
- `file_path`: Generated config path
- `run_id`: Associated run ID
- `description`: "Freqtrade backtest configuration"

This enables:
- Config traceability per run
- Config inspection via artifacts API
- Config download for debugging
- Config history for analysis

## Example Config Files

Two example config files are provided:

1. **config.backtest.example.json** - Full example with all backtest settings
2. **smoke.backtest.example.json** - Minimal example for smoke testing

Both examples:
- Have empty exchange keys and secrets
- Set `dry_run: true`
- Use safe placeholder values
- Can be used as templates for custom configs

## Security Considerations

1. **No secret storage** - Configs never contain real credentials
2. **No secret reading** - Generator never reads from `.env` or environment
3. **Validation at multiple layers** - Request, generation, and output validation
4. **Audit trail** - All config generation is logged and audited
5. **Artifact tracking** - Configs are tracked as artifacts for accountability

## Testing

The config generator is comprehensively tested in `backend/tests/test_freqtrade_config_generator.py`:

- Valid config generated correctly
- File written to expected path
- Pairs included in config
- Strategy included in config
- dry_run is always true
- Exchange key/secret are empty
- No secret-like values present
- Artifact registered correctly
- Invalid empty pairs rejected
- Unsafe strategy name rejected
- Invalid trading mode rejected
- Secrets in additional config rejected
