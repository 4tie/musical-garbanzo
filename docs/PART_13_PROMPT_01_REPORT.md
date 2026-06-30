# Part 13 Prompt 01 Report: Validation Evidence Scope

## Status

Part 12 readiness status: ready for Part 13 planning.

Prompt 01 made documentation-only changes. No runtime behavior was changed.

## Part 12 File Readiness

Confirmed these Part 12 files exist:

- `backend/app/services/strategy_readiness_gate.py`
- `backend/app/api/v1/routers/baseline.py`
- `backend/app/api/v1/routers/optimization.py`
- `frontend/src/components/StrategyReadinessBlockedBanner.tsx`
- `docs/PART_12_COMPLETION_REPORT.md`

## Repo Hygiene Status

Command:

```bash
git ls-files | grep -E '(__pycache__|\.pyc|\.venv|node_modules|\.next)'
```

Result: no output.

Status: tracked runtime cleanup remains clean.

## Files Inspected

Backend:

- `backend/app/services/strategy_readiness_gate.py`
- `backend/app/api/v1/routers/baseline.py`
- `backend/app/api/v1/routers/optimization.py`
- `backend/app/services/baseline_evaluation_service.py`
- `backend/app/services/optimization_pipeline_service.py`
- `backend/app/services/freqtrade_backtest_runner.py`
- `backend/app/services/backtest_result_parser.py`
- `backend/app/services/decision_service.py`
- `backend/app/services/decision_engine.py`
- `backend/app/repositories/runs.py`
- `backend/app/repositories/metrics.py`
- `backend/app/repositories/artifacts.py`
- `backend/app/repositories/optimization.py`
- `backend/app/core/constants.py`
- `backend/app/main.py`
- `backend/app/db/migrations.py`

Frontend:

- `frontend/src/app/baseline/page.tsx`
- `frontend/src/app/baseline/[runId]/BaselineDetailClient.tsx`
- `frontend/src/app/optimization/page.tsx`
- `frontend/src/app/optimization/[optimizationRunId]/OptimizationDetailClient.tsx`
- `frontend/src/app/strategies/[strategyName]/StrategyDetailClient.tsx`
- `frontend/src/app/strategy-lab/page.tsx`
- `frontend/src/components/StrategyReadinessBlockedBanner.tsx`
- `frontend/src/components/SectionCard.tsx`
- `frontend/src/components/StatusBadge.tsx`
- `frontend/src/lib/api/client.ts`
- `frontend/src/lib/api/types.ts`
- `frontend/src/lib/api/baseline.ts`
- `frontend/src/lib/api/optimization.ts`
- `frontend/src/lib/api/strategies.ts`

Docs:

- `docs/PART_12_COMPLETION_REPORT.md`

## Current Validation Flow Found

Current HER validation is centered on single-run evidence:

1. Baseline evaluation starts from a strategy and request inputs.
2. The API applies the Part 12 readiness gate before baseline execution.
3. `BaselineEvaluationService` creates a run, validates strategy structure, generates config, checks/downloads data when confirmed, runs one Freqtrade backtest, parses results, evaluates decision gates, writes a baseline report, and completes the run.
4. Optimization starts from a strategy and request inputs.
5. The API applies the Part 12 readiness gate before optimization execution.
6. `OptimizationPipelineService` can create or reuse baseline evidence, validate Hyperopt policy, run Hyperopt, parse trials, choose a best trial, run an optimized backtest, compare baseline and optimized metrics, and write an optimization report.
7. `FreqtradeBacktestRunner` is the safe backtest execution primitive and builds `backtesting` commands only.
8. `BacktestResultParser` normalizes Freqtrade outputs into metrics, pair results, trade summaries, quality flags, and artifacts.
9. `DecisionService` evaluates one parsed run through `DecisionEngine` and persists a decision artifact.
10. Frontend detail pages aggregate existing backend endpoints into read-only evidence views.

Gap for Part 13:

One baseline backtest or optimized backtest can be classified by decision gates, but HER does not yet persist or expose deeper validation evidence across OOS, WFO, robustness, and sensitivity checks.

## Proposed Part 13 Scope

Part 13 should add a separate Validation Evidence Layer that supports:

- validation from a baseline run
- validation from an optimization run
- validation from a best optimized trial
- validation from a manually selected ready strategy
- OOS backtest evidence
- WFO window evidence
- robustness evidence
- safe sensitivity evidence or explicit not-applicable reasons
- deterministic aggregate validation decision
- validation state persistence
- validation API
- frontend validation evidence UI

Validation states:

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

## Proposed Backend Architecture

Add backend pieces in later prompts:

- `backend/app/schemas/validation.py`
- `backend/app/repositories/validation.py`
- `backend/app/services/validation_source_resolver.py`
- `backend/app/services/validation_window_planner.py`
- `backend/app/services/validation_evidence_service.py`
- `backend/app/services/validation_decision_service.py`
- `backend/app/api/v1/routers/validation.py`
- database migrations for `validation_runs` and `validation_steps`
- constants for validation states, statuses, step keys, and error codes
- tests for schemas, repositories, source resolution, timerange planning, execution safety, aggregate decisions, and API contracts

Reuse instead of duplicate:

- readiness gate for source strategy checks
- config generation for safe run-owned Freqtrade configs
- backtest runner for real Freqtrade backtests
- result parser for metric/quality evidence
- decision service for per-backtest deterministic decisions
- artifact repository for project-relative evidence files
- optimization repository for best trial/source context

## Proposed Frontend Architecture

Add frontend pieces in later prompts:

- `frontend/src/lib/api/validation.ts`
- validation types in `frontend/src/lib/api/types.ts`
- validation request validators/builders if a start form is implemented
- `/validation` start page
- `/validation/[validationRunId]` detail page
- latest-validation evidence panels on baseline detail, optimization detail, and strategy detail pages

Reuse existing components:

- `AppShell`
- `PageHeader`
- `SectionCard`
- `StatusBadge`
- `MetricCard`
- `DataTable`
- `ControlledFailureBanner`
- `ErrorBanner`
- `EmptyState`
- `LoadingSkeleton`
- `ActionProgressPanel`
- `ActionResultBanner`
- `StrategyReadinessBlockedBanner`

UI rule:

Validation evidence must be presented as evidence only. It must not imply strategy approval, export readiness, live readiness, or profit guarantees.

## Security And Non-Goal Confirmation

Part 13 must remain local-only and evidence-only:

- no AI strategy generation
- no AI repair
- no Ollama calls
- no Discord messages
- no live trading
- no exchange order execution
- no strategy editing
- no strategy export
- no strategy approval
- no fake evidence
- no Hyperopt redesign

If a validation check cannot run safely, HER should persist or return an explicit controlled failure or `not_applicable` reason.

## Files Created

- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- `docs/PART_13_PROMPT_01_REPORT.md`

## Validation Commands

Backend command:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_strategy_readiness_gate.py tests/test_baseline_api.py tests/test_optimization_api.py -q
```

Result:

```text
70 passed, 1 skipped, 15 warnings in 1.31s
```

Frontend lint command:

```bash
cd /home/mohs/Desktop/her/frontend
npm run lint
```

Result:

```text
passed
```

Frontend build command:

```bash
cd /home/mohs/Desktop/her/frontend
npm run build
```

Result:

```text
passed
```

## Prompt 2 Readiness

Prompt 2 can continue after the docs-only commit is pushed to `origin/main`.
