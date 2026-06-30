# Part 09 Prompt 05 Report

## Runs Table Built

Built the read-only unified Runs page at `/runs`.

The table includes:

- run id
- type: baseline or optimization
- strategy name
- pairs
- timeframe
- status
- classification or result status
- trials count for optimization records when exposed by the list endpoint
- best trial id for optimization records
- created timestamp
- updated timestamp
- view-only action

No run controls, approval controls, export controls, AI controls, Discord controls, or live trading controls were added.

## APIs Used

The Runs page uses the Prompt 2 read-only API client:

- `listBaselineRuns`
- `listOptimizationRuns`
- `mergeUnifiedRunRows`

Baseline rows are derived from baseline-like records returned by `/api/runs`.
Optimization rows come from `/api/optimization/runs`.

## Filters and Search Behavior

Added client-side search across:

- id
- run type
- strategy name
- pairs
- timeframe
- status
- classification
- result status
- best trial id

Added filters:

- all
- baseline
- optimization
- completed
- failed
- rejected
- controlled failure

The table supports sortable columns where values are available.
The table uses the persisted theme density setting for comfortable or compact row spacing.
Run IDs can be copied with the copy button.
Rows navigate to read-only detail routes.

## Status Mapping

The page maps backend status and result values into clear UI labels:

- `pipeline_completed` -> completed pipeline
- `optimization_rejected` -> rejected result
- `strategy_rejected` -> rejected result
- `system_failed` -> failed pipeline
- `controlled_failure` -> controlled failure
- `running` -> running
- `pending` -> pending

`optimization_rejected` is not treated as a system crash.
Its result copy is:

`Optimization completed, but validation rejected the optimized result.`

## Empty and Error States

If no runs match the loaded real data, the page shows:

`No runs found. This dashboard is read-only and does not start pipelines yet.`

If one source fails and the other loads, the page shows a controlled partial-data banner and keeps the available real rows visible.

If both baseline and optimization sources fail, the page shows an error banner and does not render fallback or mock data.

## Validation Commands

```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
npm run build
```

Results:

- `npm run lint` passed
- `npm run build` passed

## Whether Prompt 6 Can Continue

Prompt 6 can continue.

Recommended next scope:

- Replace the baseline and optimization detail placeholders with real API-backed detail pages.
- Keep row destinations read-only.
- Continue showing empty states instead of fake records or invented metrics.
