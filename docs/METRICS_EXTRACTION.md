# Metrics Extraction

Part 05 extracts normalized metrics from raw Freqtrade backtest payloads.

Metrics extraction is evidence collection only. It does not approve, reject, export, promote, or classify strategies, and it does not claim that any strategy is profitable.

## Supported Metrics

The extractor targets:

- Net profit.
- Net profit percent.
- Profit factor.
- Maximum drawdown.
- Maximum drawdown percent.
- Sharpe ratio.
- Calmar ratio.
- Win rate.
- Trade count.
- Wins, losses, and draws.
- Average winning trade.
- Average losing trade.
- Expectancy.
- Average duration.
- Best pair.
- Worst pair.

Missing fields are allowed. The extractor returns warnings instead of inventing values.

## Extraction Priority

Extraction priority is:

1. Trade-level data from structured JSON or ZIP-loaded JSON payloads.
2. Summary-level fields from structured JSON or ZIP-loaded JSON payloads.
3. Stdout table fallback when structured data is unavailable.

Trade-level data is preferred because it can calculate expectancy directly from real trade profits.

## Expectancy Formulas

### Trade-Level Formula

When per-trade profit values exist:

`expectancy = sum(trade_profit_values) / trade_count`

This is equivalent to average profit per trade.

### Summary-Level Formula

When trade-level data is unavailable but summary inputs exist:

`expectancy = (win_rate * avg_win) - (loss_rate * abs(avg_loss))`

Where:

- `win_rate = wins / (wins + losses)`
- `loss_rate = losses / (wins + losses)`
- `avg_loss` may be stored as a negative number, but the formula uses its absolute value.

### Missing Inputs

If inputs are insufficient, expectancy is `null` and the extractor adds warnings such as:

- `trade_level_data_missing`
- `trade_profit_values_missing`
- `summary_win_loss_counts_missing`
- `summary_average_win_loss_missing`
- `summary_trade_count_zero`

Expectancy is never fabricated.

## Raw JSON Tolerance

Freqtrade result schemas can vary by version and export mode. The extractor checks multiple possible key names for common fields, including variants such as:

- `profit_factor` and `profitfactor`
- `total_profit`, `profit_total_abs`, and `net_profit`
- `max_drawdown`, `max_drawdown_abs`, and `max_relative_drawdown`
- `win_rate`, `winrate`, and `wins_percent`
- `total_trades`, `trade_count`, and `total_count`

The extractor tries common containers such as:

- Top-level result objects.
- `strategy` dictionaries.
- First strategy result under `strategy`.
- First item under `strategy_comparison`.

Unsupported or unfamiliar shapes return warnings and partial metrics where possible.

## Stdout Fallback Limitations

Stdout parsing is lower quality because stdout is formatted for humans and can change between Freqtrade versions.

The stdout fallback extracts only simple table-like lines such as:

- `Total profit | 42.5`
- `Profit factor | 1.25`
- `Trades | 10`
- `Win rate | 60%`
- `Wins | 6`
- `Losses | 4`
- `Avg win | 10`
- `Avg loss | -5`

Stdout-derived expectancy is marked with `expectancy_source=stdout_fallback`.

Stdout fallback is not final readiness proof when structured JSON or ZIP result data is expected.

## Missing Metric Behavior

The extractor does not crash when fields are missing. It returns:

- `success=false` when no meaningful metrics are extracted.
- Partial `ExtractedBacktestMetrics` when some metrics are available.
- `warnings` for missing fields.
- `errors` for malformed payloads passed through from the raw loader.

Important warning examples:

- `trade_count_missing`
- `profit_factor_missing`
- `payload_has_no_raw_data`
- `no_metrics_extracted`

## Pair-Level Extraction

Part 05 also extracts pair-level result evidence into `ExtractedPairResult`.

The pair parser supports:

- Freqtrade-style `results_per_pair` rows.
- Direct pair result lists such as `pair_results`, `pair_summary`, and `results_by_pair`.
- Pair result dictionaries keyed by pair name.
- Trade lists grouped by `pair`.
- Stdout `BACKTESTING REPORT` pair tables as fallback.

Extracted pair fields include:

- Pair name.
- Trade count.
- Net profit.
- Net profit percent.
- Profit factor.
- Max drawdown.
- Win rate.
- Wins, losses, and draws.
- Expectancy.
- Average duration.
- Raw source row.

Structured JSON is preferred over stdout tables. Stdout pair extraction is marked lower quality and is not final readiness proof.

## Trade Summary Extraction

The trade summary parser extracts:

- Total trades.
- Wins.
- Losses.
- Draws.
- Average duration.
- Best pair.
- Worst pair.
- Raw source summary.

When trade-level rows exist, totals are derived from those rows. When trade-level rows are unavailable, summary fields are used if present.

## Best/Worst Pair Rule

Best and worst pair are selected from parsed pair results:

1. Use highest and lowest `net_profit` when available.
2. If no pair has `net_profit`, fall back to highest and lowest `net_profit_pct`.
3. If neither value exists, both fields remain `null`.

This is evidence only. It does not approve or reject a strategy.

## No-Trade Handling

When zero trades are detected, the parser adds warning `no_trades_detected`.

No-trade output may still include a pair row or trade summary if Freqtrade produced one. The parser preserves that evidence but does not make an acceptance decision.

## Why Metrics Are Not Final Approval

Metrics are evidence, not decisions.

Part 05 does not:

- Decide profitability.
- Approve or reject strategies.
- Export strategies.
- Run Hyperopt.
- Run robustness checks.
- Run walk-forward analysis.
- Start dry-run or live trading.

Later HER parts may use these metrics as inputs to quality gates, but this extractor remains a normalization and calculation layer only.

## Result Quality Flags

Parsed metrics, pair results, and trade summaries can be passed to the result quality service.

The quality service adds flags for cases such as:

- No trades.
- Too few trades.
- Missing structured backtest file.
- Stdout-only fallback parsing.
- Partial parse.
- Negative expectancy.
- High drawdown.
- Single-pair dependency.
- Missing pair results.
- Missing profit factor.
- Missing drawdown.
- Parser warnings and errors.

The quality service also reports:

- `is_usable_for_metrics`
- `is_usable_for_decision`

These values describe parser evidence sufficiency only. They are not strategy approval, rejection, or trading readiness.

See `docs/RESULT_QUALITY_FLAGS.md` for the full flag list and usability rules.
