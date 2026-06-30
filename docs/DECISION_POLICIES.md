# Decision Policies

## Purpose

Part 06 decision policies centralize the thresholds used to evaluate already-parsed backtest evidence.

The policy layer answers questions such as:

- How many trades are enough for this timeframe?
- What profit factor threshold applies to this risk profile?
- What drawdown level is acceptable for each classification tier?
- Which evidence gaps are blocking versus warning conditions?

Decision policies do not run Freqtrade, download market data, call Ollama, send Discord messages, approve strategies, export strategies, or predict future trading outcomes.

## Risk Profile Thresholds

The default policy set has three risk profiles. Thresholds are starting defaults and can be tuned in future parts as HER collects more validation evidence.

| Risk profile | Candidate PF | Promising PF | Validated PF | Candidate max DD | Promising max DD | Validated max DD | Candidate expectancy | Promising expectancy | Validated expectancy |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Conservative | `1.15` | `1.30` | `1.50` | `25%` | `20%` | `15%` | `0.00` | `0.05` | `0.10` |
| Balanced | `1.10` | `1.25` | `1.40` | `30%` | `25%` | `20%` | `0.00` | `0.03` | `0.08` |
| Aggressive | `1.05` | `1.18` | `1.30` | `40%` | `35%` | `30%` | `0.00` | `0.01` | `0.05` |

Additional defaults:

- Single-pair dependency warning threshold: `0.80`.
- Minimum pair count warning: fewer than `2` pairs.
- High drawdown blocking threshold: `40%` conservative, `45%` balanced, `55%` aggressive.
- Optional win-rate threshold: not enforced in the initial policy because win rate alone is insufficient evidence.

## Minimum Trades By Timeframe

The base minimum-trade table is:

| Timeframe | Base minimum trades |
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

- Conservative: `+25%`.
- Balanced: no change.
- Aggressive: `-20%`.

The adjusted minimum is rounded to the nearest integer. Unknown or missing timeframes fall back to the `1h` baseline.

## Blocking Rules

Initial blocking rules:

- Negative expectancy is always blocking.
- Profit factor below `1.0` is blocking.
- Drawdown above `high_drawdown_block_threshold` is blocking.
- Missing trade count is blocking.
- Result quality parse errors are blocking.

Initial warning rules:

- Missing profit factor is at least a warning and may block decision usability when parser quality says the core metric is missing.
- Missing drawdown is a warning.
- Single-pair dependency is a warning unless a future policy makes it blocking.
- Low pair count is a warning.

These rules define gate behavior for future decision logic. This policy layer does not assign final classifications by itself.

## Engine Usage

`DecisionPolicyService` provides thresholds to `DecisionEngine`.

`DecisionEngine` applies the thresholds through named gates and returns an in-memory `DecisionResult`. That result is explainable but is not saved by the engine. A later service layer is responsible for loading run evidence, saving decision rows, writing report artifacts, and optionally applying safe run classifications.

## Not Profit Guarantees

Thresholds are acceptance gates for historical parsed evidence. They do not prove that a strategy will make money in future trading.

A `candidate`, `promising`, or `validated` Part 06 result still requires later walk-forward, out-of-sample, robustness, and review stages before any export or deployment discussion.

## Future Tuning

Future HER parts can tune policies by:

- Adding exchange-specific or market-regime-specific thresholds.
- Adjusting minimum trade counts after real validation data accumulates.
- Making pair concentration stricter for multi-pair workflows.
- Adding Sharpe, Calmar, or average win/loss gates when those metrics are reliably parsed.
- Versioning policy names so historical decisions remain reproducible.
- Allowing user-visible threshold presets without silently changing existing decisions.
