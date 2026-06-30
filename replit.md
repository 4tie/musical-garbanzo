# HER — AutoQuant Strategy Lab

Local-only trading strategy validation system. Runs Freqtrade backtests, collects multi-stage validation evidence, applies deterministic gates, and classifies strategies as `rejected / candidate / promising / validated`.

**Core rule:** AI suggests. Backend validates. Freqtrade tests. HER decides.

---

## Architecture

| Layer | Stack | Port |
|---|---|---|
| Frontend | Next.js 16 (App Router, Tailwind CSS v4, TypeScript) | 5000 |
| Backend | FastAPI 0.104.1, SQLite (aiosqlite), Pydantic 2.5.0 | 8000 |
| Backtest engine | Freqtrade 2026.6 (backtesting mode only — no live trading) | — |

---

## Running on Replit

Both workflows start automatically. Restart them from the Workflows pane if needed:

```
Workflow: "Start application"  →  cd frontend && npm run dev -- --port 5000
Workflow: "Backend API"        →  cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Frontend → Backend connectivity:** The frontend uses `NEXT_PUBLIC_API_BASE_URL=""` (relative paths). Next.js rewrites in `next.config.ts` proxy all `/api/**` and `/health` requests to `http://127.0.0.1:8000`. This avoids the Replit browser-isolation problem where browser code cannot reach `127.0.0.1:8000` directly.

---

## Install Dependencies

```bash
# Backend (from project root)
cd backend && pip install -r requirements.txt
# If freqtrade overrides FastAPI version, re-pin:
pip install "fastapi==0.104.1" "pydantic==2.5.0" --force-reinstall

# Frontend
cd frontend && npm install
```

---

## Verify Everything Works

1. Backend health: `curl http://127.0.0.1:8000/health` → `{"status":"ok",...}`
2. Dashboard shows **Backend: healthy** green badge
3. Journey page loads strategies from API

---

## Key Documentation

| File | Purpose |
|---|---|
| `AGENTS.md` | AI assistant rules (read before editing anything) |
| `knowledge_base/API_INDEX.md` | Every endpoint with paths and frontend client |
| `knowledge_base/CODE_MAP.md` | File-by-file responsibility map |
| `knowledge_base/RUNBOOK.md` | Full operational guide |
| `docs/SAFETY_RULES.md` | Non-negotiable safety constraints |
| `docs/FRONTEND_BACKEND_INTEGRATION_FIX_REPORT.md` | Connection fix details |

---

## User Preferences

- Dark-mode first UI; use `var(--app-*)` CSS variables — no hardcoded Tailwind color classes
- All API calls go through `frontend/src/lib/api/*.ts` clients — never `fetch()` directly in components
- No mock data, no placeholder charts, no fake metrics — real API data only
- Confirmation dialog required before any Freqtrade run (`user_confirmed: true`)
- Safety disclaimers must remain on all validation and decision pages
