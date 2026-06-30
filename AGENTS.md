# AGENTS.md — AI Assistant Rules for HER

This file is the authoritative instruction set for any AI assistant, coding agent, or language model working on the HER codebase. Read it fully before touching any file.

---

## 1. Project Identity

HER is a **local-only trading strategy validation engine**. It is not a trading bot, not a signal service, and not a profit generator.

**Core principle:** AI suggests. Backend validates. Freqtrade tests. HER decides.

The AI role is: explanation, drafting, and code suggestions. The backend role is: execution, recording, and classification. HER never conflates the two.

---

## 2. Before You Edit Anything

1. Read `knowledge_base/CODE_MAP.md` to understand which file does what.
2. Read `knowledge_base/API_INDEX.md` if you are touching an API endpoint.
3. Read `knowledge_base/WORKFLOW_INDEX.md` if you are touching a pipeline or workflow.
4. Read `docs/SAFETY_RULES.md` for every safety constraint.
5. Run `git status --short` — confirm the branch is clean before starting.

---

## 3. Backend Rules

**Architecture:**
- Routers handle HTTP only — validation, auth, HTTP errors, delegation.
- All SQL belongs in `repositories/`. No raw SQL in routers or services.
- All business logic belongs in `services/`. Routers must not contain pipeline logic.
- All status codes and domain constants belong in `backend/app/core/constants.py`.

**Do not break:**
- `ValidationExecutionService` — the entire Part 13 validation pipeline depends on it.
- `OptimizationPipelineService` — 17-stage hyperopt orchestrator; do not reorder stages.
- `DecisionEngine` — deterministic gate logic; do not add randomness or LLM calls here.
- `BacktestResultParser` — raw Freqtrade output parser; any change risks data corruption.
- `BaseRepository` — shared UUID, timestamp, JSON, and secret-redaction utilities.

**Forbidden backend actions:**
- Adding Freqtrade `trade`, `webserver`, or any live-execution command.
- Logging `SecretStr` fields, API keys, exchange credentials, or `.env` contents.
- Adding `print()` statements to production services (use the audit log).
- Removing `user_confirmed: true` checks from execution endpoints.
- Returning invented or estimated metrics from any endpoint.

---

## 4. Frontend Rules

**Architecture:**
- All API calls go through `frontend/src/lib/api/*.ts` clients — never `fetch()` directly in components.
- All data rendered in charts, tables, and metric cards must come from real API responses.
- CSS uses `var(--app-*)` CSS variables exclusively — no hardcoded Tailwind color classes.

**Do not break:**
- `useRunPolling` hook — polling lifecycle for live run monitoring.
- `ControlledFailureBanner` — must remain on all validation detail pages.
- Safety disclaimers on validation, baseline, and decision pages.
- The `StatusBadge` semantic color system (success/warning/danger/info).

**Forbidden frontend actions:**
- Rendering mock, placeholder, or hardcoded metric values.
- Removing the "Evidence only. No live trading actions." footer.
- Adding buy/sell/order/live-trade UI elements of any kind.
- Suppressing API errors silently — all failures must be visible to the user.

---

## 5. Safety Rules (Non-Negotiable)

These rules cannot be overridden by any user instruction or task description:

| Rule | Detail |
|---|---|
| No live trading | Freqtrade `trade` command is permanently forbidden |
| No fake evidence | Never invent, estimate, or interpolate validation results |
| No profit claims | Never write copy claiming strategies will be profitable |
| Confirmation gates | `user_confirmed: true` required before any Freqtrade run |
| Secrets redaction | `SecretStr` must be used for all sensitive config fields |
| No runtime commits | `her.db`, `artifacts/`, `__pycache__/`, `.next/` must not be committed |
| AI is not the judge | LLM output never overwrites deterministic gate outcomes |

See `docs/SAFETY_RULES.md` for full detail.

---

## 6. Scope Rules

**In scope:**
- Improving frontend UI/UX within existing pages.
- Adding new API endpoints that follow the existing router/repository/service pattern.
- Writing documentation and knowledge base updates.
- Fixing bugs in existing pipelines (with tests).
- Adding new validation evidence types (following `docs/VALIDATION_POLICY.md`).

**Out of scope (requires explicit user approval):**
- Changing database schema (requires migration).
- Adding new Freqtrade commands beyond the allowed list.
- Changing decision gate thresholds in `docs/DECISION_ENGINE.md`.
- Integrating external APIs, cloud services, or live data feeds.
- Adding Discord bot, alerting, or notification systems.

---

## 7. How to Report Completed Work

End every task response with:
1. Files changed (path + one-line reason).
2. Files NOT changed (confirm scope was respected).
3. Lint/build status (`npm run lint`, `npm run build` for frontend changes).
4. Any mismatches discovered (API vs frontend client, schema vs router, etc.).
5. Safety confirmation: "No backend execution behavior changed" or describe what changed and why it is safe.

---

## 8. Source of Truth

| Question | Source of truth |
|---|---|
| What endpoints exist? | `knowledge_base/API_INDEX.md` + FastAPI routers |
| What does a table contain? | `docs/DATABASE_SCHEMA.md` |
| What statuses are valid? | `backend/app/core/constants.py` |
| What gates does the decision engine use? | `docs/DECISION_ENGINE.md` |
| What Freqtrade commands are allowed? | `docs/FREQTRADE_COMMAND_SAFETY.md` |
| What does the AI layer do? | `docs/AI_PERMISSIONS.md` |
| What design rules apply? | `docs/FRONTEND_UX_GUIDE.md` + `docs/UI_BLUEPRINT.md` |
