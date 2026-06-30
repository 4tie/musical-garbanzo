# HER Frontend UX Guide

This document defines the design rules, component conventions, data-rendering rules, and interaction patterns for the HER Next.js frontend. It is the authority for all UI decisions.

---

## 1. Design Direction

**Dark-mode first.** The dashboard is permanently dark. No light-mode toggle exists or should be added. The palette is analytical, not commercial — no bright gradients, no gamification, no "trading platform" aesthetics.

**Workflow-first layout.** Every page exists to help the user understand where a strategy is in the validation lifecycle and what evidence has been collected. Navigation flows from left to right: Discover → Test → Evidence.

**Evidence over decoration.** Charts and tables render only when real data is available. Empty states explain why data is absent. Loading states show a spinner. Neither shows placeholder numbers or sample charts.

---

## 2. CSS Design System

All colors are defined as CSS custom properties in `frontend/src/app/globals.css`. **No hardcoded Tailwind color classes** (e.g., `text-green-500`, `bg-gray-800`) may be used in components. Always use the `var(--app-*)` variables.

| Variable | Purpose |
|---|---|
| `--app-bg` | Page background |
| `--app-surface` | Card/panel background |
| `--app-surface-muted` | Subtle secondary surface |
| `--app-border` | Border color |
| `--app-text` | Primary text |
| `--app-text-muted` | Secondary/label text |
| `--app-accent` | Primary accent (cyan `#06b6d4`) |
| `--app-accent-hover` | Hover state for accent |
| `--app-success` | Pass/healthy state (green) |
| `--app-warning` | Caution/partial state (amber) |
| `--app-danger` | Failure/error state (red) |
| `--app-radius` | Border radius (consistent rounding) |

---

## 3. Sidebar Navigation

The sidebar is grouped into four sections with semantic labels:

| Group | Items |
|---|---|
| **DISCOVER** | Dashboard, Strategy Journey, Strategies |
| **TEST** | Runs, Baseline, Optimization, Validation |
| **EVIDENCE** | Results, Reports |
| **SYSTEM** | Settings |

**Rules:**
- Active item has background `var(--app-accent)` with white text.
- Inactive items use `var(--app-text-muted)` and highlight on hover.
- Each item has a two-letter abbreviation badge for visual scanning.
- The sidebar footer always shows: "Evidence only. No live trading actions."

---

## 4. Status Badge System

`StatusBadge` is the canonical component for all status/classification indicators. It accepts a `status` string and maps it to a semantic variant:

| Status string(s) | Variant | Color |
|---|---|---|
| `ok`, `healthy`, `available`, `validated`, `passed`, `success` | `success` | Green (`--app-success`) |
| `promising`, `candidate`, `running`, `pending`, `optimizing` | `info` or `optimization` | Cyan/blue |
| `unknown`, `unavailable`, `partial`, `warning` | `warning` | Amber (`--app-warning`) |
| `rejected`, `failed`, `failed_controlled`, `error`, `danger` | `danger` | Red (`--app-danger`) |
| `empty`, `not_started` | `muted` | Gray |

Never use raw color classes to indicate status. Always use `StatusBadge`.

---

## 5. Page Structure Conventions

Every page follows this structure:

```tsx
<PageHeader
  title="Page Title"
  description="One-sentence description of what this page shows."
/>

{/* Safety banner if needed */}
<ControlledFailureBanner ... />

{/* Page content in SectionCard containers */}
<SectionCard title="Section" description="What this section shows.">
  ...
</SectionCard>
```

**`PageHeader`** — Title, description, optional action buttons (never "Buy", "Sell", "Trade").

**`SectionCard`** — Groups related content. Has a title, optional description, and optional header action slot.

**`MetricCard`** — Displays a single metric: `label`, `value`, optional `sub` text, optional `variant` for color-coding.

---

## 6. Real-Data-Only Rule

**No component may render estimated, hardcoded, or mock data.**

Enforcement:
- API calls return `null | undefined` when data is not available. Components check for this and render an empty state, not a fallback number.
- Chart components only render when their data array has at least one item. An empty array renders an empty-state message, not a blank chart or sample data.
- No `Math.random()` calls in any production component.
- No hardcoded strategy names, metric values, or run IDs in any JSX.

---

## 7. Loading, Empty, and Error States

Every data-dependent section must handle all three states explicitly:

**Loading:** Show a spinner or skeleton. Never show stale data from a previous fetch.

**Empty:** Show an explanatory message: "No runs found yet. Run data will appear after backend validation pipelines create records." Include a link to the relevant action page if appropriate.

**Error:** Show the error message from the API response. Never suppress API errors. Use `var(--app-danger)` for error text. Include a "Retry" button where polling is applicable.

---

## 8. Live Run Polling

The `useRunPolling` hook (`frontend/src/hooks/useRunPolling.ts`) provides real-time run status updates:

- **Interval:** 2 seconds while the run is in a non-terminal state.
- **Terminal states:** `completed`, `failed`, `failed_controlled`, `rejected`, `candidate`, `promising`, `validated`. Polling stops on any terminal state.
- **Error handling:** If the API call fails, the error is surfaced in the UI. Polling continues until a terminal state or the component unmounts.
- **`LiveRunPanel` component:** The standard UI for monitoring an active run. Shows current stage name, pulsing dot indicator, elapsed time, and a "Retry" button on error.

---

## 9. Run Confirmation Rules

Before submitting any request that launches a Freqtrade execution:

1. Show a confirmation dialog describing exactly what will run: strategy name, timeframe, pairs, and mode.
2. The confirm button must not be pre-selected.
3. The request body must include `user_confirmed: true`.
4. After submission, immediately switch to the live run panel view.

Do not skip confirmation or auto-confirm for any reason.

---

## 10. Validation Pages — Required Disclaimers

Every validation-related page (`/validation`, `/validation/[id]`, decision result sections) must display:

- `ControlledFailureBanner` when the validation status is `rejected` or `failed_controlled`.
- The text: "Past backtest performance does not guarantee future live trading results."
- The text: "This evidence is for research and evaluation purposes only."

These disclaimers are non-negotiable and must not be removed, hidden, or styled in a way that makes them less prominent than the surrounding content.

---

## 11. Decision and Classification Display

When displaying decision engine results:

- Show `classification` using `StatusBadge` with the correct variant.
- Show the `confidence_score` as a number out of 100, labeled "Evidence strength" — never "Accuracy" or "Probability".
- Show individual gate results (`gates_json`) as a pass/fail checklist.
- Show `blocking_failures_json` prominently if classification is `rejected`.
- Show `warnings_json` with amber indicators.
- Never display the classification without also showing at least one piece of supporting evidence (gates, metrics, or blocking failures).

---

## 12. Next Action Panel

The `NextActionPanel` component surfaces the system's recommendation for what the user should do after a run completes. Rules:

- Show the `next_action` field from the decision result or run record.
- If the run is `rejected`, show the specific reason and the suggested remediation step.
- If the run is `candidate` or `promising`, show the path forward (optimization, validation).
- If the run is `validated`, show the export/review option — but no auto-export.
- Never invent a next action; always render only what the backend provides.

---

## 13. Navigation and Routing

| Path | Purpose |
|---|---|
| `/` | Dashboard — system health + recent activity |
| `/journey` | Strategy Journey — full lifecycle for one strategy |
| `/strategies` | Strategy library |
| `/strategies/[name]` | Strategy detail + readiness |
| `/runs` | All runs (baseline + optimization) |
| `/baseline` | Start a baseline evaluation |
| `/baseline/[runId]` | Baseline detail + evidence |
| `/optimization` | Start an optimization run |
| `/optimization/[id]` | Optimization detail + trials |
| `/validation` | List validation runs |
| `/validation/[id]` | Validation evidence detail |
| `/results` | Results browser |
| `/reports` | Reports list |
| `/settings` | System settings |
| `/ai-assistant` | Local AI assistant |

All navigation is read-only inspection except for the "start" pages (`/baseline`, `/optimization`, `/validation` form views) which require confirmation before any action.
