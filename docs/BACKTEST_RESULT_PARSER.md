# Backtest Result Parser

Part 05 teaches HER how to discover and later parse real Freqtrade backtest outputs.

This document currently covers the discovery and raw loading layers. Discovery locates raw output files for a `run_id` and returns structured metadata. Loading reads supported raw files into safe payload envelopes. Neither layer extracts normalized metrics, classifies strategy performance, approves strategies, calls Ollama, sends Discord messages, or runs Freqtrade.

## Discovery Purpose

The discovery service finds raw Freqtrade output files created by Part 04 so later parser prompts can load structured result data safely.

Discovery answers:

- Which raw output files exist for this run?
- Is there a structured JSON or ZIP result candidate?
- Where are stdout and stderr logs?
- Are outputs missing, ambiguous, or fallback-only?

Discovery does not answer whether a strategy is profitable or ready for trading.

## Expected Directories

Primary Part 04 artifact locations:

- `artifacts/runs/{run_id}/raw_freqtrade/`
- `artifacts/runs/{run_id}/raw_freqtrade/backtest_results/`
- SQLite artifact records for the same `run_id`

Optional workspace location:

- `freqtrade_workspace/user_data/backtest_results/`

The workspace directory is considered only when artifact records or obvious run metadata link files to the run. HER must not scan arbitrary folders.

## File Type Classification

Discovery classifies files without reading their contents:

- `json`: Structured JSON result candidate.
- `zip`: Structured ZIP result bundle candidate.
- `meta_json`: Metadata JSON, not a primary result candidate.
- `stdout_log`: Captured stdout fallback log.
- `stderr_log`: Captured stderr fallback log.
- `unknown`: Unsupported file type.

`.env` files are skipped. Paths outside the project root are rejected.

## Primary Result Selection Rules

Primary result selection prefers structured files:

1. Artifact registry files.
2. Run `backtest_results` files.
3. Run raw Freqtrade files.
4. Linked Freqtrade workspace files.

Within those sources, JSON is preferred over ZIP. Stdout and stderr are never primary structured results; they are fallback diagnostics only.

If multiple candidates exist, discovery returns all files and selects the best primary candidate deterministically. Later parser prompts may add stricter ambiguity handling if needed.

## Missing Result Behavior

Discovery must not crash when files are missing.

If no files exist, the result includes:

- `success=false`
- `primary_result_path=null`
- `files=[]`
- warning `no_backtest_output_files_found`

If only stdout/stderr exists, the result includes:

- `success=false`
- stdout/stderr paths where present
- warning `only_stdout_stderr_available`

This prevents HER from treating logs as proof of a completed or parseable backtest.

## Why Stdout Parsing Is Fallback Only

Freqtrade stdout is formatted for humans and may change between versions. Structured JSON or ZIP output is safer for metrics extraction because fields can be validated, stored, and traced.

Stdout/stderr remain useful for:

- Diagnosing failed backtests.
- Showing command errors.
- Explaining why structured result files are missing.
- Supporting future partial parser warnings.

They are not used as readiness proof.

## Supported Input Types

The raw loader supports:

- JSON result files.
- ZIP files that contain JSON members.
- `stdout.log` as a fallback text source.
- `stderr.log` as diagnostic error text.

Unsupported file types are returned as controlled payload warnings or errors. They are not parsed as result data.

## JSON Loading Behavior

JSON files are read only when they are inside the project root and are not blocked file types such as `.env` or SQLite database files.

The loader:

- Enforces a maximum JSON input size of `25_000_000` bytes.
- Parses JSON into a dictionary.
- Preserves the raw dictionary in `raw_data`.
- Detects common Freqtrade result-shape keys such as `strategy`, `strategy_comparison`, and `metadata`.
- Returns `unrecognized_freqtrade_json_shape` as a warning when the JSON is valid but not obviously a Freqtrade result.

Malformed JSON returns a controlled `json_load_error` payload. It does not crash the caller.

## ZIP Loading Behavior

ZIP files are opened in memory and are not extracted to disk.

The loader:

- Reads only `.json` members.
- Ignores non-JSON members.
- Ignores unsafe member paths.
- Returns one payload per safe JSON member.
- Preserves the source ZIP path and loaded member name in `zip_members`.
- Enforces a maximum ZIP member size of `25_000_000` bytes.
- Enforces a maximum total JSON member read budget of `50_000_000` bytes.

ZIP files with no safe JSON members return a controlled payload with warning `zip_no_json_members`.

Malformed ZIP files or malformed JSON members return controlled payload errors. They do not crash the caller.

## ZIP Safety Rules

The loader protects against zip slip by ignoring members that:

- Use absolute paths.
- Include `..` path traversal.
- Use unsafe backslash traversal.
- Are directories instead of files.

Members are read directly from the archive and never written to disk.

## Stdout and Stderr Fallback Behavior

`stdout.log` is loaded as `stdout_table_fallback`.

This is useful for diagnostics and future partial parsing, but stdout-only loading is not full parser readiness. Stdout is human-oriented and can change across Freqtrade versions.

`stderr.log` is loaded as `stderr_error_text`.

Stderr is diagnostic only and is not a metrics source.

Text files are read with UTF-8 replacement for invalid bytes and a maximum text input size of `5_000_000` bytes.

## File Size Limits

Current raw loader limits:

- Text logs: `5_000_000` bytes.
- Direct JSON files: `25_000_000` bytes.
- Individual ZIP JSON members: `25_000_000` bytes.
- Total ZIP JSON member read budget: `50_000_000` bytes.

Oversized files return controlled errors and are not loaded.

## Malformed File Behavior

The loader returns controlled payload errors for:

- Malformed JSON.
- Malformed ZIP archives.
- Oversized files.
- Missing files.
- Directories passed as files.
- Paths outside the project root.
- `.env` files.
- SQLite database files.

These errors are included in `RawBacktestPayload.errors` and rolled up into `RawBacktestLoadResult.errors` when loading from discovery.

## Metrics Extraction Layer

The metrics extractor consumes `RawBacktestPayload` objects and returns `MetricsExtractionResult`.

It extracts normalized metric fields where available, including profit, drawdown, ratio, trade-count, win/loss, duration, pair summary, and expectancy fields. The parser orchestrator can persist these extracted metrics into SQLite. Extraction itself does not classify strategy quality.

Extraction priority:

1. Trade-level JSON data.
2. Summary-level JSON data.
3. Stdout fallback text.

Expectancy source is labeled as:

- `trade_level`
- `summary_level`
- `stdout_fallback`
- `not_available`

See `docs/METRICS_EXTRACTION.md` for detailed formulas, supported fields, and missing-data behavior.

## Pair And Trade Summary Parser

The pair/trade parser consumes `RawBacktestPayload` objects and returns `PairTradeParseResult`.

It extracts:

- Pair-level result rows.
- Trade-list results grouped by pair.
- Aggregate trade summary fields.
- Best and worst pair evidence.
- No-trade warnings.

Structured JSON and ZIP-loaded JSON are preferred. Stdout `BACKTESTING REPORT` tables are fallback only and are marked lower quality.

The parser does not approve, reject, classify, or claim profitability for any strategy.

## Parser Persistence Pipeline

`BacktestResultParser` connects the Part 05 parser layers to the Part 03 database and artifact system.

Pipeline:

1. Discover raw Freqtrade outputs for a `run_id`.
2. Load JSON, ZIP JSON members, or stdout fallback payloads.
3. Extract normalized aggregate metrics.
4. Extract pair-level results and trade summary.
5. Build result quality flags.
6. Save parsed evidence into SQLite.
7. Write a normalized JSON artifact.
8. Record parser logs and audit evidence.

The parser can also parse explicit paths through `parse_from_paths(run_id, paths, force=False)` for tests and controlled tooling.

## Database Writes

The parser writes:

- `metrics_snapshots`: one new snapshot per parse unless `force=true` deletes previous snapshots first.
- `pair_results`: upserted by `(run_id, pair)`.
- `trade_summaries`: replaced for the run before inserting the latest parsed summary.
- `run_logs`: parser completion, warnings, and failures.
- `audit_logs`: parser attempt and result-quality evidence.
- `artifacts`: normalized parsed result artifact metadata.

Quality flags are stored in audit evidence and in the normalized artifact. The raw Freqtrade outputs remain untouched.

## Normalized Artifact

The parser writes:

`artifacts/runs/{run_id}/normalized/backtest_result.normalized.json`

The artifact includes:

- Metrics.
- Pair results.
- Trade summary.
- Quality flags.
- Parser metadata.
- Source files.
- Creation timestamp.

It is registered as artifact type `metrics_json` with description `Normalized parsed backtest result`.

## Idempotency

Parser re-runs are designed to avoid unbounded duplication of current-state rows:

- Pair results are upserted by run and pair.
- Trade summary rows are replaced for the run.
- Normalized artifact metadata is updated for the same run/path.
- Metric snapshots append by default for history.
- When `force=true`, previous metric snapshots for the run are deleted before saving the current snapshot.

The parser never deletes raw Freqtrade outputs or raw logs.

## Not Decided Here

Parser persistence does not:

- Approve or reject strategies.
- Claim profitability.
- Change strategy classification.
- Change run status.
- Start live trading or dry-run loops.
- Run Freqtrade.
- Call Ollama.
- Send Discord messages.

## Results API

Parsed results are exposed through the Results API:

- `POST /api/results/backtest/{run_id}/parse`
- `GET /api/results/backtest/{run_id}`
- `GET /api/results/backtest/{run_id}/quality`
- `GET /api/results/backtest/{run_id}/normalized`
- `GET /api/runs/{run_id}/result-quality`

Existing Part 03 metrics routes continue to expose persisted rows:

- `GET /api/runs/{run_id}/metrics/latest`
- `GET /api/runs/{run_id}/pair-results`
- `GET /api/runs/{run_id}/trade-summary`

All routes are mounted under both `/api` and `/api/v1`.

The parse endpoint only parses already captured raw outputs. It does not run Freqtrade, download data, call Ollama, send Discord messages, classify strategies, or approve/reject strategies.
