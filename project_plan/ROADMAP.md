# HER Project Roadmap

---

## Completed Foundation

### Part 01 — Project Setup
- Monorepo structure: `backend/`, `frontend/`, `docs/`, `scripts/`, `data/`, `artifacts/`
- FastAPI backend skeleton with CORS, health endpoint, and lifespan DB init
- Next.js 16 frontend with App Router, Tailwind CSS v4, TypeScript

### Part 02–03 — Database Foundation
- SQLite schema via custom migration engine (`db/migrations.py`)
- All core tables: `runs`, `run_stages`, `strategies`, `strategy_versions`, `artifacts`, `metrics_snapshots`, `decision_results`, `audit_logs`
- `BaseRepository` with UUID gen, ISO timestamps, JSON serialization, secret redaction

### Part 04 — Freqtrade Integration
- `FreqtradeCommandRunner` with command allowlist enforcement
- `FreqtradeConfigGenerator` — always writes `dry_run: true`, no API keys
- `FreqtradeWorkspaceService` — validates directory structure
- `FreqtradeDataService` — check and download historical data
- Safety: `trade` and `webserver` commands permanently blocked

### Part 05 — Backtest Result Parser
- `BacktestResultParser` — discovers, loads, normalizes Freqtrade JSON output
- `ResultQualityService` — quality flags (low trade count, suspicious win rate, short timerange, partial parse)
- Normalized artifact written to `artifacts/<run_id>/normalized_result.json`
- Pair-level performance extraction and trade summary aggregation

### Part 06 — Decision Engine
- `DecisionEngine` with deterministic gates: `minimum_trades`, `expectancy`, `profit_factor`, `drawdown`, `pair_dependency`
- Three policies: `conservative`, `balanced`, `aggressive`
- Classifications: `rejected`, `candidate`, `promising`, `validated`
- `confidence_score` (0–100) as evidence strength indicator
- All gate outcomes stored in `decision_results`

### Part 07 — Baseline Evaluation Pipeline
- 8-stage `BaselineEvaluationService` with full stage recording
- `StrategyReadinessGate` pre-execution check
- Controlled failure handling with user-facing messages and next-action hints
- `POST /api/baseline/evaluate` with `user_confirmed` gate

### Part 08 — Optimization Pipeline (Hyperopt)
- 17-stage `OptimizationPipelineService`
- Hyperopt execution, trial parsing, best trial selection
- Optimized backtest run and comparison against baseline
- `optimization_runs` and `optimization_trials` tables
- `GET /api/optimization/runs/{id}/trials` for trial visualization

### Part 09 — Frontend Dashboard
- Next.js App Router with full sidebar navigation
- Dashboard: system health, run summaries, recent activity
- Baseline detail page: stages, metrics, decision, artifacts
- Optimization detail page: trials table, comparison, best trial
- Real-time polling via `useRunPolling` hook (2s interval)

### Part 10 — Safe Run Controls
- Confirmation dialogs before all execution endpoints
- `DataAvailabilityPreview` component for pre-run data checks
- Audit log integration for all execution events
- Retry history tracking

### Part 11 — Strategy Workspace
- `StrategyWorkspaceService` — import, validate, manage strategies
- Strategy library page with readiness indicators
- Strategy detail page with parameter display
- `StrategySelect` shared component for all run forms

### Part 12 — Readiness Gating
- `StrategyReadinessGate` enforced before every pipeline entry
- Sidecar JSON validation, file existence check, parameter completeness
- Readiness issues displayed in strategy detail and surfaced before form submit

### Part 13 — Validation Evidence (OOS + WFO + Robustness)
- `ValidationExecutionService` — full three-part validation pipeline
- `validation_runs` and `validation_evidence` tables
- OOS validation card, WFO walk-forward card, robustness card
- Redesigned validation detail page with dark theme CSS variables
- `ControlledFailureBanner` on all validation pages

### Part 14 — Frontend UX Redesign
- Grouped sidebar navigation (Discover / Test / Evidence / System)
- Cyan accent design system (`#06b6d4`) with `var(--app-*)` CSS variables
- `WorkflowStepper` — 6-step lifecycle visualizer
- `LiveRunPanel` — real-time run monitoring with pulsing indicator
- `NextActionPanel` — post-run guidance from backend data
- Strategy Journey page (`/journey`) — unified strategy lifecycle view
- All validation cards converted from light-mode to dark theme variables
- Knowledge base and AI onboarding documentation layer

---

## Immediate Next Steps

### Frontend Polish
- **Optimization trial charts** — scatter plot of trial number vs loss score, profit factor, drawdown using real `optimization_trials` API data
- **Baseline comparison view** — side-by-side baseline vs optimized metrics on baseline detail page
- **Strategy Journey polish** — readiness issues list, step-by-step guided instructions per step
- **Smoke test suite** — automated API smoke tests using `scripts/api-smoke.mjs`
- **Error boundary components** — catch and display React rendering errors gracefully

### Backend Enhancements
- **Validation re-run** — allow re-running validation with different OOS timerange or WFO config without creating a new strategy record
- **Metrics history chart data endpoint** — return time-series metrics suitable for charting without client-side transformation
- **Audit log pagination** — `GET /api/audit-logs` needs cursor-based pagination for large datasets
- **Mismatch resolution** — frontend calls `/api/freqtrade/strategies` and `/api/freqtrade/data` (GET) which don't exist; add these endpoints or update frontend clients

---

## Next Product Direction

### AI Strategy Designer
- Local Ollama integration for strategy spec generation from natural language prompt
- `StrategySpec` JSON schema with strict validation
- Deterministic template → `.py` file generator (no free-form code gen)
- AI action audit logging
- User review and edit step before any file is written

### AI Repair Agent
- Post-rejection analysis: pass decision result and blocking failures to Ollama
- Suggest targeted parameter or strategy modifications
- Suggestions displayed as read-only recommendations — never auto-applied
- Each suggestion logged in audit log

### Candidate Promotion and Export
- Export gate: `decision_status = "validated"` + all three evidence types present
- Explicit user confirmation with full gate summary before export
- Export bundle: `.py`, `.json` params, validation report, export manifest with SHA-256
- Export history tracked in database

### Discovery Loop
- Automated strategy variant generation from a base spec
- Batch baseline evaluation across multiple variants
- Comparative leaderboard view (ranked by confidence score)
- Automatic de-duplication of structurally identical strategies

---

## Later Goals

### Monte Carlo Simulation
- Re-sample trade sequences to estimate outcome distribution
- Surface 5th/95th percentile outcomes alongside median
- Flag strategies where downside tail is unacceptable

### Portfolio-Level Validation
- Multi-strategy correlation analysis
- Combined drawdown simulation across a portfolio of candidates
- Portfolio-level decision gate

### Walk-Forward Anchoring
- Anchored WFO (fixed start date, expanding window) as alternative to rolling WFO
- Configurable per validation run

### Dry-Run Preparation (Future Phase)
- Paper trading mode using Freqtrade `--dry-run` with exchange connectivity
- Separate dry-run validation evidence type
- Explicit human gate before any dry-run is enabled
- **Note:** This is a future phase only. No live exchange connectivity in the current system.
