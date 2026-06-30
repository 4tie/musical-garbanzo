# Part 11 Prompt 01 Report

## Files Inspected

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

HER currently has a real file-backed strategy listing at `/api/freqtrade/strategies`. It scans `freqtrade_workspace/user_data/strategies/*.py`, derives the strategy name from the file stem, detects a sidecar JSON named `{strategy_name}.json`, and warns when the sidecar is missing. It does not import strategy code while scanning.

HER also has a database-backed `/api/strategies` router for logical strategy records and versions. That registry is not a reliable Part 11 library source because records may not match real local files and do not prove syntax, sidecar validity, or readiness.

The frontend currently uses `StrategySelect` in both `/baseline` and `/optimization`. The selector calls `/api/freqtrade/strategies`, but its TypeScript type expects `name` and `path` while the backend returns `strategy_name`, `file_path`, `params_path`, and `has_sidecar_json`.

The `/strategies` route exists in the sidebar but is currently a placeholder page.

Baseline has a strategy validation stage that checks name, existence, safe path, and sidecar presence. Missing sidecar is a warning, not a blocker.

Optimization does not have an equivalent early readiness check before it creates the optimization run. If `run_baseline_first` is enabled, it indirectly exercises baseline validation first.

## Endpoint Gaps

- No Part 11 workspace endpoint currently returns readiness.
- No endpoint parses sidecar JSON and returns params summary.
- No endpoint returns project-relative strategy and sidecar paths.
- No endpoint returns syntax or static structure errors.
- No `/api/strategies/{strategy_name}/params` endpoint exists.
- Existing `/api/strategies` is database CRUD and conflicts with the desired workspace endpoint.
- Existing `/api/freqtrade/strategies/{strategy_name}` can call Freqtrade visibility checks when configured, which should not be part of passive workspace inspection.

## File Safety Concerns

- Backend must never import strategy files for inspection.
- Backend must never execute Freqtrade during passive listing/detail reads.
- Returned paths should be project-relative instead of absolute.
- Params previews should be bounded to avoid sending huge JSON blobs.
- Import/staging, if added later, must be an explicit write path with validation and overwrite protection.
- Runtime files such as `data/her.db`, logs, artifacts, downloaded data, strategy files, and sidecar JSON must remain uncommitted.

## Recommended Implementation Path

1. Add a workspace read model and static inspection service around the existing `FreqtradeStrategyService`.
2. Use `ast.parse` for Python syntax and structure checks without importing modules.
3. Parse sidecar JSON with `json.load` and return controlled parse errors.
4. Promote the Part 11 frontend contract to `/api/strategies`.
5. Resolve the current `/api/strategies` database-router conflict by moving registry routes or keeping them out of the Part 11 UI.
6. Add `/api/strategies`, `/api/strategies/{strategy_name}`, and `/api/strategies/{strategy_name}/params`.
7. Add frontend API types/helpers in a new strategies API module.
8. Replace the `/strategies` placeholder with a real workspace library.
9. Add `/strategies/[strategyName]`.
10. Update `StrategySelect` and Part 10 forms to consume readiness-aware strategy selections.
11. Reuse the same backend readiness service before baseline and optimization execution.

## Whether Prompt 2 Can Continue

Yes. Prompt 2 can continue with backend workspace schemas, static inspection service, and tests, without running Freqtrade or modifying strategy files.

