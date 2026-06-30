# Decision Engine

## Purpose

The Part 06 Decision Engine evaluates already-parsed Part 05 backtest evidence against deterministic acceptance gates and returns an explainable `DecisionResult`.

It does not persist decisions, update runs, run Freqtrade, download market data, call Ollama, send Discord messages, approve strategies, export strategies, start trading loops, or predict future outcomes.

`DecisionService` is the separate orchestration layer that can load persisted Part 05 evidence, call the engine, save the returned decision, write a report artifact, and optionally apply the safe Part 06 classification to the run.

## Gate List

The engine evaluates these gates:

- `parse_quality_gate` - checks parser errors, stdout fallback, partial parse, and decision usability.
- `minimum_trades_gate` - checks trade count against the timeframe and risk-profile policy minimum.
- `profit_factor_gate` - checks missing profit factor, PF below `1.0`, and candidate/promising/validated PF tiers.
- `expectancy_gate` - checks missing or negative expectancy and policy expectancy tiers.
- `drawdown_gate` - checks missing drawdown, blocking high drawdown, and policy drawdown tiers.
- `win_loss_balance_gate` - warns on missing win/loss evidence or very low win rate.
- `pair_dependency_gate` - warns on missing pair evidence, single-pair evidence, or concentrated pair contribution.

Gate statuses:

- `passed`
- `failed`
- `warning`
- `not_applicable`
- `insufficient_data`

Gate severities:

- `info`
- `warning`
- `blocking`

## Classification Definitions

### `rejected`

Assigned when any blocking gate fails, or when the evidence does not meet the minimum thresholds for `candidate`.

Examples:

- Negative expectancy.
- Profit factor below `1.0`.
- Drawdown above the blocking threshold.
- Missing trade count.
- Trade count below the policy minimum.
- Parser quality errors.

### `candidate`

Assigned when no blocking gate fails and baseline evidence meets candidate thresholds:

- Profit factor meets candidate threshold.
- Expectancy meets candidate threshold.
- Drawdown is at or below candidate maximum.
- Minimum trade count passed.

### `promising`

Assigned when no blocking gate fails and baseline evidence meets the stronger promising thresholds:

- Profit factor meets promising threshold.
- Expectancy meets promising threshold.
- Drawdown is at or below promising maximum.
- Minimum trade count passed.

### `validated`

Assigned only when clean baseline evidence meets strict validated thresholds:

- Profit factor meets validated threshold.
- Expectancy meets validated threshold.
- Drawdown is at or below validated maximum.
- Minimum trade count passed.
- Parse quality is usable.
- No critical warnings are present.

`validated` is not approved. It is not exported. It is not live-ready. It only means the single parsed baseline backtest evidence is strong enough for future WFO, OOS, robustness, and review stages.

## Confidence Score Behavior

The confidence score is a bounded evidence-strength score from `0` to `100`.

It starts at `100` and applies penalties for:

- Warning gates.
- Missing optional metrics.
- Single-pair dependency.
- Drawdown near thresholds.
- Trade count near the minimum.

Caps:

- Rejected due to blocking failure: maximum `40`.
- Parser evidence not usable: maximum `20`.
- Explicit no-trade result: maximum `10`.

The score is not a probability and does not predict future returns.

## Examples

### Rejected

Metrics:

- Profit factor: `0.44`
- Expectancy: `-1.14`
- Drawdown: `99.6%`

Expected classification: `rejected`.

Reasons include:

- `negative_expectancy`
- `profit_factor_below_one`
- `drawdown_above_limit`

### Candidate

Metrics:

- Profit factor: above candidate threshold.
- Expectancy: non-negative.
- Drawdown: within candidate maximum.
- Trade count: at or above minimum.

Expected classification: `candidate`.

### Promising

Metrics:

- Profit factor: above promising threshold.
- Expectancy: above promising threshold.
- Drawdown: within promising maximum.
- Trade count: at or above minimum.

Expected classification: `promising`.

### Validated

Metrics:

- Profit factor: above validated threshold.
- Expectancy: above validated threshold.
- Drawdown: within validated maximum.
- Trade count: at or above minimum.
- Parse and warning gates are clean.

Expected classification: `validated`.

This still requires future validation before export or deployment can be considered.

## What Part 06 Does Not Decide

Part 06 does not decide:

- Strategy approval.
- Strategy export.
- Live readiness.
- Dry-run readiness.
- Future profitability.
- WFO/OOS success.
- Robustness success.
- Multi-pair generalization.

## Decision Service Persistence

`DecisionService.evaluate_run()` connects the pure engine to persisted run evidence:

1. Loads the run record.
2. Loads the latest metrics snapshot, pair results, trade summary, quality report, and normalized artifact path.
3. Builds a policy through `DecisionPolicyService`.
4. Evaluates the evidence with `DecisionEngine`.
5. Saves the `DecisionResult` through `DecisionRepository`.
6. Writes `artifacts/runs/{run_id}/decisions/decision_result.json`.
7. Registers the decision artifact as `metrics_json` with description `Decision engine result`.
8. Optionally applies `runs.classification` when `apply_to_run=true`.
9. Adds run logs and an audit entry.

Controlled failure behavior:

- Missing run returns `run_not_found`.
- Missing parsed metrics returns `parsed_metrics_missing` and tells the caller to run the Part 05 parse endpoint or script first.

Run update behavior:

- `apply_to_run=true` updates `runs.classification` only to `rejected`, `candidate`, `promising`, or `validated`.
- The service does not set `approved`, `exported`, live-ready state, or strategy file changes.
- Run status is not changed by this service.

Idempotency:

- Re-running evaluation creates another decision row by default.
- `force=true` deletes prior decision rows for the run before saving the new decision.
- The decision report artifact path is overwritten safely.

## Decision API

The Decisions router exposes safe API access under both `/api` and `/api/v1`:

- `GET /decisions/policies`
- `GET /decisions/policies/{policy_name}`
- `POST /decisions/runs/{run_id}/evaluate`
- `GET /decisions/runs/{run_id}`
- `GET /decisions/runs/{run_id}/latest`
- `GET /results/backtest/{run_id}/decision`
- `GET /runs/{run_id}/decision`

The evaluate endpoint calls `DecisionService.evaluate_run()` and requires parsed Part 05 metrics. It does not run Freqtrade, parse raw output, call Ollama, send Discord messages, approve strategies, or export strategies.

Outward API payloads are sanitized to avoid deployment-oriented wording in decision responses. The persisted decision and report artifact remain traceable evidence records.

## Why Validated Is Not Approved

`validated` in Part 06 means the baseline parsed backtest evidence passed strict single-backtest gates. A single backtest can still be overfit, pair-dependent, regime-dependent, or sensitive to parameters.

Later HER parts must handle walk-forward analysis, out-of-sample validation, robustness checks, review, and explicit export controls before any deployment-oriented workflow exists.
