# Part 13 Prompt 03 Report: Validation Policy Service

## Status

Part 13 Prompt 3 is complete.

This prompt added deterministic validation policy and decision rules only. It did not run Freqtrade, add frontend, approve strategies, export strategies, or make profit guarantees.

## Files Created Or Updated

Backend:

- `backend/app/services/validation_policy_service.py`
- `backend/app/schemas/validation.py`
- `backend/tests/test_validation_policy_service.py`
- `backend/tests/test_validation_schemas.py`

Docs:

- `docs/VALIDATION_POLICY.md`
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- `docs/PART_13_PROMPT_03_REPORT.md`

## Policy Thresholds

Conservative:

- OOS profit factor >= `1.20`
- OOS expectancy > `0`
- OOS minimum trades higher than balanced, timeframe-adjusted
- Maximum OOS drawdown <= `25%`
- WFO pass rate >= `70%`
- Robustness critical failures = `0`

Balanced:

- OOS profit factor >= `1.10`
- OOS expectancy > `0`
- OOS minimum trades timeframe-adjusted
- Maximum OOS drawdown <= `35%`
- WFO pass rate >= `60%`
- Robustness critical failures = `0`

Aggressive:

- OOS profit factor >= `1.05`
- OOS expectancy > `0`
- Lower OOS minimum trades, timeframe-adjusted
- Maximum OOS drawdown <= `45%`
- WFO pass rate >= `50%`
- Robustness critical failures = `0`

## Decision Rules

`validated` only if:

- OOS passed.
- WFO passed, or WFO was disabled with an explicit warning.
- Robustness passed.
- No critical risk flags exist.
- No critical metrics are missing.

`rejected` if:

- OOS failed.
- WFO failed.
- Robustness has a critical failure.
- OOS has zero trades.
- Critical metrics are missing.
- Drawdown exceeds the policy maximum.
- Expectancy is less than or equal to zero.

Every failure issue includes:

- `code`
- `severity`
- `message`
- `metric_name`
- `actual_value`
- `threshold`
- `next_action`

## Tests Added

Added `backend/tests/test_validation_policy_service.py` covering:

- conservative thresholds
- balanced thresholds
- aggressive thresholds
- OOS pass
- OOS fail profit factor
- OOS fail expectancy
- OOS fail drawdown
- OOS fail zero trades
- WFO pass
- WFO fail pass rate
- robustness pass
- robustness fail critical
- final validated decision
- final rejected decision
- missing metrics rejected safely
- no profit guarantee wording

## Validation Results

Requested command:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_validation_policy_service.py -q
```

Result:

```text
16 passed
```

Additional compatibility check:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_validation_schemas.py -q
```

Result:

```text
24 passed
```

## Prompt 4 Readiness

Prompt 4 can continue after the requested focused tests pass and this commit is pushed to `origin/main`.
