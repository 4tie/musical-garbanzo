# Part 13 Prompt 02 Report: Validation Schemas And Persistence

## Status

Part 13 Prompt 2 is complete.

This prompt added constants, schemas, database tables, repository persistence, tests, and docs. It did not run Freqtrade, run validation, add frontend, call Ollama, approve strategies, or export strategies.

## Files Created Or Updated

Backend:

- `backend/app/core/constants.py`
- `backend/app/db/migrations.py`
- `backend/app/schemas/validation.py`
- `backend/app/repositories/validation.py`
- `backend/tests/test_validation_repository.py`
- `backend/tests/test_validation_schemas.py`

Docs:

- `docs/DATABASE_SCHEMA.md`
- `docs/API_CONTRACTS.md`
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- `docs/PART_13_PROMPT_02_REPORT.md`

## DB Schema Summary

Added table `validation_runs`:

- `id`
- `source_type`
- `source_run_id`
- `strategy_name`
- `timeframe`
- `pairs_json`
- `exchange`
- `risk_profile`
- `status`
- `decision_status`
- `timerange`
- `oos_timerange`
- `wfo_config_json`
- `policy_json`
- `request_json`
- `decision_json`
- `summary_json`
- `report_artifact_path`
- `created_at`
- `updated_at`

Added indexes:

- `idx_validation_runs_strategy_name`
- `idx_validation_runs_status`
- `idx_validation_runs_decision_status`
- `idx_validation_runs_created_at`

Added table `validation_evidence`:

- `id`
- `validation_run_id`
- `evidence_type`
- `status`
- `window_index`
- `timerange`
- `metrics_json`
- `decision_json`
- `issues_json`
- `warnings_json`
- `artifact_paths_json`
- `created_at`

Added indexes:

- `idx_validation_evidence_run_id`
- `idx_validation_evidence_type`
- `idx_validation_evidence_status`
- `idx_validation_evidence_window_index`

## Evidence Persistence Summary

`ValidationRepository` supports:

- `create_validation_run`
- `update_validation_run`
- `get_validation_run`
- `list_validation_runs`
- `create_evidence`
- `bulk_create_evidence`
- `list_evidence`
- `get_evidence`
- `save_decision`
- `get_decision`
- `serialize_run`
- `serialize_evidence`

Evidence persistence supports:

- OOS evidence through `evidence_type=oos`
- WFO window evidence through `evidence_type=wfo_window`
- WFO aggregate evidence through `evidence_type=wfo_summary`
- Robustness evidence through `evidence_type=robustness`
- Sensitivity evidence through `evidence_type=sensitivity`
- Aggregate decision evidence through `evidence_type=validation_decision`

JSON columns round-trip into frontend-ready keys:

- `pairs`
- `wfo_config`
- `policy`
- `request`
- `decision`
- `summary`
- `metrics`
- `issues`
- `warnings`
- `artifact_paths`

## Schema/API Contract Summary

Added `backend/app/schemas/validation.py` with:

- `ValidationRunRequest`
- `ValidationRunResponse`
- `ValidationRunListItem`
- `ValidationRunDetail`
- `ValidationStatusResponse`
- `ValidationEvidence`
- `OOSValidationResult`
- `WFOWindowResult`
- `WFOValidationResult`
- `RobustnessCheckResult`
- `SensitivityCheckResult`
- `ValidationDecision`
- `ValidationIssue`
- `ValidationPolicy`
- `ValidationSummary`

Validation request rules:

- `strategy_name` required
- `pairs` non-empty
- `timeframe` required
- `source_type` allowed values: `strategy`, `baseline_run`, `optimization_run`, `optimized_run`
- `risk_profile` allowed values: `conservative`, `balanced`, `aggressive`
- `oos_ratio` between `0.10` and `0.50`
- WFO values positive
- `user_confirmed=false` is schema-valid, but future execution services must stop before real Freqtrade execution

Schema safety:

- Extra undeclared fields are rejected on validation schemas.
- Raw stdout/stderr fields are not part of evidence schemas.
- Approval/export/live-trading fields are not part of evidence schemas.

## Validation Constants

Added:

- `VALIDATION_STAGES`
- `VALIDATION_STATUSES`
- `VALIDATION_DECISION_STATUSES`
- `VALIDATION_SOURCE_TYPES`
- `VALIDATION_EVIDENCE_TYPES`

## Test Results

Command:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_validation_repository.py tests/test_validation_schemas.py -q
```

Result:

```text
35 passed, 2 warnings
```

## Runtime File Safety

Runtime/generated files were not intentionally staged or committed.

Required runtime file check:

```bash
cd /home/mohs/Desktop/her
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
```

Result is recorded in the final response for this prompt.

## Prompt 3 Readiness

Prompt 3 can continue after the focused tests pass, runtime-file guard remains clean, and the commit is pushed to `origin/main`.
