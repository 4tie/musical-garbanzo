# HER Project Charter

## What HER Is

HER (AutoQuant Strategy Lab) is a local-only, single-user trading strategy validation engine. It is built to help one private researcher rigorously test, evaluate, and classify Freqtrade-compatible trading strategies using historical backtest evidence.

HER is:
- A validation pipeline (baseline → optimization → validation → decision)
- An evidence recorder (every result stored, artifacts registered, audit log maintained)
- A deterministic classifier (gates applied to metrics; classification based on evidence, not opinion)
- A research dashboard (read-only inspection of all evidence and decisions)

HER is not:
- A trading bot (no live orders, no exchange connectivity)
- A signal service (no real-time market data)
- A profit guarantee (no strategy is guaranteed to perform in live markets)
- An AI trading system (Ollama/LLM provides suggestions only; never executes)

---

## Why HER Exists

The problem: backtesting a trading strategy is easy; knowing whether that backtest result is meaningful is hard. A single backtest on a favorable period proves nothing. HER forces every strategy through multiple independent validation stages and applies objective, policy-defined gates before any positive classification is assigned.

The solution HER provides:
1. **Reproducibility** — every run is recorded with all parameters, outputs, artifacts, and decisions.
2. **Multi-stage evidence** — baseline, optimization, OOS, WFO, and robustness evidence are collected separately.
3. **Deterministic gates** — no human opinion decides the classification; the decision engine applies fixed policy thresholds.
4. **Traceability** — every action is logged in the audit log; every artifact is registered with SHA-256.
5. **Safety** — no live trading is possible from within HER at any stage.

---

## Corrected Product Definition

HER is a **local strategy validation lab**, not an automated trading system.

Common misunderstanding → Correct understanding:
- "HER finds profitable strategies" → HER classifies evidence quality; it does not predict future profitability.
- "`validated` means the strategy works" → `validated` means the strategy survived all configured validation checks on historical data.
- "HER runs trades" → HER runs Freqtrade in backtest/hyperopt mode only; no live orders are ever placed.
- "The AI picks the strategy" → The deterministic decision engine classifies; the AI layer only explains and suggests.

---

## Core Workflow

```
Strategy (discovered or designed)
    ↓
Readiness Gate (sidecar JSON, parameters, config check)
    ↓
Baseline Evaluation (Freqtrade backtest → parse → decision engine)
    ↓
Optimization (Freqtrade hyperopt → trial selection → comparison vs baseline)
    ↓
Validation (OOS backtest + WFO windows + robustness sweep)
    ↓
Final Decision (all evidence evaluated → classification assigned)
    ↓
Candidate Record (artifacts, reports, decision stored — no auto-export)
```

Each stage is independently recorded. Failure at any stage produces a `failed_controlled` status with a reason and a next-action suggestion, not a silent error.

---

## Classification Levels

| Classification | Meaning |
|---|---|
| `rejected` | Failed one or more blocking gates (e.g., negative expectancy, insufficient trades). Not a system error. |
| `candidate` | Meets minimum thresholds; worth further investigation but not yet reliable. |
| `promising` | Meets higher performance tiers across multiple metrics; warrants optimization. |
| `validated` | Passed baseline gates AND survived OOS, WFO, and robustness checks. Historical evidence is strong. Does not mean future profit is guaranteed. |
| `failed_controlled` | A known, expected failure type (data missing, config invalid, etc.). Actionable next step is provided. |
| `elite` | Reserved for strategies that pass validation at the strictest risk profile across multiple timeframes (future use). |

---

## Terminology Quick Reference

See `docs/GLOSSARY.md` for full definitions. Key terms:

- **Strategy** — A Freqtrade Python strategy file with a matching sidecar JSON spec.
- **Baseline** — The first full backtest evaluation of a strategy against its default parameters.
- **Optimization run** — A Hyperopt session exploring the parameter space to find better settings.
- **Validation run** — Post-optimization evidence collection: OOS, WFO, and robustness.
- **Decision engine** — The deterministic gate system that assigns classifications.
- **Artifact** — A file produced by a run (JSON results, normalized output, logs, reports).
- **Readiness gate** — A pre-execution check ensuring the strategy is properly configured before any run is launched.

---

## Project Boundaries

In scope:
- Local Freqtrade backtesting and hyperopt (CLI execution only)
- Evidence recording and classification
- Frontend inspection dashboard
- Local Ollama AI for explanation and strategy drafting suggestions

Out of scope (permanently, unless charter is revised):
- Live exchange connectivity
- Real-money order placement
- Cloud deployment or multi-user access
- Automated strategy promotion or export without human review
- Real-time market data ingestion
