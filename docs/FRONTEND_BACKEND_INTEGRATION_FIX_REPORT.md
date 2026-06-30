# Frontend ↔ Backend Integration Fix Report

**Status:** Fixed  
**Date:** 2026-06-30  
**Severity:** Critical (frontend could not read any backend data)

---

## Root Cause

The frontend API client (`frontend/src/lib/api/client.ts`) defaulted to
`http://127.0.0.1:8000` as the backend base URL. This works when both the
browser and the backend run on the same machine, but **Replit's preview pane
is a proxied iframe** — the browser code executes on the user's device, where
`127.0.0.1:8000` is the user's own machine, not the Replit container running
the backend. Every API call silently failed (ECONNREFUSED) instead of reaching
the FastAPI server.

**Secondary issue:** Python dependencies installed via `pip install -r
requirements.txt` had a version conflict. `freqtrade==2026.6` (pulled from
the package firewall) depended on `fastapi==0.138.2`, which has a breaking
internal API change (`PYDANTIC_V2` removed from `fastapi._compat`) that
caused the backend to crash on import.

---

## Files Changed

| File | Change |
|---|---|
| `frontend/next.config.ts` | Added `async rewrites()` — proxies `/api/**` and `/health` from the Next.js dev server to `http://127.0.0.1:8000`. Added broader `allowedDevOrigins`. |
| `frontend/.env.local` | Created — sets `NEXT_PUBLIC_API_BASE_URL=` (empty string) so the client uses relative paths instead of the hardcoded `127.0.0.1:8000` URL. |
| `frontend/src/lib/api/client.ts` | Updated `API_BASE_URL` derivation to treat explicit empty string as "relative mode" rather than falling back to the default. Updated `buildUrl()` to return a relative path (`/api/...`) when `API_BASE_URL` is `""`. |
| `backend/requirements.txt` | Updated `freqtrade` version to match what is actually available (`2026.6`). |
| `replit.md` | Created — project overview and user preferences for Replit. |
| `.env` | Attempted (blocked by Replit filesystem rules — backend defaults are used instead). |

---

## How the Fix Works

### Step 1 — Frontend uses relative paths

`frontend/.env.local` sets `NEXT_PUBLIC_API_BASE_URL=` (empty). The updated
`API_BASE_URL` derivation in `client.ts` treats an explicitly set empty string
as relative mode:

```ts
export const API_BASE_URL = (() => {
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env !== undefined) return env.replace(/\/+$/, ''); // '' = relative mode
  return DEFAULT_API_BASE_URL;
})();
```

`buildUrl()` now returns a relative URL (`/api/runs`) when `API_BASE_URL` is
`""`, by using a dummy absolute base for URL construction and then stripping
the origin:

```ts
const RELATIVE_URL_BASE = 'http://localhost';

function buildUrl(path, query) {
  const urlBase = API_BASE_URL || RELATIVE_URL_BASE;
  const url = new URL(`${urlBase}${normalizedPath}`);
  // ... add query params ...
  if (!API_BASE_URL) return url.pathname + url.search;
  return url.toString();
}
```

### Step 2 — Next.js rewrites proxy the backend

`frontend/next.config.ts` adds rewrites that run on the Next.js server
(which can reach `127.0.0.1:8000`):

```ts
async rewrites() {
  const backendOrigin = process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8000';
  return [
    { source: '/health', destination: `${backendOrigin}/health` },
    { source: '/api/:path*', destination: `${backendOrigin}/api/:path*` },
  ];
}
```

**Data flow:**

```
Browser → GET /api/runs (relative, goes to Next.js on *.replit.dev)
       → Next.js rewrite → GET http://127.0.0.1:8000/api/runs
       → FastAPI backend
       → Response forwarded back through Next.js → Browser
```

### Step 3 — FastAPI dependency version conflict resolved

`freqtrade==2026.6` pulled in `fastapi==0.138.2` which has breaking internal
changes incompatible with Pydantic 2.5.0. After the freqtrade install,
explicit re-installation pins the correct versions:

```bash
pip install "fastapi==0.104.1" "pydantic==2.5.0" "pydantic-settings==2.1.0" --force-reinstall
```

---

## API Paths — Before / After

All documented API mismatches (from `knowledge_base/PROJECT_KNOWLEDGE_BASE_REPORT.md`)
were investigated against the live backend. All paths exist — the mismatches
were documentation gaps, not implementation gaps:

| Frontend call | Backend route | Status |
|---|---|---|
| `GET /api/freqtrade/strategies` | `GET /api/freqtrade/strategies` (in `freqtrade.py` router) | ✅ Exists |
| `GET /api/freqtrade/data` | `GET /api/freqtrade/data` (in `freqtrade.py` router, line 227) | ✅ Exists |
| `GET /api/baseline/runs/{id}/report` | `GET /api/baseline/runs/{run_id}/report` (in `baseline.py` router) | ✅ Exists |
| `GET /api/decisions/runs/{runId}/latest` | `GET /api/decisions/runs/{run_id}/latest` (in `decisions.py` router) | ✅ Exists |
| `GET /api/runs/{runId}/decision` | `GET /api/runs/{run_id}/decision` (in `decisions.py` router) | ✅ Exists |
| `GET /api/optimization/runs/{id}/best-trial` | `GET /api/optimization/runs/{id}/best-trial` (in `optimization.py` router) | ✅ Exists |
| `GET /api/optimization/runs/{id}/comparison` | `GET /api/optimization/runs/{id}/comparison` (in `optimization.py` router) | ✅ Exists |

The root cause was **connectivity only** — the paths themselves were correct.

---

## CORS Settings

The backend already configures `allow_origins=["*"]` in `CORSMiddleware`.
No backend CORS changes were required.

---

## Before / After Behavior

| | Before | After |
|---|---|---|
| Dashboard system health | ❌ ECONNREFUSED — never showed "healthy" | ✅ Shows "Backend: healthy" |
| Strategy Journey data | ❌ All API calls failed silently | ✅ Strategies, runs, statuses loaded |
| Any API call from browser | ❌ `fetch('http://127.0.0.1:8000/...')` fails | ✅ `fetch('/api/...')` proxied via Next.js |
| Backend startup | ❌ `ImportError: cannot import name 'PYDANTIC_V2'` | ✅ FastAPI 0.104.1 + Pydantic 2.5.0 compatible |

---

## How Verified

1. `curl http://127.0.0.1:8000/health` → `{"status":"ok","app":"HER","environment":"local","backend":"healthy"}`
2. `curl http://127.0.0.1:8000/api/system/status` → full JSON with `backend: "healthy"`, `database: "healthy"`, `freqtrade: "configured"`
3. Dashboard screenshot shows "Backend: healthy" green badge
4. Journey page screenshot shows strategies loaded from API (`AIStrategy` with real readiness status and sidecar detection)
5. Next.js workflow logs show successful proxy requests to `http://127.0.0.1:8000/api/*`

---

## Remaining Issues

| Issue | Priority | Notes |
|---|---|---|
| `.env` file cannot be written to Replit filesystem | Low | Backend defaults are sufficient for local dev; use Replit Secrets for sensitive values |
| `freqtrade==2026.5.1` in `requirements.txt` was unavailable | Medium | Updated to `2026.6` which is the available version |
| FastAPI version conflict on fresh install | Medium | `pip install -r requirements.txt --force-reinstall` is needed if freqtrade installs a newer fastapi first. See `knowledge_base/RUNBOOK.md` install notes. |

---

## Safety Confirmation

No backend execution behavior changed. No Freqtrade command allowlist was
modified. No fake data was added. All safety rules from `docs/SAFETY_RULES.md`
and `AGENTS.md` remain in effect.
