# HER — AutoQuant Strategy Lab

> **AI suggests. Backend validates. Freqtrade tests. HER decides.**

HER is a local-only trading strategy validation system. It is **not** a profit generator and makes **no** promises about future trading results. It is a rigorous evidence engine that records, evaluates, and classifies backtest evidence using deterministic gates — then surfaces that evidence for human review.

---

## What HER does

1. **Discover** — Import or design Freqtrade-compatible strategies via the Strategy Workspace.
2. **Baseline** — Run a full backtest through the HER pipeline; parse and evaluate results.
3. **Optimize** — Run Hyperopt trials; select the best trial; compare against baseline.
4. **Validate** — Run OOS, WFO, and robustness checks; collect structured evidence.
5. **Decide** — Decision engine applies deterministic gates; assigns `rejected`, `candidate`, `promising`, or `validated`.
6. **Inspect** — Frontend dashboard surfaces all evidence, artifacts, and decisions read-only.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 |
| Backend | FastAPI · Python 3.11 · Pydantic v2 · SQLite (via SQLAlchemy) |
| Database | SQLite (`data/her.db`) |
| Trading engine | Freqtrade (local install, CLI only) |
| AI (local) | Ollama — suggestion only, never execution |
| Artifacts | Local filesystem (`artifacts/`, `freqtrade_workspace/`) |
| Secrets | `.env` file only — never hardcoded |

---

## Quick Start (Replit)

Two workflows are pre-configured. Start them from the **Workflows** pane or they auto-start:

| Workflow | Command | Port |
|---|---|---|
| **Start application** | `cd frontend && npm run dev -- --port 5000` | 5000 (webview) |
| **Backend API** | `cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` | 8000 (console) |

API docs (when backend is running): `http://localhost:8000/docs`

### Quick Start (Local machine)

```bash
# Backend
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # starts on port 3000 by default
```

---

## Key Commands

```bash
# Frontend lint
cd frontend && npm run lint

# Frontend production build check
cd frontend && npm run build

# Backend tests
pytest backend/tests -v

# Check no runtime files are staged
git status --short
git ls-files | grep -E '(__pycache__|\.pyc|node_modules|\.next|\.venv|her\.db)'
```

---

## Repository Layout

```
her/
├── backend/
│   └── app/
│       ├── api/v1/routers/   # FastAPI route handlers (one file per domain)
│       ├── core/             # config.py, constants.py
│       ├── db/               # sqlite.py, migrations.py
│       ├── models/           # SQLAlchemy models
│       ├── repositories/     # ALL SQL lives here — never in routers
│       ├── schemas/          # Pydantic v2 request/response models
│       └── services/         # Business logic (pipelines, parsers, engines)
├── frontend/
│   └── src/
│       ├── app/              # Next.js App Router pages
│       ├── components/       # Shared UI components
│       ├── hooks/            # Custom React hooks (useRunPolling, etc.)
│       └── lib/api/          # Typed API client functions per domain
├── docs/                     # Architecture, policy, and design guide documents
├── knowledge_base/           # AI onboarding: API index, code map, runbook
├── project_plan/             # Roadmap
├── data/                     # her.db (SQLite — never commit)
├── artifacts/                # Run output files (never commit)
├── freqtrade_workspace/      # Freqtrade user_data (never commit)
└── scripts/                  # Dev helper scripts
```

---

## Core Safety Rules

- **No live trading.** Freqtrade `trade` and `webserver` commands are forbidden at all times.
- **No fake data.** Charts and metrics render only from real API responses — no mocks, no stubs.
- **No profit guarantees.** `validated` means evidence survived checks — not future profit.
- **Confirmation required.** Any endpoint that launches a Freqtrade run requires `user_confirmed: true`.
- **Secrets in `.env` only.** Never log, display, or commit credentials.
- **No runtime files committed.** `her.db`, `artifacts/`, `__pycache__/`, `.next/` are gitignored.

Full rulebook: `docs/SAFETY_RULES.md` · AI rules: `docs/AI_PERMISSIONS.md`

---

## Knowledge Base (AI onboarding)

| Document | Purpose |
|---|---|
| `knowledge_base/API_INDEX.md` | Every endpoint: method, path, fields, frontend client |
| `knowledge_base/CODE_MAP.md` | File-by-file responsibility map for backend and frontend |
| `knowledge_base/WORKFLOW_INDEX.md` | End-to-end workflow documentation per domain |
| `knowledge_base/RUNBOOK.md` | Install, start, test, smoke, reset, common failures |
| `project_plan/ROADMAP.md` | Completed parts, next steps, future direction |
| `docs/PROJECT_CHARTER.md` | What HER is, why it exists, core terminology |
| `docs/GLOSSARY.md` | Definitions for every domain term |
| `docs/SAFETY_RULES.md` | All safety constraints in one place |
| `docs/FRONTEND_UX_GUIDE.md` | Design rules, dark theme, real-data-only charts |

---

## Important Disclaimer

HER is a validation engine, not a guaranteed profitable strategy generator. Every result shown is historical backtest evidence. Past backtest performance does not guarantee future live trading results. All outputs are for research and evaluation purposes only. No financial advice is implied or given.
