# HER Frontend Visual Redesign Report

## Design Direction

- Chosen direction: premium dark trading research cockpit, using deep charcoal/navy surfaces, cyan accent, semantic status colors, compact cards, and stronger workflow hierarchy.
- Visual concept generated with the built-in image tool as a design anchor: `/home/mohs/.codex/generated_images/019f1bcb-4f24-74c3-8f55-1336114c0b3c`.
- Implementation stayed code-native. No raster UI, mock charts, fake strategy data, or placeholder metrics were added.

## Pages Changed

- `/journey`: reworked into the main workflow cockpit with strategy overview, live workflow state, timeline, evidence summary metrics, and one next safe action.
- `/validation`: converted the list page away from hardcoded light Tailwind colors to shared dark HER components.
- Existing major pages affected by shared component restyling: Dashboard, Strategy Workspace, Runs, Baseline detail, Optimization detail, Validation detail, Results, Reports, Settings.

## Components Changed

- `AppShell`, `Sidebar`, `TopHeader`, `PageHeader`, `SectionCard`
- `MetricCard`, `EmptyState`, `LoadingSkeleton`, `DataTable`
- `NextActionPanel`, `LiveRunPanel`, `Button`
- `ThemeProvider`
- `useRunPolling`

## Functionality Preserved

- All API calls still go through `frontend/src/lib/api/*`.
- Strategy Workspace still loads real workspace strategy summaries from `/api/strategies`.
- Runs page still reads baseline and optimization APIs and remains read-only.
- Validation list still reads `listValidationRuns`.
- Confirmation gates and run forms were not removed or bypassed.
- Copy buttons and controlled failure components were not removed.
- No backend execution behavior, database schema, Freqtrade runner, thresholds, or repositories were changed.

## Real Data Handling

- Journey strategy, readiness, sidecar, run counts, latest validation state, and workflow timeline are derived from existing backend responses.
- Journey metric cards read latest baseline detail metrics when a real latest baseline exists.
- Missing metrics render "Not available yet"; no fallback numbers or fake charts are shown.
- Live workflow panel shows "No active run." unless a real pending/running baseline or optimization run exists.

## Still Unavailable

- Metrics/Decisions/Artifacts/Health sidebar links were not added because there are no matching real pages yet.
- Journey cannot show stage-level progress for validation runs because the existing `LiveRunPanel` only supports baseline and optimization polling.
- The top header still shows `Backend: unknown` on pages that do not pass `systemStatus` into `AppShell`; this is existing header wiring, not backend failure.

## Verification

- Browser plugin availability: absent in this session.
- Fallback used: system Chrome headless screenshots because Playwright's managed browser was not installed and the Playwright Node module was not available as a project dependency.
- Backend started read-only for smoke checks: `../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000`.
- Frontend started at `http://localhost:3000`: `npm run dev -- --port 3000`.
- Screenshots captured outside the repo:
  - `/tmp/her-journey-desktop.png`
  - `/tmp/her-journey-mobile.png`
  - `/tmp/her-strategies-desktop.png`
  - `/tmp/her-runs-desktop.png`
  - `/tmp/her-validation-desktop.png`
- Manual visual checks confirmed:
  - Frontend opens without crash.
  - Sidebar navigation works on desktop.
  - Mobile Journey content no longer horizontally overflows.
  - Strategy Workspace loads real `AIStrategy` records from backend.
  - Runs page shows a real empty state without mock rows.
  - Validation list shows a real empty state without mock rows.
  - No chart uses fake data.
  - No run starts without confirmation.
  - Safety footer remains visible in the sidebar on desktop.

## Test Results

- `cd frontend && npm run lint`
  - Result: passed with 3 pre-existing warnings:
    - `frontend/src/app/optimization/page.tsx`: unused `useRef`
    - `frontend/src/app/optimization/page.tsx`: unused `RiskProfileSelect`
    - `frontend/src/components/SystemHealthCard.tsx`: unused `SectionCard`
- `cd frontend && npm run build`
  - Result: passed.
- Backend tests were not run because no backend files were changed.

## Repo Hygiene

- `git ls-files | grep -E '(__pycache__|\\.pyc|\\.venv|node_modules|\\.next)'`
  - Result: empty.
- Runtime directories such as `node_modules` and `.next` were generated locally during verification but are untracked/ignored.

## Known Issues

- The desktop sidebar is hidden on small screens to prevent horizontal overflow. A future pass should add a mobile navigation drawer or compact top navigation.
- Some older pages outside this patch may still contain hardcoded light-mode classes and should be migrated gradually to the shared component system.
- The lint warnings listed above remain outside this redesign slice.

## Next Recommendation

Add a compact mobile navigation drawer and then migrate remaining hardcoded page-level styling to shared HER primitives, starting with baseline and optimization detail pages.
