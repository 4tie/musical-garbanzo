# Part 05 Result Parser Plan

## Part 05 Goal

Part 05 makes HER understand real Freqtrade backtest results.

The goal is to discover raw Freqtrade backtest outputs produced by Part 04, load them safely, extract normalized metrics, calculate expectancy, save parsed results into the Part 03 SQLite tables, and expose result APIs for the frontend and future AutoQuant decision stages.

Part 05 must not use fake or mock backtest success as proof of readiness. Unit tests may use small parser fixtures, but final readiness requires parsing a real Freqtrade smoke run produced by Part 04.

## Explicit Scope

Part 05 includes:

- Discovering real Freqtrade backtest result files for a HER run.
- Loading Freqtrade JSON, ZIP, and stdout/stderr result sources safely.
- Extracting normalized backtest metrics.
- Calculating expectancy from extracted win/loss data.
- Extracting pair-level results.
- Extracting trade summary information.
- Producing result-quality flags for missing, partial, ambiguous, or unsupported results.
- Saving parsed data into `metrics_snapshots`, `pair_results`, and `trade_summaries`.
- Registering parser logs and audit evidence where appropriate.
- Exposing OpenAPI-safe result APIs.
- Validating the parser against a real Part 04 Freqtrade smoke run.

## Explicit Non-Goals

Part 05 does not:

- Generate strategies.
- Call Ollama or any AI model.
- Repair strategies.
- Run Hyperopt.
- Run walk-forward, out-of-sample, or robustness analysis.
- Approve, reject, export, or promote a strategy.
- Classify a strategy as profitable.
- Claim any strategy is profitable.
- Send Discord notifications.
- Start live trading.
- Start dry-run trading loops.
- Place exchange orders.
- Treat fake, mocked, or synthetic backtest output as readiness proof.

## Expected Freqtrade Output Sources

The parser should support the Part 04 artifact layout first:

- `artifacts/runs/{run_id}/raw_freqtrade/backtest_results/`
- `artifacts/runs/{run_id}/raw_freqtrade/stdout.log`
- `artifacts/runs/{run_id}/raw_freqtrade/stderr.log`
- Artifact rows that point to raw Freqtrade outputs.

The parser may also inspect the configured Freqtrade workspace when a run artifact points there:

- `freqtrade_workspace/user_data/backtest_results/`

Expected result formats:

- Freqtrade JSON result files.
- Freqtrade ZIP result bundles that contain JSON result files.
- Captured stdout/stderr text as diagnostic fallback, not as the preferred source for metrics.

JSON or ZIP content is the preferred source of truth. Stdout parsing should be limited to supplemental diagnostics and quality flags unless no structured result exists.

## Result Discovery Plan

Result discovery should:

1. Resolve the run's raw Freqtrade artifact directory.
2. Confirm candidate paths are inside known HER artifact or configured Freqtrade workspace directories.
3. List candidate result files by supported extension and expected naming pattern.
4. Prefer structured JSON over ZIP, and ZIP over stdout/stderr text.
5. Prefer files linked by artifact records over unrelated workspace files.
6. Detect multiple plausible candidates and flag ambiguity instead of silently choosing an unsafe result.
7. Record missing, unsupported, stale, or ambiguous result conditions as quality flags.

Discovery must never delete, overwrite, or move raw Freqtrade output files.

## JSON, ZIP, and Stdout Loader Plan

### JSON Loader

- Open only resolved safe paths.
- Enforce a maximum input size.
- Decode as UTF-8.
- Parse with the standard JSON parser.
- Preserve the source path and raw parsed object metadata in `raw_json`.
- Return a controlled parse error if the schema is unsupported.

### ZIP Loader

- Open only resolved safe paths.
- Reject ZIP entries with absolute paths or `..` traversal.
- Read only supported JSON or text members.
- Enforce per-member and total extracted size limits.
- Prefer the most specific Freqtrade backtest JSON member.
- Never extract files onto disk unless a later prompt explicitly adds a safe extraction need.

### Stdout and Stderr Loader

- Read captured text logs only from approved artifact paths.
- Decode text with replacement for invalid bytes.
- Sanitize secrets before storing or returning text.
- Use stdout/stderr for diagnostics, error reporting, and quality flags.
- Do not treat stdout-only parsing as full readiness if structured Freqtrade JSON exists or is expected.

## Metrics Extraction Plan

The parser should normalize the metrics needed by `metrics_snapshots`:

- `net_profit`
- `profit_factor`
- `max_drawdown`
- `sharpe`
- `calmar`
- `win_rate`
- `trade_count`
- `expectancy`
- `avg_win`
- `avg_loss`
- `raw_json`

Extraction rules:

- Preserve the original Freqtrade result object in `raw_json`.
- Normalize percentages consistently and document whether stored values are fractions or percent values.
- Convert numeric fields defensively and flag missing or invalid values.
- Support known Freqtrade schema variants without relying on a single brittle key path.
- Avoid inventing metrics that are not present or derivable from real result data.
- Store `None` for unavailable optional metrics and add quality flags.

## Expectancy Calculation Rules

Expectancy must follow the HER trading definition:

`Expectancy = (Win Rate * Average Win) - (Loss Rate * Absolute Average Loss)`

Where:

- `Win Rate` is represented as a fraction from `0` to `1`.
- `Average Win` is the mean profit of winning trades.
- `Loss Rate = 1 - Win Rate`.
- `Absolute Average Loss` is the mean losing trade amount expressed as a positive number.

Rules:

- Prefer Freqtrade-provided expectancy when its units and source are clear.
- Recalculate expectancy when win rate, average win, and average loss are available.
- Do not calculate expectancy from incomplete or synthetic values.
- If `trade_count` is zero, expectancy must be `None` and quality flags must include `zero_trades`.
- If win/loss inputs are missing, expectancy must be `None` and quality flags must include `missing_expectancy_inputs`.

## Pair Results Extraction Plan

The parser should extract per-pair results into `pair_results`:

- `run_id`
- `pair`
- `net_profit`
- `profit_factor`
- `max_drawdown`
- `trade_count`
- `win_rate`
- `expectancy`
- `raw_json`

Rules:

- Preserve every pair row present in the real Freqtrade result.
- Normalize pair names exactly as reported by Freqtrade.
- Use the existing `(run_id, pair)` uniqueness rule for idempotent saves.
- Flag missing pair breakdowns as `no_pair_breakdown`.
- Do not infer missing pair results from aggregate-only output.

## Trade Summary Extraction Plan

The parser should extract the aggregate trade summary into `trade_summaries`:

- `run_id`
- `total_trades`
- `wins`
- `losses`
- `draws`
- `avg_duration`
- `best_pair`
- `worst_pair`
- `raw_json`

Rules:

- Prefer structured summary fields from Freqtrade JSON.
- Derive `wins`, `losses`, and `draws` only when real trade or summary data supports it.
- Preserve duration units clearly.
- Flag missing aggregate trade data as `no_trade_summary`.
- Do not claim result quality is sufficient just because a summary row can be saved.

## Result Quality Flags

Part 05 should produce result-quality flags for frontend and future AutoQuant use. Initial flags:

- `ok`
- `no_result_file`
- `parse_error`
- `unsupported_format`
- `unsupported_schema`
- `multiple_candidates`
- `stale_artifact`
- `missing_metrics`
- `missing_expectancy_inputs`
- `zero_trades`
- `insufficient_trades`
- `no_pair_breakdown`
- `no_trade_summary`
- `stdout_only`
- `partial_parse`
- `suspected_schema_drift`

Flags are evidence labels, not approval decisions.

## Database Save Plan

Parsed results should be saved into the existing Part 03 tables:

- `metrics_snapshots`
- `pair_results`
- `trade_summaries`
- `run_logs`
- `audit_logs`

Save behavior:

- Use repository methods where they already exist.
- Save parser work in a transaction when multiple result tables are updated together.
- Make repeated parsing idempotent for a run and stage.
- Preserve raw source metadata and extracted raw objects in `raw_json`.
- Register run logs for parser start, warnings, and completion.
- Register audit logs for parser execution and source selection.
- Never store secrets from configs, environment variables, command output, or logs.

## API Plan

Part 05 should expose OpenAPI-safe result access while preserving existing Part 03 contracts.

Existing result endpoints remain valid:

- `GET /api/runs/{run_id}/metrics`
- `GET /api/runs/{run_id}/metrics/latest`
- `POST /api/runs/{run_id}/metrics`
- `GET /api/runs/{run_id}/pair-results`
- `POST /api/runs/{run_id}/pair-results`
- `GET /api/runs/{run_id}/trade-summary`
- `POST /api/runs/{run_id}/trade-summary`

Part 05 may add parser-focused endpoints:

- `POST /api/runs/{run_id}/backtest-results/parse`
- `GET /api/runs/{run_id}/backtest-results`
- `GET /api/runs/{run_id}/result-quality`

API responses must:

- Use explicit Pydantic response models.
- Avoid raw unbounded stdout or stderr by default.
- Include quality flags and source metadata.
- Avoid secret-bearing configuration fields.
- Not classify profitability or readiness for trading.

## Real Parser Validation Plan

Final Part 05 readiness must parse a real Part 04 smoke run.

Preferred validation target:

- Run ID: `b1527590-b972-4d6b-83c4-5e72118217ef`
- Freqtrade version recorded by Part 04: `freqtrade 2026.5.1`

Validation steps for the final Part 05 prompt:

1. Confirm real Part 04 smoke artifacts exist locally.
2. Parse the real structured Freqtrade backtest output.
3. Save metrics, pair results, and trade summary rows.
4. Verify rows through repository or API reads.
5. Confirm quality flags reflect the real result accurately.
6. Confirm no fake or fixture output is used as readiness proof.

If the prior real smoke artifacts are unavailable, a later validation prompt may rerun the Part 04 real smoke script. This plan prompt must not run Freqtrade.

## Safety Rules

Part 05 must follow these boundaries:

- Do not run live trading.
- Do not start dry-run trading loops.
- Do not run Hyperopt.
- Do not call Ollama.
- Do not send Discord messages.
- Do not place exchange orders.
- Do not expose `.env` content or secrets.
- Do not commit runtime databases, logs, market data, or backtest result artifacts.
- Do not modify raw Freqtrade output files.
- Do not use fake or mock output as readiness proof.
- Do not classify any strategy as profitable.
- Do not approve, export, or promote strategies.
- Do not hide parser failures or schema drift.

Part 05 is a parser and metrics extraction layer only.
