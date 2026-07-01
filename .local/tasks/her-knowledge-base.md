# HER Project Knowledge Base & AI Onboarding Index

## What & Why
Create a structured, comprehensive documentation layer for the HER project so that any future AI assistant, developer, or coding agent can navigate and understand the system without inspecting the entire codebase from scratch. This is a documentation-only task — no backend or frontend behavior is changed.

## Done looks like
- `README.md` (root) updated with project summary, tech stack, commands, workflow, and safety disclaimer
- `AGENTS.md` (root) created with strict AI behavior rules, safety rules, forbidden actions, and scope guidance
- `docs/PROJECT_CHARTER.md` — what HER is, why it exists, corrected product definition, and terminology
- `docs/SAFETY_RULES.md` — all safety constraints (no live trading, no fake evidence, confirmation rules, secrets redaction, etc.)
- `docs/GLOSSARY.md` — definitions for all domain terms (strategy, baseline, trial, OOS, WFO, candidate, elite, etc.)
- `docs/FRONTEND_UX_GUIDE.md` — design direction, dark dashboard style, chart/real-data rules, polling rules, error/empty/loading states
- `knowledge_base/API_INDEX.md` — full API index built from inspecting FastAPI routers and frontend API clients; each endpoint documented with method, path, source file, purpose, request/response fields, execution flags, confirmation requirements, frontend client and page; mismatches and missing integrations flagged
- `knowledge_base/WORKFLOW_INDEX.md` — all major implemented workflows documented with frontend page, API calls, backend services, DB repos, artifacts, status/failure states, and next action; planned/future workflows clearly marked
- `knowledge_base/CODE_MAP.md` — file-by-file map of backend (routers, services, repos, schemas, DB, tests) and frontend (routes, API clients, components, layouts); each entry has path, responsibility, used-by, and do-not-break notes
- `knowledge_base/RUNBOOK.md` — install assumptions, start commands, test/lint/build commands, repo hygiene, manual smoke workflow, common failures, and what not to delete
- `project_plan/ROADMAP.md` — completed foundation, immediate next steps (frontend workflow redesign, Strategy Journey page, etc.), next product direction (AI Strategy Designer, Repair Agent, candidate promotion), and later goals
- `knowledge_base/PROJECT_KNOWLEDGE_BASE_REPORT.md` — completion report listing files created, mismatches discovered, whether source code changed, commands run, and next recommended step
- No source code (backend or frontend) modified
- No runtime files committed

## Out of scope
- Any backend behavior changes
- Any frontend behavior changes (except fixing broken docs links if discovered)
- Inventing endpoints, workflows, or metrics that do not exist
- Adding fake data, mock results, or profit guarantees
- Implementing any features from the roadmap

## Steps
1. **Inspect backend routers and frontend API clients in depth** — Read all FastAPI router files (`runs.py`, `strategies.py`, `optimization.py`, `freqtrade.py`, and any others) and all frontend API client files (`runs.ts`, `strategies.ts`, `optimization.ts`, `client.ts`, etc.) to build a complete, accurate picture of every real endpoint, its parameters, and its frontend usage. Flag mismatches.

2. **Write `README.md`** — Update the root README with project summary, HER goal, core rule (AI suggests → Backend validates → Freqtrade tests → HER decides), tech stack, backend/frontend start commands, test commands, repo hygiene rules, high-level workflow, and safety disclaimer.

3. **Write `AGENTS.md`** — Create the AI assistant instruction file covering project identity, behavior rules, backend and frontend source-of-truth rules, all safety rules (no live trading, no fake data, no profit guarantees, no hidden execution, confirmation-before-run), forbidden runtime files, expected workflow before editing, required tests before commit, how to report completed work, and how to avoid scope creep.

4. **Write `docs/PROJECT_CHARTER.md`** — Document what HER is, why it exists, the problem it solves, the corrected product definition, the core Strategy → Baseline → Optimization → Validation → Candidate Decision workflow, and the meaning of each status label (promising, validated, rejected, elite).

5. **Write `docs/SAFETY_RULES.md`** — Enumerate every safety constraint from the spec and any additional ones found in the codebase (e.g. `AI_PERMISSIONS.md`, `VALIDATION_POLICY.md`): no live trading, no exchange orders, no approval/export unless gates pass, no fake evidence, confirmation required, secrets redaction, stdout/stderr handling, runtime files not committed, Freqtrade command safety rules.

6. **Write `docs/GLOSSARY.md`** — Define all domain terms: HER, strategy, sidecar JSON, readiness gate, baseline, optimization, trial, best trial, optimized run, validation, OOS, WFO, robustness, sensitivity, candidate, promising, validated, rejected, elite, positive expectancy, profit factor, drawdown, trade count, controlled failure, artifact, runtime file.

7. **Write `docs/FRONTEND_UX_GUIDE.md`** — Document design direction, dark dashboard style, workflow-first layout, real-data-only charts, no fake states/progress, live polling rules, run confirmation rules, error/empty/loading states, status badge meanings, decision banner wording, validation disclaimer, and next action panel rules. Base on `UI_BLUEPRINT.md` and frontend component inspection.

8. **Write `knowledge_base/API_INDEX.md`** — Using the endpoint data gathered in Step 1, produce the full indexed API reference grouped by domain (system, strategies, strategy workspace, runs, run stages, baseline, optimization, validation, metrics, results, decisions, artifacts, logs, retry history, audit logs, freqtrade). Include all required fields per endpoint and flag any mismatches or missing frontend integrations.

9. **Write `knowledge_base/WORKFLOW_INDEX.md`** — Document all implemented workflows (strategy readiness, baseline run, optimization, validation, OOS, WFO, robustness, result parsing, decision) with frontend page/component, API calls, backend services, DB repos, artifacts, status/failure states, and next action. Mark all future/planned workflows clearly.

10. **Write `knowledge_base/CODE_MAP.md`** — Produce the file-by-file backend and frontend code map with paths, responsibilities, used-by relationships, and do-not-break notes for critical components (e.g. `ValidationExecutionService`, `OptimizationRepository`, `decision_engine.py`, `backtest_result_parser.py`).

11. **Write `knowledge_base/RUNBOOK.md`** — Document install assumptions, backend/frontend start commands, test/lint/build commands, repo hygiene commands, manual smoke workflow steps, common failures and their meanings, how to reset runtime files safely, and what must never be deleted.

12. **Write `project_plan/ROADMAP.md`** — Produce the roadmap covering: completed foundation, immediate next (frontend workflow redesign, Strategy Journey page, live run panel, optimization charts, validation evidence redesign, smoke test), next product direction (AI Strategy Designer, deterministic StrategySpec, AI Repair Agent, candidate promotion, discovery loop), and later goals (Monte Carlo, portfolio-level validation, dry-run prep).

13. **Write `knowledge_base/PROJECT_KNOWLEDGE_BASE_REPORT.md`** — Create the completion report: files created/updated, contents summary, API/frontend/backend mismatches discovered, confirmation that no source code changed, any commands run, repo hygiene result, remaining gaps, and next recommended step.

14. **Validate and commit** — Run `git status --short` and `git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'` to confirm only documentation files changed and no runtime files are staged. Commit with message: `Docs: add HER project knowledge base and AI onboarding index`.

## Relevant files
- `backend/app/main.py`
- `backend/app/api/v1/routers/runs.py`
- `backend/app/api/v1/routers/strategies.py`
- `backend/app/api/v1/routers/optimization.py`
- `backend/app/api/v1/routers/freqtrade.py`
- `backend/app/repositories/runs.py`
- `backend/app/repositories/strategies.py`
- `backend/app/repositories/artifacts.py`
- `backend/app/services/freqtrade_backtest_runner.py`
- `backend/app/services/optimization_pipeline_service.py`
- `backend/app/services/decision_engine.py`
- `backend/app/services/backtest_result_parser.py`
- `backend/app/core/config.py`
- `backend/app/core/constants.py`
- `backend/app/db/sqlite.py`
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/runs.ts`
- `frontend/src/lib/api/strategies.ts`
- `frontend/src/lib/api/optimization.ts`
- `frontend/src/app/autoquant/`
- `frontend/src/app/strategy-lab/`
- `frontend/src/app/optimizer/`
- `frontend/src/app/results/`
- `frontend/src/app/runs/`
- `frontend/src/components/AppShell.tsx`
- `frontend/src/components/Sidebar.tsx`
- `frontend/src/components/WorkflowStepper.tsx`
- `docs/BACKEND_ARCHITECTURE.md`
- `docs/PROJECT_STRUCTURE.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/DECISION_ENGINE.md`
- `docs/VALIDATION_POLICY.md`
- `docs/QUALITY_RULES.md`
- `docs/FREQTRADE_INTEGRATION.md`
- `docs/AI_PERMISSIONS.md`
- `docs/UI_BLUEPRINT.md`
- `docs/PARTS_ROADMAP.md`
- `README.md`
