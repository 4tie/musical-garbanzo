# UI Workflow Acceptance Checklist

## Build Verification

- [ ] `cd frontend && npm run lint` — passes with no errors
- [ ] `cd frontend && npm run build` — produces successful build
- [ ] No TypeScript errors in new components

## Safety Rules

- [ ] No guaranteed profit language anywhere in new code
- [ ] No "approved for live trading" text
- [ ] No one-click live trading controls
- [ ] No exchange order controls
- [ ] No fake metrics or fake charts
- [ ] No fake run IDs or fake completed states
- [ ] No hidden execution
- [ ] No auto-run without confirmation
- [ ] `ControlledFailureBanner` present on validation detail page
- [ ] Validation evidence disclaimer present: "Validation is evidence only. It is not strategy approval, export, live-trading authorization, or a guarantee of future performance."

## Existing Functionality Preserved

- [ ] Dashboard page works as before
- [ ] Baseline list page works as before
- [ ] Baseline detail page works as before (including Run Validation button)
- [ ] Optimization list page works as before
- [ ] Optimization detail page works as before (including Run Validation button)
- [ ] Validation list page works as before
- [ ] Strategies page works as before
- [ ] Runs page works as before
- [ ] Settings page works as before
- [ ] Reports page works as before
- [ ] `ValidationConfirmationDialog` still used in baseline and optimization detail
- [ ] Copy buttons for IDs and artifact paths still present

## New Features

- [ ] Strategy Journey page exists at `/journey`
- [ ] Strategy Journey page is linked in sidebar under "Discover"
- [ ] Journey page shows strategy selector dropdown
- [ ] Journey page shows workflow stepper with 6 steps
- [ ] Journey page shows "Not started" when no backend data exists for a step
- [ ] Journey page shows live run panel when a run is active
- [ ] Journey page shows evidence summary sidebar
- [ ] Journey page shows next action panel with backend-driven links
- [ ] Journey page shows strategy readiness issues
- [ ] `WorkflowStepper` component exists and supports vertical/horizontal orientation
- [ ] `LiveRunPanel` component exists and uses `useRunPolling`
- [ ] `NextActionPanel` component exists

## Validation Evidence Redesign

- [ ] Validation detail page uses dark theme CSS variables only
- [ ] No hardcoded gray/green/red Tailwind classes in validation detail
- [ ] `OOSValidationCard` uses dark theme
- [ ] `WFOValidationCard` uses dark theme and has pass rate progress bar
- [ ] `RobustnessValidationCard` uses dark theme
- [ ] Final decision section visible with blocking failures, reasons, warnings
- [ ] Proper loading and error states consistent with rest of app

## Design System

- [ ] Default accent color is now cyan (`#06b6d4`)
- [ ] Sidebar groups navigation into: Discover, Test, Evidence, System
- [ ] All new components use `var(--app-*)` CSS variables only

## Data Integrity

- [ ] No fake data in any new component or page
- [ ] No mock charts
- [ ] All charts use real backend data only
- [ ] Empty states shown when no backend data exists
- [ ] Controlled failure banners preserved everywhere they existed
