# Walk-Forward Validation

## What WFO Means

Walk-forward validation splits a larger timerange into repeated chronological train/test windows. Each window uses an earlier train segment followed by a later test segment.

In Part 13 Prompt 5, HER only builds these windows. It does not run Hyperopt, run Freqtrade, add frontend behavior, or modify strategy files.

## Why WFO Matters

One backtest can look good because the strategy fits one specific market period. Walk-forward validation checks whether performance is more stable across multiple later test periods.

WFO adds evidence, but it does not prove future profitability.

## Supported Timerange Format

```text
YYYYMMDD-YYYYMMDD
```

Example:

```text
20240101-20240601
```

## Window Rules

Each generated window contains:

- `window_index`
- `train_timerange`
- `test_timerange`
- `train_start`
- `train_end`
- `test_start`
- `test_end`
- `status`

Rules:

- Train period must come before test period.
- Test starts exactly at train end.
- Test windows do not overlap.
- `step_days` must be greater than or equal to `test_days`.
- `max_windows` limits the number of returned windows.
- Invalid or too-short ranges are rejected.
- Output ordering is deterministic.

## Example

Input:

```json
{
  "timerange": "20240101-20240601",
  "train_days": 60,
  "test_days": 30,
  "step_days": 30,
  "max_windows": 5
}
```

Output:

```json
[
  {
    "window_index": 1,
    "train_timerange": "20240101-20240301",
    "test_timerange": "20240301-20240331",
    "status": "pending"
  },
  {
    "window_index": 2,
    "train_timerange": "20240131-20240331",
    "test_timerange": "20240331-20240430",
    "status": "pending"
  },
  {
    "window_index": 3,
    "train_timerange": "20240301-20240430",
    "test_timerange": "20240430-20240530",
    "status": "pending"
  }
]
```

## Limitations

The WFO window builder only creates date windows. It does not check whether candle data exists, whether Freqtrade can run those windows, or whether the strategy passes policy thresholds. Later Part 13 services must run and parse real evidence before HER can make validation decisions.

## No Guarantee Statement

Passing future WFO validation is not a profit guarantee. WFO is evidence that a strategy survived repeated historical holdout checks, not proof of future performance.
