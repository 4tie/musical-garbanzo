# Part 13 Prompt 04 Report: OOS Timerange Splitter

## Status

Part 13 Prompt 4 is complete.

This prompt added a pure OOS timerange splitting service. It did not run Freqtrade, add frontend, or modify strategy files.

## Files Created Or Updated

Backend:

- `backend/app/services/oos_timerange_service.py`
- `backend/tests/test_oos_timerange_service.py`

Docs:

- `docs/OOS_VALIDATION.md`
- `docs/PART_13_VALIDATION_EVIDENCE_PLAN.md`
- `docs/PART_13_PROMPT_04_REPORT.md`

## Split Rules

Supported timerange format:

```text
YYYYMMDD-YYYYMMDD
```

The service returns:

- `full_timerange`
- `in_sample_timerange`
- `out_of_sample_timerange`
- `oos_ratio`
- `total_days`
- `in_sample_days`
- `out_of_sample_days`
- `warnings`

The split is deterministic:

- in-sample starts at the full timerange start
- OOS starts exactly at the in-sample end
- OOS ends at the full timerange end
- `in_sample_days + out_of_sample_days == total_days`
- OOS days are rounded up so the holdout period is not smaller than the requested ratio

## Supported Ratios

- `0.20`: 80% in-sample, 20% OOS
- `0.30`: 70% in-sample, 30% OOS
- `0.40`: 60% in-sample, 40% OOS

## Safety Behavior

The service rejects:

- malformed timeranges
- invalid calendar dates
- end date before or equal to start date
- unsupported OOS ratios
- too-short timeranges

The service does not:

- run Freqtrade
- inspect data files
- modify strategy files
- add frontend behavior
- approve or export strategies
- make profit guarantees

## Tests Added

Added `backend/tests/test_oos_timerange_service.py` covering:

- valid 70/30 split
- valid 60/40 split
- valid 80/20 split
- malformed timerange rejected
- end before start rejected
- too-short rejected
- deterministic output
- OOS starts at the in-sample end boundary
- no missing dates
- `build_from_days` works
- invalid build order rejected
- timeframe-specific minimum duration warning

## Validation Result

Command:

```bash
cd /home/mohs/Desktop/her/backend
../.venv/bin/python -m pytest tests/test_oos_timerange_service.py -q
```

Result:

```text
18 passed
```

## Prompt 5 Readiness

Prompt 5 can continue after this commit is pushed to `origin/main`.
