# Decision Real Validation

## Purpose

This validation proves that Part 06 can evaluate a real parsed smoke run from Part 05 and classify poor real evidence as `rejected`.

The validation uses already-saved parsed metrics, pair results, trade summary, quality flags, and normalized artifacts. It does not create fake decision evidence.

## Command

```bash
source .venv/bin/activate
python scripts/evaluate-real-smoke-decision.py --latest-smoke --force --risk-profile balanced --apply-to-run
```

If parsed metrics are missing, run the Part 05 parser first:

```bash
python scripts/parse-real-smoke-backtest.py --latest-smoke --force
python scripts/evaluate-real-smoke-decision.py --latest-smoke --force --risk-profile balanced --apply-to-run
```

## Expected Result

Expected classification:

`rejected`

Expected success marker:

`REAL_DECISION_PASSED`

The known Part 05 real smoke run has poor parsed evidence:

- Negative expectancy.
- Profit factor below `1.0`.
- Very high drawdown.
- Single-pair dependency.
- Parser quality warnings may be present.

These are real parsed metrics from a real smoke result, not synthetic proof.

## Why Rejected Is Correct

The smoke strategy exists to validate integration and parsing, not strategy quality.

Part 06 should reject the run because:

- Negative expectancy means the average parsed trade outcome is unfavorable.
- Profit factor below `1.0` means parsed gross losses exceed parsed gross wins.
- Drawdown above the blocking threshold indicates unacceptable baseline risk evidence.
- Single-pair evidence is too narrow for broader confidence.

Rejecting this result confirms the decision engine is not treating a successful integration smoke run as a successful strategy.

## What It Validates

This validation checks:

- The script can find the latest real smoke run.
- Existing Part 05 parsed metrics can be loaded.
- `DecisionService` can call the policy and decision engine.
- A decision is saved.
- A decision artifact is written.
- The run classification can be safely set to `rejected` when `--apply-to-run` is used.
- The output includes classification, confidence, blocking failures, reasons, quality flags, and report path.

## What It Does Not Prove

This validation does not prove:

- Future trading performance.
- Strategy approval.
- Strategy export readiness.
- Live or dry-run readiness.
- Walk-forward behavior.
- Out-of-sample behavior.
- Robustness.
- Multi-pair generalization.

The script does not run external trading tools, download market data, call model services, send notifications, package strategies, or start trading loops.

## Inspecting The Decision Artifact

After a successful run, inspect:

```bash
cat artifacts/runs/{run_id}/decisions/decision_result.json
```

The artifact contains:

- Classification.
- Confidence score.
- Gate results.
- Reasons.
- Evidence references.
- Warnings.
- Blocking failures.
- Next actions.

The artifact is runtime output and should remain traceable to the evaluated run.
