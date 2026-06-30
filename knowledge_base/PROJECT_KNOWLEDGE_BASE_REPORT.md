# HER Knowledge Base Completion Report

## Summary

This report records the files created and updated as part of the HER Project Knowledge Base and AI Onboarding Index task. No backend or frontend source code was modified.

---

## Files Created or Updated

| File | Action | Contents |
|---|---|---|
| `README.md` | Updated | Project summary, tech stack, Replit + local start commands, repo layout, safety rules, knowledge base index, disclaimer |
| `AGENTS.md` | Created | AI assistant rules: project identity, backend/frontend/safety rules, scope limits, source-of-truth table, how to report work |
| `docs/PROJECT_CHARTER.md` | Created | What HER is, corrected product definition, core workflow, classification levels, project boundaries |
| `docs/SAFETY_RULES.md` | Created | 10 non-negotiable safety rules: no live trading, confirmation gates, no fake evidence, secrets redaction, no runtime commits, Freqtrade command safety, AI layer boundaries, audit trail, controlled failure |
| `docs/GLOSSARY.md` | Created | 30+ domain term definitions: artifact, baseline, best trial, candidate, confidence score, controlled failure, decision engine, elite, expectancy, Freqtrade, gate, HER, hyperopt, loss score, metrics snapshot, OOS, optimized run, optimization run, pair dependency, positive expectancy, profit factor, promising, readiness gate, rejected, robustness, run, run stage, sensitivity, sharpe, sidecar JSON, strategy, strategy version, trade count, trial, validated, validation run, WFO |
| `docs/FRONTEND_UX_GUIDE.md` | Created | Design direction, CSS variable system, sidebar structure, status badge system, page structure conventions, real-data-only rule, loading/empty/error states, live run polling rules, confirmation rules, validation disclaimers, decision display rules, next action panel rules, navigation table |
| `knowledge_base/API_INDEX.md` | Created | Every endpoint: method, path, request fields, response fields, frontend client function, pages that use it; mismatch flags |
| `knowledge_base/WORKFLOW_INDEX.md` | Created | 7 implemented workflows + 3 planned: readiness check, baseline pipeline (8 stages), optimization pipeline (17 stages), validation pipeline (OOS+WFO+robustness), decision engine, result parsing, strategy import |
| `knowledge_base/CODE_MAP.md` | Created | File-by-file map: backend (entry, core, db, repositories, services, schemas, routers) + frontend (pages, API clients, components, hooks, config) with responsibility, used-by, and do-not-break notes |
| `knowledge_base/RUNBOOK.md` | Created | Environment assumptions, start commands (Replit + local), verification checklist, install commands, test/lint/build commands, repo hygiene, manual smoke workflow, common failure table, DB reset procedure, what must never be deleted, `.env` reference |
| `project_plan/ROADMAP.md` | Created | Completed Parts 01–14, immediate next steps (trial charts, comparison view, smoke tests, mismatch fixes), next product direction (AI Strategy Designer, Repair Agent, candidate promotion, discovery loop), later goals (Monte Carlo, portfolio validation, dry-run prep) |

---

## Mismatches Discovered

These are API/frontend discrepancies found during documentation. No code was changed — they are recorded here and in `API_INDEX.md` for the next engineering session.

| # | Mismatch | Detail |
|---|---|---|
| 1 | Frontend calls `GET /api/freqtrade/strategies` | No such endpoint in the Freqtrade router; router has `GET /api/v1/freqtrade/status` and `GET /api/v1/freqtrade/workspace`. Frontend client `freqtrade.ts` may be calling a non-existent path. |
| 2 | Frontend calls `GET /api/freqtrade/data` | No GET data endpoint in the Freqtrade router; router has `POST /data/check` and `POST /data/download` only. |
| 3 | Frontend calls `GET /api/baseline/runs/{id}/report` | Not confirmed in the baseline router (which has `evaluate`, `runs/{id}`, `runs/{id}/status`). May exist as an unlisted route or may be a missing implementation. |
| 4 | Frontend calls `GET /api/decisions/runs/{runId}/latest` | Not confirmed in the decisions router. May be a missing convenience route. |
| 5 | Frontend calls `GET /api/runs/{runId}/decision` | Appears to be a convenience route not confirmed in the runs router. May be handled by the decisions router under a different path. |
| 6 | Frontend calls separate `GET .../best-trial` and `GET .../comparison` | Backend detail endpoint may combine these; separate convenience routes not confirmed. |

**Recommended fix:** Audit `frontend/src/lib/api/*.ts` clients against the running FastAPI `/docs` endpoint to confirm which calls return 404 in practice, then either add the missing backend routes or update the frontend clients to use the correct paths.

---

## Source Code Changes

**None.** No backend Python files and no frontend TypeScript/TSX files were modified. The only source code change during the broader session (before this task) was the `frontend/next.config.ts` `allowedDevOrigins` update and the `frontend/src/app/journey/page.tsx` TypeScript fix (`timeframe` → `mode` on `RunListItem`).

---

## Commands Run During This Task

```bash
mkdir -p knowledge_base project_plan
```

No tests were run (documentation-only task). No lint or build was triggered.

---

## Remaining Gaps

| Gap | Priority | Notes |
|---|---|---|
| Mismatch resolution (6 items above) | High | Required before next frontend development session |
| `docs/FRONTEND_UX_GUIDE.md` chart section | Medium | Chart library (recharts? d3?) not confirmed — optimization trial charts not yet implemented |
| `knowledge_base/API_INDEX.md` decisions router | Medium | `POST /api/decisions/runs/{id}/evaluate` internal/external exposure not fully confirmed |
| `project_plan/ROADMAP.md` timelines | Low | Roadmap has no dates — intentional (local project, no sprint schedule) |
| Audit log pagination | Medium | Frontend `listAuditLogs()` may hit performance issues without cursor pagination on large datasets |

---

## Next Recommended Step

**Resolve the 6 API mismatches** listed above. Start by running the backend with `--reload` and checking `http://localhost:8000/docs` against `knowledge_base/API_INDEX.md` to confirm which paths exist. Then either:
- Add missing backend routes (e.g., `GET /api/baseline/runs/{id}/report`, `GET /api/decisions/runs/{runId}/latest`)
- Or update frontend clients to call the correct existing paths

This is a quick audit that will prevent silent 404 errors in the frontend when those code paths are exercised.
