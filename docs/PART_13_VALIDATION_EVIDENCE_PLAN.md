# Part 13 Validation Evidence Layer Plan

## Purpose

Part 13 adds a validation evidence layer that answers whether a strategy survived deeper validation or only looked good in one backtest.

The layer must evaluate strategy evidence across:

- Out-of-sample validation, OOS
- Walk-forward validation, WFO
- Robustness checks
- Sensitivity checks when they can be implemented safely without redesigning Hyperopt
- Deterministic validation decisions
- Persisted evidence exposed through backend APIs and frontend evidence views

Core rule:

AI suggests. Backend validates. Freqtrade tests. HER decides.

## Existing Services To Reuse

Backend services and repositories already provide most of the execution and evidence primitives:

- `backend/app/services/strategy_readiness_gate.py`: blocks non-ready strategies before baseline and optimization execution.
- `backend/app/services/baseline_evaluation_service.py`: orchestrates safe real baseline backtests, parsing, decision evaluation, reports, logs, and artifacts.
- `backend/app/services/optimization_pipeline_service.py`: orchestrates baseline reference, Hyperopt execution, best-trial selection, optimized backtest, comparison, and optimization report.
- `backend/app/services/freqtrade_backtest_runner.py`: builds and runs Freqtrade `backtesting`, captures stdout/stderr, discovers artifacts, and never runs live trading commands.
- `backend/app/services/backtest_result_parser.py`: discovers raw Freqtrade outputs, extracts metrics, pair results, trade summaries, quality flags, and normalized result artifacts.
- `backend/app/services/decision_service.py`: loads parsed evidence, evaluates deterministic decision gates, persists decisions, and writes decision artifacts.
- `backend/app/services/decision_engine.py`: deterministic risk and quality gates with no persistence, AI, notifications, approval, export, or Freqtrade execution.
- `backend/app/repositories/runs.py`: run metadata and classification persistence.
- `backend/app/repositories/metrics.py`: metric snapshots, pair results, and trade summaries.
- `backend/app/repositories/artifacts.py`: project-relative artifact registration.
- `backend/app/repositories/optimization.py`: optimization run and trial persistence, including selected-for-validation trial metadata.

Frontend areas to reuse:

- Baseline start and detail pages
- Optimization start and detail pages
- Strategy workspace list/detail pages
- `frontend/src/lib/api/*` client conventions
- Evidence-style components such as `SectionCard`, `StatusBadge`, `MetricCard`, `DataTable`, `ControlledFailureBanner`, `ErrorBanner`, `LoadingSkeleton`, and `EmptyState`

## Candidate Source Options

Part 13 validation should support multiple evidence sources while normalizing them into one validation request model.

1. Baseline run
   - Source: an existing run with parsed metrics and a decision.
   - Use case: validate a manually selected or uploaded strategy beyond its first baseline.
   - Required source data: `run_id`, strategy name or strategy id, pairs, timeframe, timerange, parsed metric snapshot, and result quality report.

2. Optimization run
   - Source: a completed optimization pipeline.
   - Use case: validate the optimized strategy result, not only the in-sample Hyperopt result.
   - Required source data: `optimization_run_id`, `baseline_run_id`, `optimized_run_id`, `best_trial_id`, strategy name, pairs, timeframe, and materialized parameter artifacts.

3. Best optimized trial
   - Source: one persisted optimization trial marked `is_best` or `is_selected_for_validation`.
   - Use case: validate the best candidate from Hyperopt before treating it as a real candidate.
   - Required source data: `trial_id`, `optimization_run_id`, parameter JSON, generated config/materialized strategy artifact, and the optimized backtest run id if available.

4. Manually selected strategy
   - Source: a strategy from the Strategy Workspace.
   - Use case: validate a strategy that has not gone through optimization.
   - Required source data: `strategy_name`, readiness status, pairs, timeframe, timerange, exchange, risk profile, and user confirmation.

Every source must pass the Part 12 readiness gate before HER starts new Freqtrade execution.

## OOS Validation Plan

OOS validation should run a real Freqtrade backtest on a timerange that was not used as the source in-sample evidence.

Implementation plan:

1. Add a validation request schema that accepts `source_type`, source id fields, pairs, timeframe, exchange, risk profile, and explicit OOS timerange options.
2. Resolve the source into a validation subject with strategy name, parameters/config source, source run ids, and original timerange.
3. Split timeranges deterministically when the user supplies a full timerange and no explicit OOS range:
   - Default candidate: 70 percent in-sample reference, 30 percent OOS.
   - Supported ratio options: 80/20, 70/30, and 60/40.
   - OOS days are rounded up so the holdout segment is not smaller than the requested ratio.
   - OOS starts exactly at the in-sample end boundary; there is no date gap or overlap.
   - Require enough calendar span to make the split meaningful.
   - If timerange is missing or too short, return a controlled validation error instead of inventing evidence.
4. Generate a run-owned Freqtrade config for the OOS run using the existing config generation path.
5. Execute OOS with `FreqtradeBacktestRunner.run_backtest`.
6. Parse OOS results through `BacktestResultParser`.
7. Evaluate OOS parsed evidence through `DecisionService`.
8. Persist OOS evidence as:
   - child `runs` row or validation step row linked to the validation run
   - normalized result artifact
   - decision artifact
   - validation evidence report section
9. Set validation state:
   - `oos_failed` when Freqtrade execution, parsing, quality, or risk gates fail.
   - `oos_passed` when the OOS run completes, parses, and meets policy thresholds.

OOS must never reuse the exact same timerange as the source run unless the request explicitly marks the source as unknown and the backend records an insufficiency warning. The preferred behavior is controlled failure when no honest OOS split exists.

Prompt 4 implementation status:

- Added `OOSTimerangeService`.
- Added `parse_timerange`, `build_timerange`, `split_timerange`, `build_from_days`, and `validate_min_duration`.
- Added focused tests for 70/30, 60/40, 80/20, malformed input, invalid ordering, too-short ranges, deterministic output, contiguous boundaries, and day-count conservation.
- Added docs in `docs/OOS_VALIDATION.md`.
- Did not run Freqtrade, add frontend, or modify strategy files.

## WFO Validation Plan

Walk-forward validation should test stability across multiple chronological windows rather than a single holdout period.

Implementation plan:

1. Add a WFO planner that derives windows from a requested timerange:
   - Minimum default: three windows.
   - Each window has train/reference and validation segments.
   - Windows must be chronological and non-overlapping for validation segments.
   - Prompt 5 added `WFOWindowService` to generate deterministic train/test windows.
   - Generated windows use 1-based `window_index`, include train/test date fields, and start with `status="pending"`.
   - `step_days` must be greater than or equal to `test_days` so test windows do not overlap.
   - The builder rejects malformed timeranges, invalid numeric config, and ranges too short for one full train/test window.
2. For Part 13, avoid Hyperopt redesign:
   - If validating an optimized trial, reuse fixed selected parameters across WFO validation windows.
   - Do not re-run Hyperopt per window unless a later part explicitly adds that expensive workflow.
3. For each WFO validation segment:
   - Run Freqtrade backtesting with the selected strategy/config.
   - Parse metrics and quality evidence.
   - Evaluate deterministic decision gates.
4. Aggregate WFO evidence:
   - pass count
   - fail count
   - median and worst profit factor
   - median and worst drawdown
   - median and worst trade count
   - profitable-window ratio
   - critical quality flags
   - decision classifications by window
5. Set validation state:
   - `wfo_failed` when fewer than the configured minimum windows pass, any critical quality flag appears, or worst-window risk violates blocking thresholds.
   - `wfo_passed` when stability thresholds are met.

Initial thresholds should be conservative and deterministic:

- At least two out of three windows pass decision gates.
- No window has parser errors or unusable decision evidence.
- Worst-window drawdown must not exceed the policy blocking threshold.
- Worst-window trade count must meet a minimum viable threshold.
- No single window should dominate all positive evidence.

## Robustness Plan

Robustness checks should test whether small environment or assumption changes break the strategy.

Safe initial checks:

1. Pair subset robustness
   - Re-run validation on subsets of the requested pairs when at least three pairs are present.
   - Reject if performance depends entirely on one pair or one subset.

2. Fee/slippage stress if supported safely by existing config generation
   - Use config-level overrides only when the current Freqtrade config path supports them safely.
   - If not safely supported, record `not_applicable` with a reason instead of editing strategy code or faking evidence.

3. Timerange edge robustness
   - Shift validation windows slightly earlier/later when enough data exists.
   - Reject if tiny date shifts invert the decision.

4. Data sufficiency and parser quality robustness
   - Require usable parser quality.
   - Reject evidence with critical parser flags, missing trade counts, missing drawdown, or one-pair dependency flags.

Robustness state rules:

- `robustness_failed` when critical checks fail or available checks show fragile performance.
- `robustness_passed` when all required robustness checks pass and optional checks either pass or are explicitly not applicable with reasons.

Prompt 6 implementation status:

- Added `RobustnessEvaluator`.
- Added metric stability checks for trade count, profit factor, expectancy, and drawdown.
- Added WFO stability checks for supplied pass rate, zero-trade windows, non-positive expectancy, profit factor not above 1, and unstable drawdown.
- Added sensitivity variant checks that evaluate provided variant evidence only.
- Added robustness summaries for passed, warning, failed, and critical findings.
- Added docs in `docs/ROBUSTNESS_VALIDATION.md`.
- Did not run Freqtrade, add frontend, approve strategies, export strategies, modify strategy files, or make profit guarantees.

## Sensitivity Plan

Sensitivity checks are safely feasible only when they can be run without editing strategy code or redesigning Hyperopt.

Allowed Part 13 sensitivity checks:

- Fixed-parameter perturbation for optimized trial parameters when materialized params can be adjusted in a generated run-owned config or sidecar copy.
- Small timerange perturbations.
- Pair-list perturbations.
- Stake amount should not be used as a profitability sensitivity signal unless metrics are normalized and the decision policy treats it correctly.

Do not implement sensitivity checks that require:

- Editing user strategy files in place
- Exporting approved strategy variants
- Re-running Hyperopt with a redesigned search policy
- Any AI repair, generation, or parameter suggestion

If safe parameter perturbation is not possible with the current codebase, Part 13 should record sensitivity as `not_applicable` and explain why.

## Validation Decision Plan

Validation state values:

- `not_validated`
- `oos_failed`
- `oos_passed`
- `wfo_failed`
- `wfo_passed`
- `robustness_failed`
- `robustness_passed`
- `validated`
- `rejected`
- `validation_error`

Decision progression:

1. Start as `not_validated`.
2. If source resolution or readiness fails, return a controlled error and persist `validation_error` only if a validation run was created.
3. OOS must pass before WFO can mark success.
4. WFO must pass before robustness can mark success.
5. Robustness must pass before final `validated`.
6. Any critical failure produces `rejected` or a stage-specific failed state:
   - Evidence generation failure: `validation_error` when system or artifact failure prevents judgment.
   - Valid evidence that fails gates: `rejected`, with the most specific failed state captured in stages.
7. `validated` is evidence status only. It is not approval, export, live readiness, or a profit guarantee.

The validation decision should be a new deterministic evaluator, for example `ValidationDecisionService`, that aggregates child run decisions and robustness evidence. It should reuse `DecisionService` for individual backtest decisions instead of duplicating metric gates.

Prompt 3 implementation status:

- Added `ValidationPolicyService`.
- Added deterministic default policies for conservative, balanced, and aggressive risk profiles.
- Added OOS, WFO, robustness, and final-decision evaluation methods.
- Added failure issues with code, severity, metric name, actual value, threshold, and next action.
- Added docs in `docs/VALIDATION_POLICY.md`.
- Did not run Freqtrade, add frontend, approve strategies, export strategies, or make profit guarantees.

Prompt 7 execution-service status:

- Added `ValidationExecutionService`.
- Added candidate reference resolution for strategy, baseline run, optimization run, and optimized run source types.
- Added strategy readiness gating before any validation backtest execution.
- Added explicit user confirmation blocking before real validation backtests.
- Added OOS execution on out-of-sample timerange only.
- Added WFO test-window execution using fixed strategy parameters and existing backtest/parser/decision services.
- Added robustness evaluation using `RobustnessEvaluator`.
- Added final deterministic decision through `ValidationPolicyService.make_final_decision`.
- Added report artifact writing at `artifacts/runs/{validation_run_id}/validation/validation_report.json`.
- Added controlled failure responses without stack traces.
- Did not add API routes, frontend code, strategy approval, strategy export, live trading, Ollama calls, or profit guarantees.

## Evidence Persistence Plan

Recommended persistence model:

1. Add validation-specific tables through migrations:
   - `validation_runs`
   - `validation_evidence`

2. Prompt 2 persistence status:
   - Added `validation_runs`.
   - Added `validation_evidence`.
   - Added `ValidationRepository`.
   - Added focused schema and repository tests.
   - Did not add execution services, API routes, frontend pages, Freqtrade calls, Ollama calls, approval, or export.

3. `validation_runs` fields:
   - `id`
   - `source_type`
   - `source_run_id`
   - `strategy_name`
   - `timeframe`
   - `pairs_json`
   - `exchange`
   - `risk_profile`
   - `status`
   - `validation_state`
   - `final_decision_json`
   - `request_json`
   - `report_artifact_path`
   - `created_at`
   - `updated_at`

4. `validation_evidence` fields:
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

5. Artifact layout:
   - `artifacts/runs/{validation_run_id}/validation/validation_report.json`
   - `artifacts/runs/{validation_run_id}/validation/oos_summary.json`
   - `artifacts/runs/{validation_run_id}/validation/wfo_summary.json`
   - `artifacts/runs/{validation_run_id}/validation/robustness_summary.json`

5. Child Freqtrade backtest runs should continue to use existing run-owned artifact directories.

All artifact paths returned by APIs must be project-relative.

## Validation API Plan

Add a new backend router, for example `backend/app/api/v1/routers/validation.py`, mounted under both `/api` and `/api/v1`.

Initial endpoints:

- `POST /api/validation/run`
  - Starts a synchronous local validation run for Part 13.
  - Requires `user_confirmed=true` before any Freqtrade execution.
  - Applies Part 12 readiness gate before execution.
  - Returns validation run id, status, validation state, warnings, errors, and next actions.

- `GET /api/validation/runs`
  - Lists validation runs with filters for strategy, state, source type, and status.

- `GET /api/validation/runs/{validation_run_id}`
  - Returns full validation run detail, source context, step summaries, aggregate decision, artifacts, warnings, and errors.

- `GET /api/validation/runs/{validation_run_id}/status`
  - Lightweight status for polling.

- `GET /api/validation/runs/{validation_run_id}/evidence`
  - Returns all validation evidence grouped by evidence type.

- `GET /api/validation/runs/{validation_run_id}/report`
  - Returns validation report artifact metadata.

- `GET /api/validation/sources/{source_type}/{source_id}/latest`
  - Optional helper to show latest validation evidence for a baseline run, optimization run, best trial, or strategy.

API rules:

- No raw stdout/stderr by default.
- No secrets in response payloads.
- No absolute project paths unless an existing contract already requires them; prefer project-relative paths.
- Controlled failures must be explicit and user-facing.
- Validation state must not be confused with approval/export/live status.

Prompt 8 API implementation status:

- Added validation router at `backend/app/api/v1/routers/validation.py`.
- Added 6 endpoints: POST /run, GET /runs, GET /runs/{id}, GET /runs/{id}/status, GET /runs/{id}/evidence, GET /runs/{id}/report.
- Router mounted under both `/api` and `/api/v1` in `backend/app/main.py`.
- Added comprehensive API tests in `backend/tests/test_validation_api.py`.
- Added evidence sanitization to remove stdout/stderr and secrets.
- Added controlled failure responses without stack traces.
- Added OpenAPI tag "Validation".
- Updated `docs/API_CONTRACTS.md` with full API contracts.
- Did not add frontend code, strategy approval, strategy export, live trading, Ollama calls, or profit guarantees.

## Frontend Evidence UI Plan

Add frontend support in small layers:

1. API client and types
   - `frontend/src/lib/api/validation.ts`
   - validation request/response/detail/status/report types in `frontend/src/lib/api/types.ts`
   - validators and builders if there is a start form

2. Validation start page
   - Route: `/validation`
   - Supports source options:
     - baseline run id
     - optimization run id
     - best trial id
     - strategy name
   - Requires explicit confirmation before execution.
   - Shows controlled failures and readiness blocks using existing banner patterns.

3. Validation detail page
   - Route: `/validation/[validationRunId]`
   - Evidence sections:
     - Header summary
     - Validation decision
     - OOS evidence
     - WFO windows
     - Robustness checks
     - Sensitivity checks or not-applicable reasons
     - Artifacts
     - Warnings/errors/next actions

4. Evidence cards on existing pages
   - Baseline detail page: latest validation evidence for this baseline run.
   - Optimization detail page: latest validation evidence for optimized run or best trial.
   - Strategy detail page: latest validation evidence for this strategy.

5. UI semantics
   - `validated` means deeper validation evidence passed.
   - `rejected` means evidence exists and failed gates.
   - `validation_error` means HER could not complete the validation workflow.
   - Never display validation as approval, export readiness, live readiness, or profit guarantee.

Prompt 9 frontend implementation status:

- Added validation API client at `frontend/src/lib/api/validation.ts`.
- Added validation types to `frontend/src/lib/api/types.ts`.
- Added validation list page at `frontend/src/app/validation/page.tsx`.
- Added validation detail page at `frontend/src/app/validation/[validationRunId]/page.tsx`.
- Added ValidationDecisionBanner component with disclaimers.
- Added OOSValidationCard component for OOS evidence.
- Added WFOValidationCard component for WFO evidence.
- Added RobustnessValidationCard component for robustness checks.
- Added Validation navigation item to Sidebar.
- Added error handling with empty states and retry buttons.
- Added "Run Validation" action from baseline/optimization detail pages with confirmation dialog.
- Added ValidationConfirmationDialog component for validation start confirmation.
- Did not add strategy readiness banner integration (deferred).
- Did not add export/approval/live controls.
- Did not add AI repair.
- Did not claim guaranteed profitability.

Part 13 fix (optimization_run resolver):

- Updated ValidationExecutionService to use OptimizationRepository for optimization_run source type.
- optimization_run source now uses optimized_run_id as the actual candidate source.
- Added controlled failures for missing optimization_run (optimization_run_not_found).
- Added controlled failures for missing optimized_run_id (optimized_run_missing).
- Added warning for optimized run with no metrics (optimized_source_metrics_missing).
- Added backend tests for optimization_run resolver behavior.

## Security Rules

- Do not call AI services.
- Do not call Ollama.
- Do not send Discord messages.
- Do not place orders.
- Do not start live or dry-run trading.
- Freqtrade command execution must remain limited to safe local validation commands such as `backtesting`.
- Do not edit user strategy files in place.
- Do not export approved strategies.
- Do not persist secrets in artifacts, logs, reports, or API responses.
- Do not fake evidence; if a check cannot run, persist `not_applicable` or a controlled error with a reason.
- Keep all generated runtime artifacts under run-owned artifact/config/workspace paths.
- Keep `data/her.db` and runtime artifacts out of commits.

## Non-Goals

Part 13 must not implement:

- AI strategy generation
- AI strategy repair
- Strategy editing
- Strategy export
- Strategy approval
- Live trading
- Exchange order execution
- Profit guarantees
- Fake evidence
- Discord notifications
- Ollama calls
- New pair discovery unless safely reused from existing code
- Hyperopt redesign

## Real Validation Plan

Validation must be backed by real local evidence:

1. Unit tests for schemas, repositories, planners, and decision aggregation.
2. API tests proving readiness gating, confirmation gating, controlled failures, and detail/status/report contracts.
3. Runner tests proving generated commands remain safe and use `backtesting` only.
4. Parser integration tests using fixture artifacts.
5. Frontend lint/build and component-level tests where existing patterns support them.
6. At least one real local smoke validation only when explicitly requested in later prompts and when it can be run without live trading, Discord, Ollama, or strategy export.

No prompt should claim a strategy is validated without persisted OOS, WFO, robustness, and risk evidence.

## Repo Hygiene Rules

- Keep `.venv`, `__pycache__`, `.pyc`, `node_modules`, `.next`, runtime databases, and generated artifacts out of Git.
- Before commits, run:
  - `git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'`
  - expected no output
- Commit source, tests, docs, and migrations only.
- Do not normalize or revert unrelated user/runtime changes.
- Use focused validation commands before broad suites.
- Use the repo `.venv` for backend validation.
