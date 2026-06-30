# HER Safety Rules

This document is the single authoritative source for all safety constraints in the HER system. These rules apply to backend code, frontend code, AI behavior, and documentation. They cannot be overridden by any task description, user preference, or AI suggestion.

---

## 1. No Live Trading — Ever

**Rule:** Freqtrade `trade` and `webserver` commands are permanently forbidden in HER at every stage of development.

**Implementation:**
- `backend/app/core/constants.py` maintains `ALLOWED_FREQTRADE_COMMANDS = ["backtesting", "hyperopt", "download-data", "list-strategies"]`.
- `FreqtradeCommandRunner` checks against this allowlist before executing any CLI command and raises an error if a forbidden command is requested.
- All generated Freqtrade configs hard-code `dry_run: true` and include no exchange API keys.
- No frontend page, button, or action can initiate a live trade.

**Violation:** Any code path that reaches `freqtrade trade` is a critical safety failure.

---

## 2. Confirmation Required Before Any Run

**Rule:** Every endpoint that launches a Freqtrade execution (backtest, hyperopt, download-data) requires the request body to include `user_confirmed: true`.

**Affected endpoints:**
- `POST /api/baseline/evaluate`
- `POST /api/optimization/run`
- `POST /api/validation/run`
- `POST /api/v1/freqtrade/backtest`
- `POST /api/v1/freqtrade/data/download`

**Implementation:** Each service checks `request.user_confirmed` and raises `HTTP 422` if it is false or absent.

**Frontend rule:** Confirmation dialogs must accurately describe what will be executed (strategy name, timeframe, pairs) before the user confirms. The confirmation text must not be pre-checked.

---

## 3. No Fake Evidence

**Rule:** No metric, chart, table, or status indicator may display invented, estimated, interpolated, or hardcoded data. All displayed values must come from real API responses.

**Frontend implementation:**
- All chart and metric components receive data via props from API calls.
- Loading states show a spinner; empty states show an empty-state message. Neither shows placeholder numbers.
- No `Math.random()`, hardcoded strategy names, or mock metric values in any production component.

**Backend implementation:**
- The `BacktestResultParser` operates only on real Freqtrade output files.
- If a file is missing or malformed, the result quality flag is set and the issue is surfaced — not silently skipped.
- The decision engine never fabricates or adjusts metrics before applying gates.

---

## 4. No Profit Guarantees

**Rule:** No code, comment, UI copy, or documentation may claim that HER produces profitable strategies or that `validated` status implies future live trading success.

**Required disclaimers:**
- Root `README.md` disclaimer section.
- `ControlledFailureBanner` on validation pages.
- "Evidence only. No live trading actions." footer in the app shell.
- "Read-only inspection mode" banner on the dashboard.
- Validation detail pages must include: "Past backtest performance does not guarantee future live trading results."

---

## 5. Secrets Must Never Be Exposed

**Rule:** API keys, exchange credentials, Ollama tokens, and any `.env` value must never appear in logs, API responses, frontend output, or committed files.

**Implementation:**
- All sensitive config fields use Pydantic `SecretStr` — not plain `str`.
- `BaseRepository` provides a `redact_secrets()` utility; use it before storing any config in the database.
- The `GET /api/settings/public` endpoint returns only non-sensitive settings.
- `.env` is in `.gitignore` — verify before every commit.
- `stdout` and `stderr` from Freqtrade runs are captured to files and never logged to the application console without redaction.

---

## 6. No Runtime Files in Version Control

**Rule:** The following must never be committed:

| Pattern | Reason |
|---|---|
| `data/her.db` | Contains real run data; changes every run |
| `artifacts/` | Freqtrade output files; large, transient |
| `freqtrade_workspace/user_data/` | Local data directory |
| `__pycache__/`, `*.pyc` | Python bytecode |
| `.next/` | Next.js build output |
| `node_modules/` | Frontend dependencies |
| `.venv/` | Python virtual environment |
| `.env` | Secrets |

**Verification command:**
```bash
git ls-files | grep -E '(__pycache__|\.pyc|node_modules|\.next|\.venv|her\.db|artifacts/)'
```
This must return empty before any commit.

---

## 7. Freqtrade Command Safety

**Allowed commands:** `backtesting`, `hyperopt`, `download-data`, `list-strategies`

**Forbidden commands:** `trade`, `webserver`, `create-userdir`, `install-ui` (and any command not in the allowlist)

**Config safety rules:**
- Generated backtest configs always include `"dry_run": true`.
- Generated configs never include exchange `key` or `secret` fields.
- Config files are written to the `artifacts/` run directory, not the global Freqtrade config.
- Each run gets an isolated artifact directory; runs cannot overwrite each other's outputs.

See `docs/FREQTRADE_COMMAND_SAFETY.md` for the full Freqtrade safety policy.

---

## 8. AI Layer Boundaries

**Rule:** The local AI (Ollama) layer is permitted to suggest, explain, and draft — it is never permitted to execute, classify, or override.

**Allowed AI actions:**
- Explaining metric values to the user.
- Suggesting indicator combinations for a strategy spec.
- Drafting a strategy spec JSON (which the user must review and confirm).
- Summarizing validation evidence in human-readable language.
- Generating a repair suggestion for a rejected strategy.

**Forbidden AI actions:**
- Calling any execution endpoint directly.
- Modifying `decision_results` or `metrics_snapshots` tables.
- Claiming a strategy is profitable or will succeed in live markets.
- Generating free-form Python code outside the strategy template.
- Reading or modifying `.env` values.

See `docs/AI_PERMISSIONS.md` for the complete AI permissions matrix.

---

## 9. Audit Trail

**Rule:** Every significant action (run created, run started, run completed, decision evaluated, artifact registered) must produce an audit log entry via `AuditLogRepository`.

**Implementation:** Services call `audit_log.record(action, entity_type, entity_id, details)` after each significant state change.

**Why this matters:** The audit log is the primary traceability mechanism. Without it, there is no record of what happened if a run produces unexpected results.

---

## 10. Controlled Failure vs System Error

**Rule:** Expected failure modes (data missing, strategy invalid, config error, hyperopt convergence failure) must be classified as `failed_controlled`, not as unhandled exceptions.

**Implementation:**
- `constants.py` maps known error types to user-facing messages and `next_action` suggestions.
- Services catch expected exceptions and call `run_repo.mark_failed(run_id, failure_type, reason)`.
- Unexpected exceptions propagate normally and produce a `500` response — they are not silently swallowed.

This distinction matters: `failed_controlled` is informational ("this strategy doesn't work on this data"); an unhandled exception is a bug.
