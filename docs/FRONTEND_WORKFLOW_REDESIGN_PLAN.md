# Frontend Workflow Redesign Plan

## Objective

Redesign and improve the HER frontend UI/UX while preserving all backend behavior.
The goal is to make HER feel like a real strategy discovery cockpit — guiding the user
clearly through the strategy lifecycle from readiness check through validation evidence.

## Design Principles

- Dark navy/charcoal background with glass-like cards
- Accent color: cyan (`#06b6d4`) — analytical, not hype
- Success: controlled green (`#22c55e`)
- Warning: amber (`#f59e0b`)
- Failure: red (`#ef4444`)
- No fake data, no mock charts, no approval/export/live-trading controls
- Every page answers: what is this, what data is real, what is the status, what is next

## Changes Made

### 1. Navigation — `Sidebar.tsx`
- Grouped navigation into four sections: Discover, Test, Evidence, System
- Added "Strategy Journey" link (`/journey`) under Discover
- Reduced sidebar width from 256px to 240px for slightly more content space
- Retained "Evidence only. No live trading actions." footer disclaimer

### 2. Default Accent Color — `globals.css`
- Changed default accent from emerald (`#10b981`) to cyan (`#06b6d4`)
- Cyan feels more analytical and less "profit-hype" than green
- All existing accent variants (emerald, blue, purple, amber, rose, cyan, neutral) preserved

### 3. New Page — `/journey`
- Full strategy lifecycle page at `frontend/src/app/journey/page.tsx`
- Strategy selector dropdown (fetches from `/api/strategies`)
- Journey timeline using `WorkflowStepper` — shows 6 lifecycle steps
- Live run panel for any active baseline or optimization run
- Evidence summary sidebar showing run counts and latest status per type
- Latest baseline snapshot cards
- Strategy issues section (if any readiness issues)
- NextActionPanel with links to relevant detail pages
- All data fetched from real backend APIs; no fake data

### 4. New Component — `WorkflowStepper`
- Horizontal or vertical stepper for journey lifecycle
- 6 step statuses: `not_started`, `running`, `passed`, `failed`, `blocked`, `skipped`
- Clickable step labels link to detail pages when available
- Timestamps shown when backend provides them
- No fake completion — "not started" shown when no backend record exists

### 5. New Component — `LiveRunPanel`
- Uses existing `useRunPolling` hook (2s interval, stops on terminal state)
- Pulsing dot indicator for active runs
- Shows current stage name
- Shows last updated time
- Shows "Polling every 2s" while active
- Shows "Retry" button when polling has stopped
- Shows polling errors without crashing

### 6. New Component — `NextActionPanel`
- Tooltip-enhanced action buttons
- Supports `primary`, `secondary`, `warning` tones
- Supports `href` navigation or `onClick` callbacks
- Renders nothing when no actions are available

### 7. Validation Detail Redesign — `/validation/[validationRunId]/page.tsx`
- Completely removed all light-mode Tailwind classes (`text-gray-*`, `bg-green-100`, etc.)
- Replaced with `var(--app-*)` CSS variable system throughout
- Added proper `PageHeader`, `ControlledFailureBanner`, `CopyButton` components
- Added `SectionCard` wrappers for all sections
- Added `StatusBadge` components replacing hardcoded inline badge styles
- Added final decision section with blocking failures, reasons, warnings, next actions
- Added proper loading skeleton and error states consistent with other pages
- Kept all existing safety disclaimers

### 8. OOSValidationCard Redesign
- Replaced all gray/green/red hardcoded classes with CSS variables
- Added proper `SectionCard` title action with `StatusBadge`
- Added `description` to explain what OOS is
- Metric grid uses consistent border/bg styling

### 9. WFOValidationCard Redesign
- Same treatment as OOS card
- Pass rate bar now uses gradient from green/warning/danger based on rate
- Window table styled with dark theme (no `bg-white`, `bg-gray-50` etc.)
- `StatusBadge` used for window pass/fail status

### 10. RobustnessValidationCard Redesign
- Same treatment as OOS/WFO cards
- Overall status card at top
- Per-check cards with consistent dark styling
- Issues and warnings use CSS variable colors

## APIs Used

| Component / Page | API endpoint |
|---|---|
| Journey page | `/api/strategies`, `/api/baseline/runs`, `/api/optimization/runs`, `/api/validation/runs` |
| LiveRunPanel | `/api/baseline/{id}/status`, `/api/optimization/{id}/status` (via `useRunPolling`) |
| Validation detail | `/api/validation/runs/{id}`, `/api/validation/runs/{id}/evidence` |

## Polling Behavior

- `useRunPolling` hook polls every 2 seconds while status is active
- Polling stops automatically on terminal states: `completed`, `failed`, `rejected`, `controlled_failure`, `error`
- "Last updated" timestamp shown from backend data
- "Retry" button appears when polling is stopped
- No fake progress — stage-based status only
