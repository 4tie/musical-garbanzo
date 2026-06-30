# Part 09 Prompt 01 Report

## Files Inspected

Frontend:

- `frontend/package.json`
- `frontend/src/app/layout.tsx`
- `frontend/src/app/globals.css`
- `frontend/src/app/page.tsx`
- `frontend/src/app/runs/page.tsx`
- `frontend/src/app/results/page.tsx`
- `frontend/src/app/settings/page.tsx`
- `frontend/src/app/autoquant/page.tsx`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/TopBar.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/components/SystemHealthCard.tsx`
- `frontend/src/components/EmptyState.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- `frontend/postcss.config.mjs`
- `frontend/next.config.ts`
- `frontend/tsconfig.json`

Backend:

- `backend/app/main.py`
- `backend/app/api/v1/routers/runs.py`
- `backend/app/api/v1/routers/run_stages.py`
- `backend/app/api/v1/routers/baseline.py`
- `backend/app/api/v1/routers/optimization.py`
- `backend/app/api/v1/routers/results.py`
- `backend/app/api/v1/routers/decisions.py`
- `backend/app/api/v1/routers/artifacts.py`
- `backend/app/api/v1/routers/metrics.py`
- `backend/app/api/v1/routers/logs.py`
- `backend/app/api/v1/routers/retry_history.py`
- `backend/app/api/v1/routers/audit_logs.py`
- `backend/app/schemas/runs.py`
- `backend/app/schemas/run_stages.py`
- `backend/app/schemas/baseline.py`
- `backend/app/schemas/optimization.py`
- `backend/app/schemas/backtest_results.py`
- `backend/app/schemas/metrics.py`

Docs:

- `docs/API_CONTRACTS.md`
- `docs/BASELINE_EVALUATION.md`
- `docs/OPTIMIZATION_PIPELINE.md`
- `docs/OPTIMIZATION_REAL_VALIDATION.md`
- `docs/PART_08_COMPLETION_REPORT.md`

## Frontend Stack Summary

The frontend is a Next.js App Router app using React 19, TypeScript, and Tailwind CSS v4. The current app has a basic dark shell, sidebar navigation, top bar, health cards, status badge, and empty-state component.

The frontend is still mostly placeholder-level for Part 09:

- `/` shows system health but also action-oriented placeholder controls.
- `/runs`, `/results`, `/autoquant`, and `/settings` are placeholders.
- `frontend/src/lib/api.ts` only wraps health, system status, and public settings.
- There is no Recharts dependency yet.
- There is no theme provider, localStorage-backed settings, accent preset handling, table density support, drawer, table, timeline, JSON viewer, or chart components.

Existing scripts:

- `dev`: `next dev`
- `build`: `next build`
- `start`: `next start`
- `lint`: `eslint`

## API Contract Map Summary

The backend mounts read/write routers under `/api` and `/api/v1`. Part 09 should use only read-only GET endpoints.

Read-only endpoints available for Part 09:

- system: `/health`, `/api/system/status`, `/api/settings/public`
- runs: `/api/runs`, `/api/runs/{run_id}`
- stages: `/api/runs/{run_id}/stages`, `/api/runs/{run_id}/stages/{stage_key}`
- baseline: `/api/baseline/runs/{run_id}`, `/api/baseline/runs/{run_id}/status`, `/api/baseline/runs/{run_id}/report`
- optimization: `/api/optimization/runs`, `/api/optimization/runs/{optimization_run_id}`, `/api/optimization/runs/{optimization_run_id}/status`, `/api/optimization/runs/{optimization_run_id}/trials`, `/api/optimization/runs/{optimization_run_id}/trials/{trial_id}`, `/api/optimization/runs/{optimization_run_id}/best-trial`, `/api/optimization/runs/{optimization_run_id}/comparison`, `/api/optimization/runs/{optimization_run_id}/report`
- metrics/results: `/api/runs/{run_id}/metrics`, `/api/runs/{run_id}/metrics/latest`, `/api/runs/{run_id}/pair-results`, `/api/runs/{run_id}/trade-summary`, `/api/results/backtest/{run_id}`, `/api/results/backtest/{run_id}/quality`, `/api/runs/{run_id}/result-quality`, `/api/results/backtest/{run_id}/normalized`
- decisions: `/api/decisions/policies`, `/api/decisions/policies/{policy_name}`, `/api/decisions/runs/{run_id}`, `/api/decisions/runs/{run_id}/latest`, `/api/results/backtest/{run_id}/decision`, `/api/runs/{run_id}/decision`
- artifacts/evidence: `/api/artifacts`, `/api/artifacts/{artifact_id}`, `/api/runs/{run_id}/artifacts`, `/api/audit-logs`
- logs/retries: `/api/runs/{run_id}/logs`, `/api/runs/{run_id}/retry-history`

Mutation endpoints exist in the same routers and must not be surfaced in Part 09.

## Pages Planned

- Dashboard: read-only Mission Control overview, system status, run counts, optimization summaries, recent controlled failures, safety rule.
- Runs list: searchable/filterable/sortable table of HER runs.
- Baseline run detail: stage timeline, metrics, result quality, decision, pair results, trade summary, logs, artifacts.
- Optimization runs list: searchable/filterable/sortable optimization table with result-status semantics.
- Optimization run detail: run summary, all trials, best trial, comparison, report, artifacts, trial drawer.
- Reports/artifacts view: artifact and report metadata/content where safely exposed by API.
- Settings: theme mode, accent preset, density, reduced motion, and read-only backend settings/status.

## Components Planned

- `AppShell`
- `Sidebar`
- `TopHeader`
- `ThemeProvider`
- `ThemeSettings`
- `StatusBadge`
- `MetricCard`
- `SectionCard`
- `DataTable`
- `EmptyState`
- `LoadingSkeleton`
- `ErrorBanner`
- `ControlledFailureBanner`
- `PipelineTimeline`
- `Drawer`
- `TrialParamsViewer`
- `JsonViewer`
- `ComparisonChart`
- `MetricTrendChart`
- `PageHeader`
- `CopyButton`
- `Tabs`

## Risks and Gaps Found

1. Optimization stages are not fully exposed by the optimization detail/status endpoints. `get_optimization_run` returns `stages=[]`; `get_optimization_status` returns `current_stage=None` and `stage_progress=None`.
2. Baseline report and optimization report endpoints are inconsistent. Baseline report returns artifact metadata only; optimization report returns parsed JSON content.
3. Optimization trial status filtering is accepted by the router but not currently passed into `repo.list_trials`, so frontend should filter client-side until a backend change is deliberately planned.
4. Run list pagination has `limit` and `offset` but no total count.
5. Current frontend dashboard includes run-start and AI-oriented placeholders. Those conflict with Part 09 read-only rules and should be replaced in Prompt 2.
6. Current top bar includes an `Ask AI` button. The Part 09 Mission Control shell should not expose that control.
7. Existing frontend API client is too small for Part 09 and should be expanded with read-only functions only.
8. Large `raw_json` and `raw_trial` payloads should be displayed lazily in drawers or JSON viewers, not in main tables.
9. Decision saved-result payloads are less strictly typed at the router boundary than optimization/baseline responses, so the UI should render them defensively.
10. Recharts is not installed, so chart implementation requires a dependency addition in a later prompt.

## Backend Changes Needed Before UI

No backend changes are required before Prompt 2.

The documented gaps are manageable in the frontend:

- use generic `/api/runs/{run_id}/stages` where optimization-specific stage fields are unavailable
- show honest empty/unavailable states for missing report, stage, or quality data
- filter optimization trial status client-side for now
- keep raw payloads out of high-level tables

## Whether Prompt 2 Can Continue

Prompt 2 can continue.

Recommended Prompt 2 scope:

- Build the read-only Mission Control foundation.
- Replace action-oriented dashboard/top-bar controls with inspection-only UI.
- Add theme/density settings and read-only API client functions.
- Do not add run start, approval, export, AI repair, Discord, or live trading controls.
- Do not change backend behavior unless a contract mismatch blocks the UI and is documented first.
