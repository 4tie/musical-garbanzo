# Backtest Real Parse Validation

## Purpose

`scripts/parse-real-smoke-backtest.py` validates that Part 05 can parse a real Freqtrade backtest output produced by the Part 04 smoke test.

This is the final readiness check for the parser layer. It must use real smoke artifacts and must not use fake, demo, or mocked output as proof.

## Command

```bash
source .venv/bin/activate
python scripts/parse-real-smoke-backtest.py --latest-smoke --force
```

If no real smoke run or raw artifacts exist, run:

```bash
python scripts/freqtrade-real-smoke-test.py
python scripts/parse-real-smoke-backtest.py --latest-smoke --force
```

## What It Validates

The script validates:

- Latest real smoke run discovery.
- Raw Freqtrade artifact discovery.
- Raw result loading.
- Metrics extraction.
- Expectancy calculation.
- Pair result parsing.
- Trade summary parsing.
- Quality flag generation.
- SQLite persistence for metrics, pair results, and trade summary.
- Parser logs and audit records.
- Normalized artifact creation.
- Results API readiness through persisted rows.

## What It Does Not Prove

The script does not prove:

- A strategy is profitable.
- A strategy is approved.
- A strategy is ready for export.
- A strategy is ready for dry-run or live trading.
- Hyperopt, walk-forward analysis, or robustness analysis works.

It also does not run Freqtrade, download data, call Ollama, send Discord messages, or place exchange orders.

## Inspecting The Normalized Artifact

After a successful parse, inspect:

```bash
cat artifacts/runs/{run_id}/normalized/backtest_result.normalized.json
```

The artifact includes:

- Metrics.
- Pair results.
- Trade summary.
- Quality flags.
- Parser metadata.
- Source files.
- Creation timestamp.

The artifact is runtime output and must not be committed.

## Common Failures

### `REAL_PARSE_PENDING: run scripts/freqtrade-real-smoke-test.py first`

No real smoke run or raw artifacts exist in the local database/artifact tree.

Action:

```bash
python scripts/freqtrade-real-smoke-test.py
python scripts/parse-real-smoke-backtest.py --latest-smoke --force
```

### `REAL_PARSE_FAILED`

The script found a real smoke run but parsing did not produce saved metrics and a normalized artifact.

Check:

- `artifacts/runs/{run_id}/raw_freqtrade/`
- `artifacts/runs/{run_id}/raw_freqtrade/backtest_results/`
- `artifacts/runs/{run_id}/raw_freqtrade/stdout.log`
- `artifacts/runs/{run_id}/raw_freqtrade/stderr.log`
- Parser warnings and errors printed by the script.

### Missing Structured Result File

If only stdout/stderr exists, HER may parse fallback text if enough data is present, but structured JSON/ZIP output is preferred. A fallback-only parse should be treated as lower quality.

### No Metrics Extracted

The raw output format may have changed or Freqtrade may not have produced parseable result data. This must not be converted into fake metrics.
