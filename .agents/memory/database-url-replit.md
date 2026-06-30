---
name: DATABASE_URL injection on Replit conflicts with HER SQLite setup
description: Replit injects a PostgreSQL DATABASE_URL env var; HER's sqlite.py must not treat it as a file path.
---

# DATABASE_URL on Replit

**Why:** Replit automatically injects `DATABASE_URL` pointing to its managed PostgreSQL instance. HER's `get_database_path()` in `backend/app/db/sqlite.py` originally used the URL as-is when it wasn't a `sqlite:///` URL, producing a garbled path that exposed the injected connection string (including credentials) in the `/api/system/status` API response.

**Fix applied:** `get_database_path()` now falls back to `./data/her.db` for any non-SQLite URL:
```python
if db_url.startswith("sqlite:///"):
    db_path = db_url.replace("sqlite:///", "")
else:
    db_path = "./data/her.db"  # HER is SQLite-only; ignore injected PostgreSQL URL
```

**How to apply:** If `DATABASE_URL` is ever changed or a new non-SQLite URL appears, the fallback ensures HER always uses its local SQLite file. The API's `database_path` field now always returns the resolved absolute path to `data/her.db`.

**Safety:** The `database_path` in `/api/system/status` no longer leaks credentials.
