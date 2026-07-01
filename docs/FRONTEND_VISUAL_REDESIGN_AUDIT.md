# HER Frontend Visual Redesign Audit

**Date:** 2026-07-01
**Scope:** UI/UX visual redesign — no backend changes

---

## What Currently Looks Weak

### Layout & Shell
- `TopHeader` contains a permanently-disabled search input that takes up width and signals "unfinished prototype"
- Sidebar code badges (DB, JN, ST…) feel developer-tool-ish, not polished
- Content max-width is `max-w-7xl` — acceptable but padding/spacing feels slightly cramped on medium screens
- No visual hierarchy between page title (in shell) and page-level `PageHeader` — both repeat the same title

### Cards & Components
- `MetricCard` wraps `SectionCard` — this creates a card nested inside a card. When metric cards are used inside a `SectionCard` grid, the result is double borders and double hover effects, which looks amateur.
- `SectionCard` title is plain `text-base font-semibold` — blends into content too easily; no visual distinction from body text
- `card-hover` applies `translateY(-1px)` on all `SectionCard` uses, including static metric grids — causes jittery mass-hover on grids
- `EmptyState` defaults to "HER" text as icon — generic and doesn't convey meaning
- `LoadingSkeleton` shimmer is subtle but correct

### Banners & Notices
- `ControlledFailureBanner` is amber/warning-styled but used on the Dashboard and Journey page as a generic "read-only inspection mode" notice — amber implies a problem; a read-only notice should be info/neutral
- Multiple pages stack the same "evidence only / no live trading" text redundantly (banner + footer + disclaimer)
- `ErrorBanner` is functional but visually heavy

### Status Badges
- `StatusBadge` is functional but lacks a dot indicator — status meaning relies only on color, which is less readable at a glance
- Badges are slightly too tall (`min-h-6`) for dense data tables

### Pages
- **Dashboard**: Large amber "Read-only inspection mode" banner above system overview makes the first impression feel like a warning screen
- **Journey**: Previously improved — cockpit header added, action buttons added
- **Runs**: Correct but sparse — filters are functional, table is readable
- **Baseline detail**: Correct — stages, metrics, decisions present
- **Optimization detail**: Has charts but they're SVG-based bar/line charts rendered inline
- **Validation detail/list**: Functional

### Navigation
- "Strategy Journey" should be the primary cockpit entry, but visually it appears as a peer of "Dashboard"
- Sidebar footer `"Evidence only. No live trading actions."` is good but easy to miss

---

## What Pages Are Too Cluttered

- **Dashboard** — banner + 4-card grid + 5-card summary + 3-column activity + 3-column charts is too much vertically. Key insight is buried.
- **Baseline detail** — all sections at same visual weight; summary should be above stages
- **Optimization detail** — trials table + drawer + charts + comparison all compete

---

## What Sections Are Repetitive

- "Evidence only" / "read-only" disclaimers appear in banner, footer, and page copy on multiple pages
- Page title appears in both `TopHeader` H1 and `PageHeader` H1 on every page
- "No real data yet" / "No runs found yet" appears in multiple identical empty states

---

## What Navigation Is Confusing

- "Runs" (generic list) and "Baseline" / "Optimization" / "Validation" (specific list + start form) are at the same level — users may not know which to use
- "Results" and "Reports" in Evidence are unclear without tooltips
- Some sidebar items (ai-assistant, autoquant, optimizer, strategy-lab, strategy-editor) exist as routes but are not in sidebar

---

## What Layout Should Change

- TopHeader: remove disabled search; make thinner (56px); cleaner right-side controls
- MetricCard: standalone card, no SectionCard wrapper
- SectionCard headers: add a subtle accent treatment, make title more visually distinct
- WorkflowStepper: larger circles, better timeline feel
- NextActionPanel: more premium call-to-action design
- Dashboard: move disclaimer to a subtle top strip instead of a large amber banner

---

## What Components Will Be Touched

| Component | Change |
|---|---|
| `globals.css` | Token refinements, add surface layers |
| `Sidebar.tsx` | Better branding, hierarchy, active states |
| `TopHeader.tsx` | Remove dead search, cleaner layout |
| `AppShell.tsx` | Minor padding/max-width improvements |
| `SectionCard.tsx` | Better header treatment, `noPad` prop, soften hover |
| `MetricCard.tsx` | Remove SectionCard wrapper — standalone card |
| `StatusBadge.tsx` | Add dot indicator, more compact |
| `EmptyState.tsx` | Remove "HER" default icon, better design |
| `WorkflowStepper.tsx` | Larger circles, better typography |
| `NextActionPanel.tsx` | Premium action panel design |
| `PageHeader.tsx` | Remove redundant title (now in shell) — keep description only |
| `Button.tsx` | Minor size/weight refinements |
| `LoadingSkeleton.tsx` | Keep as-is (works correctly) |
| `ControlledFailureBanner.tsx` | Keep semantic amber for actual failures |
| Dashboard `page.tsx` | Replace generic amber banner with subtle info notice |

---

## What Should Stay Unchanged

- All API calls and data fetching logic
- All confirmation dialogs
- All controlled failure messages on actual failure states
- All safety disclaimers on validation pages
- All copy buttons
- Color tokens (keep the cyan/navy palette — it's correct)
- Route structure
- Authentication/auth approach (none)
