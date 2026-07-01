# HER Frontend Visual Redesign Report

**Date:** 2026-07-01  
**Scope:** Full frontend visual redesign — no backend changes  
**Commit message:** `Frontend: redesign HER visual system and workflow layout`

---

## Design Direction Chosen

**Concept:** Premium dark trading research cockpit  
**Palette:** Deep navy backgrounds (`#070b12`) with layered dark surfaces, electric cyan accent (`#06b6d4`), semantic status colors  
**Feel:** Calm, technical, evidence-driven — not casino, not crypto hype

Key decisions:
- Deeper, more layered dark backgrounds with three distinct surface levels
- Thinner, more precise borders (`#1d2d42`)
- Breadcrumb section context in top header instead of dead search input
- Strategy Journey promoted to first nav position under Discover
- MetricCard decoupled from SectionCard — standalone flat cards, no nested borders
- WorkflowStepper with SVG icons and animated ping for running state
- StatusBadge with optional dot indicator for at-a-glance scanning
- NextActionPanel styled with accent border to stand out as the primary CTA
- Dashboard amber safety banner replaced with a subtle one-line info strip

---

## Pages Changed

| Page | Change |
|---|---|
| `/` Dashboard | Removed misused amber ControlledFailureBanner, replaced with subtle info strip |
| `/journey` | Previously improved cockpit header remains; now uses redesigned components |
| All pages | All use redesigned AppShell, Sidebar, TopHeader, SectionCard, StatusBadge |

---

## Components Changed

| Component | What Changed |
|---|---|
| `globals.css` | Refined color tokens (deeper navy, 3-layer surfaces), new shadow tokens, sidebar/header height CSS variables |
| `Sidebar.tsx` | Rebranded to "AutoQuant / Strategy Lab", Strategy Journey listed first (primary dot), narrower (228px), cleaner group labels, refined active state |
| `TopHeader.tsx` | Removed disabled search input, added breadcrumb (`HER › SECTION`), 56px height, SVG refresh icon, dot-enhanced backend status |
| `AppShell.tsx` | Max-width updated to 1320px, removed `overflow-hidden` from outer, uses CSS var for sidebar width |
| `SectionCard.tsx` | Title reduced to `text-sm`, description to `text-xs`, added `noPad` prop for full-bleed content, added `accent` prop for top-border highlight, removed `card-hover` (hover effect now opt-in) |
| `MetricCard.tsx` | Removed SectionCard wrapper entirely — standalone `div` with own border/bg, monospace value option, label uses 10px uppercase tracking |
| `StatusBadge.tsx` | Added `dot` prop for colored dot indicator; refined color intensities; expanded `inferTone` with more status strings |
| `EmptyState.tsx` | Replaced "HER" text default icon with SVG circle+crosshair; added optional `action` slot |
| `PageHeader.tsx` | Title reduced to `text-xl`, description to `text-xs` — less visual competition with section headers |
| `Button.tsx` | Tightened sizing (`h-9` for md), refined disabled opacity, subtle `shadow-sm` on primary |
| `WorkflowStepper.tsx` | Larger circles (36px), SVG checkmark/cross icons, animated ping for running state, timestamp right-aligned, connector uses step color |
| `NextActionPanel.tsx` | Accent-bordered panel with SVG arrow icon, UPPERCASE tracking title, more compact action buttons |

---

## Routes Affected

All routes — they all use `AppShell` which wraps `Sidebar` and `TopHeader`.  
No route was added, removed, or structurally changed.

---

## Functionality Preserved

- ✅ All API calls and data fetching unchanged
- ✅ Strategy Workspace loads real strategies
- ✅ Runs page loads real runs
- ✅ Baseline / Optimization / Validation detail load real backend data
- ✅ Confirmation dialogs untouched
- ✅ Copy buttons untouched
- ✅ Controlled failure messages on actual failure states preserved
- ✅ Safety disclaimers kept (reformatted, not removed)
- ✅ Empty states show when real data is unavailable
- ✅ No mock data added anywhere
- ✅ No chart data fabricated
- ✅ Backend unchanged

---

## What Data Is Real

All data rendered in the frontend comes from real API responses:
- `/api/strategies` — strategy list and readiness
- `/api/runs`, `/api/baseline/runs`, `/api/optimization/runs`, `/api/validation/runs`
- `/health`, `/api/system/status`

---

## What Remains Unavailable

- Search functionality — still disabled (no search backend)
- Profit factor / expectancy on journey page — requires completed run records (none exist yet)
- Pairs / risk profile on journey page — pairs shown from optimization runs; risk profile not in `RunListItem` shape (only in `RunRead`, which requires a separate fetch per run)

---

## Build / Lint Results

```
npm run lint  →  ✓ 0 errors, 0 warnings
npm run build →  ✓ All 18 routes built successfully
npx tsc       →  ✓ 0 type errors
```

---

## Repo Hygiene

```
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
→ no tracked build artifacts
```

---

## Known Issues

- `Backend: unknown` appears on initial journey page load (before health check resolves) — this is a timing issue in all pages that don't pass `systemStatus` to AppShell; the badge resolves after the first API call
- `SectionCard` `card-hover` was removed from all cards by default; any card that was previously hover-interactive and relied on this for feedback may feel less reactive — but no cards were actually click-targets, so this is acceptable

---

## Next Recommendations

1. **Add `systemStatus` to journey page `AppShell`** — currently the journey page doesn't fetch system status so the header shows "Backend: unknown" on first load
2. **Task #2** — Add optimization trial charts and baseline comparison view (the data model is there; recharts or similar SVG charts are ready to add)
3. **Task #4** — API smoke test suite to catch regressions
4. **Strategy Journey improvements** — fetch `RunRead` for the latest baseline to display pairs/risk_profile in the cockpit header
