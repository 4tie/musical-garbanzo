# Part 14: Guided Strategy Workflow Report

## Summary

This report documents the frontend redesign implemented for the HER strategy discovery system,
focusing on the guided strategy workflow, live run monitoring, optimization charts, validation
evidence redesign, and manual workflow checklist.

## What Pages Changed

### Modified Pages

| Page | What Changed |
|------|-------------|
| `/validation/[validationRunId]` | Full redesign: dark theme, proper components, final decision section, improved evidence cards |

### New Pages

| Page | Description |
|------|------------|
| `/journey` | Strategy Journey page — full lifecycle view with stepper, live run panel, evidence summary |

### Modified Components

| Component | What Changed |
|-----------|-------------|
| `Sidebar.tsx` | Grouped nav into Discover/Test/Evidence/System sections, added Journey link |
| `OOSValidationCard.tsx` | Full dark theme redesign, StatusBadge, description, proper metric grid |
| `WFOValidationCard.tsx` | Full dark theme redesign, pass rate bar, dark table, StatusBadge for windows |
| `RobustnessValidationCard.tsx` | Full dark theme redesign, per-check cards, issue/warning lists |
| `globals.css` | Default accent changed from emerald to cyan |

### New Components

| Component | Description |
|-----------|------------|
| `WorkflowStepper.tsx` | Vertical/horizontal lifecycle stepper with 6 step statuses |
| `LiveRunPanel.tsx` | Live run progress panel using `useRunPolling` hook |
| `NextActionPanel.tsx` | Contextual next-action button panel with tooltips |

## What APIs Are Used

### Journey Page
- `GET /api/strategies` — list all strategies for selector
- `GET /api/baseline/runs` — list baseline runs (filtered client-side by strategy)
- `GET /api/optimization/runs` — list optimization runs (filtered client-side by strategy)
- `GET /api/validation/runs` — list validation runs (filtered client-side by strategy)

### LiveRunPanel (via `useRunPolling`)
- `GET /api/baseline/{runId}/status` — polls baseline status every 2s
- `GET /api/optimization/{runId}/status` — polls optimization status every 2s

### Validation Detail
- `GET /api/validation/runs/{id}` — full validation run detail
- `GET /api/validation/runs/{id}/evidence` — OOS, WFO, robustness, sensitivity evidence

## What Live Polling Does

The `LiveRunPanel` component uses the existing `useRunPolling` hook:
- Polls every 2 seconds while the run status is active (`running`, `pending`, `queued`)
- Automatically stops polling when a terminal state is reached:
  - `completed`, `failed`, `optimization_rejected`, `rejected`, `controlled_failure`, `error`
- Shows the current stage key (mapped to a human-readable label)
- Shows "Last updated" timestamp from backend `updated_at` field
- Shows "Polling every 2s" indicator while active
- Shows "Retry" button when polling is stopped
- Shows polling errors without crashing the UI
- Does not show fake progress percentages

## What Charts Were Added

No new charting libraries were added. The existing SVG-based charts in `OptimizationDetailClient`
remain unchanged. All existing trial charts (profit factor, expectancy, drawdown, loss score) continue
to use real trial data only.

The WFO pass rate bar in `WFOValidationCard` is a simple CSS progress bar — not a chart library —
and uses real `passed / total` counts from the backend.

## Real Data vs Unavailable Data

### Real data (from backend):
- Strategy readiness and issues
- Baseline run status, classification, timestamps
- Optimization run epochs, result status, timestamps
- Validation run decision status, timestamps
- OOS evidence: status, metrics, issues, warnings, timerange
- WFO evidence: windows, pass rate, per-window metrics
- Robustness evidence: check results, issues, warnings
- Final validation decision: status, reasons, blocking failures

### Not available / deferred:
- Live Freqtrade process output streaming (no WebSocket endpoint in backend)
- Per-step progress percentage during baseline (backend does not provide granular progress)
- Strategy pair performance charts on Journey page (available on baseline detail page)
- Historical strategy performance trends (no aggregate trend endpoint)

## What Remains Deferred

- WebSocket-based live log streaming (would require backend WebSocket endpoint)
- Journey page "Start Baseline" / "Start Optimization" action buttons (require confirmation dialog integration — available on baseline/optimization detail pages)
- Strategy workspace integration on journey page (links to `/strategies/{name}`)
- Optimization trial chart mini-previews on journey page (full charts on optimization detail)

## Backend Changes

No backend changes were made. No endpoints were added or removed. No behavior was changed.

## Test Results

Run verification commands:

```bash
cd frontend && npm run lint
cd frontend && npm run build
```

## Repo Hygiene

```bash
git status --short
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
```

Expected: no runtime files tracked, no fake data committed.

## Key Safety Rules Maintained

1. No "profitable" language in any new UI
2. No live trading controls
3. No fake data or mock charts
4. Every run action still requires confirmation dialog
5. All existing safety banners preserved
6. Validation evidence disclaimer present on validation detail page
7. `ControlledFailureBanner` present on validation detail and journey pages
8. "Evidence only" disclaimer in sidebar footer
