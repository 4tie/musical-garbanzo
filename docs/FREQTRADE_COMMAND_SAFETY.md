# Freqtrade Command Safety

## Overview

HER AutoQuant integrates with Freqtrade for backtesting and data management. To ensure safe operation and prevent accidental live trading, all Freqtrade commands are executed through a controlled command runner with strict allowlist validation.

## Why the Command Allowlist Exists

Freqtrade is a powerful trading bot that can execute live trades when configured incorrectly. To prevent accidental financial loss, HER enforces:

1. **Explicit allowlist** - Only specific safe commands are permitted
2. **Forbidden command blocking** - Dangerous commands are rejected before execution
3. **No shell execution** - Commands are executed as subprocess arrays, never shell strings
4. **Secret sanitization** - Tokens, secrets, and passwords are redacted from logs
5. **Timeout enforcement** - Commands cannot run indefinitely
6. **Audit logging** - All command attempts are recorded for traceability

## Allowed Commands (Part 04)

The following Freqtrade subcommands are explicitly allowed for Part 04:

- `create-userdir` - Initialize Freqtrade user data directory structure
- `show-config` - Display current Freqtrade configuration
- `list-strategies` - List available trading strategies
- `list-data` - List available market data files
- `download-data` - Download historical market data for backtesting
- `backtesting` - Run backtests against historical data

### Special Case: Version Check

- `--version` - Allowed as a standalone version check: `freqtrade --version`

## Forbidden Commands

The following commands are explicitly blocked and will never execute:

- `trade` - Live trading command
- `webserver` - Freqtrade web server (could enable live trading)
- `edge` - Edge trading analysis (could enable live trading)
- `install-ui` - UI installation (could enable live trading)
- Any command containing live order execution intent (`live`, `order`, `orders`, `forcebuy`, `forcesell`, `cancel-open-orders`)
- Any command outside the allowlist
- Commands with shell operators (`&&`, `;`, `|`, `>`, `<`, `` ` ``, `$()`)
- Commands attempting to access `.env` files
- Environment dump commands (`env`, `printenv`, `set`, `export`)

## Examples of Allowed Command Arrays

```python
# Version check
["--version"]

# List available data
["list-data", "--userdir", "/path/to/user_data"]

# Download data
["download-data", "--pairs", "BTC/USDT", "--timeframe", "1h", "--days", "30"]

# List strategies
["list-strategies", "--userdir", "/path/to/user_data"]

# Run backtest
["backtesting", "--strategy", "MyStrategy", "--timerange", "20240101-20240131"]
```

## Examples of Blocked Commands

```python
# Live trading - BLOCKED
["trade"]

# Web server - BLOCKED
["webserver"]

# Shell operator - BLOCKED
["list-data", "&&", "cat", ".env"]

# Environment dump - BLOCKED
["list-data", ";", "env"]

# Accessing .env - BLOCKED
["show-config", "--config", ".env"]

# Unknown command - BLOCKED
["hyperopt"]

# Live order intent - BLOCKED
["backtesting", "--live"]
```

## No Shell Execution Rule

**Critical:** The command runner NEVER uses `shell=True`. All commands are executed as subprocess argument arrays:

```python
# SAFE - List arguments, shell=False
subprocess.run(["freqtrade", "list-data"], shell=False, capture_output=True)

# UNSAFE - Never used in HER
subprocess.run("freqtrade list-data", shell=True)
```

This prevents:
- Shell injection attacks
- Command chaining with operators
- Environment variable expansion
- Path traversal via shell metacharacters

## Timeout Behavior

All commands have a default timeout of 300 seconds (5 minutes). If a command exceeds this timeout:

1. The subprocess is terminated
2. The result is marked as `timed_out=True`
3. An error message is returned
4. Logs and audit records are created

Timeouts can be customized per command:

```python
runner.run(["backtesting"], timeout_seconds=600)  # 10 minutes
```

## Secret Sanitization

The command runner automatically redacts secret-like values from:

1. Command arguments (for logs and audit records)
2. stdout output
3. stderr output

### Secret Markers

Values under keys containing these markers are redacted:

- `token`
- `secret`
- `password`
- `api_key` / `api-key` / `apikey`
- `private_key` / `private-key`
- `app_secret_key` / `app-secret-key`
- `discord_bot_token` / `discord-bot-token`

### Sanitization Examples

```python
# Command with API key
["list-data", "--api-key", "super-secret"]
# Logged as: ["list-data", "[REDACTED]", "[REDACTED]"]

# Output with token
"DISCORD_BOT_TOKEN=abc123\n"
# Logged as: "[REDACTED]\n"

# Key/value pattern
"api_key: xyz789\n"
# Logged as: "api_key: [REDACTED]\n"
```

## Audit Logging

Every command execution attempt is recorded in the audit log with:

- Actor: `system`
- Action type: `freqtrade_command_attempt`
- Sanitized command array
- Return code
- Success/failure status
- Blocked status
- Duration
- Sanitized stdout/stderr
- Approval flag (True if not blocked, False if blocked)

## Error Handling

The command runner returns controlled results for all error scenarios:

1. **Freqtrade not configured** - Returns error without attempting execution
2. **Command blocked** - Returns blocked result with validation error
3. **Command timeout** - Returns timed out result with partial output
4. **Execution failure** - Returns failure result with error message
5. **Logging failure** - Command result is still returned (logging is best-effort)

## Testing

The safety layer is comprehensively tested in `backend/tests/test_freqtrade_command_runner.py`:

- Version command allowed
- list-data command allowed
- backtesting command allowed (mocked, no real execution)
- trade command blocked
- webserver command blocked
- unknown command blocked
- shell operator blocked
- timeout handled
- command logs are sanitized
- no shell=True used
- missing Freqtrade returns controlled failure

## Future Extensions

The allowlist can be extended in future parts to include:

- `hyperopt` - Strategy optimization (with additional safeguards)
- `edge` - Edge trading analysis (read-only mode only)
- Additional data management commands

Any new commands must be explicitly added to the allowlist and validated for safety before use.
