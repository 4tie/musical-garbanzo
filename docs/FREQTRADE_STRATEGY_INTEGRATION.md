# Freqtrade Strategy Integration

## Overview

HER integrates with Freqtrade strategies by detecting and validating strategy files in the Freqtrade user_data strategies directory. This enables HER to list available strategies, validate their presence, and prepare them for backtesting.

## Strategy Directory

Strategies are located in:

```
freqtrade_workspace/user_data/strategies/
```

This is the standard Freqtrade location for user-defined trading strategies. HER expects this directory to exist and contain `.py` strategy files.

## .py Strategy File Rule

Strategy files must follow Freqtrade conventions:

- File extension: `.py`
- File name: Strategy class name (e.g., `MyStrategy.py`)
- Location: Under `freqtrade_workspace/user_data/strategies/`
- Content: Valid Python strategy class inheriting from `IStrategy`

### Example Strategy File

```python
# freqtrade_workspace/user_data/strategies/MyStrategy.py
from freqtrade.strategy import IStrategy

class MyStrategy(IStrategy):
    def populate_indicators(self, dataframe, metadata):
        # Strategy logic
        return dataframe
```

### Detection Rules

HER detects strategy files by:
1. Listing all `.py` files in the strategies directory
2. Skipping files starting with `__` (e.g., `__init__.py`)
3. Extracting strategy name from filename (stem without `.py`)
4. Checking for sidecar JSON file

## Sidecar .json Rule

Each strategy may have a sidecar JSON file for parameters:

- File name: Same as strategy file with `.json` extension
- Location: Same directory as strategy file
- Purpose: Store strategy parameters and configuration

### Example Sidecar File

```json
// freqtrade_workspace/user_data/strategies/MyStrategy.json
{
  "params": {
    "roi": {
      "0": 0.04,
      "60": 0.03,
      "120": 0.02,
      "240": 0.01
    },
    "stoploss": -0.05
  }
}
```

### Detection Behavior

- If sidecar exists: `has_sidecar_json = true`, `params_path` is set
- If sidecar missing: `has_sidecar_json = false`, warning is generated
- Missing sidecar is **not fatal** - strategy can still be used
- Later parts can generate sidecar files automatically

## Freqtrade Visibility vs File Visibility

HER provides two methods for strategy detection:

### File Visibility (Fallback)

- Scans strategies directory for `.py` files
- Works without Freqtrade installed
- Does not validate strategy syntax
- Does not detect class names
- Marked as `source = "file"`, `freqtrade_visible = false`

### Freqtrade Visibility (Preferred)

- Uses `freqtrade list-strategies --userdir <user_data>` command
- Requires Freqtrade to be installed and configured
- Validates strategy syntax
- Detects actual class names
- Marked as `source = "freqtrade"`, `freqtrade_visible = true`

### Detection Priority

1. If Freqtrade is configured: Use `list_strategies_via_freqtrade()`
2. If Freqtrade is not configured: Use `list_strategy_files()` as fallback
3. Always validate file paths and names for safety

## Why HER Does Not Import Arbitrary Strategy Code

**Critical:** HER does not import strategy Python modules in Part 04 for safety reasons:

1. **Code execution risk** - Importing arbitrary Python code can execute side effects
2. **Dependency conflicts** - Strategies may have dependencies not available in HER environment
3. **Isolation** - HER should remain isolated from strategy implementation details
4. **Validation only** - Part 04 is about detecting and validating, not executing

### Safe Detection Approach

HER uses safe detection methods:
- File system scanning (no code execution)
- Freqtrade command runner (controlled subprocess execution)
- Text pattern matching (no import/eval)
- Path validation (prevents traversal attacks)

### When Strategy Import May Happen

Future parts may include safe strategy import for:
- Parameter extraction from strategy classes
- Strategy validation and linting
- Strategy documentation generation

Any import will be:
- In isolated environment
- With explicit user consent
- With sandboxed execution
- With dependency management

## Validation in Part 04

Validation in Part 04 focuses on:

### Path Validation

- Strategy file must be within strategies directory
- Path must not contain traversal sequences (`..`)
- Path must be a `.py` file
- Path must not point to system files

### Name Validation

- Strategy name must be alphanumeric with underscores/hyphens
- Strategy name must not be empty
- Strategy name must not contain path separators
- Strategy name must not contain special characters

### File Existence Validation

- Strategy file must exist on disk
- Sidecar file existence is optional (warning if missing)
- File must be readable

### Freqtrade Visibility Validation

- Strategy must be visible to Freqtrade (if Freqtrade configured)
- Strategy class name must be detected (if Freqtrade configured)
- Strategy must not have syntax errors (if Freqtrade configured)

## Service Methods

### FreqtradeStrategyService

The strategy service provides the following methods:

#### `get_strategy_dir() -> Path`

Returns the strategies directory path.

#### `list_strategy_files() -> FreqtradeStrategyListResult`

Lists all `.py` files in the strategies directory using file system scanning.

#### `detect_sidecar_json(py_path: Path) -> Optional[Path]`

Detects the sidecar JSON file for a given strategy file.

#### `validate_strategy_file_path(path: str) -> tuple[bool, Optional[str]]`

Validates that a strategy file path is safe and within the strategies directory.

#### `validate_strategy_name(strategy_name: str) -> tuple[bool, Optional[str]]`

Validates that a strategy name is safe.

#### `find_strategy_by_name(strategy_name: str) -> Optional[FreqtradeStrategyFile]`

Finds a strategy by name in the strategies directory.

#### `list_strategies_via_freqtrade(config_path: Optional[str] = None) -> FreqtradeStrategyListResult`

Lists strategies using Freqtrade's `list-strategies` command.

#### `get_strategy_status(strategy_name: str, config_path: Optional[str] = None) -> FreqtradeStrategyStatus`

Gets the status of a specific strategy including file existence and Freqtrade visibility.

## Schemas

### FreqtradeStrategyFile

Represents a detected strategy file:

```python
{
    "strategy_name": "MyStrategy",
    "class_name": "MyStrategyClass",  # Only if detected via Freqtrade
    "file_path": "/path/to/strategies/MyStrategy.py",
    "params_path": "/path/to/strategies/MyStrategy.json",  # Optional
    "exists": true,
    "has_sidecar_json": true,
    "source": "file" or "freqtrade",
    "errors": [],
    "warnings": []
}
```

### FreqtradeStrategyStatus

Represents the status of a specific strategy:

```python
{
    "strategy_name": "MyStrategy",
    "exists": true,
    "freqtrade_visible": true,
    "has_sidecar_json": true,
    "file_path": "/path/to/strategies/MyStrategy.py",
    "params_path": "/path/to/strategies/MyStrategy.json",
    "source": "freqtrade",
    "errors": [],
    "warnings": []
}
```

### FreqtradeStrategyListResult

Result of listing strategies:

```python
{
    "strategies": [FreqtradeStrategyFile, ...],
    "freqtrade_visible": true,
    "source": "freqtrade",
    "errors": [],
    "warnings": []
}
```

## Freqtrade Command Integration

HER uses the `FreqtradeCommandRunner` to execute:

```bash
freqtrade list-strategies --userdir ./freqtrade_workspace/user_data
```

Or with a specific config:

```bash
freqtrade list-strategies --config ./freqtrade_workspace/config/runs/{run_id}.backtest.json
```

### Output Parsing

Freqtrade output format:
```
StrategyName: ClassName
OtherStrategy: OtherStrategyClass
```

HER parses this format to extract strategy names and class names.

## Error Handling

The strategy service handles errors gracefully:

- **Strategies directory missing**: Returns error, empty list
- **Freqtrade not configured**: Falls back to file scanning
- **Freqtrade command fails**: Returns error, marks `freqtrade_visible = false`
- **Invalid path/name**: Returns validation error
- **File not found**: Returns `exists = false`

## Security Considerations

1. **No arbitrary code execution** - Strategies are not imported
2. **Path validation** - Prevents directory traversal attacks
3. **Name validation** - Prevents injection attacks
4. **Controlled subprocess** - Freqtrade commands use safe command runner
5. **No file modification** - Service only reads files, never writes

## Testing

The strategy service is comprehensively tested in `backend/tests/test_freqtrade_strategy_service.py`:

- Lists `.py` files in strategies directory
- Detects sidecar `.json` files
- Missing sidecar generates warning
- Unsafe paths are rejected
- Unsafe strategy names are rejected
- Freqtrade missing returns controlled status
- No strategy code import happens
- No file overwrite happens
- Find strategy by name
- List strategies via Freqtrade command
- Get strategy status
- Strategies directory not exists handling
- Detect sidecar JSON method directly

## Future Extensions

Future parts may add:

- Strategy parameter extraction from class definitions
- Strategy syntax validation and linting
- Strategy documentation generation
- Strategy performance profiling
- Strategy A/B testing support
- Strategy version management
