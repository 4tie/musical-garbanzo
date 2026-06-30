# HER Runbook

Operational guide for starting, testing, verifying, and resetting the HER system. Covers both Replit (cloud development) and local machine setups.

---

## 1. Environment Assumptions

| Assumption | Detail |
|---|---|
| Python | 3.11 (Replit NixOS module) |
| Node.js | 20.x (Replit NixOS module) |
| Package manager | `npm` for frontend; `pip` for backend |
| Database | SQLite at `data/her.db` (auto-created on first backend start) |
| Secrets | `.env` file in project root (not committed) |
| Freqtrade | Local CLI install; path in `.env` as `FREQTRADE_PATH` |
| Ollama | Local install at `http://localhost:11434` (optional) |

---

## 2. Start Commands

### Replit (workflows pre-configured)

The two workflows auto-start. To restart manually from the Workflows pane:

```
Workflow: "Start application"   → cd frontend && npm run dev -- --port 5000
Workflow: "Backend API"         → cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Local machine

```bash
# Backend (terminal 1)
cd /path/to/her
pip install -r backend/requirements.txt
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Frontend (terminal 2)
cd /path/to/her/frontend
npm install
npm run dev            # starts on port 3000

# Or with the helper scripts:
bash scripts/dev-backend.sh
bash scripts/dev-frontend.sh
```

---

## 3. Verify Everything Is Running

1. **Backend health:** `curl http://localhost:8000/health` → `{"status":"healthy",...}`
2. **API docs:** Open `http://localhost:8000/docs` — all routers should be listed
3. **Frontend:** Open `http://localhost:5000` (Replit) or `http://localhost:3000` (local)
4. **Dashboard "Backend: healthy" badge** — green indicator in the top bar confirms frontend-to-backend connectivity

---

## 4. Install / Dependency Commands

```bash
# Backend Python dependencies
pip install -r backend/requirements.txt

# Frontend Node dependencies
cd frontend && npm install

# Check npm/node version (Replit — update PATH if needed)
export PATH="/home/runner/.nix-profile/bin:$PATH"
node --version    # should be v20.x
npm --version     # should be 10.x
```

---

## 5. Test and Lint Commands

```bash
# Frontend lint (must pass before any frontend commit)
cd frontend && npm run lint

# Frontend production build check (must pass — catches TypeScript errors)
cd frontend && npm run build

# Backend unit tests
cd /project/root
pytest backend/tests -v

# Backend tests with coverage
pytest backend/tests --cov=backend/app --cov-report=term-missing

# Single test file
pytest backend/tests/test_decision_engine.py -v
```

---

## 6. Repo Hygiene Commands

Run these before every commit to ensure no runtime or sensitive files are staged:

```bash
# Check working tree status
git --no-optional-locks status --short

# Verify no runtime files are tracked
git ls-files | grep -E '(__pycache__|\.pyc|node_modules|\.next|\.venv|her\.db|artifacts/)'
# ↑ This must return EMPTY. If not, add to .gitignore and remove from tracking.

# Remove Python bytecode from tracking (if accidentally added)
git rm -r --cached backend/**/__pycache__ 2>/dev/null || true
git rm -r --cached **/*.pyc 2>/dev/null || true
```

---

## 7. Manual Smoke Workflow

Use this checklist after a significant code change to verify the system end-to-end:

### Step 1: System health
- [ ] `GET /health` returns `{"status":"healthy"}`
- [ ] Dashboard shows "Backend: healthy" green badge
- [ ] Freqtrade status shows `executable_available: true` (if Freqtrade is installed)

### Step 2: Strategy workspace
- [ ] `/strategies` page loads without error
- [ ] At least one strategy is listed (if strategies are registered)
- [ ] Strategy detail page loads and runs readiness check

### Step 3: Baseline evaluation
- [ ] `/baseline` page form renders
- [ ] Submit with `user_confirmed: true` (via API test or form)
- [ ] Run appears in `/runs` page with `status: running`
- [ ] Polling updates stage progress
- [ ] Run reaches a terminal state (candidate/rejected/failed_controlled)
- [ ] Baseline detail page shows metrics and decision

### Step 4: Optimization
- [ ] `/optimization` page form renders
- [ ] Submit with `user_confirmed: true` and a baseline run
- [ ] Optimization run appears and progresses through stages
- [ ] Trial list populates as trials complete
- [ ] Comparison result is shown on detail page

### Step 5: Validation
- [ ] `/validation` page lists validation runs
- [ ] Validation detail page shows OOS, WFO, and robustness cards
- [ ] `ControlledFailureBanner` appears when status is rejected

### Step 6: Journey page
- [ ] `/journey` — strategy selector loads strategies
- [ ] Selecting a strategy shows correct step statuses in `WorkflowStepper`
- [ ] Evidence summary section shows counts from real data

---

## 8. Common Failures and Meanings

| Symptom | Likely cause | Fix |
|---|---|---|
| `Backend: unknown` badge | Backend not running or wrong port | Start "Backend API" workflow; check port 8000 |
| `Network error while contacting the HER backend` | Frontend can't reach port 8000 | Ensure backend workflow is running; check CORS config |
| `user_confirmed: false` error | Request submitted without confirmation | Include `user_confirmed: true` in request body |
| `strategy not found` | Strategy not registered in DB | Import via workspace; check `freqtrade_workspace/user_data/strategies/` |
| `data not available` | Historical data not downloaded | Run `POST /api/v1/freqtrade/data/download` first |
| `freqtrade not found` | `FREQTRADE_PATH` not set or Freqtrade not installed | Set `FREQTRADE_PATH` in `.env`; verify with `freqtrade --version` |
| Frontend TypeScript build error | Type mismatch in props | Check `RunListItem` vs `RunRead` — list endpoints return `RunListItem` (no `timeframe` field) |
| `__pycache__` in git | Bytecode tracked accidentally | `git rm -r --cached **/__pycache__` then re-commit |
| DB migration error on startup | Schema change without migration | Increment migration version; add new migration step |
| `allowedDevOrigins` warning in Next.js | Dev host not in whitelist | Add host to `allowedDevOrigins` in `next.config.ts` |

---

## 9. Database Reset

**Warning: This destroys all run data.** Only do this to reset a corrupted or test database.

```bash
# Stop backend workflow first
rm data/her.db
# Restart backend — it will recreate the schema automatically on startup
```

For a clean state without losing the file:
```bash
# The database is recreated from migrations on startup if tables don't exist
# To reset while keeping the file:
sqlite3 data/her.db "DROP TABLE IF EXISTS runs; DROP TABLE IF EXISTS run_stages; ..."
# ↑ Not recommended — use rm and restart instead
```

---

## 10. What Must Never Be Deleted

| Path | Why |
|---|---|
| `backend/app/services/validation_execution_service.py` | Core of Part 13; all validation runs depend on it |
| `backend/app/services/decision_engine.py` | Deterministic classification; removing breaks all decisions |
| `backend/app/core/constants.py` | All status codes, allowed commands, pipeline stages |
| `backend/app/db/migrations.py` | Schema; deleting breaks DB initialization |
| `frontend/src/components/ControlledFailureBanner.tsx` | Required safety disclaimer on validation pages |
| `frontend/src/hooks/useRunPolling.ts` | Live run monitoring used by all pipeline pages |
| `docs/SAFETY_RULES.md` | Authoritative safety constraint reference |
| `AGENTS.md` | AI assistant rules; must survive every refactor |

---

## 11. Environment Variables (`.env` reference)

The `.env` file is gitignored. Never commit it. Required variables:

```
DATABASE_URL=sqlite:///./data/her.db
APP_ENV=development
BACKEND_PORT=8000
FRONTEND_PORT=3000
FREQTRADE_PATH=/path/to/freqtrade     # or the venv freqtrade binary
FREQTRADE_USER_DATA_DIR=/path/to/her/freqtrade_workspace/user_data
OLLAMA_BASE_URL=http://localhost:11434
```

Optional (for exchange data download only — no live trading keys):
```
EXCHANGE_NAME=binance
# No key/secret — Freqtrade can download public data without API keys for most exchanges
```

See `docs/ENVIRONMENT_AND_SECRETS.md` for the full environment variable reference.
