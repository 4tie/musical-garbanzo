# Freqtrade Data Management

## Overview

HER integrates with Freqtrade for market data management, including checking data availability and downloading missing data for backtesting. Data operations are controlled and require explicit user confirmation to prevent unintended downloads.

## Where Candles Are Stored

Freqtrade stores candle (OHLCV) data in the user_data directory:

```
freqtrade_workspace/user_data/data/
├── binance/
│   ├── 1h/
│   │   >>> BTC_USDT.json
│   │   >>> ETH_USDT.json
│   ├── 5m/
│   │   >>> BTC_USDT.json
│   └── 15m/
│       >>> BTC_USDT.json
└── other_exchanges/
```

### File Naming Convention

- Pair format: `BTC/USDT` → `BTC_USDT.json`
- Path pattern: `{data_dir}/{exchange}/{timeframe}/{pair}.json`
- File format: JSON (or feather if configured)

## How list-data Works

HER uses Freqtrade's `list-data` command to check data availability:

```bash
freqtrade list-data --userdir ./freqtrade_workspace/user_data --show-timerange
```

### Command Behavior

- Lists all available data files in the data directory
- Shows timerange information if `--show-timerange` is specified
- Returns structured output with pair, timeframe, and timerange

### Output Format

```
BTC/USDT, 1h, 20240101-20240131
ETH/USDT, 1h, 20240101-20240131
BTC/USDT, 5m, 20240101-20240131
```

### HER Integration

HER parses the output to determine:
- Which pairs have data for the requested timeframe
- Whether data exists for the requested timerange
- Freqtrade visibility status

### Fallback Behavior

If Freqtrade is not configured, HER falls back to local file discovery:
- Scans the data directory for expected file paths
- Checks if files exist at expected locations
- Marks `freqtrade_visible = false`
- Returns controlled status without errors

## How download-data Works

HER uses Freqtrade's `download-data` command to download market data:

```bash
freqtrade download-data \
  --userdir ./freqtrade_workspace/user_data \
  --pairs BTC/USDT,ETH/USDT \
  --timeframes 1h,5m \
  --days 30 \
  --trading-mode spot \
  --data-format-ohlcv feather
```

### Command Components

- `--userdir` - Freqtrade user data directory
- `--config` - Optional config file path
- `--pairs` - Comma-separated list of trading pairs
- `--timeframes` - Comma-separated list of timeframes
- `--days` - Number of days of data to download
- `--timerange` - Specific timerange to download (alternative to days)
- `--trading-mode` - Trading mode: spot, futures, margin
- `--data-format-ohlcv` - Data format: feather, json, etc.

### Download Behavior

1. **Validation** - Checks prerequisites:
   - Freqtrade is configured
   - User has confirmed (`user_confirmed = true`)
   - Pairs are provided
   - Timeframes are provided
   - Either days or timerange is provided

2. **Command Building** - Constructs safe command:
   - Includes all required parameters
   - Never includes `--erase` flag
   - Uses `shell=False` for subprocess execution

3. **Execution** - Runs command via FreqtradeCommandRunner:
   - Captures stdout and stderr
   - Enforces timeout
   - Sanitizes secrets from logs
   - Records run logs if `run_id` provided
   - Records audit logs if `run_id` provided

4. **Result** - Returns structured result:
   - Success/failure status
   - Blocked status
   - Stdout/stderr output
   - Error messages
   - Duration

## User Confirmation Rule

**Critical:** HER never downloads data silently. User confirmation is required:

### Validation Layer

Request schema validation:
```python
user_confirmed: bool = Field(False, description="User must confirm to run real download")

@field_validator("user_confirmed")
@classmethod
def validate_user_confirmed(cls, v: bool) -> bool:
    if not v:
        raise ValueError("user_confirmed must be true to run real download")
    return v
```

### Runtime Layer

Service runtime check:
```python
if not request.user_confirmed:
    return FreqtradeDataDownloadResult(
        success=False,
        blocked=True,
        error="User confirmation required",
    )
```

### Why This Rule Exists

1. **Prevent unintended downloads** - Data downloads can be large and time-consuming
2. **Network usage control** - Users should control when network requests are made
3. **Cost awareness** - Some exchanges have API rate limits or costs
4. **Transparency** - Users should be aware of all external operations
5. **Audit trail** - Explicit confirmation creates clear audit trail

## Why HER Never Downloads Silently

HER enforces explicit download confirmation for several reasons:

### 1. Network Usage

- Data downloads can be hundreds of megabytes
- Uncontrolled downloads can impact network performance
- Users should control bandwidth usage

### 2. API Rate Limits

- Exchanges have API rate limits
- Uncontrolled downloads can hit limits
- Rate limit violations can affect future operations

### 3. Cost Considerations

- Some exchanges charge for API access
- Uncontrolled downloads can incur unexpected costs
- Users should control cost-generating operations

### 4. Data Freshness

- Users may want to control when data is refreshed
- Automated downloads may not align with user needs
- Explicit confirmation ensures intentional updates

### 5. Security and Privacy

- Download operations may expose usage patterns
- Users should control when external requests are made
- Explicit confirmation provides security control

## Why HER Never Uses --erase

**Critical:** HER never uses the `--erase` flag in Part 04:

### What --erase Does

The `--erase` flag tells Freqtrade to delete existing data before downloading:
```bash
freqtrade download-data --erase --pairs BTC/USDT --days 30
```

This can delete large amounts of data without confirmation.

### Why HER Avoids It

1. **Data loss risk** - Accidental data deletion can lose valuable historical data
2. **Time cost** - Re-downloading deleted data can be time-consuming
3. **No user benefit** - HER doesn't need to erase data for backtesting
4. **Safety principle** - Better to keep existing data than risk deletion
5. **Future flexibility** - Existing data may be useful for other analyses

### HER's Approach

HER uses incremental downloads:
- Downloads only missing data
- Preserves existing data
- Allows users to manage data manually if needed
- Provides clear audit trail of all operations

## How Missing Data Is Reported

HER reports missing data in a structured way:

### Check Result Schema

```python
{
    "run_id": "uuid",
    "exchange": "binance",
    "trading_mode": "spot",
    "pairs": [
        {
            "pair": "BTC/USDT",
            "timeframe": "1h",
            "exists": true,
            "file_path": "/path/to/data.json",
            "timerange": "20240101-20240131",
            "errors": [],
            "warnings": []
        },
        {
            "pair": "ETH/USDT",
            "timeframe": "1h",
            "exists": false,
            "file_path": null,
            "timerange": null,
            "errors": [],
            "warnings": []
        }
    ],
    "freqtrade_visible": true,
    "source": "freqtrade",
    "errors": [],
    "warnings": []
}
```

### Missing Data Handling

- **Not treated as failure** - Missing data is informational, not an error
- **Controlled status** - Returns clear `exists = false` flag
- **Actionable** - Users can decide whether to download missing data
- **Non-blocking** - Missing data doesn't prevent other operations

### Reporting Levels

1. **Pair level** - Each pair has its own status
2. **Timeframe level** - Status is per pair/timeframe combination
3. **Overall level** - Result has overall success/failure status

## Data Check Methods

### Freqtrade list-data (Preferred)

Uses Freqtrade command for accurate data detection:
- Validates data integrity
- Shows timerange information
- Requires Freqtrade to be configured
- Marked as `source = "freqtrade"`, `freqtrade_visible = true`

### Local File Discovery (Fallback)

Scans data directory for file existence:
- Works without Freqtrade
- Checks file paths only
- Does not validate data integrity
- Marked as `source = "file"`, `freqtrade_visible = false`

### Detection Priority

1. If Freqtrade is configured: Use `list-data`
2. If Freqtrade fails: Fall back to local file discovery
3. Always return controlled status

## Schemas

### FreqtradeDataCheckRequest

```python
{
    "run_id": "uuid",  # Optional
    "config_path": "/path/to/config.json",  # Optional
    "exchange": "binance",
    "trading_mode": "spot",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframe": "1h",
    "timerange": "20240101-20240131",  # Optional
    "show_timerange": true
}
```

### FreqtradeDataCheckResult

```python
{
    "run_id": "uuid",
    "exchange": "binance",
    "trading_mode": "spot",
    "pairs": [PairDataStatus, ...],
    "freqtrade_visible": true,
    "source": "freqtrade",
    "errors": [],
    "warnings": []
}
```

### FreqtradeDataDownloadRequest

```python
{
    "run_id": "uuid",  # Optional
    "config_path": "/path/to/config.json",  # Optional
    "exchange": "binance",
    "trading_mode": "spot",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h", "5m"],
    "days": 30,  # Optional
    "timerange": "20240101-20240131",  # Optional
    "data_format_ohlcv": "feather",
    "user_confirmed": true  # Required
}
```

### FreqtradeDataDownloadResult

```python
{
    "run_id": "uuid",
    "exchange": "binance",
    "trading_mode": "spot",
    "pairs": ["BTC/USDT", "ETH/USDT"],
    "timeframes": ["1h", "5m"],
    "success": true,
    "blocked": false,
    "stdout": "Downloaded data...",
    "stderr": "",
    "error": null,
    "duration": 45.2,
    "errors": [],
    "warnings": []
}
```

## Validation Rules

### Data Check Validation

- `pairs` must not be empty
- `trading_mode` must be one of: spot, futures, margin
- `exchange` must be provided
- `timeframe` must be provided

### Download Validation

- `pairs` must not be empty
- `timeframes` must not be empty
- `trading_mode` must be one of: spot, futures, margin
- `user_confirmed` must be true
- Either `days` or `timerange` must be provided
- No secret-like values in request

## Error Handling

The data service handles errors gracefully:

- **Freqtrade not configured** - Returns blocked status with error
- **User not confirmed** - Returns blocked status with error
- **Missing parameters** - Validation error at schema level
- **Command failure** - Returns failure result with error message
- **Timeout** - Returns timed out result with partial output
- **File system errors** - Returns error without crashing

## Security Considerations

1. **No silent downloads** - User confirmation required
2. **No data deletion** - Never uses `--erase` flag
3. **No secrets in commands** - Sanitizes secret-like values
4. **Controlled subprocess** - Uses safe command runner
5. **Audit logging** - All operations logged when `run_id` provided
6. **Path validation** - Prevents directory traversal attacks

## Testing

The data service is comprehensively tested in `backend/tests/test_freqtrade_data_service.py`:

- Command building for list-data
- Command building for download-data
- Empty pairs rejected
- Empty timeframes rejected
- Download blocked without confirmation
- Download blocked without days or timerange
- `--erase` never appears in commands
- Missing Freqtrade returns controlled status
- Logs/audit created when run_id provided
- No secrets exposed in commands
- Local file discovery
- Freqtrade list-data integration
- Freqtrade download-data integration
- Invalid trading mode rejected

## Future Extensions

Future parts may add:

- Data validation and integrity checking
- Data compression and optimization
- Data versioning and rollback
- Multi-exchange data management
- Real-time data streaming support
- Data quality metrics
