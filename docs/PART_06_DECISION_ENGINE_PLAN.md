# Part 06 Decision Engine Plan

## Part 06 Goal

Part 06 turns parsed Part 05 backtest evidence into clear, explainable strategy decisions.

The Decision Engine reads already-parsed metrics, pair results, trade summary, result quality flags, and normalized artifacts. It applies deterministic acceptance gates, assigns one safe baseline classification, stores decision evidence, and exposes decision APIs for the frontend and later workflow stages.

Part 06 evaluates evidence only. It does not claim a strategy is profitable, approved, exportable, live-ready, or safe for future trading.

## Part 05 Readiness Confirmation

Part 05 readiness evidence exists and is sufficient for Part 06 planning:

- `docs/PART_05_COMPLETION_REPORT.md` confirms the real parser validation passed.
- Real smoke run ID: `ff67da72-a62c-4a20-8674-37b1d3959cec`.
- Parser result: `REAL_PARSE_PASSED`.
- Raw structured result: `artifacts/runs/ff67da72-a62c-4a20-8674-37b1d3959cec/raw_freqtrade/backtest_results/backtest-result-2026-06-28_21-07-02.zip`.
- Normalized artifact: `artifacts/runs/ff67da72-a62c-4a20-8674-37b1d3959cec/normalized/backtest_result.normalized.json`.
- Parsed metrics include trade count, profit factor, drawdown, and expectancy.
- No fake or mock result was used as readiness proof.

The real smoke strategy produced poor evidence:

- Trade count: `8678`.
- Profit factor: `0.44620083091599505`.
- Max drawdown percent: `99.61469594219984`.
- Expectancy: `-1.1478992387900437`.
- Quality flags include `negative_expectancy` and `high_drawdown`.

Part 06 validation must classify this real smoke run as `rejected`.

## Explicit Scope

Part 06 includes:

- Reading parsed Part 05 evidence from SQLite and normalized artifacts.
- Checking parser decision usability before scoring.
- Applying deterministic acceptance gates.
- Producing one of the allowed classifications: `rejected`, `candidate`, `promising`, or `validated`.
- Producing explainable pass/fail gate evidence.
- Producing human-readable decision reasons.
- Calculating a bounded confidence score that describes evidence strength, not future profitability.
- Saving decision results in SQLite and as a report artifact.
- Updating the run classification and, where appropriate, run status to the same safe classification.
- Writing audit logs and run logs for the decision action.
- Exposing decision APIs.
- Validating decision logic against the real Part 05 smoke run.

## Explicit Non-Goals

Part 06 does not:

- Generate strategies.
- Repair strategies.
- Run Freqtrade.
- Download market data.
- Run Hyperopt.
- Run walk-forward analysis.
- Run out-of-sample validation.
- Run robustness analysis.
- Call Ollama or any AI model.
- Send Discord messages.
- Approve strategies.
- Export strategies.
- Modify strategy files.
- Start live trading.
- Start dry-run trading bot loops.
- Place exchange orders.
- Claim future profitability.
- Treat one backtest as proof of a profitable strategy.

## Allowed Classification Tiers

### `rejected`

Evidence is insufficient or failed one or more blocking gates.

Examples:

- Parser evidence is not usable for decision.
- No trades or too few trades.
- Net profit is not positive.
- Profit factor is below the minimum threshold.
- Drawdown exceeds the configured threshold.
- Expectancy is missing or not positive.
- Required core metrics are missing.
- Quality flags indicate a blocking evidence problem.

### `candidate`

Strategy has basic positive evidence but is not robust enough.

Part 06 `candidate` means the baseline backtest evidence clears minimum viability gates, but the evidence is still weak or incomplete for stronger classification. It still requires future OOS, WFO, and robustness work.

### `promising`

Strategy has stronger evidence and passes most baseline gates.

Part 06 `promising` means baseline metrics are stronger than the `candidate` threshold and no blocking gate failed. It still does not mean the strategy is approved, exportable, live-ready, or known to be profitable in the future.

### `validated`

Strategy passes strict single-backtest evaluation gates, but is not approved for export or live trading yet.

Part 06 `validated` only means parsed baseline evidence is strong enough for future WFO, OOS, and robustness parts. It does not mean live-ready, approved, exported, or profitable-guaranteed.

## Forbidden Part 06 Outcomes

Part 06 must never emit or persist these decision outcomes:

- `approved`
- `exported`
- `live_ready`
- `profitable_guaranteed`

Existing project-wide lifecycle documents may mention later states such as `approved` and `exported`. Part 06 must not use those states.

## Acceptance Gate List

The initial deterministic gates are:

- `evidence_available`: latest parsed metrics, trade summary, and quality report can be loaded.
- `decision_usable`: Part 05 quality report has `is_usable_for_decision=true`.
- `real_or_traceable_result`: decision evidence points to parsed artifacts, source files, and parser metadata.
- `core_metrics_present`: trade count, net profit, profit factor, drawdown, and expectancy are present.
- `trade_count_minimum`: trade count meets timeframe-aware minimum.
- `net_profit_positive`: net profit is greater than zero after parsed costs.
- `profit_factor_minimum`: profit factor meets the threshold for the target classification.
- `drawdown_maximum`: max drawdown percent or normalized drawdown is below the risk-profile threshold.
- `expectancy_positive`: expectancy is greater than zero.
- `win_loss_sanity`: wins/losses/trade counts are internally consistent when available.
- `pair_evidence_present`: pair results exist when the parser expects them.
- `pair_concentration_check`: single-pair dependency is surfaced and may cap confidence or classification.
- `quality_flags_check`: parser errors, missing structured result, partial parse, or missing core metrics block decisions above `rejected`.
- `overfit_warning_check`: extreme profit factor or very low trade count raises a warning and caps classification.

## Decision Policy Plan

Decision policy should be deterministic and ordered:

1. Load the latest Part 05 parsed evidence.
2. If evidence is missing or not usable for decision, classify `rejected`.
3. Evaluate every gate and store pass/fail/warning details.
4. Apply blocking gates first.
5. If any blocking gate fails, classify `rejected`.
6. If all minimum gates pass, evaluate thresholds for `candidate`, `promising`, and `validated`.
7. Assign the strongest allowed tier whose thresholds are fully met.
8. Apply classification caps for warning conditions such as stdout-only parsing, single-pair dependency, or extreme overfit-risk metrics.
9. Save a decision report with metrics snapshot IDs, quality flags, gate results, reasons, and source artifact references.
10. Update run classification only to `rejected`, `candidate`, `promising`, or `validated`.

The policy must be explainable: every classification needs both machine-readable gate results and short user-facing reasons.

## Risk Profile Thresholds

Initial thresholds are centralized in `backend/app/services/decision_policy.py` and documented in `docs/DECISION_POLICIES.md`. Defaults should prefer rejection or lower classification when evidence is ambiguous.

| Risk profile | Candidate PF | Promising PF | Validated PF | Candidate max DD | Promising max DD | Validated max DD | Candidate expectancy | Promising expectancy | Validated expectancy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `conservative` | `1.15` | `1.30` | `1.50` | `25%` | `20%` | `15%` | `0.00` | `0.05` | `0.10` |
| `balanced` | `1.10` | `1.25` | `1.40` | `30%` | `25%` | `20%` | `0.00` | `0.03` | `0.08` |
| `aggressive` | `1.05` | `1.18` | `1.30` | `40%` | `35%` | `30%` | `0.00` | `0.01` | `0.05` |

All risk profiles require:

- Positive net profit.
- Positive expectancy.
- Minimum trade count for the run timeframe.
- Decision-usable parser evidence.

## Timeframe-Aware Minimum Trades

Part 06 should infer the minimum trade count from the run timeframe. If timeframe is missing or unsupported, use the balanced `1h` default and add a warning in the future decision service.

| Timeframe | Balanced minimum trades |
| --- | ---: |
| `1m` | `500` |
| `3m` | `400` |
| `5m` | `300` |
| `15m` | `150` |
| `30m` | `100` |
| `1h` | `60` |
| `2h` | `40` |
| `4h` | `30` |
| `1d` | `20` |

Risk profile modifiers:

- `conservative`: `+25%`.
- `balanced`: no change.
- `aggressive`: `-20%`.

Minimum trades are baseline statistical sufficiency checks only. Meeting the minimum does not prove a strategy is profitable or ready for trading.

## Confidence Score Plan

The confidence score is a bounded explanation aid from `0` to `100`. It describes how complete and strong the parsed evidence is for the assigned baseline classification.

It must not be named or described as profitability probability.

Suggested components:

- Evidence completeness: core metrics, pair results, trade summary, normalized artifact, and quality report are present.
- Gate strength: number and importance of passed gates.
- Metric margin: distance above profit factor, drawdown, expectancy, and trade count thresholds.
- Evidence quality penalties: stdout-only parse, parser warnings, partial pair evidence, single-pair dependency, missing optional risk metrics.
- Overfit caution penalty: extreme profit factor, unusually few trades for timeframe, or concentrated pair evidence.

Confidence score caps:

- Any blocking gate failure caps confidence at `25`.
- `candidate` caps confidence at `60`.
- `promising` caps confidence at `80`.
- `validated` caps confidence at `95`.
- Parser warning quality caps confidence below `90`.
- Single-pair-only evidence caps confidence below `80` unless future multi-pair validation exists.

## Decision Reasons And Evidence Plan

Each decision should persist:

- `run_id`.
- Final `classification`.
- `confidence_score`.
- Risk profile used.
- Timeframe and minimum trade threshold used.
- Policy version.
- Gate results with `gate_key`, `status`, `severity`, `message`, expected value, actual value, and metric source.
- Blocking reasons.
- Warning reasons.
- Positive evidence reasons.
- Quality flags consumed from Part 05.
- Metrics snapshot ID and metric values used.
- Pair result summary and concentration notes.
- Trade summary evidence.
- Normalized artifact path.
- Raw source file references from parser metadata when available.
- Creation timestamp.

User-facing language must stay careful:

- Say "baseline evidence passed" instead of "strategy is profitable".
- Say "requires future OOS/WFO/robustness validation" for non-rejected outcomes.
- Say "`validated` is not live-ready" for `validated` decisions.

## Database Persistence Plan

Part 06 should add a dedicated persistence layer rather than overloading parser tables.

Implemented persistence table: `decision_results`.

Columns:

- `id TEXT PRIMARY KEY`
- `run_id TEXT NOT NULL`
- `classification TEXT NOT NULL`
- `confidence_score REAL`
- `policy_name TEXT NOT NULL`
- `risk_profile TEXT`
- `timeframe TEXT`
- `decision_json TEXT NOT NULL`
- `gates_json TEXT`
- `reasons_json TEXT`
- `evidence_json TEXT`
- `warnings_json TEXT`
- `blocking_failures_json TEXT`
- `normalized_result_artifact_path TEXT`
- `created_at TEXT NOT NULL`

Indexes:

- `idx_decision_results_run_id`
- `idx_decision_results_classification`
- `idx_decision_results_created_at`
- `idx_decision_results_policy_name`

Additional persistence:

- Register the Markdown or JSON decision report artifact as `report_md` or `other`.
- Add a run log entry with source `decision_engine`.
- Add an audit log entry with actor `system`, action type `decision_evaluated`, and before/after run classification.
- The repository layer stores `decision_results` only and does not update `runs.classification`.
- A later service layer may update `runs.classification` to the final allowed classification.
- A later service layer may update `runs.status` only to a safe allowed classification state when policy says the Part 06 stage owns that transition.

Part 06 must not write `approved`, `exported`, `live_ready`, or `profitable_guaranteed` to any table.

## API Plan

Decision APIs should be mounted under `/api/*` and `/api/v1/*`.

Planned endpoints:

- `POST /api/decisions/backtest/{run_id}/evaluate`
- `GET /api/decisions/backtest/{run_id}`
- `GET /api/decisions/backtest/{run_id}/report`
- `GET /api/runs/{run_id}/decision`

### Evaluate Decision

`POST /api/decisions/backtest/{run_id}/evaluate`

Behavior:

- Loads existing Part 05 parsed evidence.
- Does not run Freqtrade.
- Does not parse raw outputs unless a later prompt explicitly adds safe reparse orchestration.
- Applies gates.
- Saves a new decision report.
- Updates only safe Part 06 classification values.

Optional request body:

```json
{
  "risk_profile": "moderate",
  "force": false
}
```

Response:

```json
{
  "run_id": "uuid",
  "classification": "rejected",
  "confidence_score": 18.0,
  "passed_gates": [],
  "failed_gates": [],
  "warning_gates": [],
  "reasons": [],
  "decision_report_id": "uuid"
}
```

### Get Latest Decision

`GET /api/decisions/backtest/{run_id}`

Returns the latest saved decision report for the run.

### Get Decision Report

`GET /api/decisions/backtest/{run_id}/report`

Returns a user-facing report payload or report artifact metadata.

### Compatibility Route

`GET /api/runs/{run_id}/decision`

Returns the latest decision summary for UI run detail pages.

## Real Decision Validation Plan

Part 06 final validation must use the real Part 05 smoke run:

- Run ID: `ff67da72-a62c-4a20-8674-37b1d3959cec`.
- Use saved Part 05 parsed metrics and quality flags.
- Do not run Freqtrade.
- Do not download data.
- Do not call Ollama.
- Do not send Discord messages.
- Do not modify strategy files.

Expected result:

- Classification: `rejected`.
- Blocking reasons must include negative expectancy, profit factor below threshold, and excessive drawdown.
- Evidence should reference the parsed metrics and normalized artifact.
- The decision report should explicitly state that the result is a baseline evidence decision only.

Unit and API tests should cover:

- Missing evidence returns a controlled `rejected` decision or clear API error according to policy.
- Parser `is_usable_for_decision=false` blocks non-rejected classifications.
- Realistic poor metrics classify as `rejected`.
- Minimum viable metrics classify as `candidate`.
- Stronger metrics classify as `promising`.
- Strict metrics classify as `validated`.
- Forbidden classifications are rejected by service and API validation.
- No code path invokes Freqtrade, Ollama, Discord, or strategy file writes.

## Safety Rules

Part 06 must follow these safety rules:

- Do not run Freqtrade.
- Do not download data.
- Do not call Ollama.
- Do not send Discord messages.
- Do not approve or export a strategy.
- Do not claim future profitability.
- Do not modify strategy files.
- Do not use fake or mock results as final readiness proof.
- Do not ignore missing metrics.
- Do not silently change thresholds.
- Do not hide gate failures.
- Do not treat data availability problems as strategy quality failures unless Part 05 evidence is already parsed and decision-usable.
- Do not classify above `rejected` when parser evidence is incomplete, missing core metrics, or marked unusable for decision.
- Do not emit forbidden outcomes in API responses, database rows, logs, audit entries, report artifacts, or frontend-facing text.

## Implementation Order

1. Add decision schemas and threshold configuration. Done.
2. Add decision repository and migration for `decision_results`. Done.
3. Add acceptance policy and threshold service. Done.
4. Add decision engine service with deterministic gates.
5. Add report artifact writing and audit/run log persistence.
6. Add Decision API router.
7. Add unit tests for gates, thresholds, confidence caps, and forbidden outcomes.
8. Add API tests.
9. Validate against the real Part 05 smoke run and document the result.

Decision policy and persistence scaffolding exist. Final decision classification logic is intentionally not implemented yet.
