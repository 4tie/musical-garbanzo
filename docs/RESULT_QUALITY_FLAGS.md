# Result Quality Flags

Result quality flags help HER distinguish clean parsed backtest evidence from weak, incomplete, or fallback-only evidence.

Flags are not strategy decisions. They do not approve, reject, export, promote, or classify a strategy. They only describe whether enough parsed data exists for metrics storage, display, and a future decision engine.

## Why Quality Flags Exist

Freqtrade outputs can be complete, partial, missing, malformed, or available only as stdout text. HER needs explicit quality metadata so later AutoQuant stages can avoid treating weak parser evidence as clean evidence.

Quality flags make these cases visible:

- Missing structured backtest files.
- Stdout-only fallback parsing.
- No trades or too few trades.
- Missing core metrics.
- Parser warnings and errors.
- High drawdown or negative expectancy.
- Results dominated by one pair.
- Missing pair-level evidence.

## Severity Meaning

- `info`: Informational context only.
- `warning`: Data is usable, but the evidence is weaker or needs caution.
- `error`: Data is missing or incomplete enough to block future decision usability.
- `critical`: Severe parser or evidence failure. Reserved for later use.

## Required Flag Codes

### `no_trades`

No trades were detected in the parsed result.

Severity: `error`

Blocks future decision usability.

### `too_few_trades`

The parsed result has fewer trades than the configured minimum.

Severity: `warning`

Does not block future decision usability by itself.

### `missing_backtest_file`

No structured backtest result file was discovered.

Severity: `error`

Blocks future decision usability.

### `stdout_only_parse`

Only stdout fallback text was available for parsing.

Severity: `warning`

Does not block future decision usability by itself, but indicates lower evidence quality.

### `partial_parse`

One or more major sections are missing, such as metrics, pair results, or trade summary.

Severity: `warning`

Blocks future decision usability because a future decision engine needs complete parsed evidence.

### `negative_expectancy`

Parsed expectancy is negative.

Severity: `warning`

Does not block future decision usability by itself. A future decision engine may use it as negative evidence.

### `high_drawdown`

Parsed drawdown is above the configured threshold.

Severity: `warning`

Does not block future decision usability by itself.

### `single_pair_dependency`

One pair dominates the parsed pair-level result.

Severity: `warning`

Does not block future decision usability by itself.

### `missing_pair_results`

No pair-level results were parsed.

Severity: `warning`

Usually appears with `partial_parse`.

### `missing_profit_factor`

Profit factor is missing from parsed metrics.

Severity: `error`

Blocks future decision usability as a missing core metric.

### `missing_drawdown`

Drawdown is missing from parsed metrics.

Severity: `error`

Blocks future decision usability as a missing core metric.

### `parse_warning`

A parser or loader warning was reported.

Severity: `warning`

Does not block future decision usability by itself.

### `parse_error`

A parser or loader error was reported.

Severity: `error`

Blocks future decision usability.

## Metrics Usability

`is_usable_for_metrics=true` means enough parsed data exists for metrics-oriented display or persistence.

It is true when at least one of these exists:

- `trade_count`
- `net_profit`
- pair-level results

It does not mean the result is good or acceptable.

## Decision Usability

`is_usable_for_decision=true` means enough parsed evidence exists for a future decision engine to inspect.

It does not mean:

- Approved.
- Rejected.
- Exportable.
- Ready for dry-run trading.
- Ready for live trading.

Decision usability is false when:

- No trades were detected.
- A structured backtest file is missing.
- Parser errors exist.
- Core metrics are missing.
- The parse is partial.

Decision usability can still be true for a complete losing result. That means future logic has enough evidence to evaluate it, not that HER accepts it.

## Not Final Strategy Decisions

Quality flags are evidence labels. They intentionally stop before strategy approval, rejection, export, or trading action.

Later HER parts may consume these flags as inputs, but this service only reports parser quality and data sufficiency.
