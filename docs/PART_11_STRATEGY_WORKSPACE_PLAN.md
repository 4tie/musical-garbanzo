# Part 11 Strategy Workspace Manager Plan

## Scope

Part 11 builds a real Strategy Workspace Manager for local Freqtrade strategy files. It lets HER inspect the configured strategy workspace, read safe file metadata, detect and parse sidecar JSON, compute backend readiness, and pass ready strategy selections into the existing baseline and optimization start flows.

The source of truth for the Part 11 library is the configured Freqtrade strategies directory:

```text
freqtrade_workspace/user_data/strategies/
```

This path is resolved from `settings.FREQTRADE_USER_DATA_DIR` through `FreqtradeWorkspaceService.get_strategy_dir()` and `FreqtradeStrategyService.get_strategy_dir()`.

## Non-Goals

Part 11 does not generate strategy code, repair strategy code, approve strategies, export strategies, overwrite existing strategy files, run live trading, place exchange orders, start Freqtrade `trade`, start Freqtrade `webserver`, call Ollama, send Discord messages, claim profitability, or show fake readiness.

## Existing Code Inspected

- `backend/app/api/v1/routers/freqtrade.py`
- `backend/app/api/v1/routers/strategies.py`
- `backend/app/api/v1/routers/baseline.py`
- `backend/app/api/v1/routers/optimization.py`
- `backend/app/services/freqtrade_strategy_service.py`
- `backend/app/services/freqtrade_workspace.py`
- `backend/app/services/freqtrade_config_generator.py`
- `backend/app/services/strategy_params_materializer.py`
- `backend/app/services/baseline_evaluation_service.py`
- `backend/app/services/optimization_pipeline_service.py`
- `backend/app/core/config.py`
- `backend/app/core/constants.py`
- `backend/app/repositories/strategies.py`
- `backend/app/schemas/freqtrade_strategy.py`
- `backend/app/schemas/strategies.py`
- `backend/tests/test_freqtrade_strategy_service.py`
- `backend/tests/test_freqtrade_api.py`
- `frontend/src/components/StrategySelect.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/app/strategies/page.tsx`
- `frontend/src/app/baseline/page.tsx`
- `frontend/src/app/optimization/page.tsx`
- `frontend/src/lib/api/freqtrade.ts`
- `frontend/src/lib/api/baseline.ts`
- `frontend/src/lib/api/optimization.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/api/validators.ts`
- `frontend/src/lib/api/builders.ts`
- `docs/FREQTRADE_INTEGRATION.md`
- `docs/STRATEGY_REGISTRY.md`

## Current Strategy Flow

HER currently has two strategy concepts:

1. A real file-based Freqtrade workspace exposed through `/api/freqtrade/strategies`.
2. A database-backed strategy registry exposed through `/api/strategies`.

The file-based flow is the correct base for Part 11. `FreqtradeStrategyService.list_strategy_files()` scans `*.py` files in `freqtrade_workspace/user_data/strategies`, skips `__*` files, and checks for a sidecar named `{StrategyName}.json`. It does not import strategy code. `find_strategy_by_name()` resolves `{strategy_name}.py` and sidecar `{strategy_name}.json`. `validate_strategy_file_path()` rejects files outside the strategies directory and non-`.py` files.

The database registry is not enough for Part 11 because it can contain metadata records that do not prove local file existence, syntax, sidecar validity, or run readiness. It should not drive the Strategy Workspace library unless it is explicitly reconciled with real files.

Current workspace pairing evidence:

- `HERHyperoptSmokeStrategy.py` currently has no matching `HERHyperoptSmokeStrategy.json`.
- `best_strategy_dna.json` currently has no matching `best_strategy_dna.py`.

These are examples of why Part 11 needs readiness states instead of a simple dropdown.

## Current Limitations

- `/api/freqtrade/strategies` returns a shallow list and does not parse Python syntax, extract metadata, parse JSON params, or compute readiness.
- `/api/freqtrade/strategies/{strategy_name}` may run `freqtrade list-strategies` when Freqtrade is configured. Part 11 inspection should stay static/read-only by default.
- Existing backend strategy responses return absolute paths; Part 11 should return project-relative paths.
- `frontend/src/lib/api/freqtrade.ts` expects `name` and `path`, but the backend schema returns `strategy_name` and `file_path`.
- `StrategySelect` only lists names and cannot display readiness, missing sidecar status, invalid params, or unsafe strategies.
- `/strategies` is only a placeholder page.
- There is no `/strategies/[strategyName]` detail page.
- Baseline warns on missing sidecar but still proceeds as long as the file exists and path is safe.
- Optimization does not perform a dedicated strategy readiness check before creating an optimization run; it can rely indirectly on baseline-first flow or later Freqtrade failure.

## Backend Contract

Part 11 should add a workspace read model that is computed from real local files without importing strategy modules or executing strategy code.

Minimum response item:

```json
{
  "strategy_name": "string",
  "strategy_file_path": "project-relative path",
  "sidecar_json_path": "project-relative path or null",
  "has_sidecar": true,
  "readiness": "ready | warning | invalid | missing_sidecar | parse_error | unsafe",
  "issues": [],
  "warnings": [],
  "metadata": {},
  "params_summary": {},
  "updated_at": "string or null"
}
```

Recommended readiness rules:

- `ready`: strategy file exists, path is safe, Python parses with `ast.parse`, required Freqtrade structure is detected statically, sidecar JSON exists, and sidecar JSON parses.
- `warning`: strategy file is statically readable but has non-blocking gaps, such as unknown optional metadata.
- `missing_sidecar`: strategy file is statically readable but `{StrategyName}.json` is missing.
- `parse_error`: Python syntax or JSON parsing failed.
- `invalid`: required static Freqtrade structure is missing.
- `unsafe`: name/path validation failed, path escapes workspace, file is not a normal `.py`, or unsupported filesystem conditions are found.

Required static checks:

- Validate strategy name as a safe path segment.
- Resolve strategy path under the configured strategies directory.
- Read file text without importing it.
- Run `ast.parse` to catch syntax errors.
- Detect at least one class definition with the same name as the strategy file or a clear `IStrategy` subclass pattern.
- Detect common Freqtrade attributes or methods statically, such as `INTERFACE_VERSION`, `minimal_roi`, `stoploss`, `timeframe`, `populate_indicators`, `populate_entry_trend`, and `populate_exit_trend`.
- Detect sidecar JSON by exact `{strategy_name}.json` naming.
- Parse sidecar JSON with `json.load`; never evaluate code.
- Return only a bounded params preview and summary counts, not huge raw params by default.

## Endpoint Plan

Use a clean `/api/strategies` workspace contract for Part 11 and avoid presenting the database registry as the strategy library.

Required endpoints:

- `GET /api/strategies`
  - Returns real workspace strategies with readiness.
  - Supports optional filters such as `readiness`, `has_sidecar`, and `q`.
- `GET /api/strategies/{strategy_name}`
  - Returns one workspace strategy detail.
  - Returns 404 for missing strategy files and 400 for unsafe names.
- `GET /api/strategies/{strategy_name}/params`
  - Returns parsed sidecar JSON summary and optional bounded preview.
  - Returns controlled parse errors; never hides invalid JSON.

Optional later endpoints:

- `POST /api/strategies/import`
  - Implemented as a safe project-relative import flow.
  - Copies a `.py` strategy and optional `.json` sidecar into the configured workspace only after static validation.
  - Does not support multipart uploads yet.
  - Does not overwrite existing `.py` or `.json` targets, even when `overwrite_confirmed=true`.
  - Returns a controlled conflict payload with existing project-relative paths when a destination file already exists.
  - Validates extension, filename/path safety, strategy name, Python syntax, static strategy class presence, and sidecar JSON syntax before copying.
- `POST /api/strategies/{strategy_name}/validate`
  - Static validation only by default.
  - If a future version invokes Freqtrade validation, it must be explicit, confirmed, and not part of passive inspection.

Existing endpoint handling:

- `/api/freqtrade/strategies` can remain as a backwards-compatible wrapper during migration, but the Part 11 frontend should call `/api/strategies`.
- The current database registry under `/api/strategies` conflicts with the Part 11 workspace endpoint names. Implementation should either move legacy registry routes to `/api/strategy-registry` or make `/api/strategies` return the workspace read model and keep registry operations out of the Part 11 UI.

## Frontend Contract

Create real Strategy Workspace pages:

- `/strategies`
  - Replaces the placeholder with a real local strategy library.
  - Shows only backend-returned local files.
  - Displays readiness, sidecar status, updated time, issues, warnings, and params summary.
  - Does not fabricate strategies.
- `/strategies/[strategyName]`
  - Shows backend strategy detail.
  - Shows strategy file path, sidecar path, readiness, syntax/parse issues, static metadata, and params preview.
  - Includes safe links/buttons to use a ready or warning strategy in baseline/optimization.

Recommended frontend API module:

- Add `frontend/src/lib/api/strategies.ts`.
- Add strategy workspace response types to `frontend/src/lib/api/types.ts`.
- Add `frontend/src/lib/api/strategyAdapters.ts` for UI status mapping and run-selectability helpers.
- Keep `frontend/src/lib/api/freqtrade.ts` for Freqtrade status/data helpers.

## Part 10 Integration

Baseline and optimization forms should consume workspace-selected strategies safely.

Recommended flow:

- Strategy detail page links to `/baseline?strategy={strategy_name}` and `/optimization?strategy={strategy_name}`.
- Baseline and optimization pages read the query param and prefill `strategy_name`.
- `StrategySelect` should use the new workspace endpoint and show readiness.
- Only `ready` and possibly `warning` strategies should be selectable for run forms.
- `missing_sidecar`, `parse_error`, `invalid`, and `unsafe` strategies must not be silently startable as ready.
- Backend run services should reuse the same readiness service before baseline or optimization execution.

## Data Safety Rules

- Passive inspection must only read files under the configured strategies directory.
- Passive inspection must never import strategy modules.
- Passive inspection must never call Freqtrade.
- Passive inspection must never call Ollama, Discord, exchange APIs, `trade`, or `webserver`.
- Paths returned to the frontend must be project-relative.
- Params previews must be bounded.
- Errors must be explicit and controlled.
- Runtime files, strategy files, sidecar JSON, `data/her.db`, logs, artifacts, and downloaded market data must not be committed.

## Prompt 2 Implementation Notes

Prompt 2 added backend-only workspace schemas and `StrategyWorkspaceUtils`. The utility resolves deterministic `{StrategyName}.py` and `{StrategyName}.json` paths under the configured strategies directory, blocks traversal and absolute user-supplied paths, allows only `.py` and `.json`, performs bounded UTF-8 reads, parses Python with `ast.parse`, summarizes sidecar JSON with secret redaction, and returns readiness without importing strategy code or executing Freqtrade.

Prompt 2 does not add API routes or UI. Prompt 3 should wire these schemas/utilities into the `/api/strategies` workspace endpoints and resolve the existing database-registry route conflict.

## Prompt 3 Implementation Notes

Prompt 3 added `StrategyWorkspaceService`, a backend-only service that scans visible local `*.py` strategy files, ignores private/cache/runtime-style files, matches deterministic sidecar JSON, returns summary/detail/params records, and adds issue-based safety checks on top of the static AST/JSON utility.

The service exposes `list_strategies()`, `get_strategy(strategy_name)`, `get_strategy_params(strategy_name)`, `validate_strategy(strategy_name)`, and `resolve_strategy_for_run(strategy_name)`. It still does not add API routes or frontend pages. Prompt 4 can build frontend API types/helpers after Prompt 3 endpoints are wired, or the next backend prompt can expose this service through `/api/strategies`.

## Prompt 4 Implementation Notes

Prompt 4 added the read-only strategy workspace API at `/api/strategies`. It exposes list, detail, params, and validate endpoints backed by `StrategyWorkspaceService`, with readiness/sidecar/search pagination filters on the list endpoint. The router is mounted at `/api` before the legacy database strategy registry, while the existing `/api/v1/strategies` registry remains available for current backend tests and older contracts.

Prompt 4 does not add frontend code, run Freqtrade, import strategies, or implement import/staging.

## Prompt 5 Implementation Notes

Prompt 5 added a backend-only safe import endpoint at `POST /api/strategies/import`. The endpoint accepts a JSON request with a project-relative `source_path`, optional project-relative `sidecar_source_path`, optional `strategy_name`, and `overwrite_confirmed`.

The import service resolves source files under the project root, requires `.py` for strategies and `.json` for sidecars, rejects absolute paths and traversal, reads bounded UTF-8 text, parses Python with `ast.parse`, verifies a static strategy class signal, parses sidecar JSON with `json.loads`, and then copies files into `freqtrade_workspace/user_data/strategies/` only if no destination `.py` or `.json` already exists.

Prompt 5 intentionally does not implement multipart uploads, frontend import UI, overwrite confirmation, approval, export, strategy repair, AI generation, Freqtrade execution, or live trading. Imported files are still immediately re-inspected by the static workspace service and may return `missing_sidecar`, `unsafe`, `warning`, or `ready` based on real file evidence.

## Prompt 6 Implementation Notes

Prompt 6 added frontend-only strategy workspace API contracts. `frontend/src/lib/api/types.ts` now mirrors the backend workspace schemas for readiness, issues, summaries, details, params summaries, and import results. `frontend/src/lib/api/strategies.ts` calls the real `/api/strategies` endpoints through the shared API client; it does not use raw fetch or fake data. `frontend/src/lib/api/strategyAdapters.ts` maps backend readiness into UI labels, tones, rows, and run-selectability rules.

Prompt 6 does not add pages, alter run forms, execute Freqtrade, import strategy code, call AI/Ollama/Discord, or create fake strategy entries.

## Prompt 7 Implementation Notes

Prompt 7 replaced the `/strategies` placeholder with a real Strategy Library page. The page calls `listStrategies()` against `/api/strategies`, adapts only the backend-returned strategy records for display, and does not fabricate strategies, params, or readiness.

The page shows strategy name, backend readiness, sidecar status/path, issue and warning counts, updated time, timeframe, `can_short` when statically known, params sections, and actions for details, baseline, and optimization. Baseline/optimization actions are disabled unless backend readiness is `ready` or `warning`. The page also includes search, readiness filters, sidecar filters, sortable table columns, safety copy, backend-unavailable messaging, strategy-directory/read-error messaging, no-results states, and a no-sidecar warning when every returned strategy lacks sidecar JSON.

Prompt 7 does not add the strategy detail route, run-form query-param consumption, backend run gating, import UI, Freqtrade execution, AI/Ollama/Discord, live trading, approval, export, repair, or fake data.

## Prompt 8 Implementation Notes

Prompt 8 added the `/strategies/[strategyName]` detail page. The page calls `getStrategy()` and `validateStrategy()` through the frontend strategy workspace API client, displays only backend-returned static inspection data, and never fabricates readiness, metadata, params, issues, or warnings.

The detail view shows strategy identity, readiness badge and explanation, file and sidecar paths, static metadata, static checks, grouped issues by severity, backend warnings, params summary, and a read-only safe params preview for buy, sell, ROI, stoploss, trailing, protections, `max_open_trades`, and timeframe. The preview includes an additional frontend redaction pass for secret-like keys and does not support editing.

The Revalidate button calls `POST /api/strategies/{strategyName}/validate`, shows loading state, refreshes the detail on success, and shows controlled errors while preserving the prior detail on failure.

Prompt 8 does not add run-form query-param consumption, backend run gating, params editing, import UI, strategy repair, approval, export, Freqtrade execution, AI/Ollama/Discord, live trading, or fake data.

## Prompt 9 Implementation Notes

Prompt 9 connected Strategy Workspace selection to the Part 10 baseline and optimization run forms. `/baseline` and `/optimization` now read an initial `?strategy=StrategyName` query parameter, prefill the strategy field, and show a "Selected from Strategy Workspace" note without auto-starting, skipping confirmation, approving the strategy, or changing normal form validation.

`StrategySelect` now calls the real `/api/strategies` workspace endpoint through `listStrategies()`, shows backend readiness for selected strategies, links to the strategy detail page, and preserves a controlled warning state if the backend is unavailable or the current value is not verified by the workspace response. It does not fabricate fallback strategy entries.

Baseline and optimization forms show readiness warnings when the selected strategy is missing from the workspace response or has readiness other than `ready` or `warning`. The warning is repeated in the confirmation dialog, but the user confirmation gate remains unchanged and no run starts automatically.

Prompt 9 does not add backend run gating, auto-repair, approval, export, Freqtrade execution, AI/Ollama/Discord, live trading, or fake strategy data.

## Prompt Sequence

1. Prompt 1: Plan and contract review. Create docs only.
2. Prompt 2: Backend workspace schemas/service/tests for static inspection and params parsing. Completed in commit for `Part 11: add strategy workspace schemas and safe utilities`.
3. Prompt 3: Backend workspace service for scanning, readiness, and safety issues. Completed in commit for `Part 11: add strategy workspace service`.
4. Prompt 4: Backend strategy workspace API router. Completed in commit for `Part 11: add strategy workspace API`.
5. Prompt 5: Safe backend strategy import/staging flow. Completed in commit for `Part 11: add safe strategy import backend`.
6. Prompt 6: Frontend strategy workspace API client/types. Completed in commit for `Part 11: add strategy workspace frontend API`.
7. Prompt 7: Strategy library page. Completed in commit for `Part 11: add strategy library page`.
8. Prompt 8: Strategy detail page with params/readiness display. Completed in commit for `Part 11: add strategy detail page`.
9. Prompt 9: Baseline/optimization query-param integration and readiness-aware selector. Completed in commit for `Part 11: integrate strategy workspace with run forms`.
10. Prompt 10: Backend readiness gating reused by baseline and optimization.
11. Prompt 11: Documentation, validation, and final Part 11 completion report.

## Risks and Gaps

- `/api/v1/strategies` still means the database registry, while `/api/strategies` now means workspace files.
- Static AST checks can prove syntax and structure only; they cannot prove runtime Freqtrade compatibility.
- Sidecar JSON schemas may vary by Freqtrade version and strategy style.
- Some existing strategies may be warnings or invalid once static checks are strict.
- `StrategySelect` currently has a backend/frontend response shape mismatch.
- Optimization needs earlier readiness gating to avoid creating runs for invalid strategies.
- Import currently supports project-relative source files only; browser multipart upload and overwrite confirmation remain future work.
