# Part 13 Prompt 07 Report

## Status

Prompt 7 added the backend validation execution service. The service orchestrates validation evidence collection while reusing existing readiness, OOS, WFO, Freqtrade, parser, decision, policy, robustness, and persistence components.

The implementation does not add API routes, frontend code, strategy approval, strategy export, live trading, Ollama calls, or AI behavior.

## Files Created Or Updated

- Created `backend/app/services/validation_execution_service.py`
- Created `backend/tests/test_validation_execution_service.py`
- Created `backend/tests/test_validation_controlled_failures.py`
- Updated `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- Created `docs/PART_13_PROMPT_07_REPORT.md`

## Validation Execution Flow

Implemented stages:

- `validation_setup`
- `candidate_reference`
- `readiness_gate`
- `oos_timerange_split`
- `oos_backtest`
- `oos_result_parsing`
- `oos_decision`
- `wfo_window_generation`
- `wfo_window_execution`
- `wfo_result_parsing`
- `wfo_decision`
- `robustness_checks`
- `sensitivity_checks`
- `validation_decision`
- `validation_report`
- `completion`

The service creates a validation run record, resolves the candidate reference, checks strategy readiness, requires explicit user confirmation before Freqtrade backtests, executes OOS and WFO child backtest runs, persists evidence rows, evaluates robustness, makes the final deterministic decision, and writes a validation report.

## OOS Behavior

- Uses `OOSTimerangeService`.
- Runs the OOS backtest only on the out-of-sample timerange.
- Uses existing config generation, backtest runner, parser, and decision service dependencies.
- Missing OOS metrics are treated as evidence failure and produce a rejected final decision rather than fake evidence.

## WFO Behavior

- Uses `WFOWindowService`.
- Runs WFO test windows with fixed strategy parameters.
- Does not implement Hyperopt redesign or per-window optimization.
- Persists each WFO window as evidence and adds a WFO summary evidence record.

## Robustness Behavior

- Uses `RobustnessEvaluator`.
- Uses `ValidationPolicyService.evaluate_robustness` to normalize robustness check outcomes.
- Persists robustness checks as evidence rows.

## Final Decision Behavior

- Uses `ValidationPolicyService.make_final_decision`.
- `validated` requires OOS pass, WFO pass or disabled with warning, and robustness pass.
- Valid evidence failures complete the run with `decision_status="rejected"`.
- Execution failures return controlled `validation_error` responses.

## Report Artifact

Writes:

```text
artifacts/runs/{validation_run_id}/validation/validation_report.json
```

The report includes request metadata, candidate reference, policy, OOS result, WFO result, robustness checks, sensitivity checks, final decision, evidence IDs, artifact paths, warnings, errors, next actions, and a no-guarantee statement.

The report excludes stdout and stderr payloads and redacts secret-like fields.

## Controlled Failures

Implemented controlled responses for:

- `strategy_not_ready`
- `confirmation_required`
- `candidate_reference_missing`
- `oos_timerange_invalid`
- `oos_backtest_failed`
- `oos_parse_failed`
- `wfo_window_generation_failed`
- `wfo_backtest_failed`
- `wfo_parse_failed`
- `validation_report_failed`
- `unexpected_validation_error`

## Tests Added

`backend/tests/test_validation_execution_service.py` covers:

- readiness gate called
- confirmation blocks real validation
- OOS timerange split used
- OOS backtest called with OOS timerange
- WFO windows generated and executed
- robustness evaluator path exercised
- final decision generated
- evidence persisted
- report artifact generated
- missing metrics rejected without fake metrics
- no live/export/approval/secret wording in response

`backend/tests/test_validation_controlled_failures.py` covers:

- blocked strategy does not run backtests
- missing candidate reference controlled
- invalid OOS timerange controlled
- OOS backtest failure controlled
- WFO backtest failure controlled
- parse failure controlled
- sanitized controlled-failure response

## Validation

Command:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_validation_execution_service.py tests/test_validation_controlled_failures.py tests/test_validation_policy_service.py tests/test_oos_timerange_service.py tests/test_wfo_window_service.py tests/test_robustness_evaluator.py -q
```

Result:

```text
76 passed, 12 warnings in 1.59s
```

## Known Limitations

- WFO uses fixed strategy parameters and does not run Hyperopt per window.
- Sensitivity checks only evaluate supplied variant results. Prompt 7 does not generate sensitivity variants.
- The service has no API route or frontend entry point yet.
- Validation evidence is not approval, export, live readiness, or a performance guarantee.
