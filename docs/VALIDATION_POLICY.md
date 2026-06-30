# Part 13 Validation Policy

## Purpose

The validation policy defines deterministic rules for deciding whether deeper validation evidence passes or fails. It evaluates evidence that HER has already collected and parsed. It does not run Freqtrade, approve strategies, export strategies, place trades, or guarantee future results.

## Threshold Table

| Risk profile | OOS profit factor | OOS expectancy | OOS min trades | Max OOS drawdown | WFO pass rate | Robustness critical failures |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Conservative | >= 1.20 | > 0 | Higher than balanced, timeframe-adjusted | <= 25% | >= 70% | 0 |
| Balanced | >= 1.10 | > 0 | Timeframe-adjusted | <= 35% | >= 60% | 0 |
| Aggressive | >= 1.05 | > 0 | Lower than balanced, timeframe-adjusted | <= 45% | >= 50% | 0 |

Minimum OOS trades are adjusted by timeframe. Lower timeframes require more trades because they usually produce more signals. Higher timeframes allow fewer trades, but zero trades always rejects the evidence.

## Decision Rules

`validated` requires all of the following:

- OOS passed.
- WFO passed, or WFO was explicitly disabled and the final decision records a warning.
- Robustness checks passed.
- No critical risk flags.
- No missing critical metrics.

`rejected` is returned when any of the following are true:

- OOS failed.
- WFO failed.
- Robustness has a critical failure.
- OOS produced zero trades.
- Critical metrics are missing.
- Drawdown exceeds the policy maximum.
- Expectancy is less than or equal to zero.

Every failure includes:

- `code`
- `severity`
- `message`
- `metric_name`
- `actual_value`
- `threshold`
- `next_action`

## What Validated Means

`validated` means the available OOS, WFO, robustness, and risk evidence passed the current deterministic HER validation policy.

It is an evidence status. It should help the user understand that a strategy survived checks beyond a single backtest.

## What Validated Does Not Mean

`validated` does not mean:

- the strategy is approved
- the strategy is exported
- the strategy is ready for live trading
- the strategy is safe to trade
- future performance is guaranteed
- losses cannot happen
- exchange execution risk is solved

## Risk Profile Differences

Conservative policy uses stricter OOS profit factor, drawdown, WFO pass-rate, and minimum-trade requirements.

Balanced policy is the default. It requires positive expectancy, moderate OOS profit factor, timeframe-adjusted trade count, 35% maximum OOS drawdown, and at least 60% WFO pass rate.

Aggressive policy permits lower OOS profit factor, lower minimum trade counts, higher drawdown, and lower WFO pass rate. It still rejects zero trades, missing critical metrics, non-positive expectancy, and robustness critical failures.

## No Guarantee Statement

Validation is not a promise of future profitability. It is only a record that the available evidence passed deterministic checks at the time HER evaluated it.
