# Part 04 Freqtrade Integration Plan

## Part 04 Goal

Part 04 connects HER to a real local Freqtrade installation while preserving the Part 03 backend, database, repository, artifact, metrics, log, retry, and audit foundations.

The goal is to make HER able to detect Freqtrade, validate the local Freqtrade workspace, generate safe backtest configuration, check market data availability, optionally download missing data when explicitly allowed, run controlled real backtests, capture raw Freqtrade outputs, and expose safe backend APIs for those actions.

Part 04 readiness must be proven with real Freqtrade when Freqtrade is configured. Fake or mock backtest results may be used in unit tests for command construction and API behavior, but they are not acceptable proof that Part 04 is ready.

## Explicit Scope

Part 04 implements only the Freqtrade integration layer needed for controlled local backtesting:

- Freqtrade executable detection using configured `FREQTRADE_PATH` or PATH lookup.
- Freqtrade version detection.
- Workspace validation for HER's configured `freqtrade_workspace/` layout.
- Safe command runner with an explicit Freqtrade command allowlist.
- Backtest config generation for dry, local, backtest-only operation.
- Strategy discovery from `freqtrade_workspace/user_data/strategies/`.
- Data availability checks for exchange, pairs, timeframe, and timerange.
- Optional data download only when the API/script call explicitly allows it.
- Controlled real Freqtrade backtesting.
- Capture of stdout, stderr, exit code, generated result files, config snapshots, logs, and raw JSON artifacts.
- Registration of generated artifacts through the Part 03 artifacts repository.
- Registration of run logs, stage status, metrics snapshots, pair results, and trade summaries when parser support is added.
- Backend endpoints for detection, validation, config preview/generation, strategy listing, data checks, optional download, and backtest execution.
- A real smoke validation script that uses actual Freqtrade if configured and reports unavailable prerequisites without fabricating success.

## Explicit Non-Goals

Part 04 does not implement:

- The full AutoQuant pipeline.
- AI strategy generation.
- Ollama calls for strategy design or repair.
- AI repair loops.
- Hyperopt as a production workflow.
- Walk-forward analysis.
- Out-of-sample validation.
- Robustness scoring.
- Final strategy classification.
- Discord notifications.
- Live trading.
- Dry-run trading.
- Exchange order placement.
- Claims that any strategy is profitable.
- Secret display in API responses, logs, artifacts, OpenAPI examples, or terminal output.

## Real Freqtrade Requirement

Part 04 unit tests may use fakes or mocks to verify:

- Command construction.
- Command allowlist and denylist enforcement.
- Path validation.
- Config generation.
- API request and response behavior.
- Error handling.
- Secret redaction.

Part 04 final validation must use real Freqtrade if Freqtrade is configured. A successful unit test suite alone is not enough to mark Part 04 ready.

If Freqtrade is not configured, final validation must clearly report `not_configured` or an equivalent controlled status. It must not record fake backtest metrics, fake artifacts, or fake success.

## Safe Command Allowlist

Only these Freqtrade command forms are allowed in Part 04:

- `freqtrade --version`
- `freqtrade create-userdir`
- `freqtrade show-config`
- `freqtrade list-strategies`
- `freqtrade list-data`
- `freqtrade download-data`
- `freqtrade backtesting`

The command runner must enforce the allowlist before process execution. It should build subprocess arguments as a list, never through shell string concatenation.

Allowed commands must still pass additional validation:

- The executable must be the configured Freqtrade binary or a resolved PATH executable.
- Paths must resolve inside the HER project workspace unless explicitly configured otherwise.
- Config paths must point to generated backtest-safe files, not user secrets files.
- Strategy names must be identifiers returned by discovery or validated against a strict pattern.
- Pairs, timeframe, timerange, exchange, and trading mode must be validated before command construction.
- Timeouts must be enforced for long-running commands.
- stdout and stderr must be captured and redacted before logging or API return.

## Forbidden Command List

These commands and command classes are forbidden in Part 04:

- `freqtrade trade`
- `freqtrade webserver`
- Any live trading command.
- Any dry-run trading process that starts a bot loop.
- Any command that can place exchange orders.
- Any command that modifies exchange state.
- Any command that exposes secrets.
- Any command that prints full effective config when it contains secrets.
- Any command not explicitly listed in the Part 04 allowlist.

The runner must reject forbidden commands before execution and log a sanitized controlled failure.

## Freqtrade Workspace Paths

Part 04 uses the existing HER workspace layout:

- Project root: `/home/mohs/Desktop/her`
- Freqtrade workspace: `freqtrade_workspace/`
- User data directory: `freqtrade_workspace/user_data/`
- Strategy directory: `freqtrade_workspace/user_data/strategies/`
- Market data directory: `freqtrade_workspace/user_data/data/`
- Backtest results directory: `freqtrade_workspace/user_data/backtest_results/`
- Hyperopt results directory: `freqtrade_workspace/user_data/hyperopt_results/` (recognized, but not used as a Part 04 workflow)
- Freqtrade logs directory: `freqtrade_workspace/user_data/logs/`
- Plot directory: `freqtrade_workspace/user_data/plot/`
- Config directory: `freqtrade_workspace/config/`
- Generated config target: `freqtrade_workspace/config/config.generated.json`
- Backtest example config: `freqtrade_workspace/config/config.backtest.example.json`
- Run artifact mirror: `artifacts/runs/{run_id}/`

Runtime data, downloaded market data, generated configs that may contain sensitive local details, backtest results, logs, plots, and run artifacts must not be committed.

## Config Generation Plan

Part 04 should generate backtest-only Freqtrade config from safe inputs:

- Exchange name.
- Trading mode.
- Margin mode when applicable.
- Quote currency.
- Stake currency.
- Stake amount for backtesting.
- Pair whitelist.
- Timeframe.
- Timerange.
- Strategy name.
- User data directory.
- Data format if needed.

Generated configs must:

- Be valid JSON.
- Avoid API keys and exchange secrets.
- Disable order placement workflows.
- Use backtest-safe settings only.
- Be written to a predictable generated config path.
- Be copied or registered as a `freqtrade_config` artifact for the run when a backtest starts.
- Be redacted before appearing in API responses or logs.
- Be validated with `freqtrade show-config` only in a sanitized way.

The generated config should be reproducible from run settings and must not mutate example config files.

## Data Check And Download Plan

Part 04 data checking maps to lifecycle Stage 4: `data_availability`.

Data check behavior:

- Use `freqtrade list-data` or safe filesystem inspection to determine available exchange, pair, timeframe, and timerange coverage.
- Return structured status per pair and timeframe.
- Treat missing or incomplete data as a controlled system issue, not a strategy rejection.
- Record clear run logs with source `freqtrade` or `system`.
- Avoid storing raw OHLCV market data in SQLite.

Data download behavior:

- `freqtrade download-data` may run only when the request explicitly sets an allow-download flag.
- Download commands must be constrained to validated exchange, pairs, timeframe, and timerange.
- Download output must be captured, redacted, and logged.
- Downloaded market data remains under `freqtrade_workspace/user_data/data/` and must not be committed.
- After download, HER must re-run the data availability check before backtesting.

## Backtest Execution Plan

Part 04 backtesting maps to lifecycle Stage 5: `baseline_backtest`.

Backtest execution should:

- Require a validated Freqtrade executable.
- Require a valid workspace.
- Require a discovered or validated strategy.
- Require generated backtest-safe config.
- Require available market data or an explicit prior download.
- Run only `freqtrade backtesting` with validated arguments.
- Use a timeout.
- Capture exit code, stdout, stderr, start time, end time, and duration.
- Treat non-zero exit codes as controlled or system failures depending on cause.
- Not classify strategy profitability from a single backtest.
- Not mark a strategy `validated`, `approved`, or `profitable`.

The first Part 04 implementation should focus on reliable execution and raw capture. Deeper metric parsing can be added where it is deterministic and backed by tests.

## Artifact Capture Plan

Part 04 should preserve Freqtrade evidence without storing large runtime files in SQLite.

Expected artifacts:

- `freqtrade_config`: generated config snapshot.
- `backtest_raw`: raw Freqtrade result file or copied raw output bundle.
- `log_file`: sanitized stdout/stderr or command log when useful.
- `metrics_json`: parsed metrics only when parser output is deterministic and tied to real Freqtrade output.
- `report_md`: optional smoke validation report.

Artifact metadata should be stored in SQLite through the existing artifacts repository:

- `run_id`
- `strategy_id` when known
- `artifact_type`
- filesystem path
- sha256
- size_bytes
- description
- created_at

Raw output files should remain under `freqtrade_workspace/user_data/backtest_results/` and/or copied into `artifacts/runs/{run_id}/`. Runtime artifacts must stay ignored by Git.

## API Endpoint Plan

Part 04 should add safe backend APIs under `/api/freqtrade` or a similarly explicit `/api/*` route namespace while retaining OpenAPI-safe response models.

Planned endpoint groups:

- Environment status: detect executable, version, configured paths, and readiness without exposing secrets.
- Workspace validation: report directory existence and writability.
- Strategy detection: list available strategies and basic metadata.
- Config preview/generation: return redacted config preview and write generated config when requested.
- Data availability: check required market data for pairs, timeframe, and timerange.
- Optional data download: run only with explicit allow-download flag.
- Backtest execution: start a controlled real backtest and register artifacts/logs.
- Smoke validation: expose or support script-level validation of the full configured path.

Responses must avoid secret values and should return controlled statuses such as `ready`, `not_configured`, `missing_data`, `failed_controlled`, and `failed_system`.

## Real Smoke Validation Plan

Part 04 must include a script for real local validation, for example `scripts/smoke-freqtrade-backtest.py`.

The smoke script should:

- Activate through the existing Python environment.
- Initialize or validate the HER database only when needed.
- Detect Freqtrade.
- Validate the workspace.
- List strategies.
- Pick an explicit smoke strategy or require one as an argument.
- Check data availability for explicit pairs, timeframe, and timerange.
- Download data only if an explicit flag allows it.
- Run a real `freqtrade backtesting` command when prerequisites are met.
- Register raw artifacts and logs.
- Print a concise sanitized summary.
- Exit non-zero on real failures.
- Exit with a controlled message when Freqtrade is not configured.

The smoke script must never fabricate success. If real Freqtrade cannot run, the report must say so.

## Security Safeguards

Part 04 must preserve HER's local-only and secrets-safe design:

- No Discord messages.
- No Ollama generation calls.
- No live trading.
- No dry-run bot loops.
- No exchange order placement.
- No secret values in command logs.
- No `.env` content in API responses.
- No API keys in generated configs.
- No shell command strings.
- No command outside the allowlist.
- No directory traversal outside configured workspace paths.
- No committed runtime databases, market data, logs, artifacts, backtest results, or generated configs with local details.
- All errors returned to the API must be actionable and sanitized.
- All important write/run actions should be logged to run logs and audit logs where appropriate.

## Prompt 1 Readiness Result

Part 03A readiness is confirmed before Part 04 implementation starts:

- Required backend core, repository, router, migration, and completion report files exist.
- `STRATEGY_SOURCE_TYPES` includes `imported`.
- `RETRY_STATUSES` includes `proposed`, `approved`, `applied`, `failed`, `rejected`, and `skipped`.
- `AUDIT_ACTORS` includes `user`, `system`, `ai_assistant`, `ai_strategy_designer`, and `ai_repair_agent`.
- `LOG_LEVELS` includes `critical`.

No Freqtrade command was executed while creating this plan.
