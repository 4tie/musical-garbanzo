# Part 09 Frontend Dashboard Plan

## Scope

Part 09 builds a read-only HER Mission Control dashboard that lets the user inspect backend evidence already persisted by Parts 03 through 08.

The dashboard must show:

- baseline runs and baseline run detail
- optimization runs and optimization run detail
- pipeline stages and controlled failures
- run decisions and result quality
- metrics, pair results, and trade summaries
- all optimization trials, best trial, and full trial parameters
- baseline vs optimized comparison
- report and artifact metadata or safe report content exposed by existing APIs
- warnings, rejected results, and safety messages

Permanent user-facing rule:

`AI suggests. Backend validates. Freqtrade tests. HER decides.`

## Prompt 08 Status: COMPLETED

All requested components from Prompt 08 (Trial Detail Drawer, Params Viewer, Best Trial Panel, Comparison Panel, Artifact Metadata Panel) were already implemented in the existing `OptimizationDetailClient.tsx` file during earlier prompts.

### Existing Components Verified

1. **Trial Detail Drawer** - `TrialDetailContent` function (lines 929-980)
   - Shows trial ID, trial number, status, is_best, is_selected_for_validation
   - Displays all metrics (profit factor, expectancy, drawdown, trade count, win rate, loss score, profit total)
   - Shows rejection reason, failure reason, parameter groups
   - Includes full params, buy params, sell params, ROI params, stoploss params, trailing params
   - Displays raw safe summary and artifact paths
   - Shows timestamps

2. **Params Viewer** - `ParamsViewer` function (lines 555-563) with `JsonSection` (lines 565-580)
   - Collapsible sections using `<details>` element
   - Copy JSON button for each section
   - Syntax-friendly JSON formatting via `safeJson` function
   - Read-only only (no editing, no save, no export, no approval)
   - Shows "Not provided by backend." when data is missing

3. **Best Trial Full Panel** - `BestTrialPanel` function (lines 887-927)
   - Shows best trial identity (trial number, ID)
   - Displays full metrics
   - Shows optimized backtest linkage
   - Displays decision result
   - Includes warning that best Hyperopt trial is only candidate evidence
   - Shows params summary and why selected
   - Full params viewer integration

4. **Baseline vs Optimized Comparison Panel** - `ComparisonPanel` function (lines 514-553)
   - Shows profit factor, expectancy, drawdown, trade count, win rate
   - Shows classification and result status
   - Visual indicators: improved, worsened, unchanged, unavailable
   - Does not imply profitability
   - Shows improvement summary and warnings

5. **Artifact Metadata Panel** - `ArtifactMetadataPanel` function (lines 462-502)
   - Shows safe artifact paths and metadata
   - Includes command metadata, stdout/stderr existence
   - Shows optimization report, optimized params artifact
   - Displays normalized result and decision report
   - Does not display huge logs by default
   - Includes note that raw artifacts are local runtime files and not committed

### APIs Used

All components use real API data from:
- `getOptimizationRunDetail`
- `getOptimizationStatus`
- `listOptimizationTrials`
- `getBestTrial`
- `getOptimizationComparison`
- `getOptimizationReport`
- `getOptimizationTrialDetail`

No API gaps identified for the requested functionality.

## Prompt 09 Status: COMPLETED

All requested polish and UX improvements from Prompt 09 have been implemented.

### Reports Page

**Location**: `frontend/src/app/reports/page.tsx`

**Implementation**: Replaced placeholder with informational page documenting report access limitation.

**Features**:
- Documents that backend does not provide a dedicated reports list endpoint
- Explains how to access different report types via run detail pages:
  - Baseline reports via `/baseline/[runId]`
  - Optimization reports via `/optimization/[optimizationRunId]`
  - Decision reports in run detail pages when decision evaluation completed
  - Normalized result reports in run detail pages when result parsing completed
  - Artifact metadata in run detail pages
- Includes safety notes about report interpretation
- No fake data or invented reports

### Artifact Viewer Metadata

**Location**: Already implemented in `BaselineDetailClient.tsx` and `OptimizationDetailClient.tsx`

**Features**:
- Artifact type display (via StatusBadge)
- Path display (monospace font)
- Created timestamp when available
- Related run ID context
- Description field
- Safety note about local runtime files not being committed
- Does not load huge raw logs by default

### Empty States

**Coverage**: All data pages have proper empty states

**Locations**:
- `page.tsx` - Dashboard, decisions, charts, timeline
- `runs/page.tsx` - Runs list
- `optimization/[optimizationRunId]/OptimizationDetailClient.tsx` - Stages, trials, charts, best trial, comparison, artifacts, trial drawer
- `baseline/[runId]/BaselineDetailClient.tsx` - Metrics, pair results, quality flags, artifacts

**States covered**:
- Loading (LoadingSkeleton)
- Empty (EmptyState with descriptive messages)
- Network error (ErrorBanner)
- Backend controlled failure (ControlledFailureBanner)
- Invalid response (ErrorBanner)
- No report available (EmptyState)
- No trials available (EmptyState)
- Stage data unavailable (EmptyState)

### Safety Banners

**Consistent wording applied**:
- "Pipeline completed, strategy rejected" - Used in optimization and baseline detail pages for rejected results
- "This is not a system failure" - Included in rejected result banners
- "No live trading action exists in this dashboard" - Added to homepage and placeholder pages
- "Read-only inspection mode" - Used on homepage and placeholder pages

**Files updated**:
- `app/optimization/[optimizationRunId]/OptimizationDetailClient.tsx`
- `app/baseline/[runId]/BaselineDetailClient.tsx`
- `app/page.tsx`
- `components/PlaceholderPage.tsx`

### Charts

**Status**: Already well-implemented with safety features

**Features**:
- Uses real data only (no fake or invented data)
- Shows empty chart state if insufficient data (< 2 points)
- Readable in dark and light mode (uses CSS variables)
- Does not use misleading green for profitability (uses accent color)
- SVG-based with proper ARIA labels
- Shows point count and axis labels

**Locations**:
- `TrialLineChart` in `OptimizationDetailClient.tsx`
- Timeline charts in `page.tsx`

### Tables

**Status**: Already well-implemented with responsiveness

**Features**:
- Fits desktop view with proper column widths
- Scrolls horizontally on smaller screens (overflow-auto wrapper)
- Respects compact/comfortable density (via ThemeProvider)
- Shows copy IDs (CopyButton component)
- Shows meaningful badges (StatusBadge component)
- Keyboard navigation (Tab, Enter, Space)
- Sortable columns with visual indicators
- Row click handlers with focus states

**Locations**:
- `DataTable` component
- Used in runs page, optimization detail, baseline detail

### Accessibility / UX Basics

**Improvements made**:
- Drawer can close with Escape key (added useEffect listener)
- All buttons have labels (aria-label where needed)
- Keyboard focus visible (focus outline styles)
- Readable contrast (CSS variables ensure proper contrast in both themes)
- Reduced motion respected (uses CSS transitions that respect prefers-reduced-motion)

**Files updated**:
- `components/Drawer.tsx` - Added Escape key handler

## Non-Goals

Part 09 must not add or expose:

- new run creation controls
- baseline or optimization start buttons
- strategy approval, export, packaging, or live trading actions
- AI repair or Ollama-triggering controls
- Discord-triggering controls
- fake data, invented runs, mock metrics, or mocked API responses shown as real
- backend pipeline behavior changes, unless a frontend API contract bug is found and documented first

Pipeline completion means pipeline mechanics completed. It does not mean the strategy is profitable, approved, exportable, or live-ready. `optimization_rejected` is a valid completed result and must be displayed as a rejected outcome, not as a system failure.

## Frontend Inventory

Stack:

- Next.js App Router in `frontend/src/app`
- React 19
- TypeScript with strict mode
- Tailwind CSS v4 through `@tailwindcss/postcss`
- No daisyUI currently installed
- No charting library currently installed
- Existing API client: `frontend/src/lib/api.ts`
- Existing types: `frontend/src/lib/types.ts`

Existing scripts in `frontend/package.json`:

- `npm run dev` -> `next dev`
- `npm run build` -> `next build`
- `npm run start` -> `next start`
- `npm run lint` -> `eslint`

Existing app routes:

- `/` dashboard with system health and action-oriented placeholder cards
- `/autoquant` placeholder
- `/strategy-lab` placeholder
- `/optimizer` placeholder
- `/runs` placeholder
- `/results` placeholder
- `/strategy-editor` placeholder
- `/ai-assistant` placeholder
- `/settings` placeholder

Existing reusable components:

- `AppShell`
- `Sidebar`
- `TopBar`
- `StatusBadge`
- `SystemHealthCard`
- `EmptyState`

Frontend gaps for Part 09:

- API client only covers health, system status, and public settings.
- Current shell is dark-only and hardcoded around gray/blue colors.
- No theme provider, accent presets, density setting, or localStorage persistence.
- No Recharts dependency.
- No table, drawer, skeleton, tabs, JSON viewer, copy button, controlled-failure banner, or pipeline timeline components.
- Current dashboard and top bar contain action-oriented UI such as `Start AutoQuant Run`, `Generate Strategy Idea`, and `Ask AI`; the Part 09 Mission Control pages must avoid action triggers.
- `frontend/src/app/layout.tsx` still uses create-next-app metadata.

## API Contract Map

All frontend calls should use the `/api` prefix. The backend also mounts most routers under `/api/v1`, but Part 09 should standardize on `/api` unless a future migration requires versioning.

### System

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/health` | Lightweight backend health | `{status, app, environment, backend}` | none | network/offline error | Top header, dashboard status |
| GET | `/api/system/status` | Local backend dependency status | backend/database/freqtrade/ollama/discord states plus paths/ports | none | configured services may be missing/disabled | Dashboard, settings |
| GET | `/api/settings/public` | Public app settings | app/env/ports/paths and configured flags | none | network/offline error | Settings |

### Runs

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/runs` | List HER runs | `RunListItem[]` with id, name, mode, status, classification, timestamps | `status`, `classification`, `strategy_id`, `limit`, `offset` | empty array when no runs match | Dashboard, Runs list |
| GET | `/api/runs/{run_id}` | Run metadata detail | `RunRead` with config fields and failure reason | `run_id` | 404 if missing | Baseline run detail, generic run drawer |
| GET | `/api/runs/{run_id}/stages` | Stage timeline | `RunStageRead[]` ordered by execution order | `run_id` | empty if none; 404 if run missing | PipelineTimeline |
| GET | `/api/runs/{run_id}/stages/{stage_key}` | Stage detail | one `RunStageRead` with input/output/error/log summary | `run_id`, `stage_key` | 404 if missing | Stage drawer |
| GET | `/api/runs/{run_id}/logs` | Run log entries | `RunLogRead[]` | `stage_key`, `level`, `limit`, `offset` | empty array | Logs panel |
| GET | `/api/runs/{run_id}/retry-history` | Controlled retry history | `RetryHistoryRead[]` | `run_id` | empty array | Failures/retries panel |

Excluded mutation endpoints for Part 09: `POST /api/runs`, run status/classification/start/complete/fail, stage start/complete/fail/skip/reset, log creation, retry creation/completion.

### Baseline

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/baseline/runs/{run_id}` | Full baseline summary | run metadata, stages, latest metrics, decision summary, artifact paths, warnings/errors | `run_id` | 404 if run missing | Baseline detail page |
| GET | `/api/baseline/runs/{run_id}/status` | Lightweight baseline status | status, classification, current stage, stage results, metrics, decision, warnings/errors | `run_id` | 404 if run missing | Dashboard cards, timeline |
| GET | `/api/baseline/runs/{run_id}/report` | Baseline report metadata | artifact id/type/description/path/hash/size/created_at | `run_id` | controlled 404 when report is absent | Reports/artifacts view |

Excluded mutation endpoint for Part 09: `POST /api/baseline/evaluate`.

### Optimization

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/optimization/runs` | List optimization runs | `OptimizationRunListItem[]` with status, result status, trial counts, best trial id | `limit`, `offset`, `status` | empty array | Dashboard, Optimization runs list |
| GET | `/api/optimization/runs/{optimization_run_id}` | Optimization detail | `{run, stages, best_trial, comparison, artifact_paths}` | `optimization_run_id` | 404 if missing; `stages` currently TODO-empty | Optimization detail page |
| GET | `/api/optimization/runs/{optimization_run_id}/status` | Lightweight optimization status | status, current stage, epochs/trials counts, timestamps | `optimization_run_id` | 404 if missing; stage fields currently null | Dashboard, detail header |
| GET | `/api/optimization/runs/{optimization_run_id}/trials` | All persisted trials | `OptimizationTrial[]` including params, metrics, status, rejection/failure reason | `limit`, `offset`, `status` | empty array if no trials | Trials table, charts |
| GET | `/api/optimization/runs/{optimization_run_id}/trials/{trial_id}` | Full trial detail | `{trial, artifact_paths}` with full params/raw trial if safe | `optimization_run_id`, `trial_id` | 404 if run/trial missing | Trial detail drawer |
| GET | `/api/optimization/runs/{optimization_run_id}/best-trial` | Best trial | `OptimizationTrial` | `optimization_run_id` | controlled 404 when no best trial | Best trial card |
| GET | `/api/optimization/runs/{optimization_run_id}/comparison` | Baseline vs optimized comparison | baseline/optimized metrics, deltas, classifications, result status, warnings | `optimization_run_id` | controlled 404 when comparison unavailable | Comparison chart/panel |
| GET | `/api/optimization/runs/{optimization_run_id}/report` | Optimization report content | `{optimization_run_id, report_artifact_path, status, report}` | `optimization_run_id` | controlled 404 when missing; 500 if report JSON cannot parse | Reports/artifacts view |

Excluded mutation endpoint for Part 09: `POST /api/optimization/run`.

### Metrics and Results

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/runs/{run_id}/metrics` | Metric history | `MetricSnapshotRead[]` | `run_id` | empty array | Metric trend chart |
| GET | `/api/runs/{run_id}/metrics/latest` | Latest metric snapshot | one `MetricSnapshotRead` | `run_id` | 404 if missing | Metric cards |
| GET | `/api/runs/{run_id}/pair-results` | Per-pair results | `PairResultRead[]` with metrics and raw JSON | `run_id` | empty array | Pair results table |
| GET | `/api/runs/{run_id}/trade-summary` | Trade summary | one `TradeSummaryRead` | `run_id` | 404 if missing | Metrics panel |
| GET | `/api/results/backtest/{run_id}` | Combined parsed result | latest metrics, pair results, trade summary, quality report, normalized artifact path, warnings | `run_id` | warning fields for missing evidence | Run detail summary |
| GET | `/api/results/backtest/{run_id}/quality` | Result quality | parse quality flags and usability booleans | `run_id` | 404 if no report | Quality banner |
| GET | `/api/runs/{run_id}/result-quality` | Compatibility quality route | same as result quality | `run_id` | 404 if no report | Quality banner |
| GET | `/api/results/backtest/{run_id}/normalized` | Normalized parsed JSON artifact | normalized metrics, pair results, quality flags, metadata, source files | `run_id` | 404 if missing artifact | JSON viewer |
| GET | `/api/results/backtest/{run_id}/decision` | Latest backtest decision | latest decision payload | `run_id` | 404 if no decision | Decision panel |
| GET | `/api/runs/{run_id}/decision` | Compatibility latest decision | latest decision payload | `run_id` | 404 if no decision | Decision panel |

Excluded mutation endpoint for Part 09: `POST /api/results/backtest/{run_id}/parse`.

### Decisions

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/decisions/policies` | List deterministic policies | `DecisionPolicySummary[]` | none | empty only if policy service changes | Settings/reference |
| GET | `/api/decisions/policies/{policy_name}` | Policy detail | thresholds, criteria, descriptions | `policy_name` | 404 if unknown | Policy drawer |
| GET | `/api/decisions/runs/{run_id}` | All saved decisions | newest-first saved decisions | `run_id` | empty array; 404 if run missing | Decision history |
| GET | `/api/decisions/runs/{run_id}/latest` | Latest saved decision | latest decision | `run_id` | controlled 404 if none | Decision card |

Excluded mutation endpoint for Part 09: `POST /api/decisions/runs/{run_id}/evaluate`.

### Artifacts and Audit

| Method | URL | Purpose | Shape Summary | Params | Empty/Failure States | Planned Consumer |
| --- | --- | --- | --- | --- | --- | --- |
| GET | `/api/artifacts` | Artifact search | `ArtifactListItem[]` | `run_id`, `strategy_id`, `artifact_type`, `limit`, `offset` | empty array | Reports/artifacts page |
| GET | `/api/artifacts/{artifact_id}` | Artifact metadata detail | `ArtifactRead` | `artifact_id` | 404 if missing | Artifact drawer |
| GET | `/api/runs/{run_id}/artifacts` | Run artifacts | `ArtifactListItem[]` | `run_id` | empty array | Run detail |
| GET | `/api/audit-logs` | Audit evidence | `AuditLogRead[]` | `run_id`, `action_type`, `limit`, `offset` | empty array | Evidence/audit panel |

Excluded mutation endpoints for Part 09: `POST /api/artifacts`, `POST /api/audit-logs`.

## Planned Pages

1. Dashboard (`/`)
   - Replace action-first placeholders with read-only overview.
   - Show system status, counts by run status/classification, recent baseline runs, recent optimization runs, recent controlled failures, and safety rule.

2. Runs list (`/runs`)
   - Generic HER run table with search/filter/sort/density.
   - Row click opens run summary or navigates to baseline detail when mode indicates baseline evidence.

3. Baseline run detail (`/runs/[run_id]` or `/baseline/[run_id]`)
   - Read-only stage timeline, metrics, quality flags, decision, pair results, trade summary, artifacts, logs.

4. Optimization runs list (`/optimizer` or `/optimization`)
   - Read-only optimization run table.
   - Status/result status filters and safe explanation for `optimization_rejected`.

5. Optimization run detail (`/optimization/[optimization_run_id]`)
   - Header, request summary, status, best trial, trial table, charts, comparison, report, artifacts.
   - Trial detail drawer for full params and raw safe JSON.

6. Reports/artifacts view (`/results` or `/artifacts`)
   - Filtered artifact table and safe report display.
   - No download/export action in Part 09 unless the API already exposes safe content and the control is clearly inspect-only.

7. Settings (`/settings`)
   - Theme mode, accent preset, table density, reduced-motion preference, API base URL display.
   - Read-only backend public settings and system status.

## Planned Components

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

## Design Direction

Style: `HER Command Center`

Requirements:

- default dark theme
- light and system theme modes
- accent presets: emerald, blue, purple, amber, rose, cyan, neutral
- theme settings persisted in localStorage
- reduced motion support via `prefers-reduced-motion` and user preference
- table density: comfortable and compact
- terminal-like readability without overcrowding
- consistent cards, tables, timelines, charts, and drawers
- no childish visuals
- no fake sample data

Status colors:

- green: completed or passed stage
- blue: running or informational
- amber: warning or controlled failure
- red: failed, rejected, or dangerous
- purple: optimization-related
- gray: skipped or neutral

## Charts, Tables, and Timeline Requirements

Charts must only render from real API data. Prompt 7 introduced dependency-free SVG charts for optimization trials; add a charting library only if later chart requirements exceed the local primitives.

Planned charts:

- runs by status
- classifications count
- trials by metric
- profit factor by trial number
- expectancy by trial number
- drawdown by trial number
- baseline vs optimized comparison
- pass/fail threshold bars

Tables must support:

- sorting
- filtering
- search
- sticky header where practical
- row click into a detail drawer
- copy IDs
- empty states
- loading states
- error states
- compact and comfortable density

Timeline must support:

- status color mapping
- controlled failure messaging
- skipped-stage display
- duration display
- stage details from output/error/log summary
- running-stage pulse only when reduced motion allows it

## Safety UX Rules

- Always display `AI suggests. Backend validates. Freqtrade tests. HER decides.` near the main dashboard context.
- Label pipeline completion separately from strategy acceptance.
- Treat `optimization_rejected`, `not_improved`, `overfit_suspected`, and `invalid_optimization` as outcome states, not app crashes.
- Show controlled failures with amber/red context and exact backend details when available.
- Never convert missing data into fabricated metrics.
- Empty arrays and 404 "not found" report responses should produce honest empty states.
- Hide or remove action controls from Part 09 Mission Control pages.
- Do not expose approval/export/live trading language.
- Do not call Ollama or Discord from frontend flows.

## Risks and Gaps

1. Optimization detail currently returns `stages: []`, and status returns `current_stage: null` and `stage_progress: null`. The UI should use generic run stage endpoints where possible or show a documented unavailable state.
2. Baseline report endpoint returns metadata only, not file content. Optimization report endpoint returns JSON content. Report UI must handle this inconsistency.
3. `/api/optimization/runs/{id}/trials` accepts `status` in the router signature but currently does not pass it to the repository call. Frontend can filter client-side for Prompt 2; backend filtering should be documented before changing behavior.
4. Run list endpoint has pagination but no total count. UI can use offset/limit and "load more", not exact page totals.
5. Several endpoint families mix GET and POST routes. The frontend API layer must expose read-only functions only for Part 09.
6. Existing dashboard/top bar placeholders include action UI that conflicts with Part 09. Prompt 2 should replace or isolate them in the Mission Control surface.
7. Decision payload shape for saved decisions is repository-driven and less strongly typed in the router than optimization/baseline schemas. The UI should use defensive rendering and JSON drill-downs.
8. Large `raw_json` fields may make table rows heavy. The UI should keep raw payloads inside drawers/lazy detail panels.
9. No frontend test harness is configured beyond lint. Prompt 2 should at least run `npm run lint`; build can be used when dependencies are stable.
10. Recharts is not installed. Prompt 7 uses local SVG chart primitives; install a charting library only if later chart complexity requires it.

## Prompt-by-Prompt Implementation Plan

### Prompt 2: Foundation Shell and Read-Only API Client

Status: completed in `Part 09: add frontend API client adapters`.

- Replaced `frontend/src/lib/api.ts` with a typed `frontend/src/lib/api/` module directory while preserving `@/lib/api` imports through `index.ts`.
- Added base GET client configuration with `NEXT_PUBLIC_API_BASE_URL` override, default `http://127.0.0.1:8000`, timeout handling, safe JSON parsing, response-shape checks, and normalized errors.
- Added read-only endpoint modules for system, runs, baseline, optimization, results, decisions, artifacts, logs, retry history, and audit logs.
- Added UI adapters for run rows, baseline detail, optimization detail, trial rows/details, metric cards, comparison rows, timeline stages, and artifact links.
- Added `frontend/scripts/api-smoke.mjs` and `npm run api:smoke` for a safe read-only development API summary.
- No run start, approval, export, AI repair, Discord, or live trading API wrappers were added.

Deferred to later prompts:

- Theme provider, localStorage settings, accent presets, density setting, and reduced-motion handling.
- Replacing action-first dashboard elements with read-only Mission Control pages.

### Prompt 3: Design System and App Shell

Status: completed as a design-system and app-shell foundation in `Part 09: add command center design system`.

- Added the HER Command Center theme system with CSS variables, default dark mode, light/system modes, accent presets, density setting, reduced-motion preference, and localStorage persistence.
- Rebuilt the app shell with left sidebar, top header, main content region, and right drawer slot.
- Added navigation items for Dashboard, Runs, Baseline, Optimization, Strategies, Reports, and Settings.
- Added reusable UI primitives: `AppShell`, `Sidebar`, `TopHeader`, `ThemeProvider`, `ThemeSettings`, `StatusBadge`, `MetricCard`, `SectionCard`, `EmptyState`, `LoadingSkeleton`, `ErrorBanner`, `ControlledFailureBanner`, `Drawer`, `Button`, `Tabs`, `PageHeader`, and `CopyButton`.
- Added read-only placeholder pages for Dashboard, Runs, Baseline, Optimization, Strategies, Reports, and Settings, plus compatibility placeholders for older routes.
- Removed action-oriented dashboard placeholders and visible AI/start/export/live trading affordances from the Part 09 shell.

Deferred to later prompts:

- Implement runs and optimization run tables with sort, filter, search, density, loading, error, and empty states.
- Add real data wiring to the placeholder pages.

### Prompt 4: Dashboard Overview

Status: completed in `Part 09: add read-only dashboard overview`.

- Replaced the Dashboard placeholder with real API-backed sections for system overview, run summary, latest activity, safety summary, and charts.
- Used the Prompt 2 read-only API layer for backend health, system status, general runs, baseline-run filtering, optimization runs, and latest decisions for recent run records.
- Used the Prompt 3 design system primitives for cards, metrics, status badges, loading states, empty states, and banners.
- Added lightweight in-app chart primitives for runs by status, result status distribution, and latest runs over time.
- Kept charts gated on real API data; empty or insufficient datasets render empty chart states.
- Wired the shell refresh button to reload Dashboard data without adding run/start actions.
- Preserved `optimization_rejected` as a rejected validation result, not a system failure.

Deferred to later prompts:

- Build baseline run detail page from baseline, run stages, metrics/results, decisions, artifacts, logs, retry history, and quality endpoints.
- Include stage timeline, metric cards, pair results, trade summary, quality flags, and decision history.

### Prompt 5: Unified Runs List

Status: completed in `Part 09: add unified runs list`.

- Replaced the Runs placeholder with a real API-backed unified table for baseline and optimization runs.
- Added frontend adapters that merge baseline-like records from `/api/runs` with optimization records from `/api/optimization/runs` without changing backend meanings.
- Added columns for run ID, type, strategy, pairs, timeframe, status, classification/result status, optimization trial count, best trial ID, created timestamp, updated timestamp, and view-only actions.
- Added search, type/status filters, sortable columns, copy-ID controls, and row-click navigation to read-only detail routes.
- Added partial-data and full-error states when one or both run sources are unavailable.
- Preserved `optimization_rejected` as a rejected validation result, not a system failure.
- Added a reusable `DataTable` component that respects the persisted comfortable/compact density setting.

Deferred to later prompts:

- Replace placeholder baseline and optimization detail routes with real API-backed detail pages.
- Add load-more or pagination when exact backend totals become available.

### Prompt 6: Baseline Run Detail

Status: completed in `Part 09: add baseline run detail page`.

- Build baseline run detail from baseline, run stages, metrics/results, decisions, artifacts, logs, retry history, and quality endpoints.

Implemented:

- Replaced the baseline detail placeholder route with a read-only API-backed view.
- Added header summary with run id copy, strategy, pairs, timeframe, status, classification, and timestamps.
- Added safety explanation that pipeline completion is separate from strategy approval and rejection is not a system failure.
- Added real metric cards, decision panel, pipeline timeline, pair results table, trade summary, quality flags, and artifact/report metadata sections.
- Timeline uses generic run stages first, then baseline status/detail stage data as fallback, and only shows stages returned by APIs.
- Optional 404 responses for metrics, quality, report, decision, and artifacts render empty sections instead of fake data.

Deferred to later prompts:

- Add richer stage-detail drawers and raw JSON viewers.
- Add retry history and logs as collapsed detail panels if requested by later evidence prompts.

### Prompt 7: Optimization Detail and Trials

Status: completed in `Part 09: add optimization detail and trials table`.

- Replaced the optimization detail placeholder route with a read-only API-backed view.
- Added header summary with optimization run ID, strategy, pairs, timeframe, status, result status, epochs, spaces, and timestamps.
- Added the required `optimization_rejected` explanation copy without treating rejected validation as system failure.
- Added summary cards for loaded trial count, best trial number/ID, baseline run ID, optimized run ID, and result status.
- Added all-trials table with search, filters, sortable metrics, copy trial ID controls, and a read-only trial detail drawer.
- Added real-data SVG charts for profit factor, expectancy, drawdown, and loss score by trial number.
- Added best trial panel with params summary, metrics summary, selection context, and warning that best Hyperopt trial is not approved by itself.
- Added comparison preview and report metadata sections.
- Optional 404 responses for best trial, comparison, and report render empty/partial states instead of fake data.

Deferred to later prompts:

- Add richer report and artifact explorer pages.
- Add broader chart library only if later pages require more complex charts.

### Prompt 8: Charts

- Expand chart coverage where later pages have enough real data.
- Render charts only when real API data exists.
- Add empty states when chart data is missing.

### Prompt 9: Reports, Artifacts, and Evidence

- Build reports/artifacts view and audit evidence panels.
- Normalize baseline metadata-only report display and optimization JSON report display.

### Prompt 10: Verification and Polish

- Run lint/build.
- Browser-check dashboard, runs list, baseline detail, optimization detail, settings, and empty states.
- Verify no Part 09 page exposes start, approval, export, AI repair, Discord, or live trading actions.
