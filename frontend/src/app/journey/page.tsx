'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LiveRunPanel from '@/components/LiveRunPanel';
import NextActionPanel from '@/components/NextActionPanel';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import WorkflowStepper, { WorkflowStep, StepStatus } from '@/components/WorkflowStepper';
import MetricCard from '@/components/MetricCard';
import {
  StrategySummary,
  BaselineRunDetail,
  OptimizationRunListItem,
  RunListItem,
  getBaselineRunDetail,
  listStrategies,
  listBaselineRuns,
  listOptimizationRuns,
} from '@/lib/api';
import { listValidationRuns } from '@/lib/api/validation';
import type { ValidationRunListItem } from '@/lib/api/types';

interface JourneyState {
  strategies: StrategySummary[];
  baselineRuns: RunListItem[];
  optimizationRuns: OptimizationRunListItem[];
  validationRuns: ValidationRunListItem[];
  errors: string[];
  loadedAt: string | null;
}

interface JourneyNextAction {
  id: string;
  label: string;
  description: string;
  href?: string;
  tone?: 'primary' | 'secondary' | 'warning';
}

const INITIAL: JourneyState = {
  strategies: [],
  baselineRuns: [],
  optimizationRuns: [],
  validationRuns: [],
  errors: [],
  loadedAt: null,
};

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return '-';
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function isActiveStatus(status: string): boolean {
  return ['running', 'pending', 'queued'].includes(status);
}

function isCompleted(status: string | null | undefined): boolean {
  return ['completed', 'passed', 'candidate', 'promising', 'validated'].includes(status ?? '');
}

function isFailed(status: string | null | undefined): boolean {
  return status === 'failed' || status === 'error';
}

function isRejected(status: string | null | undefined): boolean {
  return ['rejected', 'optimization_rejected', 'controlled_failure', 'failed_controlled'].includes(status ?? '');
}

function readinessLabel(readiness: string): string {
  switch (readiness) {
    case 'ready': return 'Ready';
    case 'warning': return 'Warning';
    case 'missing_sidecar': return 'Missing sidecar';
    case 'invalid': return 'Invalid';
    case 'parse_error': return 'Parse error';
    case 'unsafe': return 'Unsafe';
    default: return readiness;
  }
}

function readinessTone(readiness: string): 'success' | 'warning' | 'danger' | 'neutral' {
  if (readiness === 'ready') return 'success';
  if (readiness === 'warning') return 'warning';
  if (['missing_sidecar', 'invalid', 'parse_error', 'unsafe'].includes(readiness)) return 'danger';
  return 'neutral';
}

function readMetric(metrics: Record<string, unknown> | null | undefined, keys: string[]): number | null {
  if (!metrics) return null;
  for (const key of keys) {
    const value = metrics[key];
    if (typeof value === 'number' && Number.isFinite(value)) return value;
    if (typeof value === 'string' && value.trim() !== '') {
      const numeric = Number(value);
      if (Number.isFinite(numeric)) return numeric;
    }
  }
  return null;
}

function fmtMetric(value: number | null, digits = 2, suffix = ''): string | null {
  if (value === null) return null;
  return `${value.toFixed(digits)}${suffix}`;
}

function fmtCount(value: number | null): string | null {
  if (value === null) return null;
  return String(Math.round(value));
}

export default function JourneyPage() {
  const [state, setState] = useState<JourneyState>(INITIAL);
  const [loading, setLoading] = useState(true);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [refreshing, setRefreshing] = useState(false);
  const [baselineDetail, setBaselineDetail] = useState<BaselineRunDetail | null>(null);
  const [baselineDetailError, setBaselineDetailError] = useState<string | null>(null);
  const [baselineDetailRunId, setBaselineDetailRunId] = useState<string | null>(null);

  const load = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) setRefreshing(true);

    const [stratResult, baselineResult, optResult, valResult] = await Promise.all([
      listStrategies({ limit: 200 }),
      listBaselineRuns({ limit: 500 }),
      listOptimizationRuns({ limit: 500 }),
      listValidationRuns({ limit: 500 }),
    ]);

    const errors: string[] = [];
    if (!stratResult.success) errors.push(`Strategies: ${stratResult.error.message}`);
    if (!baselineResult.success) errors.push(`Baseline runs: ${baselineResult.error.message}`);
    if (!optResult.success) errors.push(`Optimization runs: ${optResult.error.message}`);
    if (!valResult.success) errors.push(`Validation runs: ${valResult.error.message}`);

    const strategies = stratResult.success ? stratResult.data : [];
    const baselineRuns = baselineResult.success ? baselineResult.data : [];
    const optimizationRuns = optResult.success ? optResult.data : [];
    const validationRuns = valResult.success ? valResult.data : [];

    setState({ strategies, baselineRuns, optimizationRuns, validationRuns, errors, loadedAt: new Date().toISOString() });
    setLoading(false);
    if (markRefreshing) setRefreshing(false);

    if (strategies.length > 0 && !selectedStrategy) {
      setSelectedStrategy(strategies[0].strategy_name);
    }
  }, [selectedStrategy]);

  useEffect(() => {
    const t = window.setTimeout(() => { void load(false); }, 0);
    return () => window.clearTimeout(t);
  }, [load]);

  const strategy = useMemo(
    () => state.strategies.find((s) => s.strategy_name === selectedStrategy) ?? null,
    [state.strategies, selectedStrategy],
  );

  const strategyBaselines = useMemo(
    () => state.baselineRuns.filter(
      (r) => r.strategy_id === selectedStrategy || r.name?.includes(selectedStrategy),
    ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [state.baselineRuns, selectedStrategy],
  );

  const strategyOptimizations = useMemo(
    () => state.optimizationRuns.filter(
      (r) => r.strategy_name === selectedStrategy,
    ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [state.optimizationRuns, selectedStrategy],
  );

  const strategyValidations = useMemo(
    () => state.validationRuns.filter(
      (r) => r.strategy_name === selectedStrategy,
    ).sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
    [state.validationRuns, selectedStrategy],
  );

  const latestBaseline = strategyBaselines[0] ?? null;
  const latestOptimization = strategyOptimizations[0] ?? null;
  const latestValidation = strategyValidations[0] ?? null;

  useEffect(() => {
    let cancelled = false;

    async function loadBaselineDetail(runId: string) {
      const result = await getBaselineRunDetail(runId);
      if (cancelled) return;
      setBaselineDetailRunId(runId);
      if (result.success) {
        setBaselineDetail(result.data);
        setBaselineDetailError(null);
      } else {
        setBaselineDetail(null);
        setBaselineDetailError(result.error.message);
      }
    }

    if (latestBaseline?.id) {
      void loadBaselineDetail(latestBaseline.id);
    }

    return () => {
      cancelled = true;
    };
  }, [latestBaseline?.id]);

  const activeBaselineRun = strategyBaselines.find((r) => isActiveStatus(r.status)) ?? null;
  const activeOptimizationRun = strategyOptimizations.find((r) => isActiveStatus(r.status)) ?? null;

  // Action gating
  const canRunBaseline = useMemo(() => {
    if (!strategy) return false;
    if (activeBaselineRun || activeOptimizationRun) return false;
    return strategy.readiness === 'ready' || strategy.readiness === 'warning';
  }, [strategy, activeBaselineRun, activeOptimizationRun]);

  const canRunOptimization = useMemo(() => {
    if (!latestBaseline) return false;
    if (activeBaselineRun || activeOptimizationRun) return false;
    const cls = latestBaseline.classification;
    return isCompleted(latestBaseline.status) && !isRejected(cls);
  }, [latestBaseline, activeBaselineRun, activeOptimizationRun]);

  const canRunValidation = useMemo(() => {
    if (activeBaselineRun || activeOptimizationRun) return false;
    const baselineOk = latestBaseline && isCompleted(latestBaseline.status) && !isRejected(latestBaseline.classification);
    const optOk = latestOptimization && isCompleted(latestOptimization.status) && latestOptimization.result_status !== 'optimization_rejected';
    return Boolean(baselineOk || optOk);
  }, [latestBaseline, latestOptimization, activeBaselineRun, activeOptimizationRun]);

  const steps: WorkflowStep[] = useMemo(() => {
    if (!selectedStrategy) return [];

    const readinessStatus: StepStatus = !strategy
      ? 'not_started'
      : strategy.readiness === 'ready'
      ? 'passed'
      : strategy.readiness === 'warning'
      ? 'blocked'
      : 'failed';

    let baselineStatus: StepStatus = 'not_started';
    let baselineMsg = 'No baseline run found for this strategy.';
    let baselineTs: string | null = null;
    let baselineHref: string | undefined;
    if (latestBaseline) {
      baselineTs = latestBaseline.created_at;
      baselineHref = `/baseline/${latestBaseline.id}`;
      if (isActiveStatus(latestBaseline.status)) {
        baselineStatus = 'running';
        baselineMsg = 'Baseline run is active.';
      } else if (isCompleted(latestBaseline.status)) {
        const cls = latestBaseline.classification;
        if (isRejected(cls)) {
          baselineStatus = 'failed';
          baselineMsg = `Rejected - ${cls ?? 'no classification'}.`;
        } else {
          baselineStatus = 'passed';
          baselineMsg = cls ? `Classification: ${cls}` : 'Baseline completed.';
        }
      } else if (isFailed(latestBaseline.status)) {
        baselineStatus = 'failed';
        baselineMsg = `Pipeline failed: ${latestBaseline.status}`;
      } else {
        baselineStatus = 'blocked';
        baselineMsg = `Status: ${latestBaseline.status}`;
      }
    }

    let optStatus: StepStatus = 'not_started';
    let optMsg = 'No optimization run found.';
    let optTs: string | null = null;
    let optHref: string | undefined;
    if (latestOptimization) {
      optTs = latestOptimization.created_at;
      optHref = `/optimization/${latestOptimization.id}`;
      if (isActiveStatus(latestOptimization.status)) {
        optStatus = 'running';
        optMsg = `${latestOptimization.epochs_completed ?? 0} / ${latestOptimization.epochs_requested ?? '?'} epochs`;
      } else if (isCompleted(latestOptimization.status)) {
        const rs = latestOptimization.result_status;
        if (rs === 'optimization_rejected') {
          optStatus = 'failed';
          optMsg = 'Optimization rejected - result did not improve baseline.';
        } else {
          optStatus = 'passed';
          optMsg = rs ? `Result: ${rs}` : 'Optimization completed.';
        }
      } else if (isFailed(latestOptimization.status)) {
        optStatus = 'failed';
        optMsg = `Pipeline failed: ${latestOptimization.status}`;
      } else {
        optStatus = 'blocked';
        optMsg = `Status: ${latestOptimization.status}`;
      }
    }

    let valStatus: StepStatus = 'not_started';
    let valMsg = 'No validation run found.';
    let valTs: string | null = null;
    let valHref: string | undefined;
    if (latestValidation) {
      valTs = latestValidation.created_at;
      valHref = `/validation/${latestValidation.validation_run_id}`;
      if (isActiveStatus(latestValidation.status)) {
        valStatus = 'running';
        valMsg = 'Validation run is active.';
      } else if (isCompleted(latestValidation.status)) {
        const ds = latestValidation.decision_status ?? latestValidation.summary?.decision_status;
        valStatus = 'passed';
        valMsg = ds ? `Decision: ${String(ds)}` : 'Validation completed.';
      } else if (isFailed(latestValidation.status)) {
        valStatus = 'failed';
        valMsg = `Validation failed: ${latestValidation.status}`;
      } else {
        valStatus = 'blocked';
        valMsg = `Status: ${latestValidation.status}`;
      }
    }

    let decisionStatus: StepStatus = 'not_started';
    let decisionMsg = 'No candidate decision recorded yet.';
    if (latestValidation && valStatus === 'passed') {
      const ds = String(latestValidation.decision_status ?? latestValidation.summary?.decision_status ?? '');
      if (ds.includes('reject') || ds.includes('fail')) {
        decisionStatus = 'failed';
        decisionMsg = `Decision: ${ds}. Strategy is not a validated candidate.`;
      } else if (ds) {
        decisionStatus = 'passed';
        decisionMsg = `Decision recorded: ${ds}. Evidence only - not a live-trading authorization.`;
      }
    }

    return [
      {
        id: 'strategy',
        label: 'Strategy selected',
        status: selectedStrategy ? 'passed' : 'not_started',
        message: selectedStrategy ? `${selectedStrategy} is the active strategy.` : 'Select a strategy to begin.',
      },
      {
        id: 'readiness',
        label: 'Readiness checked',
        status: readinessStatus,
        message: strategy
          ? `${readinessLabel(strategy.readiness)}. ${strategy.issues.length} issue${strategy.issues.length !== 1 ? 's' : ''}, ${strategy.warnings.length} warning${strategy.warnings.length !== 1 ? 's' : ''}.`
          : 'Readiness not available.',
        href: selectedStrategy ? `/strategies/${encodeURIComponent(selectedStrategy)}` : undefined,
      },
      {
        id: 'baseline',
        label: 'Baseline completed',
        status: baselineStatus,
        message: baselineMsg,
        timestamp: baselineTs,
        href: baselineHref,
      },
      {
        id: 'optimization',
        label: 'Optimization completed',
        status: optStatus,
        message: optMsg,
        timestamp: optTs,
        href: optHref,
      },
      {
        id: 'validation',
        label: 'Validation completed',
        status: valStatus,
        message: valMsg,
        timestamp: valTs,
        href: valHref,
      },
      {
        id: 'decision',
        label: 'Candidate decision',
        status: decisionStatus,
        message: decisionMsg,
      },
    ];
  }, [selectedStrategy, strategy, latestBaseline, latestOptimization, latestValidation]);

  const nextActions = useMemo<JourneyNextAction[]>(() => {
    if (!selectedStrategy || !strategy) {
      return [{
        id: 'select-strategy',
        label: 'Open Strategy Workspace',
        description: 'Select or import a strategy before starting the workflow.',
        href: '/strategies',
        tone: 'primary',
      }];
    }
    const actions: JourneyNextAction[] = [];

    if (strategy.readiness !== 'ready') {
      return [{
        id: 'fix-strategy',
        label: 'Fix readiness issues',
        description: 'Review readiness issues before running.',
        href: `/strategies/${encodeURIComponent(selectedStrategy)}`,
        tone: 'warning',
      }];
    }

    if (!latestBaseline) {
      return [{
        id: 'run-baseline',
        label: 'Run baseline',
        description: 'Open the baseline form. Confirmation is required before execution.',
        href: '/baseline',
        tone: 'primary',
      }];
    }

    if (canRunOptimization && !latestOptimization) {
      return [{
        id: 'run-optimization',
        label: 'Run optimization',
        description: 'Open the optimization form. Confirmation is required before execution.',
        href: '/optimization',
        tone: 'primary',
      }];
    }

    if (canRunValidation && !latestValidation) {
      return [{
        id: 'run-validation',
        label: 'Run validation',
        description: 'Open the validation form. Confirmation is required before execution.',
        href: '/validation',
        tone: 'primary',
      }];
    }

    if (latestValidation) {
      actions.push({
        id: 'review-validation',
        label: 'Review validation evidence',
        description: 'Review OOS, WFO, and robustness evidence.',
        href: `/validation/${latestValidation.validation_run_id}`,
        tone: 'primary',
      });
    } else if (latestOptimization) {
      actions.push({
        id: 'review-optimization',
        label: 'Review best trial',
        description: 'Inspect optimization trials and baseline comparison.',
        href: `/optimization/${latestOptimization.id}`,
        tone: 'primary',
      });
    } else {
      actions.push({
        id: 'review-baseline',
        label: 'Review baseline',
        description: 'Inspect baseline metrics, decision, and pair results.',
        href: `/baseline/${latestBaseline.id}`,
        tone: 'primary',
      });
    }
    return actions;
  }, [selectedStrategy, strategy, latestBaseline, latestOptimization, latestValidation, canRunOptimization, canRunValidation]);

  const hasActiveRun = Boolean(activeBaselineRun || activeOptimizationRun);

  // Derive pairs/timeframe from latest run data
  const displayPairs = latestOptimization?.pairs ?? null;
  const displayTimeframe = strategy?.params_summary?.timeframe ?? latestOptimization?.timeframe ?? null;
  const latestDecision = latestValidation?.decision_status ?? latestValidation?.summary?.decision_status ?? null;
  const selectedBaselineDetail =
    baselineDetailRunId === latestBaseline?.id ? baselineDetail : null;
  const selectedBaselineDetailError =
    baselineDetailRunId === latestBaseline?.id ? baselineDetailError : null;
  const latestMetrics = selectedBaselineDetail?.metrics as Record<string, unknown> | null | undefined;
  const latestConfidence =
    typeof selectedBaselineDetail?.confidence_score === 'number'
      ? selectedBaselineDetail.confidence_score
      : readMetric(selectedBaselineDetail?.decision as Record<string, unknown> | null | undefined, ['confidence_score']);
  const profitFactor = readMetric(latestMetrics, ['profit_factor', 'profitFactor']);
  const expectancy = readMetric(latestMetrics, ['expectancy']);
  const maxDrawdown = readMetric(latestMetrics, ['max_drawdown', 'maxDrawdown']);
  const tradeCount = readMetric(latestMetrics, ['trade_count', 'tradeCount', 'total_trades']);

  return (
    <AppShell
      pageTitle="Strategy Journey"
      onRefresh={() => { void load(true); }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Strategy Journey"
          description="Select a strategy and follow its full discovery lifecycle: readiness, baseline, optimization, and validation."
          actions={
            state.loadedAt ? (
              <span className="text-xs text-[var(--app-text-subtle)]">Updated {fmtTs(state.loadedAt)}</span>
            ) : null
          }
        />

        {state.errors.length > 0 && (
          <ErrorBanner title="Some journey data could not be loaded">
            <ul className="list-inside list-disc space-y-1">
              {state.errors.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </ErrorBanner>
        )}

        <section className="overflow-hidden rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-glass)] shadow-[var(--app-shadow-card)]">
          <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_360px]">
            <div className="p-5 lg:p-6">
              <div className="flex flex-col gap-4 xl:flex-row xl:items-start xl:justify-between">
                <div className="min-w-0">
                  <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">
                    Strategy overview
                  </p>
                  <h2 className="mt-2 truncate text-2xl font-semibold text-[var(--app-text)]">
                    {selectedStrategy || 'Select a strategy from Strategy Workspace to begin.'}
                  </h2>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-[var(--app-text-muted)]">
                    Backend records define every stage here. Missing metrics remain unavailable until a real run produces evidence.
                  </p>
                </div>

                <div className="flex min-w-0 flex-col gap-2 sm:flex-row xl:flex-col">
                  {loading ? (
                    <div className="h-10 w-64 animate-pulse rounded-[var(--app-radius)] bg-[var(--app-surface)]" />
                  ) : state.strategies.length === 0 ? (
                    <span className="text-sm text-[var(--app-text-muted)]">No strategies found.</span>
                  ) : (
                    <label className="min-w-0">
                      <span className="sr-only">Strategy</span>
                      <select
                        id="strategy-select"
                        value={selectedStrategy}
                        onChange={(e) => setSelectedStrategy(e.target.value)}
                        className="h-10 w-full min-w-64 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-3 text-sm font-medium text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
                      >
                        {state.strategies.map((s) => (
                          <option key={s.strategy_name} value={s.strategy_name}>
                            {s.strategy_name}
                          </option>
                        ))}
                      </select>
                    </label>
                  )}
                  {selectedStrategy && (
                    <a
                      href={`/strategies/${encodeURIComponent(selectedStrategy)}`}
                      className="inline-flex h-10 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-3 text-xs font-medium text-[var(--app-text-muted)] transition-colors hover:border-[var(--app-border-strong)] hover:text-[var(--app-text)]"
                    >
                      Open workspace
                    </a>
                  )}
                </div>
              </div>

              {selectedStrategy && strategy && (
                <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
                  <OverviewTile
                    label="Readiness"
                    value={readinessLabel(strategy.readiness)}
                    status={strategy.readiness}
                    tone={readinessTone(strategy.readiness)}
                  />
                  <OverviewTile
                    label="Sidecar JSON"
                    value={strategy.has_sidecar ? 'Present' : 'Missing'}
                    status={strategy.has_sidecar ? 'configured' : 'missing'}
                    tone={strategy.has_sidecar ? 'success' : 'warning'}
                  />
                  <OverviewTile
                    label="Latest baseline"
                    value={latestBaseline?.classification ?? latestBaseline?.status ?? 'Not started'}
                    status={latestBaseline?.classification ?? latestBaseline?.status ?? 'not_started'}
                  />
                  <OverviewTile
                    label="Latest decision"
                    value={latestDecision ? String(latestDecision) : 'Not available yet'}
                    status={latestDecision ? String(latestDecision) : 'not_started'}
                  />
                </div>
              )}

              {selectedStrategy && !loading && (
                <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-[var(--app-border)] pt-4">
                  <p className="mr-1 text-xs font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">Run forms</p>
                  <ActionButton
                    label="Start Baseline"
                    href="/baseline"
                    enabled={canRunBaseline}
                    disabledReason={
                      !strategy
                        ? 'Select a strategy first.'
                        : activeBaselineRun || activeOptimizationRun
                        ? 'A run is already active.'
                        : !canRunBaseline
                        ? `Strategy readiness is ${strategy?.readiness ?? 'unknown'}. Fix issues before running.`
                        : undefined
                    }
                  />
                  <ActionButton
                    label="Start Optimization"
                    href="/optimization"
                    enabled={canRunOptimization}
                    disabledReason={
                      activeBaselineRun || activeOptimizationRun
                        ? 'A run is already active.'
                        : !latestBaseline
                        ? 'Run a baseline first.'
                        : !canRunOptimization
                        ? 'Latest baseline was rejected or is incomplete.'
                        : undefined
                    }
                  />
                  <ActionButton
                    label="Start Validation"
                    href="/validation"
                    enabled={canRunValidation}
                    disabledReason={
                      activeBaselineRun || activeOptimizationRun
                        ? 'A run is already active.'
                        : !canRunValidation
                        ? 'A completed baseline or optimization run is required.'
                        : undefined
                    }
                  />
                  <span className="text-[11px] text-[var(--app-text-subtle)]">
                    Confirmation is required before execution.
                  </span>
                </div>
              )}
            </div>

            <div className="border-t border-[var(--app-border)] bg-[var(--app-surface-muted)] p-5 lg:border-l lg:border-t-0 lg:p-6">
              <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">Current context</p>
              <div className="mt-4 space-y-3">
                <ContextRow label="Timeframe" value={displayTimeframe ?? 'Not recorded'} />
                <ContextRow
                  label="Pairs"
                  value={
                    displayPairs && displayPairs.length > 0
                      ? displayPairs.length === 1
                        ? displayPairs[0]
                        : `${displayPairs[0]} +${displayPairs.length - 1} more`
                      : 'Not recorded'
                  }
                />
                <ContextRow
                  label="Latest run"
                  value={
                    latestValidation
                      ? `Validation - ${latestValidation.status}`
                      : latestOptimization
                      ? `Optimization - ${latestOptimization.result_status ?? latestOptimization.status}`
                      : latestBaseline
                      ? `Baseline - ${latestBaseline.classification ?? latestBaseline.status}`
                      : 'Not started'
                  }
                />
                <ContextRow
                  label="Issues"
                  value={strategy ? `${strategy.issues.length} issue${strategy.issues.length !== 1 ? 's' : ''}` : 'Not available'}
                  danger={Boolean(strategy && strategy.issues.length > 0)}
                />
              </div>
            </div>
          </div>
        </section>

        {selectedStrategy && !loading && (
          <SectionCard title="Live workflow panel" description="Active pipeline status is shown only when a real backend run is pending or running.">
            {hasActiveRun ? (
              <div className="space-y-3">
                {activeBaselineRun && (
                  <LiveRunPanel runType="baseline" runId={activeBaselineRun.id} label="Baseline run (active)" />
                )}
                {activeOptimizationRun && (
                  <LiveRunPanel runType="optimization" runId={activeOptimizationRun.id} label="Optimization run (active)" />
                )}
              </div>
            ) : (
              <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
                <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <p className="text-sm font-semibold text-[var(--app-text)]">No active run.</p>
                    <p className="mt-1 text-xs leading-5 text-[var(--app-text-muted)]">
                      Stage progress will appear here after a confirmed baseline or optimization run starts.
                    </p>
                  </div>
                  <StatusBadge status="not_started" label="Idle" tone="neutral" dot />
                </div>
              </div>
            )}
          </SectionCard>
        )}

        {/* Main content */}
        {selectedStrategy && !loading && (
          <div className="grid gap-6 xl:grid-cols-3">
            {/* Journey timeline — 2/3 */}
            <div className="xl:col-span-2">
              <SectionCard
                title="Journey timeline"
                description="Status of each lifecycle stage from real backend data. Not started means no record was found."
              >
                {steps.length === 0 ? (
                  <EmptyState title="No steps" description="Select a strategy to see its journey." />
                ) : (
                  <WorkflowStepper steps={steps} orientation="vertical" />
                )}
              </SectionCard>
            </div>

            {/* Sidebar — 1/3 */}
            <div className="space-y-4">
              <SectionCard title="Evidence summary" description="Compact metrics from real baseline and validation responses.">
                <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-1">
                  <MetricCard label="Profit factor" value={fmtMetric(profitFactor)} helper="Latest baseline detail metric." />
                  <MetricCard label="Expectancy" value={fmtMetric(expectancy, 4)} helper="Latest baseline detail metric." />
                  <MetricCard label="Max drawdown" value={fmtMetric(maxDrawdown, 2)} helper="Latest baseline detail metric." />
                  <MetricCard label="Trade count" value={fmtCount(tradeCount)} helper="Latest baseline detail metric." />
                  <MetricCard label="Validation status" value={latestValidation?.decision_status ?? latestValidation?.status ?? null} helper="Latest validation record." />
                  <MetricCard label="Evidence strength" value={fmtMetric(latestConfidence, 0, '/100')} helper="Decision confidence if returned by backend." />
                </div>
                {selectedBaselineDetailError && (
                  <p className="mt-3 text-xs leading-5 text-[var(--app-warning)]">
                    Latest baseline detail unavailable: {selectedBaselineDetailError}
                  </p>
                )}
                <div className="mt-4 space-y-2 border-t border-[var(--app-border)] pt-4">
                  <EvidenceRow
                    label="Baseline runs"
                    count={strategyBaselines.length}
                    latest={latestBaseline ? {
                      status: latestBaseline.classification ?? latestBaseline.status,
                      href: `/baseline/${latestBaseline.id}`,
                      ts: latestBaseline.created_at,
                    } : null}
                  />
                  <EvidenceRow
                    label="Optimization runs"
                    count={strategyOptimizations.length}
                    latest={latestOptimization ? {
                      status: latestOptimization.result_status ?? latestOptimization.status,
                      href: `/optimization/${latestOptimization.id}`,
                      ts: latestOptimization.created_at,
                    } : null}
                  />
                  <EvidenceRow
                    label="Validation runs"
                    count={strategyValidations.length}
                    latest={latestValidation ? {
                      status: latestValidation.decision_status ?? latestValidation.status,
                      href: `/validation/${latestValidation.validation_run_id}`,
                      ts: latestValidation.created_at,
                    } : null}
                  />
                </div>
              </SectionCard>

              <NextActionPanel
                title="Next safe action"
                message="One workflow step is shown at a time. Run forms still require confirmation before execution."
                actions={nextActions}
              />
            </div>
          </div>
        )}

        {/* Latest baseline snapshot */}
        {selectedStrategy && !loading && latestBaseline && (
          <SectionCard
            title="Latest baseline snapshot"
            description={`Most recent baseline run: ${latestBaseline.id}. Open the detail page for full evidence.`}
          >
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard
                label="Classification"
                value={latestBaseline.classification ?? latestBaseline.status ?? '-'}
              />
              <MetricCard
                label="Mode"
                value={latestBaseline.mode ?? '-'}
              />
              <MetricCard
                label="Started"
                value={fmtTs(latestBaseline.started_at ?? latestBaseline.created_at)}
              />
              <MetricCard
                label="Completed"
                value={fmtTs(latestBaseline.completed_at ?? latestBaseline.updated_at)}
              />
            </div>
            <div className="mt-4">
              <a
                href={`/baseline/${latestBaseline.id}`}
                className="inline-flex h-9 items-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3.5 text-sm text-[var(--app-text-muted)] transition-colors hover:text-[var(--app-text)]"
              >
                Open full baseline detail
              </a>
            </div>
          </SectionCard>
        )}

        {/* Strategy issues */}
        {selectedStrategy && !loading && strategy && strategy.issues.length > 0 && (
          <SectionCard
            title="Strategy issues"
            description="Readiness issues detected by the backend. Resolve critical and error issues before running."
          >
            <div className="space-y-2">
              {strategy.issues.map((issue, idx) => {
                const tone =
                  issue.severity === 'critical' || issue.severity === 'error'
                    ? 'danger'
                    : issue.severity === 'warning'
                    ? 'warning'
                    : 'neutral';
                return (
                  <div key={idx} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={issue.severity} tone={tone as 'danger' | 'warning' | 'neutral'} />
                      <span className="font-mono text-xs text-[var(--app-text-muted)]">{issue.code}</span>
                    </div>
                    <p className="mt-2 text-sm leading-6 text-[var(--app-text)]">{issue.message}</p>
                  </div>
                );
              })}
            </div>
          </SectionCard>
        )}

        {/* Empty state when no strategy selected */}
        {!loading && !selectedStrategy && state.strategies.length === 0 && (
          <EmptyState
            title="No strategies found"
            description="Import strategies into the backend to see them here."
          />
        )}
      </div>
    </AppShell>
  );
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function OverviewTile({
  label,
  value,
  status,
  tone,
}: {
  label: string;
  value: string;
  status: string;
  tone?: 'success' | 'warning' | 'danger' | 'neutral' | 'info' | 'optimization';
}) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">{label}</p>
      <div className="mt-2 flex flex-col items-start gap-2">
        <p className="text-sm font-semibold leading-5 text-[var(--app-text)]">{value}</p>
        <StatusBadge status={status} tone={tone} dot />
      </div>
    </div>
  );
}

function ContextRow({ label, value, danger = false }: { label: string; value: string; danger?: boolean }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-3 py-2">
      <span className="text-xs text-[var(--app-text-subtle)]">{label}</span>
      <span className={['min-w-0 truncate text-right text-xs font-medium', danger ? 'text-[var(--app-danger)]' : 'text-[var(--app-text-muted)]'].join(' ')}>
        {value}
      </span>
    </div>
  );
}

function ActionButton({
  label,
  href,
  enabled,
  disabledReason,
}: {
  label: string;
  href: string;
  enabled: boolean;
  disabledReason?: string;
}) {
  if (enabled) {
    return (
      <a
        href={href}
        className="inline-flex h-9 items-center rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] px-4 text-sm font-medium text-[var(--app-accent)] transition-colors hover:bg-[var(--app-accent)] hover:text-[var(--app-accent-text)]"
      >
        {label}
      </a>
    );
  }

  return (
    <span
      title={disabledReason}
      className="inline-flex h-9 cursor-not-allowed items-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-4 text-sm font-medium text-[var(--app-text-subtle)] opacity-50"
    >
      {label}
    </span>
  );
}

function EvidenceRow({
  label,
  count,
  latest,
}: {
  label: string;
  count: number;
  latest: { status: string | null; href: string; ts: string } | null;
}) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
      <div className="min-w-0">
        <p className="text-xs font-semibold text-[var(--app-text)]">{label}</p>
        {latest ? (
          <p className="mt-0.5 text-[11px] text-[var(--app-text-subtle)]">
            {fmtTs(latest.ts)}
          </p>
        ) : (
          <p className="mt-0.5 text-[11px] text-[var(--app-text-subtle)]">Not started</p>
        )}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        <span className="font-mono text-xs text-[var(--app-text-muted)]">{count}</span>
        {latest?.status && (
          <StatusBadge status={latest.status} />
        )}
        {latest && (
          <a
            href={latest.href}
            className="rounded border border-[var(--app-border)] bg-[var(--app-surface)] px-2 py-0.5 text-[11px] text-[var(--app-text-muted)] transition-colors hover:text-[var(--app-accent)]"
          >
            View
          </a>
        )}
      </div>
    </div>
  );
}
