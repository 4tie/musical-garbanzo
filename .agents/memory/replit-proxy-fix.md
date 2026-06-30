---
name: Replit proxy fix for HER frontend-backend connection
description: How to make the Next.js frontend reach the FastAPI backend on Replit, where the browser cannot access 127.0.0.1:8000 directly.
---

# Replit Proxy Fix

**Why:** On Replit, the browser runs on the user's device. `127.0.0.1:8000` resolves to the user's machine, not the Replit container — so all `fetch('http://127.0.0.1:8000/...')` calls fail with ECONNREFUSED.

**How to apply:** Two coordinated changes are required:

1. `frontend/.env.local` — set `NEXT_PUBLIC_API_BASE_URL=` (empty string, not absent).
2. `frontend/next.config.ts` — add `async rewrites()` that forward `/api/:path*` and `/health` to `http://127.0.0.1:8000`.

**Code change in `client.ts`:** The `API_BASE_URL` derivation must treat an explicitly empty string as "relative mode" (not fall through to default). `buildUrl()` must return `pathname + search` (no origin) when `API_BASE_URL` is `""`, using a dummy absolute base for URL construction.

**Data flow:** Browser → `GET /api/runs` (relative, hits Next.js server on `*.replit.dev`) → Next.js rewrite → `http://127.0.0.1:8000/api/runs` → FastAPI → response forwarded back.

**BACKEND_ORIGIN env var:** `next.config.ts` reads `process.env.BACKEND_ORIGIN ?? 'http://127.0.0.1:8000'` so the target can be overridden without touching code.
