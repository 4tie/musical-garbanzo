# HER Workflow Index

End-to-end documentation of every implemented workflow in HER. Each entry maps the frontend trigger → API call → backend service → repository → database → artifact chain.

Future/planned workflows are clearly marked `[PLANNED]`.

---

## 1. Strategy Readiness Check

**Purpose:** Verify a strategy is correctly configured before any pipeline run.

**Frontend trigger:** Strategy detail page (`/strategies/[name]`) → "Check Readiness" button, or automatically before baseline/optimization submit.

**API call:** `POST /api/strategy_workspace/strategies/{name}/validate`

**Backend service:** `StrategyReadinessGate`
- Checks sidecar JSON exists and is valid
- Checks strategy `.py` file exists and is loadable
- Checks required parameters are present
- Checks Freqtrade workspace is valid

**Repository:** `StrategyRepository.get_strategy(name)`

**Response:** `StrategyDetail` with `readiness_issues[]`

**Success state:** Empty `readiness_issues` → strategy can proceed to baseline.

**Failure state:** Non-empty `readiness_issues` → each issue shown with remediation hint. Run is blocked until issues are resolved.

**Next action panel:** Shows each issue and what to fix (e.g., "Add sidecar JSON at `freqtrade_workspace/user_data/strategies/MyStrategy.json`").

---

## 2. Baseline Evaluation Pipeline

**Purpose:** Run the first full backtest of a strategy and record the decision engine result.

**Frontend trigger:** `/baseline` page → form submit with strategy + pairs + timeframe → confirmation dialog → `POST /api/baseline/evaluate`

**Confirmation required:** `user_confirmed: true` in request body.

**Backend service:** `BaselineEvaluationService.evaluate()`

**Pipeline stages (recorded in `run_stages`):**

| # | Stage key | Description |
|---|---|---|
| 1 | `readiness_check` | Re-run strategy readiness gate |
| 2 | `data_check` | Verify historical data available |
| 3 | `config_generation` | Write Freqtrade backtest config |
| 4 | `backtest_execution` | Execute Freqtrade `backtesting` |
| 5 | `result_parsing` | Parse raw JSON output → metrics |
| 6 | `quality_check` | Flag suspicious results |
| 7 | `decision_evaluation` | Apply gates → assign classification |
| 8 | `report_generation` | Write baseline report artifact |

**Services used:**
- `FreqtradeConfigGenerator` (stage 3)
- `FreqtradeBacktestRunner` (stage 4)
- `BacktestResultParser` (stage 5)
- `ResultQualityService` (stage 6)
- `DecisionEngine` (stage 7)

**Repositories written:**
- `RunRepository` — creates and updates `runs` record
- `RunStageRepository` — records each stage's start/complete/fail
- `MetricsRepository` — stores `metrics_snapshots` record
- `DecisionRepository` — stores `decision_results` record
- `ArtifactRepository` — registers all output files
- `AuditLogRepository` — records run creation and completion

**Database tables written:** `runs`, `run_stages`, `metrics_snapshots`, `decision_results`, `artifacts`, `audit_logs`

**Frontend polling:** `useRunPolling` calls `GET /api/baseline/runs/{id}/status` every 2 seconds while `status = "running"`.

**Terminal states:** `candidate`, `promising`, `validated`, `rejected`, `failed_controlled`

**Next action:**
- `candidate` / `promising` → Proceed to optimization
- `validated` → Optional: proceed to validation for extra evidence
- `rejected` → Review blocking failures; adjust strategy or data
- `failed_controlled` → Follow the `next_action` hint (data, config, or strategy issue)

---

## 3. Optimization Pipeline (Hyperopt)

**Purpose:** Search the strategy parameter space to find better-performing configurations.

**Frontend trigger:** `/optimization` page → form submit → confirmation dialog → `POST /api/optimization/run`

**Confirmation required:** `user_confirmed: true`

**Prerequisite:** Strategy must have a passing baseline (enforced by `StrategyReadinessGate`).

**Backend service:** `OptimizationPipelineService` (17 stages)

**Pipeline stages (condensed):**

| Stage group | Description |
|---|---|
| Setup (1–4) | Readiness check, data check, workspace prep, config generation |
| Execution (5–9) | Hyperopt run, progress monitoring, results retrieval |
| Selection (10–12) | Best trial identification, parameter export |
| Validation (13–15) | Optimized backtest run, result parsing, comparison vs baseline |
| Reporting (16–17) | Report generation, status update |

**Services used:**
- `FreqtradeConfigGenerator`
- `FreqtradeHyperoptRunner`
- `HyperoptResultParser`
- `FreqtradeBacktestRunner` (for the post-hyperopt optimized backtest)
- `BacktestResultParser`
- `DecisionEngine`

**Repositories written:**
- `OptimizationRepository` — creates `optimization_runs`, writes `optimization_trials`
- `RunRepository` — creates/updates the `optimized_backtest` run record
- `MetricsRepository`, `DecisionRepository`, `ArtifactRepository`, `AuditLogRepository`

**Database tables written:** `optimization_runs`, `optimization_trials`, `runs`, `run_stages`, `metrics_snapshots`, `decision_results`, `artifacts`, `audit_logs`

**Frontend polling:** `GET /api/optimization/runs/{id}/status` every 2 seconds.

**Result:** `comparison_json` in `optimization_runs` shows whether optimized result beat the baseline on key metrics.

**Next action:**
- Improved vs baseline → Proceed to validation
- Did not improve → Consider different spaces, more epochs, or reject optimization
- Failed → Follow `next_action` hint

---

## 4. Validation Pipeline (OOS + WFO + Robustness)

**Purpose:** Collect multi-stage out-of-sample evidence to detect overfitting and confirm strategy robustness.

**Frontend trigger:** `/validation` page → form submit → confirmation dialog → `POST /api/validation/run`

**Confirmation required:** `user_confirmed: true`

**Backend service:** `ValidationExecutionService.run_validation()`

**Sub-workflows executed in sequence:**

### 4a. OOS Validation
- Runs Freqtrade `backtesting` on a held-out time period not used in Hyperopt.
- `evidence_type = "oos"`, `window_index = 0`
- Pass condition: positive profit, non-negative expectancy

### 4b. WFO (Walk-Forward Optimization)
- Splits historical data into N windows (configurable via `wfo_config`)
- For each window: optimize on in-sample portion, test on out-of-sample portion
- Records each window as a separate `validation_evidence` row (`window_index = 0..N-1`)
- Pass condition: majority of windows show positive expectancy

### 4c. Robustness Check
- Runs backtest with varied slippage/spread multipliers
- Tests sensitivity to parameter perturbation
- `evidence_type = "robustness"`
- Pass condition: metrics degrade gracefully (within configured tolerance)

**Repositories written:**
- `ValidationRepository` — creates `validation_runs`, writes `validation_evidence` items
- `RunRepository`, `MetricsRepository`, `ArtifactRepository`, `AuditLogRepository`

**Database tables written:** `validation_runs`, `validation_evidence`, `runs`, `run_stages`, `metrics_snapshots`, `artifacts`, `audit_logs`

**Frontend display:**
- `OOSValidationCard` — shows OOS run metrics and pass/fail
- `WFOValidationCard` — shows per-window results table
- `RobustnessValidationCard` — shows sensitivity analysis results
- All three cards on `/validation/[id]` page

**Terminal outcomes:** `decision_status` on `validation_runs` — `validated`, `rejected`, `partial`

**Next action:**
- `validated` → Strategy has full evidence chain; available for export review
- `rejected` → Review specific failing evidence; OOS vs WFO vs robustness
- `partial` → Some evidence missing; re-run validation or adjust config

---

## 5. Decision Engine Evaluation

**Purpose:** Apply deterministic policy gates to parsed metrics and assign a classification.

**Trigger:** Called internally by `BaselineEvaluationService`, `OptimizationPipelineService`, and `ValidationExecutionService` after result parsing.

**API exposure:** `POST /api/decisions/runs/{run_id}/evaluate` (can be called manually for re-evaluation)

**Backend service:** `DecisionEngine.evaluate(run_id, policy_name)`

**Gates applied:**

| Gate | Type | Description |
|---|---|---|
| `minimum_trades_gate` | Blocking | Rejects if trade count < policy minimum (typically 30–50) |
| `expectancy_gate` | Blocking | Rejects if expectancy ≤ 0 |
| `profit_factor_gate` | Blocking | Rejects if profit_factor < policy threshold |
| `drawdown_gate` | Blocking | Rejects if max_drawdown > policy limit |
| `pair_dependency_gate` | Blocking | Rejects if one pair contributes > policy% of total profit |
| `sharpe_gate` | Non-blocking | Contributes to confidence score |
| `calmar_gate` | Non-blocking | Contributes to confidence score |
| `win_rate_gate` | Non-blocking | Contributes to confidence score |

**Output:** `decision_results` record with `classification`, `confidence_score`, `gates_json`, `blocking_failures_json`, `warnings_json`

**Policies available:** `conservative`, `balanced`, `aggressive` (different threshold values per gate)

---

## 6. Result Parsing

**Purpose:** Convert raw Freqtrade backtest JSON output into structured HER metrics.

**Trigger:** Called internally by `BaselineEvaluationService` and `OptimizationPipelineService` after each backtest execution.

**API exposure:** `POST /api/results/backtest/{run_id}/parse`

**Backend service:** `BacktestResultParser.parse_run(run_id)`

**Steps:**
1. Discover Freqtrade output JSON file in run's artifact directory
2. Load and validate JSON structure
3. Extract core metrics: `net_profit`, `profit_factor`, `max_drawdown`, `sharpe`, `calmar`, `win_rate`, `trade_count`, `expectancy`
4. Extract pair-level performance breakdown
5. Write normalized JSON artifact
6. Run `ResultQualityService` to flag suspicious results
7. Write `metrics_snapshots` record
8. Register all artifacts

**Quality flags (non-blocking, informational):**
- `low_trade_count` — fewer trades than recommended for statistical confidence
- `short_timerange` — backtest period shorter than recommended minimum
- `partial_parse` — not all expected fields could be extracted
- `suspicious_winrate` — win rate > 90% (possible lookahead bias indicator)

---

## 7. Strategy Import

**Purpose:** Import an existing `.py` strategy file into the HER strategy registry.

**Frontend trigger:** Strategy Lab or Workspace import flow → `POST /api/strategy_workspace/strategies/import`

**Backend service:** `StrategyWorkspaceService.import_strategy()`

**Steps:**
1. Locate `.py` file in Freqtrade strategies directory
2. Parse strategy class name and default parameters
3. Check for sidecar JSON (create stub if missing)
4. Register in `strategies` table
5. Create initial `strategy_versions` record
6. Run readiness check — surface any issues

---

## 8. [PLANNED] AI Strategy Designer

**Purpose:** Use local Ollama LLM to generate a strategy spec JSON from a natural language prompt.

**Frontend trigger:** Strategy Lab "Design" tab → prompt input → AI suggest → user review → confirm

**Planned flow:**
- User describes desired strategy in natural language
- AI generates a `StrategySpec` JSON (indicators, entry/exit rules, risk settings)
- User reviews and edits the spec
- System generates the Freqtrade `.py` strategy file from the spec template
- Strategy is imported and readiness-checked

**Safety rule:** AI generates the spec only. File generation uses a deterministic template. No free-form code generation.

---

## 9. [PLANNED] AI Repair Agent

**Purpose:** Analyze a rejected strategy's decision result and suggest targeted fixes.

**Frontend trigger:** Rejected strategy decision page → "Get AI Repair Suggestions" button

**Planned flow:**
- Decision result (gates, reasons, metrics) passed to Ollama
- AI generates a list of suggested parameter adjustments or strategy modifications
- User reviews suggestions — no automatic application
- Each suggestion is logged as an AI action in the audit log

---

## 10. [PLANNED] Candidate Promotion

**Purpose:** Export a `validated` strategy for use outside HER.

**Frontend trigger:** Validated strategy page → "Export" button → explicit confirmation

**Planned output:**
- Freqtrade-ready `.py` strategy file
- Matching `.json` parameter file
- Validation evidence report PDF
- Export manifest with SHA-256 checksums

**Gates before export:**
- `decision_status = "validated"` required
- OOS, WFO, and robustness evidence must all be present
- User must confirm export in a dialog listing all gate outcomes
