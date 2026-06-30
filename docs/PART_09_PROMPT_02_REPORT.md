# Part 09 Prompt 02 Report

## API Files Created

Created:

- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/errors.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/api/system.ts`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/baseline.ts`
- `frontend/src/lib/api/optimization.ts`
- `frontend/src/lib/api/results.ts`
- `frontend/src/lib/api/decisions.ts`
- `frontend/src/lib/api/artifacts.ts`
- `frontend/src/lib/api/adapters.ts`
- `frontend/src/lib/api/index.ts`
- `frontend/scripts/api-smoke.mjs`

Updated:

- `frontend/src/lib/types.ts`
- `frontend/package.json`
- `frontend/src/components/TopBar.tsx`
- `docs/PART_09_FRONTEND_DASHBOARD_PLAN.md`

Removed:

- `frontend/src/lib/api.ts`

`@/lib/api` remains usable through `frontend/src/lib/api/index.ts`.

## Endpoints Wired

System:

- `GET /health`
- `GET /api/system/status`
- `GET /api/settings/public`

Runs, stages, logs, retries:

- `GET /api/runs`
- `GET /api/runs/{run_id}`
- `GET /api/runs/{run_id}/stages`
- `GET /api/runs/{run_id}/stages/{stage_key}`
- `GET /api/runs/{run_id}/logs`
- `GET /api/runs/{run_id}/retry-history`

Baseline:

- `GET /api/baseline/runs/{run_id}`
- `GET /api/baseline/runs/{run_id}/status`
- `GET /api/baseline/runs/{run_id}/report`

There is no dedicated backend list endpoint for baseline runs. `listBaselineRuns` reads `/api/runs` and filters existing run records for baseline-like mode/name/classification values.

Optimization:

- `GET /api/optimization/runs`
- `GET /api/optimization/runs/{optimization_run_id}`
- `GET /api/optimization/runs/{optimization_run_id}/status`
- `GET /api/optimization/runs/{optimization_run_id}/trials`
- `GET /api/optimization/runs/{optimization_run_id}/trials/{trial_id}`
- `GET /api/optimization/runs/{optimization_run_id}/best-trial`
- `GET /api/optimization/runs/{optimization_run_id}/comparison`
- `GET /api/optimization/runs/{optimization_run_id}/report`

Results and metrics:

- `GET /api/runs/{run_id}/metrics`
- `GET /api/runs/{run_id}/metrics/latest`
- `GET /api/runs/{run_id}/pair-results`
- `GET /api/runs/{run_id}/trade-summary`
- `GET /api/results/backtest/{run_id}`
- `GET /api/results/backtest/{run_id}/quality`
- `GET /api/runs/{run_id}/result-quality`
- `GET /api/results/backtest/{run_id}/normalized`

Decisions:

- `GET /api/decisions/policies`
- `GET /api/decisions/policies/{policy_name}`
- `GET /api/decisions/runs/{run_id}`
- `GET /api/decisions/runs/{run_id}/latest`
- `GET /api/results/backtest/{run_id}/decision`
- `GET /api/runs/{run_id}/decision`

Artifacts and audit:

- `GET /api/artifacts`
- `GET /api/artifacts/{artifact_id}`
- `GET /api/runs/{run_id}/artifacts`
- `GET /api/audit-logs`

No POST, PATCH, approval, export, AI, Discord, or live trading wrappers were added.

## Adapter Functions Created

- `toUiStatus`
- `toRunListItem`
- `toBaselineDetail`
- `toOptimizationDetail`
- `toTrialRow`
- `toTrialDetail`
- `toMetricCard`
- `toMetricCards`
- `toComparisonRows`
- `toTimelineStages`
- `toArtifactLinks`

Status mapping preserves meaning:

- `optimization_rejected` stays `optimization_rejected`
- completed pipeline states map to `pipeline_completed`
- rejected strategy outcomes map to `strategy_rejected`
- controlled backend failures map to `controlled_failure`
- system failures map to `system_failed`
- created/pending states map to `pending`
- running states map to `running`

## Error Normalization Behavior

The base client normalizes request failures into:

- `network`
- `timeout`
- `http`
- `not_found`
- `controlled_failure`
- `empty_data`
- `invalid_response`
- `rejected_strategy`
- `pipeline_rejected`

The client:

- uses `NEXT_PUBLIC_API_BASE_URL` when set
- defaults to `http://127.0.0.1:8000`
- applies a 15 second timeout by default
- parses JSON safely
- validates array/object response shape for endpoint helpers
- returns structured errors without logging payloads or secrets

## Empty-State Behavior

Empty arrays and null/empty objects are returned as successful responses with `empty: true`. UI code can render honest empty states without treating empty evidence as fake success.

Dedicated helpers:

- `isEmptyApiData`
- `emptyDataError`
- `mapEmptyResult`

## Validation Commands

```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
npm run build
```

Results:

- `npm run lint` passed
- `npm run build` passed

No frontend test framework exists yet, so adapter tests were not added in this prompt.

## Known Limitations

- `listBaselineRuns` is client-side filtering over `/api/runs` because the backend has no dedicated baseline-run list endpoint.
- Optimization trial status filtering is applied client-side after fetch because the backend currently accepts the parameter but does not apply it.
- Optimization-specific stage fields can still be empty; Prompt 3/4 UI should use generic run stage endpoints where applicable.
- No pages were built in this prompt.
- No chart library was added in this prompt.

## Whether Prompt 3 Can Continue

Prompt 3 can continue.

Recommended next scope:

- Build status, empty, loading, error, controlled-failure, copy, and table components on top of these API results and adapters.
- Keep pages read-only.
- Do not add start, approval, export, AI repair, Discord, or live trading actions.
