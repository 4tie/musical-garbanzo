'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LiveRunPanel from '@/components/LiveRunPanel';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import NextActionPanel from '@/components/NextActionPanel';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import WorkflowStepper, { WorkflowStep, StepStatus } from '@/components/WorkflowStepper';
import MetricCard from '@/components/MetricCard';
import {
  StrategySummary,
  OptimizationRunListItem,
  RunListItem,
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

const INITIAL: JourneyState = {
  strategies: [],
  baselineRuns: [],
  optimizationRuns: [],
  validationRuns: [],
  errors: [],
  loadedAt: null,
};

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return '';
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
  return status === 'completed' || status === 'passed';
}

function isFailed(status: string | null | undefined): boolean {
  return status === 'failed' || status === 'error';
}

function isRejected(status: string | null | undefined): boolean {
  return ['rejected', 'optimization_rejected', 'controlled_failure'].includes(status ?? '');
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

export default function JourneyPage() {
  const [state, setState] = useState<JourneyState>(INITIAL);
  const [loading, setLoading] = useState(true);
  const [selectedStrategy, setSelectedStrategy] = useState<string>('');
  const [refreshing, setRefreshing] = useState(false);

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

  const activeBaselineRun = strategyBaselines.find((r) => isActiveStatus(r.status)) ?? null;
  const activeOptimizationRun = strategyOptimizations.find((r) => isActiveStatus(r.status)) ?? null;

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
          baselineMsg = `Rejected (${cls ?? 'no classification'}).`;
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
          optMsg = 'Optimization rejected. Optimized result did not improve baseline.';
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
        decisionMsg = `Decision recorded: ${ds}. Evidence only — not an approval or live-trading authorization.`;
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
          ? `Readiness: ${readinessLabel(strategy.readiness)}. ${strategy.issues.length} issue${strategy.issues.length !== 1 ? 's' : ''}, ${strategy.warnings.length} warning${strategy.warnings.length !== 1 ? 's' : ''}.`
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

  const nextActions = useMemo(() => {
    if (!selectedStrategy || !strategy) return [];
    const actions: Array<{ id: string; label: string; description: string; href?: string; tone?: 'primary' | 'secondary' | 'warning' }> = [];

    if (strategy.readiness !== 'ready') {
      actions.push({
        id: 'fix-strategy',
        label: 'Open Strategy',
        description: 'Review strategy readiness issues before running.',
        href: `/strategies/${encodeURIComponent(selectedStrategy)}`,
        tone: 'warning',
      });
    }

    if (latestBaseline) {
      actions.push({
        id: 'view-baseline',
        label: 'View Baseline',
        description: 'Inspect baseline metrics, decision, and pair results.',
        href: `/baseline/${latestBaseline.id}`,
        tone: 'secondary',
      });
    }

    if (latestOptimization) {
      actions.push({
        id: 'view-opt',
        label: 'View Optimization',
        description: 'Inspect optimization trials and baseline comparison.',
        href: `/optimization/${latestOptimization.id}`,
        tone: 'secondary',
      });
    }

    if (latestValidation) {
      actions.push({
        id: 'view-val',
        label: 'View Validation',
        description: 'Review OOS, WFO, and robustness evidence.',
        href: `/validation/${latestValidation.validation_run_id}`,
        tone: 'secondary',
      });
    }

    return actions;
  }, [selectedStrategy, strategy, latestBaseline, latestOptimization, latestValidation]);

  const hasActiveRun = Boolean(activeBaselineRun || activeOptimizationRun);

  const baselineMetrics = useMemo(() => {
    if (!latestBaseline) return null;
    return latestBaseline;
  }, [latestBaseline]);

  return (
    <AppShell
      pageTitle="Strategy Journey"
      onRefresh={() => { void load(true); }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Strategy Journey"
          description="Select a strategy and see its full discovery lifecycle — from readiness check through baseline, optimization, and validation evidence."
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

        <ControlledFailureBanner title="Evidence only — no live trading">
          The Strategy Journey is a read-only inspection surface. No run actions are available here. Every metric and chart reflects real backend data only.
        </ControlledFailureBanner>

        <SectionCard title="Select strategy" description="Choose a strategy to view its discovery lifecycle.">
          {loading ? (
            <LoadingSkeleton lines={2} />
          ) : state.strategies.length === 0 ? (
            <EmptyState
              title="No strategies found"
              description="Import strategies into the backend to see them here."
            />
          ) : (
            <div className="flex flex-wrap items-start gap-4">
              <div className="min-w-0 flex-1">
                <label htmlFor="strategy-select" className="mb-1 block text-xs font-semibold text-[var(--app-text-subtle)]">
                  Strategy
                </label>
                <select
                  id="strategy-select"
                  value={selectedStrategy}
                  onChange={(e) => setSelectedStrategy(e.target.value)}
                  className="h-10 w-full max-w-md rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
                >
                  {state.strategies.map((s) => (
                    <option key={s.strategy_name} value={s.strategy_name}>
                      {s.strategy_name}
                    </option>
                  ))}
                </select>
              </div>
              {strategy && (
                <div className="flex items-center gap-3 pt-5">
                  <StatusBadge
                    status={strategy.readiness}
                    tone={readinessTone(strategy.readiness)}
                    label={readinessLabel(strategy.readiness)}
                  />
                  {strategy.params_summary?.timeframe && (
                    <span className="rounded border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-2 py-0.5 text-xs text-[var(--app-text-muted)]">
                      {strategy.params_summary.timeframe}
                    </span>
                  )}
                  {strategy.has_sidecar && (
                    <span className="rounded border border-[rgb(34_197_94_/_0.32)] bg-[rgb(34_197_94_/_0.10)] px-2 py-0.5 text-xs text-[var(--app-success)]">
                      Sidecar ✓
                    </span>
                  )}
                </div>
              )}
            </div>
          )}
        </SectionCard>

        {selectedStrategy && !loading && (
          <>
            {hasActiveRun && (
              <SectionCard title="Live run" description="A run is currently active. Polling every 2 seconds.">
                <div className="space-y-3">
                  {activeBaselineRun && (
                    <LiveRunPanel runType="baseline" runId={activeBaselineRun.id} label="Baseline run (active)" />
                  )}
                  {activeOptimizationRun && (
                    <LiveRunPanel runType="optimization" runId={activeOptimizationRun.id} label="Optimization run (active)" />
                  )}
                </div>
              </SectionCard>
            )}

            <div className="grid gap-6 xl:grid-cols-3">
              <div className="xl:col-span-2">
                <SectionCard
                  title="Journey timeline"
                  description="Status of each lifecycle stage based on real backend data. Not started means no backend record was found."
                >
                  {steps.length === 0 ? (
                    <EmptyState title="No steps to show" description="Select a strategy to see its journey." />
                  ) : (
                    <WorkflowStepper steps={steps} orientation="vertical" />
                  )}
                </SectionCard>
              </div>

              <div className="space-y-4">
                <SectionCard title="Evidence summary" description="Latest run records for this strategy.">
                  <div className="space-y-3">
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

                {nextActions.length > 0 && (
                  <NextActionPanel
                    title="Next safe action"
                    message="Select an action below to navigate to the relevant detail page."
                    actions={nextActions}
                  />
                )}
              </div>
            </div>

            {baselineMetrics && (
              <SectionCard
                title="Latest baseline snapshot"
                description={`Quick-view of the most recent baseline run (${latestBaseline?.id ?? ''}). Open the baseline detail for full evidence.`}
              >
                <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                  <MetricCard
                    label="Status"
                    value={latestBaseline?.classification ?? latestBaseline?.status ?? 'Unknown'}
                  />
                  <MetricCard
                    label="Mode"
                    value={latestBaseline?.mode ?? 'Not recorded'}
                  />
                  <MetricCard
                    label="Created"
                    value={fmtTs(latestBaseline?.created_at)}
                  />
                  <MetricCard
                    label="Updated"
                    value={fmtTs(latestBaseline?.updated_at)}
                  />
                </div>
                <div className="mt-4">
                  <a
                    href={`/baseline/${latestBaseline?.id}`}
                    className="inline-flex h-9 items-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3.5 text-sm text-[var(--app-text-muted)] hover:text-[var(--app-text)] transition-colors"
                  >
                    Open full baseline detail →
                  </a>
                </div>
              </SectionCard>
            )}

            {strategy && strategy.issues.length > 0 && (
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
          </>
        )}
      </div>
    </AppShell>
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
            className="rounded border border-[var(--app-border)] bg-[var(--app-surface)] px-2 py-0.5 text-[11px] text-[var(--app-text-muted)] hover:text-[var(--app-accent)] transition-colors"
          >
            View
          </a>
        )}
      </div>
    </div>
  );
}
