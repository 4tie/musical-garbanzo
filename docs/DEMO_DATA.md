# Demo Data

HER includes optional demo data for frontend and API development without running Freqtrade.

## Purpose

Demo data provides one placeholder strategy, one placeholder run, stage statuses, logs, metrics, pair results, a trade summary, artifacts, and an audit log. It is only for development and UI wiring.

Demo data is not real trading evidence. It is marked with `is_demo = 1` where the table supports that flag, uses obvious demo names, and stores placeholder artifact paths only.

## Seed

```bash
source .venv/bin/activate
python scripts/seed-demo-data.py
```

The seed script initializes the database if needed, clears previous demo records only, and creates a fresh demo strategy/run set.

## Clear

```bash
source .venv/bin/activate
python scripts/seed-demo-data.py --clear
```

`--clear` deletes demo runs, demo strategies, and records linked to demo runs or strategies. It does not delete non-demo runs, strategies, Freqtrade data, backtest results, or local configuration.

## Frontend Use

The frontend can use demo records from:
- `GET /api/runs`
- `GET /api/strategies`
- `GET /api/artifacts`
- `GET /api/runs/{run_id}/metrics`
- `GET /api/runs/{run_id}/pair-results`
- `GET /api/runs/{run_id}/trade-summary`
- `GET /api/runs/{run_id}/logs`

UI labels should keep demo records visibly separate from real validation output.
