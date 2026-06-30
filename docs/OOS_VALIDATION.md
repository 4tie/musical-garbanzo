# Out-of-Sample Validation

## What OOS Means

Out-of-sample validation tests a strategy on a later time period that was not used as the in-sample reference period.

HER uses OOS timerange splitting to separate a full historical timerange into:

- an in-sample segment
- an out-of-sample segment

The split is deterministic and date-based.

## Why OOS Matters

A strategy can look good in one backtest because it overfits one period of market behavior. OOS validation checks whether the same strategy still produces acceptable evidence on a later unseen period.

OOS does not prove future profitability. It only adds evidence that the strategy survived one holdout-period check.

## Supported Format

HER supports Freqtrade-style date timeranges:

```text
YYYYMMDD-YYYYMMDD
```

Example:

```text
20240101-20240601
```

The start date is the beginning of the full range. The end date must be after the start date.

## Split Rules

Supported OOS ratios:

- `0.20`: 80% in-sample, 20% OOS
- `0.30`: 70% in-sample, 30% OOS
- `0.40`: 60% in-sample, 40% OOS

Default:

- 70% in-sample
- 30% OOS

HER uses contiguous boundaries:

- in-sample starts at the full start date
- OOS starts exactly at the in-sample end date
- OOS ends at the full end date
- in-sample days + OOS days = total days

OOS days are rounded up so the OOS segment is not smaller than the requested ratio.

## Examples

Default 70/30 split:

```json
{
  "full_timerange": "20240101-20240601",
  "in_sample_timerange": "20240101-20240416",
  "out_of_sample_timerange": "20240416-20240601",
  "oos_ratio": 0.3,
  "total_days": 152,
  "in_sample_days": 106,
  "out_of_sample_days": 46,
  "warnings": []
}
```

80/20 split:

```json
{
  "full_timerange": "20240101-20240601",
  "in_sample_timerange": "20240101-20240501",
  "out_of_sample_timerange": "20240501-20240601",
  "oos_ratio": 0.2,
  "total_days": 152,
  "in_sample_days": 121,
  "out_of_sample_days": 31,
  "warnings": []
}
```

## Safety Rules

HER rejects:

- malformed timeranges
- invalid calendar dates
- end dates before or equal to start dates
- unsupported OOS ratios
- too-short timeranges

The splitter does not run Freqtrade, inspect data files, modify strategy files, approve strategies, export strategies, or place trades.

## Limitations

OOS splitting is calendar-based. It does not prove that exchange candle data exists for every date in the range. Later validation steps must still check data availability and parse actual Freqtrade results.

Short timeranges can produce misleading holdout evidence, so HER rejects ranges below the minimum duration threshold.

## No Guarantee Statement

Passing OOS validation is not a profit guarantee. It is only evidence that the strategy passed deterministic checks on a holdout timerange.
