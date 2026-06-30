# HER Code Map

File-by-file responsibility map for the HER backend and frontend. Use this to understand what each file does, what it is used by, and what must never be broken. Built from direct code inspection.

---

## Backend (`backend/app/`)

### Entry Point

| File | Responsibility | Used by | Do-not-break |
|---|---|---|---|
| `main.py` | FastAPI app creation, CORS config, router registration, lifespan (DB init) | Everything | Router prefix structure; CORS must allow frontend origin |

### Core (`core/`)

| File | Responsibility | Used by | Do-not-break |
|---|---|---|---|
| `config.py` | Pydantic `Settings` loaded from `.env`; provides `project_root`, `freqtrade_user_data_dir`, Freqtrade/Ollama readiness checks | All services, routers | `BACKEND_PORT=8000`, `FRONTEND_PORT=3000`; `SecretStr` for all sensitive fields |
| `constants.py` | Domain constants: `RUN_MODES`, `STATUSES`, `PIPELINE_STAGES`, `ALLOWED_FREQTRADE_COMMANDS`, `ERROR_MESSAGES`, `NEXT_ACTIONS` | Services, repositories, routers | Never add `"trade"` or `"webserver"` to `ALLOWED_FREQTRADE_COMMANDS` |

### Database (`db/`)

| File | Responsibility | Used by | Do-not-break |
|---|---|---|---|
| `sqlite.py` | `get_connection()`, `fetch_one()`, `fetch_all()`, `execute()`, `transaction()` context manager | All repositories | `PRAGMA foreign_keys = ON` must stay; `transaction()` must commit/rollback atomically |
| `migrations.py` | Schema migration engine; creates all tables on startup | `main.py` lifespan | Table definitions; adding columns requires a migration version bump |

### Repositories (`repositories/`)

**Critical rule:** ALL SQL lives here. No raw SQL in routers or services.

| File | Responsibility | Key methods | Do-not-break |
|---|---|---|---|
| `base.py` | `BaseRepository` — UUID gen, ISO timestamps, JSON serialize, secret redaction | All repos inherit this | `redact_secrets()` — must be called before any config stored in DB |
| `runs.py` | Full lifecycle for `runs` table | `create_run`, `get_run`, `list_runs`, `mark_started`, `mark_completed`, `mark_failed`, `update_status` | Status transition logic; `failed_controlled` vs `failed` distinction |
| `run_stages.py` | Stage-level progress for `run_stages` | `create_stages`, `start_stage`, `complete_stage`, `fail_stage` | `duration_ms` calculation; `order_index` must match constants |
| `strategies.py` | Strategy and version management | `create_strategy`, `get_strategy`, `list_strategies`, `archive_strategy`, `create_version` | `strategy_versions` FK integrity |
| `optimization.py` | Optimization run and trial management | `create_optimization_run`, `list_trials`, `get_best_trial`, `save_comparison` | `best_trial_id` must be set before comparison is saved |
| `validation.py` | Validation run and evidence management | `create_validation_run`, `add_evidence`, `list_evidence`, `update_decision` | Evidence grouping by `evidence_type`; `window_index` order |
| `artifacts.py` | Artifact registration and retrieval | `register_artifact`, `list_run_artifacts`, `get_artifact` | SHA-256 hash must be computed before registration |
| `metrics.py` | Metrics snapshot persistence | `save_metrics_snapshot`, `get_latest_metrics`, `list_metric_snapshots` | `stage_key` must match constants; do not overwrite existing snapshots |
| `decisions.py` | Decision result persistence | `save_decision`, `get_latest_decision`, `list_run_decisions` | `gates_json` structure must match `DecisionEngine` output format |
| `logs.py` | Run log entry management | `add_log`, `list_logs` | Log entries are append-only |
| `audit_logs.py` | Audit log (append-only actions ledger) | `record`, `list_logs` | Append-only; never delete or update audit records |
| `retry_history.py` | Retry attempt tracking | `record_retry`, `list_retries` | Linked to `runs.id` |

### Services (`services/`)

| File | Responsibility | Calls | Do-not-break |
|---|---|---|---|
| `decision_engine.py` | Deterministic gate evaluation → classification | `MetricsRepository`, `DecisionRepository` | Gate logic must be deterministic (no randomness, no LLM); all gate outcomes must be recorded |
| `backtest_result_parser.py` | Freqtrade output → `MetricsSnapshot` | `ArtifactRepository`, `MetricsRepository`, `ResultQualityService` | Output normalization; `normalized_result.json` artifact must always be written |
| `freqtrade_backtest_runner.py` | Subprocess execution of `freqtrade backtesting` | `FreqtradeConfigGenerator`, `ArtifactRepository` | Command allowlist check; stdout/stderr must be captured to file, not logged |
| `optimization_pipeline_service.py` | 17-stage Hyperopt orchestration | `OptimizationRepository`, `RunRepository`, `FreqtradeHyperoptRunner`, `BacktestResultParser`, `DecisionEngine` | Stage order; controlled failure handling for each stage |
| `validation_execution_service.py` | OOS + WFO + robustness orchestration | `ValidationRepository`, `FreqtradeBacktestRunner`, `BacktestResultParser`, `DecisionEngine` | Evidence grouping; all three evidence types must be attempted |
| `freqtrade_config_generator.py` | Writes Freqtrade config JSON files | `ArtifactRepository` | `dry_run: true` must always be in generated config; no exchange keys |
| `result_quality_service.py` | Quality flag analysis on parsed results | `MetricsRepository` | Quality flags are informational only; do not block classification |
| `strategy_readiness_gate.py` | Pre-run strategy validation | `StrategyRepository` | Must block pipeline if issues found; never skip in production |
| `strategy_workspace_service.py` | Strategy import and workspace management | `StrategyRepository` | File path resolution must use `config.freqtrade_user_data_dir` |
| `baseline_evaluation_service.py` | 8-stage baseline pipeline orchestration | `RunRepository`, `RunStageRepository`, `FreqtradeBacktestRunner`, `BacktestResultParser`, `DecisionEngine` | Stage recording must be complete even on failure |

### Schemas (`schemas/`)

| File | Responsibility | Do-not-break |
|---|---|---|
| `runs.py` | `RunCreate`, `RunUpdate`, `RunRead`, `RunListItem`, `RunStatusUpdate` | `RunListItem` fields (used by Journey page + all list views) |
| `optimization.py` | `OptimizationRequest`, `OptimizationRunDetail`, `OptimizationTrial` | `user_confirmed` field required in `OptimizationRequest` |
| `validation.py` | `ValidationRequest`, `ValidationRunDetail`, `ValidationEvidence` | `user_confirmed` field required in `ValidationRequest` |
| `strategies.py` | `StrategyCreate`, `StrategyRead`, `StrategyVersionRead` | `readiness_issues` field in workspace response |
| `common.py` | Shared response wrappers and base models | — |
| `freqtrade_*.py` | Freqtrade CLI interface schemas | `dry_run` must default to `true` in any config schema |

### API Routers (`api/v1/routers/`)

| File | Path prefix | Do-not-break |
|---|---|---|
| `runs.py` | `/api/v1/runs` | Lifecycle endpoints; `fail` endpoint controlled-failure distinction |
| `strategies.py` | `/api/v1/strategies` | Archive is soft delete only |
| `baseline.py` | `/api/v1/baseline` | `user_confirmed` gate in evaluate endpoint |
| `optimization.py` | `/api/v1/optimization` | `user_confirmed` gate; trial listing pagination |
| `validation.py` | `/api/v1/validation` | `user_confirmed` gate; evidence grouping response format |
| `decisions.py` | `/api/v1/decisions` | Policy name validation; gates JSON format |
| `results.py` | `/api/v1/results` | Combined result response format |
| `freqtrade.py` | `/api/v1/freqtrade` | Command allowlist check before any subprocess call |
| `system.py` | `/api/system` | Public settings must not expose secrets |
| `strategy_workspace.py` | `/api/strategy_workspace` | Workspace path resolution |
| `metrics.py` | `/api/v1/runs/{id}/metrics` | Stage key validation |
| `artifacts.py` | `/api/artifacts` | SHA-256 integrity |
| `logs.py`, `audit_logs.py` | `/api/v1/runs/{id}/logs`, `/api/audit-logs` | Append-only semantics |
| `run_stages.py` | `/api/v1/runs/{id}/stages` | Stage key must be in constants |
| `retry_history.py` | `/api/v1/runs/{id}/retry-history` | FK integrity |

---

## Frontend (`frontend/src/`)

### Pages (`app/`)

| Route | File | Responsibility | Key API calls |
|---|---|---|---|
| `/` | `app/page.tsx` | Dashboard — system health + run summary + activity | `fetchHealth`, `fetchSystemStatus`, `listRuns`, `listBaselineRuns`, `listOptimizationRuns`, `getLatestRunDecision` |
| `/journey` | `app/journey/page.tsx` | Strategy lifecycle view — all stages for one strategy | `listStrategies`, `listBaselineRuns`, `listOptimizationRuns`, `listValidationRuns` |
| `/strategies` | `app/strategies/page.tsx` | Strategy library list | `listStrategies` |
| `/strategies/[name]` | `app/strategies/[strategyName]/page.tsx` | Strategy detail + readiness | `getStrategy`, `validateStrategy` |
| `/runs` | `app/runs/page.tsx` | All runs table | `listBaselineRuns`, `listOptimizationRuns` |
| `/baseline` | `app/baseline/page.tsx` | Baseline evaluation form | `startBaselineEvaluation` |
| `/baseline/[runId]` | `app/baseline/[runId]/page.tsx` | Baseline evidence detail | `getBaselineRunDetail`, `getBaselineStatus`, `listRunStages`, `getLatestMetrics`, `listPairResults`, `getTradeSummary`, `getResultQuality`, `getBacktestResults`, `getLatestRunDecision`, `listRunArtifacts` |
| `/optimization` | `app/optimization/page.tsx` | Optimization run form | `startOptimization` |
| `/optimization/[id]` | `app/optimization/[optimizationRunId]/page.tsx` | Optimization detail + trials | `getOptimizationRunDetail`, `getOptimizationStatus`, `getBestTrial`, `getOptimizationComparison`, `listOptimizationTrials` |
| `/validation` | `app/validation/page.tsx` | Validation run list | `listValidationRuns` |
| `/validation/[id]` | `app/validation/[validationRunId]/page.tsx` | Validation evidence detail | `getValidationRun`, `getValidationEvidence` |
| `/settings` | `app/settings/page.tsx` | System settings display | `fetchPublicSettings`, `getFreqtradeStatus` |

### API Clients (`lib/api/`)

| File | Domain | Key functions |
|---|---|---|
| `client.ts` | Base HTTP | `get()`, `post()`, `patch()` — all API calls go through this |
| `runs.ts` | Runs | `listRuns`, `getRun`, `listRunStages`, `getRunStage`, `getRunLogs`, `getRetryHistory` |
| `baseline.ts` | Baseline | `startBaselineEvaluation`, `getBaselineRunDetail`, `getBaselineStatus` |
| `optimization.ts` | Optimization | `startOptimization`, `listOptimizationRuns`, `getOptimizationRunDetail`, `getOptimizationStatus`, `listOptimizationTrials`, `getBestTrial`, `getOptimizationComparison` |
| `validation.ts` | Validation | `startValidationRun`, `listValidationRuns`, `getValidationRun`, `getValidationStatus`, `getValidationEvidence` |
| `strategies.ts` | Strategies | `listStrategies`, `getStrategy`, `validateStrategy`, `importStrategy`, `getStrategyParams` |
| `results.ts` | Results | `getRunMetrics`, `getLatestMetrics`, `listPairResults`, `getTradeSummary`, `getBacktestResults`, `getResultQuality` |
| `decisions.ts` | Decisions | `listPolicies`, `getPolicy`, `getRunDecision`, `getLatestRunDecision` |
| `freqtrade.ts` | Freqtrade | `getFreqtradeStatus`, `getFreqtradeWorkspace`, `checkData` |
| `artifacts.ts` | Artifacts | `listArtifacts`, `getArtifact`, `listRunArtifacts`, `listAuditLogs` |
| `system.ts` | System | `fetchHealth`, `fetchSystemStatus`, `fetchPublicSettings` |

### Components (`components/`)

| Component | Responsibility | Do-not-break |
|---|---|---|
| `AppShell.tsx` | Main layout wrapper — sidebar + header | "Evidence only" footer; system health indicator |
| `Sidebar.tsx` | Navigation with grouped sections | Group structure (Discover/Test/Evidence/System); active state |
| `WorkflowStepper.tsx` | 6-step lifecycle progress indicator | Step status mapping to real API data |
| `LiveRunPanel.tsx` | Real-time run monitoring with polling | `useRunPolling` integration; terminal state detection |
| `NextActionPanel.tsx` | Post-run guidance from API data | Must only render backend-provided `next_action`, never invented |
| `StatusBadge.tsx` | Semantic status indicator | Color mapping table (see UX guide) |
| `ControlledFailureBanner.tsx` | Validation rejection disclaimer | Must remain on all validation pages; not removable |
| `OOSValidationCard.tsx` | OOS evidence display | Uses `var(--app-*)` CSS variables only |
| `WFOValidationCard.tsx` | WFO window evidence display | Uses `var(--app-*)` CSS variables only |
| `RobustnessValidationCard.tsx` | Robustness check evidence display | Uses `var(--app-*)` CSS variables only |
| `DataAvailabilityPreview.tsx` | Pre-run data check display | Calls `checkData()`; must show real availability |
| `StrategySelect.tsx` | Strategy selector dropdown | Loads from `listStrategies()`; no hardcoded options |
| `MetricCard.tsx` | Single metric display unit | Renders `null` or `—` when value is undefined; never a fallback number |
| `SectionCard.tsx` | Content section wrapper | — |
| `PageHeader.tsx` | Page title + description header | — |
| `DataTable.tsx` | Generic sortable/searchable table | — |
| `CopyButton.tsx` | Copy-to-clipboard for IDs | — |

### Hooks (`hooks/`)

| Hook | Responsibility | Do-not-break |
|---|---|---|
| `useRunPolling.ts` | Polls run status every 2s; stops on terminal states | Terminal state list must match `constants.py`; cleanup on unmount |

### Configuration

| File | Responsibility | Do-not-break |
|---|---|---|
| `next.config.ts` | Next.js config — `allowedDevOrigins` for Replit proxy | Wildcard Replit dev domains must stay for preview to work |
| `app/globals.css` | CSS custom properties (`--app-*`), base styles | All `--app-*` variable definitions; cyan accent `#06b6d4` |
| `tsconfig.json` | TypeScript config — `@/` path alias | `@/` → `./src/` alias |
