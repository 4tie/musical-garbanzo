# HER Glossary

Definitions for all domain terms used in the HER codebase, documentation, and UI. Listed alphabetically.

---

## A

**Artifact**
A file produced by a run and registered in the `artifacts` database table. Every artifact has a `run_id`, `artifact_type`, filesystem `path`, `sha256` hash, and `size_bytes`. Examples: normalized backtest JSON, Hyperopt result JSON, strategy report PDF, stage logs. Artifacts are stored under `artifacts/<run_id>/` and are never committed to version control.

**Audit Log**
An append-only record of every significant system action written to the `audit_logs` database table. Each entry contains `action`, `entity_type`, `entity_id`, `details`, and `created_at`. Used for traceability: if a run produced a surprising result, the audit log shows every step that led to it.

---

## B

**Baseline**
The first full evaluation of a strategy. A baseline run executes a Freqtrade backtest with the strategy's default parameters, parses the result, evaluates it through the decision engine, and stores metrics and a decision. The baseline is the reference point for all subsequent optimization and validation. Without a passing baseline, optimization and validation cannot proceed.

**Baseline Run**
A `runs` table record with `mode = "baseline"`. Produced by `POST /api/baseline/evaluate`. Its lifecycle: `pending` → `running` → `candidate` | `rejected` | `failed_controlled`.

**Best Trial**
The Hyperopt trial selected as the winner of an optimization run. Selection is based on the lowest loss score (the Hyperopt objective function value). Stored in `optimization_runs.best_trial_id`. The best trial's parameters become the starting point for the optimized backtest run.

---

## C

**Calmar Ratio**
A risk-adjusted return metric: annualized return divided by maximum drawdown. Stored in `metrics_snapshots.calmar`. Higher is better; a Calmar below 0 means the strategy lost money.

**Candidate**
A classification level assigned by the decision engine. Means the strategy met minimum thresholds (non-negative expectancy, sufficient trades) but did not reach `promising` or `validated` levels. Worth further investigation. Stored as `classification = "candidate"` in `runs` and `decision_results`.

**Confidence Score**
A 0–100 integer produced by the decision engine representing evidence strength. Not a probability of future profitability. A score of 90 means the evidence is comprehensive and consistent; a score of 30 means the evidence is thin or borderline. Stored in `decision_results.confidence_score`.

**Controlled Failure**
An expected, handled failure type — the opposite of a bug. Examples: strategy file not found, insufficient historical data, Hyperopt convergence failure. Produces `status = "failed_controlled"` with a `failure_reason` and a `next_action` suggestion. The UI surfaces these with `ControlledFailureBanner` to distinguish them from unexpected system errors.

---

## D

**Decision Engine**
The deterministic evaluation component (`backend/app/services/decision_engine.py`) that applies policy-defined gates to parsed backtest metrics and assigns a classification. It is stateless and contains no randomness or AI calls. The same metrics always produce the same classification for a given policy. See `docs/DECISION_ENGINE.md`.

**Decision Result**
A record in the `decision_results` table produced by the decision engine for a specific run. Contains `classification`, `confidence_score`, `policy_name`, `gates_json` (each gate and its pass/fail outcome), `reasons_json`, `evidence_json`, `warnings_json`, and `blocking_failures_json`.

**Drawdown**
The peak-to-trough decline in portfolio value expressed as a percentage. `max_drawdown` is the worst single drawdown over the backtest period. Stored in `metrics_snapshots.max_drawdown`. The drawdown gate rejects strategies where drawdown exceeds the policy threshold.

---

## E

**Elite**
A reserved classification for strategies that pass strict validation at multiple timeframes and risk profiles. Not yet implemented. When implemented, `elite` will require passing the most conservative risk profile gates across at least two independent validation runs.

**Expectancy**
The average profit or loss per trade, expressed as a ratio: `(win_rate × avg_win) − (loss_rate × avg_loss)`. Positive expectancy is required for any classification above `rejected`. Stored in `metrics_snapshots.expectancy`.

---

## F

**Freqtrade**
The open-source algorithmic trading framework used as HER's execution engine. HER calls Freqtrade as a CLI subprocess in `backtesting` or `hyperopt` mode only. Live trading (`freqtrade trade`) is forbidden. See `docs/FREQTRADE_INTEGRATION.md`.

---

## G

**Gate**
A single acceptance criterion in the decision engine. Each gate checks one metric against a policy threshold and returns pass or fail. Blocking gates (e.g., `minimum_trades_gate`, `expectancy_gate`) cause `rejected` classification if they fail. Non-blocking gates contribute to the confidence score without blocking promotion.

---

## H

**HER**
The project name. Stands for nothing specific — it is the system identity. Pronounced as the pronoun.

**Hyperopt**
Freqtrade's hyperparameter optimization mode. HER's optimization pipeline runs Freqtrade in hyperopt mode to search the strategy's parameter space for configurations that improve the loss score. Results are stored as `optimization_trials`.

---

## L

**Loss Score**
The value minimized during Hyperopt. Lower is better. Computed by the Hyperopt objective function (configurable per policy). The trial with the lowest loss score becomes the `best_trial`.

---

## M

**Metrics Snapshot**
A record in `metrics_snapshots` containing the parsed performance metrics for a run at a specific `stage_key`. Key fields: `net_profit`, `profit_factor`, `max_drawdown`, `sharpe`, `calmar`, `win_rate`, `trade_count`, `expectancy`. Created by `BacktestResultParser` after every successful backtest.

---

## O

**Optimized Run**
A `runs` table record with `mode = "optimized_backtest"`. A backtest run executed using the best trial parameters found by Hyperopt. Its result is compared against the baseline to determine if optimization improved performance.

**Optimization Run**
A record in `optimization_runs` tracking the full Hyperopt pipeline: setup, execution, trial selection, optimized backtest, and comparison. Contains the `best_trial_id`, `comparison_json` (optimized vs baseline), and `result_status`.

**OOS (Out-of-Sample)**
Out-of-sample validation. A backtest run on a time period that was not used during Hyperopt training. OOS results that are consistent with baseline results are evidence against overfitting. Stored as `validation_evidence` with `evidence_type = "oos"`.

---

## P

**Pair Dependency Gate**
A decision engine gate that checks whether the strategy's performance is concentrated in too few trading pairs. A strategy that relies on one pair for 90% of its profit is considered fragile.

**Positive Expectancy**
A strategy has positive expectancy when `expectancy > 0`. Required for any classification above `rejected`. This is the single most important gate in the decision engine.

**Profit Factor**
The ratio of gross profit to gross loss: `total_profit / total_loss`. A profit factor above 1.0 means the strategy made more than it lost in gross terms. Stored in `metrics_snapshots.profit_factor`. Typical minimum threshold: 1.2 (balanced profile).

**Promising**
A classification level above `candidate`. Assigned when a strategy meets elevated performance thresholds across multiple metrics. Indicates the strategy is worth running through the full optimization and validation pipeline.

---

## R

**Readiness Gate**
A pre-execution check that runs before any Freqtrade call. Verifies the strategy has a valid sidecar JSON, required parameters, accessible file path, and valid configuration. A strategy that fails the readiness gate cannot enter the baseline pipeline. Implemented in `StrategyReadinessGate` service.

**Rejected**
A classification assigned when the strategy fails one or more blocking gates. `rejected` is not a system error — it is the decision engine's conclusion that this strategy's evidence does not meet minimum standards. The rejection reason is stored in `decision_results.blocking_failures_json`.

**Robustness**
A validation check that tests the strategy across varied conditions (different slippage, spread multipliers, or parameter perturbations). A robust strategy degrades gracefully under adverse conditions. Stored as `validation_evidence` with `evidence_type = "robustness"`.

**Run**
A single execution record in the `runs` table. Every Freqtrade execution (baseline, optimized backtest, OOS) and every validation pipeline produces a run. Runs have a lifecycle: `pending` → `running` → terminal state.

**Run Stage**
A single step within a multi-stage pipeline, recorded in `run_stages`. Each stage has a `stage_key`, `order_index`, `status`, `duration_ms`, `input_json`, `output_json`, and `error_json`. Used to track granular progress.

---

## S

**Sensitivity**
Analysis of how much a strategy's metrics change when its parameters are varied slightly. A strategy with high sensitivity (small parameter changes cause large metric swings) is likely overfit. Sensitivity analysis is part of the robustness validation.

**Sharpe Ratio**
Risk-adjusted return metric: `(return − risk_free_rate) / standard_deviation_of_returns`. Stored in `metrics_snapshots.sharpe`. Used as a non-blocking quality signal.

**Sidecar JSON**
A `.json` file paired with a Freqtrade strategy `.py` file. Contains the strategy specification: name, class name, timeframe, pairs, parameter ranges, and configuration metadata. Required by the readiness gate before any run.

**Strategy**
A Freqtrade-compatible trading algorithm implemented as a Python class in a `.py` file, with a matching sidecar JSON spec. Registered in the `strategies` table. Each strategy can have multiple versions tracked in `strategy_versions`.

**Strategy Version**
A snapshot of a strategy's code and parameters at a point in time, stored in `strategy_versions`. Each version has a `version_number`, `py_path`, `json_path`, `code_hash`, and optional notes.

---

## T

**Trade Count**
The total number of trades executed in a backtest. The `minimum_trades_gate` rejects strategies with too few trades (typically fewer than 30–50) because insufficient trade count makes metrics statistically unreliable.

**Trial**
A single Hyperopt evaluation, recorded in `optimization_trials`. Each trial tests one combination of parameters from the search space and records its loss score and key metrics.

---

## V

**Validated**
The highest standard classification. Assigned when a strategy has:
1. A passing baseline (meets `validated` gate thresholds).
2. A passing OOS run (positive results on held-out data).
3. Passing WFO windows (consistent across multiple walk-forward periods).
4. A passing robustness check (graceful degradation under stress).

`validated` does not mean the strategy will be profitable in live markets. It means the historical evidence, collected under multiple independent conditions, passed all configured gates.

**Validation Run**
A record in `validation_runs` tracking the full Part 13 validation pipeline: OOS, WFO, and robustness. Associated evidence items are stored in `validation_evidence`.

---

## W

**WFO (Walk-Forward Optimization)**
Walk-forward optimization. A validation technique that divides the historical data into sequential in-sample (training) and out-of-sample (testing) windows, optimizes on each in-sample period, and evaluates on the following out-of-sample period. WFO evidence is stored as `validation_evidence` with `evidence_type = "wfo"` and a `window_index`.
