# Part 06 Completion Report

## Summary

Part 06 is complete. HER now has a Decision Engine and Acceptance Gates that evaluate already-parsed Part 05 backtest evidence, persist explainable decision results, update run classification safely, write decision artifacts, and expose decision APIs.

Part 06 decision logic evaluates evidence only. It does not approve strategies, export strategies, claim future profitability, start live or dry-run trading, call Ollama, or send Discord notifications.

## Files Created Or Updated

Core implementation:

- `backend/app/core/constants.py`
- `backend/app/db/migrations.py`
- `backend/app/schemas/decisions.py`
- `backend/app/repositories/decisions.py`
- `backend/app/repositories/runs.py`
- `backend/app/services/decision_policy.py`
- `backend/app/services/decision_engine.py`
- `backend/app/services/decision_service.py`
- `backend/app/api/v1/routers/decisions.py`
- `backend/app/main.py`
- `scripts/evaluate-real-smoke-decision.py`

Tests:

- `backend/tests/test_decision_repository.py`
- `backend/tests/test_decision_policy.py`
- `backend/tests/test_decision_engine.py`
- `backend/tests/test_decision_service.py`
- `backend/tests/test_decision_api.py`
- `backend/tests/test_decision_real_script_safety.py`
- `backend/tests/conftest.py`
- `backend/tests/test_pytest_database_isolation.py`

Documentation:

- `docs/PART_06_DECISION_ENGINE_PLAN.md`
- `docs/DECISION_POLICIES.md`
- `docs/DECISION_ENGINE.md`
- `docs/DECISION_REAL_VALIDATION.md`
- `docs/DATABASE_SCHEMA.md`
- `docs/API_CONTRACTS.md`
- `docs/EVIDENCE_AND_TRACEABILITY.md`
- `docs/TRADING_DEFINITIONS.md`
- `docs/PARTS_ROADMAP.md`
- `docs/PART_06_COMPLETION_REPORT.md`

## Decision Schema Status

Decision schemas exist in `backend/app/schemas/decisions.py`.

Implemented schemas include:

- `MetricThresholds`
- `DecisionPolicy`
- `DecisionPolicySummary`
- `DecisionGateResult`
- `DecisionReason`
- `DecisionEvidence`
- `DecisionResult`
- `DecisionEvaluationRequest`
- `DecisionEvaluationResponse`

Allowed classifications are restricted to:

- `rejected`
- `candidate`
- `promising`
- `validated`

Forbidden Part 06 outcomes are not used:

- `approved`
- `exported`
- `live_ready`
- `profitable_guaranteed`

## Decision DB Migration Status

The SQLite migration creates the `decision_results` table idempotently.

Verified by:

```bash
python scripts/init-db.py
```

Result:

- Database initialized successfully.
- `decision_results` was listed among created/verified tables.

## Policy Service Status

`DecisionPolicyService` centralizes thresholds and risk profile behavior.

Implemented risk profiles:

- `default_conservative`
- `default_balanced`
- `default_aggressive`

Implemented threshold categories:

- Timeframe-aware minimum trades.
- Profit factor thresholds for `candidate`, `promising`, and `validated`.
- Drawdown thresholds by risk profile.
- Expectancy thresholds by risk profile.
- Warning thresholds for single-pair dependency and low pair count.
- Blocking thresholds for negative expectancy, profit factor below `1.0`, high drawdown, missing trade count, parser errors, and unusable result quality.

Thresholds are not profitability guarantees. They are deterministic evidence gates for baseline classification only.

## Decision Engine Status

`DecisionEngine` applies deterministic gates to parsed Part 05 evidence.

The engine produces:

- Gate results.
- Blocking failures.
- Warning reasons.
- Evidence snapshots.
- Bounded confidence score.
- One safe classification.

The engine does not run Freqtrade, download data, call Ollama, send Discord messages, modify strategy files, approve strategies, or export strategies.

## Decision Service Status

`DecisionService` connects parsed evidence, policy selection, decision evaluation, persistence, run update, report artifact writing, logs, and audit records.

Implemented behavior:

- Loads latest parsed metrics, pair results, trade summary, quality flags, normalized artifact path, and run metadata.
- Returns controlled failures for missing run or missing parsed metrics.
- Uses `DecisionPolicyService` and `DecisionEngine`.
- Saves decisions through `DecisionRepository`.
- Writes `artifacts/runs/{run_id}/decisions/decision_result.json`.
- Registers the decision artifact.
- Optionally applies safe run classification when `apply_to_run=true`.
- Adds run logs and audit records for traceability.

## Decision API Status

Decision APIs are mounted under both `/api` and `/api/v1`.

Verified endpoints:

- `GET /health`
- `GET /api/decisions/policies`
- `GET /api/decisions/runs/{run_id}/latest`
- `GET /api/results/backtest/{run_id}/decision`
- `GET /api/runs/{run_id}/decision`
- `GET /openapi.json`

All checked endpoints returned HTTP `200` during completion validation.

## Test DB Isolation Status

Pytest now uses an isolated SQLite database under `.pytest_runtime/`.

Runtime database before tests:

```text
-rw-r--r-- 1 mohs mohs 40513536 Jun 29 22:53 data/her.db
ee9653ee189508be7b1cf7820fa84eca2a67ba18d349a31028d396ad4a1f646b  data/her.db
```

Runtime database after tests:

```text
-rw-r--r-- 1 mohs mohs 40513536 Jun 29 22:53 data/her.db
ee9653ee189508be7b1cf7820fa84eca2a67ba18d349a31028d396ad4a1f646b  data/her.db
```

Result:

- `pytest backend/tests` did not delete, reset, or modify `data/her.db`.
- Runtime SQLite data stayed separate from test SQLite data.

## Real Decision Validation Result

Real validation passed using a new real smoke run.

Commands:

```bash
python scripts/freqtrade-real-smoke-test.py
python scripts/parse-real-smoke-backtest.py --latest-smoke --force
python scripts/evaluate-real-smoke-decision.py --latest-smoke --force --risk-profile balanced --apply-to-run
```

Results:

- `REAL_SMOKE_PASSED`
- `REAL_PARSE_PASSED`
- `REAL_DECISION_PASSED`

## Real Run Evaluated

Run ID:

```text
598953f4-a4e4-4c3c-8b1f-550cbe626686
```

Run metadata:

- Name: `Real Freqtrade Smoke Test`
- Status after smoke validation: `validated`
- Decision classification after Part 06 evaluation: `rejected`
- Timeframe: `5m`
- Original smoke risk profile: `conservative`
- Decision risk profile: `balanced`

## Classification Result

Classification:

```text
rejected
```

This is the expected Part 06 classification because the real parsed smoke evidence failed blocking gates.

## Confidence Score

Confidence score:

```text
40.0
```

This score describes evidence completeness and decision confidence for the assigned baseline classification. It is not a probability of profitability.

## Blocking Failures

Blocking failures:

- `profit_factor_below_one`
- `negative_expectancy`
- `drawdown_above_limit`

## Reasons

Decision reason codes:

- `profit_factor_below_one`
- `negative_expectancy`
- `drawdown_above_limit`
- `low_win_rate_warning`
- `single_pair_dependency_warning`

## Quality Flags Considered

Quality flags:

- `negative_expectancy`
- `high_drawdown`
- `single_pair_dependency`
- `parse_warning`

## Parsed Evidence Snapshot

Parsed evidence:

- Trade count: `8685`
- Profit factor: `0.44619376311576026`
- Max drawdown: `9961.829898889988`
- Expectancy: `-1.1470116597973516`
- Win rate: `0.19792746113989637`
- Pair count: `1`

## Decision Artifact Path

Decision artifact:

```text
artifacts/runs/598953f4-a4e4-4c3c-8b1f-550cbe626686/decisions/decision_result.json
```

Normalized parsed result artifact:

```text
artifacts/runs/598953f4-a4e4-4c3c-8b1f-550cbe626686/normalized/backtest_result.normalized.json
```

## Run Classification Update Result

`apply_to_run=true` was used.

Result:

- `run_updated: True`
- `runs.classification` updated to `rejected`
- `runs.status` remained `validated`

This preserves the distinction between smoke integration validation and strategy evidence classification.

## Test Results

Validation commands:

```bash
python scripts/init-db.py
python scripts/check-system.py
pytest backend/tests
```

Results:

- Database init passed.
- System check passed with expected local warnings for missing `.env`, disabled Ollama, and disabled Discord.
- Backend tests passed: `522 passed, 19 warnings`.

## API Check Results

Checked endpoints:

- `/health`: HTTP `200`
- `/api/decisions/policies`: HTTP `200`
- `/api/decisions/runs/598953f4-a4e4-4c3c-8b1f-550cbe626686/latest`: HTTP `200`
- `/api/results/backtest/598953f4-a4e4-4c3c-8b1f-550cbe626686/decision`: HTTP `200`
- `/api/runs/598953f4-a4e4-4c3c-8b1f-550cbe626686/decision`: HTTP `200`
- `/openapi.json`: HTTP `200`

## Security And Secrets Result

Secret scan passed across:

- Public settings response.
- System status response.
- Decision API responses.
- Decision artifact.
- Run logs and JSON artifacts for the evaluated run.
- OpenAPI response.

No Discord token, `APP_SECRET_KEY`, exchange key, API secret, or `.env` content was found in the checked outputs.

## Runtime Files Not Committed

The following runtime paths must remain unstaged and uncommitted:

- `.env`
- `data/her.db`
- `data/*.db`
- `logs/`
- `artifacts/runs/`
- `freqtrade_workspace/config/runs/`
- `freqtrade_workspace/user_data/data/`
- `freqtrade_workspace/user_data/backtest_results/`
- `freqtrade_workspace/user_data/hyperopt_results/`

## What Part 06 Did Not Implement

Part 06 did not implement:

- Strategy generation.
- Strategy repair.
- Hyperopt.
- Walk-forward analysis.
- Out-of-sample validation.
- Robustness analysis.
- Strategy approval.
- Strategy export.
- Live trading.
- Dry-run trading bot loops.
- Future profitability claims.

## Readiness For Part 07

HER is ready for Part 07.

Part 06 acceptance criteria are satisfied:

- Tests passed.
- Real smoke validation passed.
- Real parsed evidence was classified as `rejected`.
- Decision result was persisted.
- Decision artifact was written.
- Run classification was updated safely.
- Decision APIs returned clean responses.
- No fake/mock result was used as readiness proof.
- No secrets were exposed in checked outputs.
- Runtime files were not staged for commit.
