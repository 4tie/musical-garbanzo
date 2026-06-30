'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import AppShell from '@/components/AppShell';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import MetricCard from '@/components/MetricCard';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import {
  ApiError,
  DecisionRecord,
  HealthResponse,
  OptimizationRunListItem,
  RunListItem,
  SystemStatusResponse,
  fetchHealth,
  fetchSystemStatus,
  getLatestRunDecision,
  listBaselineRuns,
  listOptimizationRuns,
  listRuns,
  toRunListItem,
  toUiStatus,
} from '@/lib/api';

const NO_RUNS_COPY =
  'No runs found yet. Run data will appear after backend validation pipelines create records.';
const OPTIMIZATION_REJECTED_COPY =
  'Optimization completed, but validation rejected the optimized result.';

interface DashboardState {
  health: HealthResponse | null;
  systemStatus: SystemStatusResponse | null;
  runs: RunListItem[];
  baselineRuns: RunListItem[];
  optimizationRuns: OptimizationRunListItem[];
  decisions: LatestDecision[];
  errors: DashboardError[];
  loadedAt: string | null;
}

interface DashboardError {
  source: string;
  error: ApiError;
}

interface LatestDecision {
  runId: string;
  runName: string;
  decision: DecisionRecord;
}

interface ActivityItem {
  id: string;
  title: string;
  subtitle: string;
  status: string;
  tone?: 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral';
  timestamp: string | null;
  note?: string;
}

interface ChartDatum {
  label: string;
  value: number;
}

const initialState: DashboardState = {
  health: null,
  systemStatus: null,
  runs: [],
  baselineRuns: [],
  optimizationRuns: [],
  decisions: [],
  errors: [],
  loadedAt: null,
};

export default function Dashboard() {
  const [dashboard, setDashboard] = useState<DashboardState>(initialState);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadDashboard = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const [healthResult, systemResult, runsResult, baselineResult, optimizationResult] = await Promise.all([
      fetchHealth(),
      fetchSystemStatus(),
      listRuns({ limit: 500 }),
      listBaselineRuns({ limit: 500 }),
      listOptimizationRuns({ limit: 500 }),
    ]);

    const errors: DashboardError[] = [];
    const runs = runsResult.success ? runsResult.data : [];
    const baselineRuns = baselineResult.success ? baselineResult.data : [];
    const optimizationRuns = optimizationResult.success ? optimizationResult.data : [];
    const health = healthResult.success ? healthResult.data : null;
    const systemStatus = systemResult.success ? systemResult.data : null;

    collectError(errors, 'Backend health', healthResult);
    collectError(errors, 'System status', systemResult);
    collectError(errors, 'Runs', runsResult);
    collectError(errors, 'Baseline runs', baselineResult);
    collectError(errors, 'Optimization runs', optimizationResult);

    const decisions = runsResult.success ? await fetchLatestDecisions(runs.slice(0, 5), errors) : [];

    setDashboard({
      health,
      systemStatus,
      runs,
      baselineRuns,
      optimizationRuns,
      decisions,
      errors,
      loadedAt: new Date().toISOString(),
    });
    setLoading(false);
    if (markRefreshing) {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadDashboard(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadDashboard]);

  const summary = useMemo(() => buildRunSummary(dashboard), [dashboard]);
  const latestRun = useMemo(() => findLatestRun(dashboard), [dashboard]);
  const statusChart = useMemo(() => buildRunsByStatus(dashboard), [dashboard]);
  const resultChart = useMemo(() => buildResultStatusDistribution(dashboard), [dashboard]);
  const timelineChart = useMemo(() => buildRunsOverTime(dashboard), [dashboard]);
  const baselineActivity = useMemo(
    () => dashboard.baselineRuns.slice(0, 5).map(toRunActivity),
    [dashboard.baselineRuns],
  );
  const optimizationActivity = useMemo(
    () => dashboard.optimizationRuns.slice(0, 5).map(toOptimizationActivity),
    [dashboard.optimizationRuns],
  );

  return (
    <AppShell
      pageTitle="Dashboard"
      systemStatus={dashboard.systemStatus}
      onRefresh={() => {
        void loadDashboard(true);
      }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="HER Command Center"
          description="Read-only overview of backend validation evidence. Counts, activity, and charts are rendered only from API responses."
          actions={
            dashboard.loadedAt ? (
              <span className="text-xs text-[var(--app-text-subtle)]">
                Updated {formatDateTime(dashboard.loadedAt)}
              </span>
            ) : null
          }
        />

        {dashboard.errors.length > 0 && (
          <ErrorBanner title="Some dashboard data could not be loaded">
            <ul className="list-inside list-disc">
              {dashboard.errors.map((item) => (
                <li key={`${item.source}-${item.error.kind}`}>
                  {item.source}: {item.error.message}
                </li>
              ))}
            </ul>
          </ErrorBanner>
        )}

        <ControlledFailureBanner title="Read-only inspection mode">
          This dashboard is read-only. HER is a validation engine, not a profit generator. No live trading actions exist in this dashboard, and rejected validation results are not system failures.
        </ControlledFailureBanner>

        <SectionCard title="System overview" description="Availability and latest run state from real API responses.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <OverviewCard
                title="Backend health"
                status={dashboard.health?.status ?? dashboard.systemStatus?.backend ?? 'unknown'}
                detail={
                  dashboard.health
                    ? `${dashboard.health.app} ${dashboard.health.backend} backend responded.`
                    : 'Backend health endpoint unavailable.'
                }
              />
              <OverviewCard
                title="Baseline pipeline"
                status={dashboard.errors.some((error) => error.source === 'Baseline runs') ? 'unavailable' : 'available'}
                detail={
                  summary.baselineRuns === 0
                    ? NO_RUNS_COPY
                    : `${summary.baselineRuns} baseline run record${plural(summary.baselineRuns)} found.`
                }
              />
              <OverviewCard
                title="Optimization pipeline"
                status={dashboard.errors.some((error) => error.source === 'Optimization runs') ? 'unavailable' : 'available'}
                detail={
                  summary.optimizationRuns === 0
                    ? NO_RUNS_COPY
                    : `${summary.optimizationRuns} optimization run record${plural(summary.optimizationRuns)} found.`
                }
              />
              <OverviewCard
                title="Latest run status"
                status={latestRun?.status ?? 'empty'}
                detail={latestRun ? `${latestRun.title} - ${formatDateTime(latestRun.timestamp)}` : NO_RUNS_COPY}
                note={latestRun?.note}
              />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Run summary" description="Rejected results are counted separately from system failures.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : summary.totalRecords === 0 ? (
            <EmptyState title="No runs found yet" description={NO_RUNS_COPY} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
              <MetricCard label="Baseline runs" value={summary.baselineRuns} helper="Filtered from real run records." />
              <MetricCard label="Optimization runs" value={summary.optimizationRuns} helper="From optimization API records." />
              <MetricCard label="Completed runs" value={summary.completedRuns} tone="good" helper="Pipeline completion only." />
              <MetricCard label="Controlled failures" value={summary.controlledFailures} tone="warning" helper="Expected blocked or controlled states." />
              <MetricCard label="Rejected results" value={summary.rejectedResults} tone="danger" helper="Validation rejection, not app failure." />
            </div>
          )}
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-3">
          <ActivityList
            title="Latest baseline runs"
            items={baselineActivity}
            loading={loading}
            emptyDescription={NO_RUNS_COPY}
          />
          <ActivityList
            title="Latest optimization runs"
            items={optimizationActivity}
            loading={loading}
            emptyDescription={NO_RUNS_COPY}
          />
          <DecisionList
            decisions={dashboard.decisions}
            loading={loading}
            emptyDescription="No saved decisions were found on the latest run records."
          />
        </div>

        <div className="grid gap-6 xl:grid-cols-3">
          <BarChartCard
            title="Runs by status"
            description="General and optimization run records grouped by backend status."
            data={statusChart}
          />
          <BarChartCard
            title="Result status distribution"
            description="Optimization result statuses and run classifications from real records."
            data={resultChart}
            emptyDescription="No result statuses are available yet."
          />
          <TimelineChartCard
            title="Latest runs over time"
            description="Run records grouped by creation date."
            data={timelineChart}
          />
        </div>
      </div>
    </AppShell>
  );
}

function OverviewCard({
  title,
  status,
  detail,
  note,
}: {
  title: string;
  status: string;
  detail: string;
  note?: string;
}) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
        <StatusBadge status={status} />
      </div>
      <p className="mt-3 text-sm leading-6 text-[var(--app-text-muted)]">{detail}</p>
      {note && <p className="mt-2 text-xs leading-5 text-[var(--app-warning)]">{note}</p>}
    </div>
  );
}

function ActivityList({
  title,
  items,
  loading,
  emptyDescription,
}: {
  title: string;
  items: ActivityItem[];
  loading: boolean;
  emptyDescription: string;
}) {
  return (
    <SectionCard title={title}>
      {loading ? (
        <LoadingSkeleton lines={5} />
      ) : items.length === 0 ? (
        <EmptyState title="No records found" description={emptyDescription} />
      ) : (
        <div className="space-y-3">
          {items.map((item) => (
            <div
              key={item.id}
              className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-[var(--app-text)]">{item.title}</p>
                  <p className="mt-1 text-xs text-[var(--app-text-muted)]">{item.subtitle}</p>
                </div>
                <StatusBadge status={item.status} tone={item.tone} />
              </div>
              {item.note && <p className="mt-2 text-xs leading-5 text-[var(--app-warning)]">{item.note}</p>}
              {item.timestamp && (
                <p className="mt-2 text-xs text-[var(--app-text-subtle)]">{formatDateTime(item.timestamp)}</p>
              )}
            </div>
          ))}
        </div>
      )}
    </SectionCard>
  );
}

function DecisionList({
  decisions,
  loading,
  emptyDescription,
}: {
  decisions: LatestDecision[];
  loading: boolean;
  emptyDescription: string;
}) {
  return (
    <SectionCard title="Latest decisions">
      {loading ? (
        <LoadingSkeleton lines={5} />
      ) : decisions.length === 0 ? (
        <EmptyState title="No decisions found" description={emptyDescription} />
      ) : (
        <div className="space-y-3">
          {decisions.map((item) => {
            const classification = stringifyField(item.decision.classification) ?? 'decision saved';
            return (
              <div
                key={`${item.runId}-${classification}`}
                className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold text-[var(--app-text)]">{item.runName}</p>
                    <p className="mt-1 text-xs text-[var(--app-text-muted)]">Run ID: {item.runId}</p>
                  </div>
                  <StatusBadge status={classification} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

function BarChartCard({
  title,
  description,
  data,
  emptyDescription = 'Not enough real data is available for this chart yet.',
}: {
  title: string;
  description: string;
  data: ChartDatum[];
  emptyDescription?: string;
}) {
  const total = data.reduce((sum, item) => sum + item.value, 0);

  return (
    <SectionCard title={title} description={description}>
      {total === 0 ? (
        <EmptyState title="Empty chart state" description={emptyDescription} />
      ) : (
        <div className="space-y-3">
          {data.map((item) => {
            const width = `${Math.max(6, (item.value / total) * 100)}%`;
            return (
              <div key={item.label}>
                <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                  <span className="truncate text-[var(--app-text-muted)]">{item.label}</span>
                  <span className="font-mono text-[var(--app-text)]">{item.value}</span>
                </div>
                <div className="h-2 rounded-full bg-[var(--app-surface-muted)]">
                  <div
                    className="h-2 rounded-full bg-[var(--app-accent)]"
                    style={{ width }}
                    aria-label={`${item.label}: ${item.value}`}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </SectionCard>
  );
}

function TimelineChartCard({
  title,
  description,
  data,
}: {
  title: string;
  description: string;
  data: ChartDatum[];
}) {
  const maxValue = Math.max(0, ...data.map((item) => item.value));

  return (
    <SectionCard title={title} description={description}>
      {data.length < 2 || maxValue === 0 ? (
        <EmptyState
          title="Empty chart state"
          description="At least two dated run records are needed for the timeline chart."
        />
      ) : (
        <div className="space-y-4">
          <svg viewBox="0 0 320 128" className="h-32 w-full" role="img" aria-label={title}>
            <polyline
              fill="none"
              stroke="var(--app-accent)"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="3"
              points={toPolylinePoints(data, maxValue)}
            />
            {data.map((item, index) => {
              const { x, y } = toPoint(index, data.length, item.value, maxValue);
              return <circle key={item.label} cx={x} cy={y} r="4" fill="var(--app-accent)" />;
            })}
          </svg>
          <div className="flex justify-between gap-3 text-xs text-[var(--app-text-subtle)]">
            <span>{data[0]?.label}</span>
            <span>{data.at(-1)?.label}</span>
          </div>
        </div>
      )}
    </SectionCard>
  );
}

async function fetchLatestDecisions(runs: RunListItem[], errors: DashboardError[]) {
  const results = await Promise.all(
    runs.map(async (run) => {
      const result = await getLatestRunDecision(run.id);
      if (!result.success) {
        if (result.error.kind !== 'not_found') {
          errors.push({ source: `Decision ${run.id}`, error: result.error });
        }
        return null;
      }
      return {
        runId: run.id,
        runName: run.name,
        decision: result.data,
      };
    }),
  );

  return results.filter((item): item is LatestDecision => item !== null);
}

function collectError<T>(
  errors: DashboardError[],
  source: string,
  result: { success: true; data: T } | { success: false; error: ApiError },
) {
  if (!result.success) {
    errors.push({ source, error: result.error });
  }
}

function buildRunSummary(dashboard: DashboardState) {
  const rejectedOptimization = dashboard.optimizationRuns.filter((run) =>
    isRejectedResultStatus(run.result_status),
  ).length;
  const rejectedRuns = dashboard.runs.filter((run) => isRejectedResultStatus(run.classification)).length;
  const completedRuns =
    dashboard.runs.filter((run) => isCompletedStatus(run.status)).length +
    dashboard.optimizationRuns.filter((run) => isCompletedStatus(run.status)).length;
  const controlledFailures =
    dashboard.runs.filter((run) => isControlledFailure(run.status)).length +
    dashboard.optimizationRuns.filter((run) => isControlledFailure(run.status)).length;

  return {
    baselineRuns: dashboard.baselineRuns.length,
    optimizationRuns: dashboard.optimizationRuns.length,
    completedRuns,
    controlledFailures,
    rejectedResults: rejectedRuns + rejectedOptimization,
    totalRecords: dashboard.runs.length + dashboard.optimizationRuns.length,
  };
}

function findLatestRun(dashboard: DashboardState): ActivityItem | null {
  const items = [
    ...dashboard.runs.map(toRunActivity),
    ...dashboard.optimizationRuns.map(toOptimizationActivity),
  ].filter((item) => item.timestamp);

  return items.sort((left, right) => compareDateDesc(left.timestamp, right.timestamp))[0] ?? null;
}

function buildRunsByStatus(dashboard: DashboardState): ChartDatum[] {
  return countBy([
    ...dashboard.runs.map((run) => run.status),
    ...dashboard.optimizationRuns.map((run) => run.status),
  ]);
}

function buildResultStatusDistribution(dashboard: DashboardState): ChartDatum[] {
  return countBy([
    ...dashboard.runs.flatMap((run) => (run.classification ? [run.classification] : [])),
    ...dashboard.optimizationRuns.flatMap((run) => (run.result_status ? [run.result_status] : [])),
  ]);
}

function buildRunsOverTime(dashboard: DashboardState): ChartDatum[] {
  const labels = [
    ...dashboard.runs.map((run) => dateLabel(run.created_at)),
    ...dashboard.optimizationRuns.map((run) => dateLabel(run.created_at)),
  ].filter((label): label is string => Boolean(label));

  return countBy(labels).sort((left, right) => left.label.localeCompare(right.label)).slice(-10);
}

function toRunActivity(run: RunListItem): ActivityItem {
  const uiRun = toRunListItem(run);
  const uiStatus = toUiStatus({ status: run.status, classification: run.classification });
  return {
    id: run.id,
    title: uiRun.label,
    subtitle: `${run.mode} - ${run.id}`,
    status: run.classification ?? run.status,
    tone: uiStatusToTone(uiStatus),
    timestamp: run.created_at,
    note: uiStatus === 'strategy_rejected' ? 'Rejected strategy does not mean system failure.' : undefined,
  };
}

function toOptimizationActivity(run: OptimizationRunListItem): ActivityItem {
  const uiStatus = toUiStatus({ status: run.status, resultStatus: run.result_status });
  return {
    id: run.id,
    title: run.strategy_name,
    subtitle: `${run.timeframe} - ${run.pairs.join(', ') || run.id}`,
    status: run.result_status ?? run.status,
    tone: uiStatusToTone(uiStatus),
    timestamp: run.created_at,
    note: run.result_status === 'optimization_rejected' ? OPTIMIZATION_REJECTED_COPY : undefined,
  };
}

function countBy(values: string[]): ChartDatum[] {
  const counts = new Map<string, number>();
  for (const value of values) {
    const label = value || 'unknown';
    counts.set(label, (counts.get(label) ?? 0) + 1);
  }
  return Array.from(counts.entries())
    .map(([label, value]) => ({ label, value }))
    .sort((left, right) => right.value - left.value || left.label.localeCompare(right.label));
}

function toPolylinePoints(data: ChartDatum[], maxValue: number): string {
  return data
    .map((item, index) => {
      const { x, y } = toPoint(index, data.length, item.value, maxValue);
      return `${x},${y}`;
    })
    .join(' ');
}

function toPoint(index: number, count: number, value: number, maxValue: number) {
  const x = count === 1 ? 160 : 14 + (index / (count - 1)) * 292;
  const y = 112 - (value / Math.max(1, maxValue)) * 96;
  return { x, y };
}

function uiStatusToTone(
  status: ReturnType<typeof toUiStatus>,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  switch (status) {
    case 'pipeline_completed':
      return 'success';
    case 'running':
      return 'info';
    case 'controlled_failure':
      return 'warning';
    case 'strategy_rejected':
    case 'system_failed':
      return 'danger';
    case 'optimization_rejected':
      return 'optimization';
    default:
      return 'neutral';
  }
}

function isCompletedStatus(status: string | null | undefined): boolean {
  return status === 'completed' || status === 'passed';
}

function isControlledFailure(status: string | null | undefined): boolean {
  return status === 'failed_controlled' || status === 'confirmation_required';
}

function isRejectedResultStatus(status: string | null | undefined): boolean {
  return (
    status === 'rejected' ||
    status === 'optimization_rejected' ||
    status === 'not_improved' ||
    status === 'overfit_suspected' ||
    status === 'invalid_optimization'
  );
}

function dateLabel(value: string | null | undefined): string | null {
  if (!value) {
    return null;
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  return date.toISOString().slice(0, 10);
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'unknown time';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function compareDateDesc(left: string | null, right: string | null): number {
  return new Date(right ?? 0).getTime() - new Date(left ?? 0).getTime();
}

function stringifyField(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function plural(count: number): string {
  return count === 1 ? '' : 's';
}
