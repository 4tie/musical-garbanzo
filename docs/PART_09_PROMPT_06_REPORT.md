# Part 09 Prompt 06 Report

## Baseline Detail Sections Built

Built `/baseline/[runId]` as a read-only baseline evaluation detail page.

Sections included:

- header summary
- safety explanation
- metrics cards
- decision panel
- pipeline timeline
- pair results table
- trade summary
- quality flags
- artifacts and report metadata

The page includes copy-run-id and back-to-Runs controls. It does not include start, approval, export, AI, Discord, or live trading actions.

## APIs Used

The page uses the existing Prompt 2 read-only API layer:

- `getRun`
- `getBaselineRunDetail`
- `getBaselineStatus`
- `listRunStages`
- `getLatestMetrics`
- `listPairResults`
- `getTradeSummary`
- `getResultQuality`
- `getBacktestResults`
- `getLatestRunDecision`
- `listRunArtifacts`
- `getBaselineReport`

No backend mutation APIs were added or called.

## Timeline Behavior

Timeline data is selected from real API responses in this order:

1. generic run stages from `/api/runs/{run_id}/stages`
2. baseline status `stage_results`
3. baseline detail `stages`

Only returned stages are rendered. Missing stage data shows a controlled empty state.

## Metrics and Decision Behavior

Metrics are built from the latest persisted metric snapshot when available, with fallback to baseline detail/status metrics or combined backtest metrics when those APIs return data.

Metric cards are shown only for returned values:

- profit factor
- expectancy
- max drawdown
- trade count
- win rate
- net profit
- Sharpe
- Calmar

Decision data is merged from the persisted latest decision when available, plus baseline detail/status decision summaries. The panel shows classification, confidence score, policy, blocking failures, warnings, and reasons when present.

## Empty and Error States

Required data failures for run metadata or baseline detail show an error banner.

Optional missing data shows empty states instead of fake content:

- metrics
- decision
- timeline
- pair results
- trade summary
- quality flags
- artifacts/report metadata

Optional 404 responses are treated as missing evidence rather than page failure.

## Validation Commands

```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
npm run build
```

Results:

- `npm run lint` passed
- `npm run build` passed

## Whether Prompt 7 Can Continue

Prompt 7 can continue.

Recommended next scope:

- Build the optimization run detail and trials page from real optimization APIs.
- Preserve read-only behavior and keep rejected optimization results distinct from system failures.
