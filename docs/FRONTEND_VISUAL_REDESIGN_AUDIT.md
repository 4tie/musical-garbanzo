# HER Frontend Visual Redesign Audit

## Current Weak Spots

- The app already follows the dark HER design rules, but many surfaces still read as a careful admin panel rather than a premium research cockpit.
- Page rhythm is repetitive: header, warning, section card, table/card grid repeats across Dashboard, Journey, Runs, Strategies, and detail pages.
- Visual hierarchy is too flat. Important workflow state, next action, and evidence availability do not consistently dominate raw tables or secondary metadata.
- Tables and cards are functional but boxy; density, borders, and backgrounds do not create enough scan-friendly layering.
- Empty and loading states are correct but visually plain, so unavailable evidence feels like a blank area rather than an intentional "not available yet" state.
- Strategy Journey has the right data sources, but the top section mixes selector, status, actions, and latest-run text into one dense strip.
- Live workflow visibility is weak when there is no active run. The requested "No active run" state should be explicit and polished.

## Cluttered or Repetitive Pages

- `/journey`: core workflow page, but needs a stronger summary-first cockpit layout and clearer next safe action.
- `/runs`: useful table controls, but search/filter chrome should feel more integrated and less generic.
- `/strategies`: filter-heavy table page needs stronger workspace framing and cleaner scan hierarchy.
- Baseline, optimization, and validation detail pages benefit from shared card/table/metric restyling without changing their backend contracts.
- Dashboard already has real-data charts and summaries, but shared surface updates should make it feel less like stacked sections.

## Navigation Issues

- Grouped navigation works and should stay, but active state should be more prominent and the sidebar should carry the read-only safety posture more clearly.
- Existing pages only should be linked. Planned Metrics, Decisions, Artifacts, and Health destinations should not become live links until routes exist.

## Layout Changes Planned

- Tighten the shell with a layered charcoal/navy background, sticky sidebar, and more deliberate content gutters.
- Improve the sidebar brand block, active state, group spacing, and footer safety treatment.
- Upgrade `PageHeader`, `SectionCard`, `MetricCard`, `DataTable`, `EmptyState`, `LoadingSkeleton`, `LiveRunPanel`, and `NextActionPanel`.
- Rework `/journey` into a workflow cockpit:
  - strategy overview first
  - status/readiness/sidecar/latest run summary
  - explicit live workflow panel, including "No active run"
  - timeline and evidence summary beside one clear next action
  - latest baseline snapshot and readiness issues below

## What Must Stay Unchanged

- Backend behavior, schemas, endpoints, confirmation gates, and execution logic.
- All frontend API calls through `frontend/src/lib/api/*`.
- No mock metrics, fake charts, hardcoded runs, or invented strategy states.
- `ControlledFailureBanner`, validation safety copy, copy buttons, and confirmation dialogs.
- Existing route contracts for Strategy Workspace, Runs, Baseline detail, Optimization detail, Validation list, and Validation detail.

## Files Planned To Touch

- `frontend/src/app/globals.css` - theme tokens and shared visual depth.
- `frontend/src/components/AppShell.tsx` - main shell background and content width.
- `frontend/src/components/Sidebar.tsx` - navigation polish and stronger read-only safety footer.
- `frontend/src/components/PageHeader.tsx` - summary-first page framing.
- `frontend/src/components/SectionCard.tsx` - premium panel styling.
- `frontend/src/components/MetricCard.tsx` - denser evidence metric cards.
- `frontend/src/components/EmptyState.tsx` - polished unavailable-data states.
- `frontend/src/components/LoadingSkeleton.tsx` - richer loading treatment.
- `frontend/src/components/DataTable.tsx` - cleaner table surface.
- `frontend/src/components/NextActionPanel.tsx` - clearer next-action emphasis.
- `frontend/src/components/LiveRunPanel.tsx` - active/no-active run presentation.
- `frontend/src/app/journey/page.tsx` - main workflow cockpit redesign.
- `docs/FRONTEND_VISUAL_REDESIGN_REPORT.md` - final implementation and verification report.
