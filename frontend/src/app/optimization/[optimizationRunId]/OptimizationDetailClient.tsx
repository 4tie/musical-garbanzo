'use client';

import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import CopyButton from '@/components/CopyButton';
import DataTable, { DataTableColumn } from '@/components/DataTable';
import Drawer from '@/components/Drawer';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import MetricCard from '@/components/MetricCard';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import {
  ApiError,
  ApiResult,
  JsonObject,
  OptimizationComparison,
  OptimizationReport,
  OptimizationRunDetail,
  OptimizationStatusResponse,
  OptimizationTrial,
  OptimizationTrialDetail,
  UiTimelineStage,
  getBestTrial,
  getOptimizationComparison,
  getOptimizationReport,
  getOptimizationRunDetail,
  getOptimizationStatus,
  getOptimizationTrialDetail,
  listOptimizationTrials,
  toTimelineStages,
  toUiStatus,
} from '@/lib/api';
import { startValidation } from '@/lib/api/validation';
import ValidationConfirmationDialog from '@/components/ValidationConfirmationDialog';

type TrialFilter = 'all' | 'best' | 'completed' | 'rejected' | 'failed' | 'ignored';

interface OptimizationDetailClientProps {
  optimizationRunId: string;
}

interface SourceError {
  source: string;
  error: ApiError;
}

interface OptimizationDetailState {
  detail: OptimizationRunDetail | null;
  status: OptimizationStatusResponse | null;
  trials: OptimizationTrial[];
  bestTrial: OptimizationTrial | null;
  comparison: OptimizationComparison | null;
  report: OptimizationReport | null;
  errors: SourceError[];
  loadedAt: string | null;
  validationDialogOpen: boolean;
}

interface TrialDetailState {
  trialId: string | null;
  detail: OptimizationTrialDetail | null;
  loading: boolean;
  error: ApiError | null;
}

interface ChartPoint {
  trialNumber: number;
  value: number;
}

interface ArtifactEvidenceRow {
  key: string;
  label: string;
  status: string;
  path: string | null;
  source: string;
  note: string;
}

interface ComparisonRow {
  key: string;
  label: string;
  baseline: unknown;
  optimized: unknown;
  indicator: 'improved' | 'worsened' | 'unchanged' | 'unavailable';
  delta?: unknown;
  lowerIsBetter?: boolean;
}

const emptyState: OptimizationDetailState = {
  detail: null,
  status: null,
  trials: [],
  bestTrial: null,
  comparison: null,
  report: null,
  errors: [],
  loadedAt: null,
  validationDialogOpen: false,
};

const initialTrialDetail: TrialDetailState = {
  trialId: null,
  detail: null,
  loading: false,
  error: null,
};

const filters: Array<{ id: TrialFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'best', label: 'Best' },
  { id: 'completed', label: 'Completed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'failed', label: 'Failed' },
  { id: 'ignored', label: 'Ignored' },
];

const coreSources = new Set(['Optimization detail']);

export default function OptimizationDetailClient({ optimizationRunId }: OptimizationDetailClientProps) {
  const router = useRouter();
  const [state, setState] = useState<OptimizationDetailState>(emptyState);
  const [trialDetail, setTrialDetail] = useState<TrialDetailState>(initialTrialDetail);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<TrialFilter>('all');

  const loadOptimization = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const [detailResult, statusResult, trialsResult, bestTrialResult, comparisonResult, reportResult] =
      await Promise.all([
        getOptimizationRunDetail(optimizationRunId),
        getOptimizationStatus(optimizationRunId),
        loadAllTrials(optimizationRunId),
        getBestTrial(optimizationRunId),
        getOptimizationComparison(optimizationRunId),
        getOptimizationReport(optimizationRunId),
      ]);

    const errors: SourceError[] = [];
    collectError(errors, 'Optimization detail', detailResult, true);
    collectError(errors, 'Optimization status', statusResult);
    collectError(errors, 'Trials', trialsResult, true);
    collectError(errors, 'Best trial', bestTrialResult);
    collectError(errors, 'Comparison', comparisonResult);
    collectError(errors, 'Optimization report', reportResult);

    setState({
      detail: detailResult.success ? detailResult.data : null,
      status: statusResult.success ? statusResult.data : null,
      trials: trialsResult.success ? trialsResult.data : [],
      bestTrial: bestTrialResult.success
        ? bestTrialResult.data
        : detailResult.success
          ? detailResult.data.best_trial
          : null,
      comparison: comparisonResult.success
        ? comparisonResult.data
        : detailResult.success
          ? detailResult.data.comparison
          : null,
      report: reportResult.success ? reportResult.data : null,
      errors,
      loadedAt: new Date().toISOString(),
      validationDialogOpen: false,
    });
    setLoading(false);
    if (markRefreshing) {
      setRefreshing(false);
    }
  }, [optimizationRunId]);

  const handleRunValidation = useCallback(async () => {
    if (!state.detail || !state.detail.run) {
      return;
    }

    const request = {
      source_type: 'optimization_run' as const,
      source_run_id: optimizationRunId,
      strategy_name: state.detail.run.strategy_name || '',
      pairs: state.detail.run.pairs || [],
      timeframe: state.detail.run.timeframe || '',
      exchange: state.detail.run.exchange || 'binance',
      risk_profile: state.detail.run.risk_profile || 'balanced',
      timerange: '',
      oos_ratio: 0.30,
      wfo_enabled: true,
      wfo_train_days: 45,
      wfo_test_days: 15,
      wfo_step_days: 15,
      wfo_max_windows: 2,
      robustness_enabled: true,
      sensitivity_enabled: false,
      user_confirmed: true,
    };

    const result = await startValidation(request);

    if (result.success && result.data) {
      setState((prev) => ({ ...prev, validationDialogOpen: false }));
      router.push(`/validation/${result.data.validation_run_id}`);
    }
  }, [state.detail, optimizationRunId, router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadOptimization(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadOptimization]);

  const run = state.detail?.run ?? null;
  const summary = useMemo(() => buildSummary(state, optimizationRunId), [optimizationRunId, state]);
  const timeline = useMemo(() => buildTimeline(state), [state]);
  const filteredTrials = useMemo(
    () => filterTrials(state.trials, filter, query),
    [filter, query, state.trials],
  );
  const trialCharts = useMemo(() => buildTrialCharts(state.trials), [state.trials]);
  const comparisonRows = useMemo(() => buildComparisonRows(state.comparison), [state.comparison]);
  const artifactRows = useMemo(() => buildArtifactEvidenceRows(state), [state]);
  const blockingErrors = state.errors.filter((item) => coreSources.has(item.source));
  const partialErrors = state.errors.filter((item) => !coreSources.has(item.source));

  const trialColumns = useMemo<DataTableColumn<OptimizationTrial>[]>(
    () => [
      {
        id: 'trial_number',
        header: 'Trial',
        sortValue: (row) => row.trial_number,
        render: (row) => (
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs text-[var(--app-text)]">#{row.trial_number}</span>
            <span onClick={(event) => event.stopPropagation()}>
              <CopyButton value={row.id} label="Copy ID" />
            </span>
          </div>
        ),
      },
      { id: 'status', header: 'Status', sortValue: (row) => row.status, render: (row) => <StatusBadge status={row.status} tone={trialTone(row)} /> },
      { id: 'best', header: 'Best', sortValue: (row) => Number(row.is_best), render: (row) => yesNo(row.is_best) },
      { id: 'selected', header: 'Selected', sortValue: (row) => Number(row.is_selected_for_validation), render: (row) => yesNo(row.is_selected_for_validation) },
      { id: 'profit_factor', header: 'Profit factor', sortValue: (row) => row.profit_factor ?? -Infinity, render: (row) => formatNumber(row.profit_factor) },
      { id: 'expectancy', header: 'Expectancy', sortValue: (row) => row.expectancy ?? -Infinity, render: (row) => formatNumber(row.expectancy) },
      { id: 'drawdown', header: 'Drawdown', sortValue: (row) => row.max_drawdown ?? Infinity, render: (row) => formatPercent(row.max_drawdown) },
      { id: 'trades', header: 'Trades', sortValue: (row) => row.trade_count ?? -1, render: (row) => formatValue(row.trade_count) },
      { id: 'win_rate', header: 'Win rate', sortValue: (row) => row.win_rate ?? -Infinity, render: (row) => formatPercent(row.win_rate) },
      { id: 'loss', header: 'Loss score', sortValue: (row) => row.loss_score ?? Infinity, render: (row) => formatNumber(row.loss_score) },
      { id: 'rejection', header: 'Rejection reason', sortValue: (row) => row.rejection_reason ?? '', render: (row) => row.rejection_reason ?? 'n/a' },
      { id: 'failure', header: 'Failure reason', sortValue: (row) => row.failure_reason ?? '', render: (row) => row.failure_reason ?? 'n/a' },
    ],
    [],
  );

  async function openTrialDrawer(trial: OptimizationTrial) {
    setTrialDetail({ trialId: trial.id, detail: null, loading: true, error: null });
    const result = await getOptimizationTrialDetail(optimizationRunId, trial.id);
    if (result.success) {
      setTrialDetail({ trialId: trial.id, detail: result.data, loading: false, error: null });
    } else {
      setTrialDetail({ trialId: trial.id, detail: null, loading: false, error: result.error });
    }
  }

  return (
    <AppShell
      pageTitle="Optimization Detail"
      onRefresh={() => {
        void loadOptimization(true);
      }}
      refreshDisabled={refreshing}
      drawer={
        <Drawer
          open={Boolean(trialDetail.trialId)}
          title="Trial detail"
          onClose={() => setTrialDetail(initialTrialDetail)}
        >
          <TrialDetailContent state={trialDetail} />
        </Drawer>
      }
    >
      <div className="space-y-6">
        <PageHeader
          title="Optimization run detail"
          description="Read-only optimization evidence, all persisted trials, best trial context, and baseline-vs-optimized comparison."
          actions={
            <>
              {state.loadedAt && (
                <span className="text-xs text-[var(--app-text-subtle)]">
                  Updated {formatDateTime(state.loadedAt)}
                </span>
              )}
              {state.detail?.run?.optimized_run_id && state.detail.run.strategy_name && state.detail.run.pairs && state.detail.run.timeframe && (
                <Button
                  variant="primary"
                  onClick={() => setState((prev) => ({ ...prev, validationDialogOpen: true }))}
                >
                  Run Validation
                </Button>
              )}
              <Button variant="secondary" onClick={() => router.push('/runs')}>
                Back to Runs
              </Button>
            </>
          }
        />

        {blockingErrors.length > 0 && (
          <ErrorBanner title="Optimization run could not be loaded">
            <ul className="list-inside list-disc">
              {blockingErrors.map((item) => (
                <li key={`${item.source}-${item.error.kind}`}>
                  {item.source}: {item.error.message}
                </li>
              ))}
            </ul>
          </ErrorBanner>
        )}

        {partialErrors.length > 0 && (
          <ControlledFailureBanner title="Some optimization evidence is unavailable">
            <ul className="list-inside list-disc">
              {partialErrors.map((item) => (
                <li key={`${item.source}-${item.error.kind}`}>
                  {item.source}: {item.error.message}
                </li>
              ))}
            </ul>
          </ControlledFailureBanner>
        )}

        {summary.resultStatus === 'optimization_rejected' && (
          <ControlledFailureBanner title="Pipeline completed, strategy rejected">
            This is not a system failure. The optimization pipeline completed successfully, but validation rejected the optimized result.
          </ControlledFailureBanner>
        )}

        <SectionCard title="Header summary" description="Optimization identity, scope, and backend status metadata.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <SummaryField label="Optimization run ID" value={summary.id} action={<CopyButton value={summary.id} label="Copy ID" />} mono />
              <SummaryField label="Strategy" value={summary.strategyName} />
              <SummaryField label="Pairs" value={summary.pairs} />
              <SummaryField label="Timeframe" value={summary.timeframe} />
              <SummaryField label="Status" value={<StatusBadge status={summary.status} label={statusLabel(summary.status, summary.resultStatus)} tone={statusTone(summary.status, summary.resultStatus)} />} />
              <SummaryField label="Result status" value={summary.resultStatus} />
              <SummaryField label="Epochs" value={summary.epochs} />
              <SummaryField label="Spaces" value={summary.spaces} />
              <SummaryField label="Created" value={formatDateTime(summary.createdAt)} />
              <SummaryField label="Updated" value={formatDateTime(summary.updatedAt)} />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Summary cards" description="Key IDs and counts from persisted optimization metadata.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-6">
              <MetricCard label="Trials count" value={state.trials.length} helper="Loaded from paged real trial records." />
              <MetricCard label="Best trial number" value={state.bestTrial?.trial_number ?? null} helper="Best persisted trial, if selected." />
              <MetricCard label="Best trial ID" value={state.bestTrial?.id ?? run?.best_trial_id ?? null} helper="Copy from table or drawer for full ID." />
              <MetricCard label="Baseline run ID" value={run?.baseline_run_id ?? null} helper="Reference baseline run." />
              <MetricCard label="Optimized run ID" value={run?.optimized_run_id ?? null} helper="Validated optimized backtest run." />
              <MetricCard label="Result status" value={summary.resultStatus} tone={summary.resultStatus === 'optimization_rejected' ? 'danger' : 'neutral'} />
            </div>
          )}
          {!loading && (
            <div className="mt-4 flex flex-wrap gap-2">
              {run?.baseline_run_id && (
                <Button variant="secondary" size="sm" onClick={() => router.push(`/baseline/${encodeURIComponent(run.baseline_run_id ?? '')}`)}>
                  View baseline run
                </Button>
              )}
              {run?.optimized_run_id && (
                <Button variant="secondary" size="sm" onClick={() => router.push(`/baseline/${encodeURIComponent(run.optimized_run_id ?? '')}`)}>
                  View optimized run
                </Button>
              )}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Stage timeline" description="Only real stages returned by optimization APIs are shown.">
          {loading ? (
            <LoadingSkeleton lines={8} />
          ) : timeline.length === 0 ? (
            <EmptyState title="No optimization stages found" description="The optimization APIs did not return stage records for this run." />
          ) : (
            <div className="space-y-3">
              {timeline.map((stage) => (
                <TimelineItem key={stage.id} stage={stage} />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Trials" description="All loaded trials are visible, including failed, rejected, and ignored trials.">
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Search trials</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search trial number, ID, status, rejection, failure"
                className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
              />
            </label>
            <div className="flex flex-wrap gap-2">
              {filters.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={filter === item.id ? 'primary' : 'secondary'}
                  onClick={() => setFilter(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>
          {loading ? (
            <LoadingSkeleton lines={7} />
          ) : (
            <DataTable
              rows={filteredTrials}
              columns={trialColumns}
              getRowKey={(row) => row.id}
              onRowClick={(row) => {
                void openTrialDrawer(row);
              }}
              initialSortColumn="trial_number"
              initialSortDirection="asc"
              emptyState={<EmptyState title="No trials found" description="No persisted optimization trials matched the current filters." />}
            />
          )}
        </SectionCard>

        <SectionCard title="Trial charts" description="Charts render only when at least two real numeric trial values exist.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : state.trials.length === 0 ? (
            <EmptyState title="No trial chart data found" description="No trials were returned, so no chart data can be drawn." />
          ) : (
            <div className="grid gap-4 xl:grid-cols-2">
              <TrialLineChart title="Profit factor by trial number" points={trialCharts.profitFactor} valueLabel="Profit factor" />
              <TrialLineChart title="Expectancy by trial number" points={trialCharts.expectancy} valueLabel="Expectancy" />
              <TrialLineChart title="Drawdown by trial number" points={trialCharts.drawdown} valueLabel="Drawdown" percent />
              <TrialLineChart title="Loss score by trial number" points={trialCharts.lossScore} valueLabel="Loss score" />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Best trial" description="Best Hyperopt trial is inspection evidence only. It is not approved by itself.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : !state.bestTrial ? (
            <EmptyState title="No best trial found" description="The backend did not return a selected best trial for this optimization run." />
          ) : (
            <BestTrialPanel
              trial={state.bestTrial}
              report={state.report?.report ?? null}
              optimizedRunId={run?.optimized_run_id ?? state.comparison?.optimized_run_id ?? null}
              decisionResult={state.comparison?.optimized_classification ?? stringValue(state.report?.report.optimized_classification) ?? null}
            />
          )}
        </SectionCard>

        <SectionCard title="Baseline vs optimized comparison" description="Directional indicators compare validation evidence only. They do not imply profitability.">
          {loading ? (
            <LoadingSkeleton lines={5} />
          ) : !state.comparison ? (
            <EmptyState title="No comparison found" description="The backend did not return baseline-vs-optimized comparison data for this run." />
          ) : (
            <ComparisonPanel comparison={state.comparison} rows={comparisonRows} />
          )}
        </SectionCard>

        <SectionCard title="Artifact metadata" description="Safe local artifact paths and metadata only. Huge raw logs are not loaded by default.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : (
            <ArtifactMetadataPanel rows={artifactRows} report={state.report} reportPath={run?.report_artifact_path ?? null} />
          )}
        </SectionCard>

        <ValidationConfirmationDialog
          open={state.validationDialogOpen}
          strategyName={state.detail?.run?.strategy_name || ''}
          sourceType="optimization_run"
          sourceRunId={optimizationRunId}
          pairs={state.detail?.run?.pairs || []}
          timeframe={state.detail?.run?.timeframe || ''}
          riskProfile={state.detail?.run?.risk_profile || 'balanced'}
          onConfirm={handleRunValidation}
          onCancel={() => setState((prev) => ({ ...prev, validationDialogOpen: false }))}
        />
      </div>
    </AppShell>
  );
}

function ArtifactMetadataPanel({
  rows,
  report,
  reportPath,
}: {
  rows: ArtifactEvidenceRow[];
  report: OptimizationReport | null;
  reportPath: string | null;
}) {
  return (
    <div className="space-y-4">
      <ControlledFailureBanner title="Local artifact note">
        Raw artifacts are local runtime files and are not committed. The dashboard shows paths and
        metadata only; it does not open huge stdout, stderr, or raw result logs by default.
      </ControlledFailureBanner>
      {rows.length === 0 ? (
        <EmptyState title="No artifact metadata found" description="The backend did not return safe artifact paths or report metadata for this optimization run." />
      ) : (
        <div className="grid gap-3">
          {rows.map((row) => (
            <div key={row.key} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-[var(--app-text)]">{row.label}</p>
                  <p className="mt-1 text-xs text-[var(--app-text-subtle)]">{row.source}</p>
                </div>
                <StatusBadge status={row.status} tone={row.path ? 'success' : 'neutral'} />
              </div>
              <p className="mt-3 text-sm leading-6 text-[var(--app-text-muted)]">{row.note}</p>
              {row.path ? (
                <div className="mt-3 flex min-w-0 items-center gap-2">
                  <code className="min-w-0 truncate rounded-[var(--app-radius)] bg-[var(--app-surface)] px-2 py-1 text-xs text-[var(--app-text)]">
                    {row.path}
                  </code>
                  <CopyButton value={row.path} label="Copy path" />
                </div>
              ) : (
                <p className="mt-3 text-sm text-[var(--app-text-subtle)]">Not provided by backend.</p>
              )}
            </div>
          ))}
        </div>
      )}
      <div className="grid gap-4 md:grid-cols-2">
        <SummaryField label="Report status" value={report?.status ?? 'Not provided by backend.'} />
        <SummaryField label="Report path" value={report?.report_artifact_path ?? reportPath ?? 'Not provided by backend.'} mono />
        <SummaryField label="Report keys" value={report ? Object.keys(report.report).join(', ') || 'No top-level keys' : 'Not provided by backend.'} />
      </div>
    </div>
  );
}

function ComparisonPanel({ comparison, rows }: { comparison: OptimizationComparison; rows: ComparisonRow[] }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge
          status={comparison.result_status ?? 'not provided'}
          tone={comparison.result_status === 'optimization_rejected' ? 'danger' : 'optimization'}
        />
        {comparison.improvement_summary ? (
          <p className="text-sm text-[var(--app-text-muted)]">{comparison.improvement_summary}</p>
        ) : (
          <p className="text-sm text-[var(--app-text-muted)]">Not provided by backend.</p>
        )}
      </div>
      <div className="grid gap-3">
        {rows.map((row) => (
          <div key={row.key} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
            <div className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div>
                <p className="text-sm font-semibold text-[var(--app-text)]">{row.label}</p>
                <p className="mt-1 text-sm text-[var(--app-text-muted)]">
                  {formatValue(row.baseline)} -&gt; {formatValue(row.optimized)}
                </p>
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <StatusBadge status={row.indicator} tone={comparisonTone(row.indicator)} />
                {row.delta !== undefined && (
                  <span className="text-xs text-[var(--app-text-subtle)]">Delta: {formatValue(row.delta)}</span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
      {comparison.warnings.length > 0 && (
        <ListBlock title="Comparison warnings" items={comparison.warnings} empty="No warnings." />
      )}
    </div>
  );
}

function ParamsViewer({ sections }: { sections: Array<{ title: string; value: unknown }> }) {
  return (
    <div className="space-y-3">
      {sections.map((section) => (
        <JsonSection key={section.title} title={section.title} value={section.value} />
      ))}
    </div>
  );
}

function JsonSection({ title, value }: { title: string; value: unknown }) {
  const hasValue = hasJsonContent(value);
  const json = hasValue ? safeJson(value) : 'Not provided by backend.';

  return (
    <details className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)]">
      <summary className="flex cursor-pointer items-center justify-between gap-3 px-4 py-3 text-sm font-semibold text-[var(--app-text)]">
        <span>{title}</span>
        {hasValue && <CopyButton value={json} label="Copy JSON" />}
      </summary>
      <pre className="max-h-80 overflow-auto border-t border-[var(--app-border)] bg-[var(--app-surface)] p-4 text-xs leading-5 text-[var(--app-text-muted)]">
        {json}
      </pre>
    </details>
  );
}

function hasJsonContent(value: unknown): boolean {
  if (value === null || value === undefined) {
    return false;
  }
  if (typeof value === 'object') {
    return Object.keys(value as JsonObject).length > 0;
  }
  return false;
}

function safeJson(value: unknown): string {
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function compareValues(
  baseline: unknown,
  optimized: unknown,
  higherIsBetter: boolean,
): 'improved' | 'worsened' | 'unchanged' | 'unavailable' {
  if (baseline == null || optimized == null) {
    return 'unavailable';
  }
  if (typeof baseline !== 'number' || typeof optimized !== 'number') {
    return 'unavailable';
  }
  if (baseline === optimized) {
    return 'unchanged';
  }
  const improved = higherIsBetter ? optimized > baseline : optimized < baseline;
  return improved ? 'improved' : 'worsened';
}

function compareClassifications(
  baseline: string | null | undefined,
  optimized: string | null | undefined,
): 'improved' | 'worsened' | 'unchanged' | 'unavailable' {
  if (!baseline || !optimized) {
    return 'unavailable';
  }
  if (baseline === optimized) {
    return 'unchanged';
  }
  // approved > rejected > unknown
  const ranking = { approved: 2, rejected: 1, unknown: 0 };
  const baselineRank = ranking[baseline as keyof typeof ranking] ?? 0;
  const optimizedRank = ranking[optimized as keyof typeof ranking] ?? 0;
  if (optimizedRank > baselineRank) {
    return 'improved';
  }
  if (optimizedRank < baselineRank) {
    return 'worsened';
  }
  return 'unchanged';
}

async function loadAllTrials(optimizationRunId: string): Promise<ApiResult<OptimizationTrial[]>> {
  const pageSize = 500;
  const maxRows = 5000;
  const trials: OptimizationTrial[] = [];

  for (let offset = 0; offset < maxRows; offset += pageSize) {
    const result = await listOptimizationTrials(optimizationRunId, { limit: pageSize, offset });
    if (!result.success) {
      return result;
    }
    trials.push(...result.data);
    if (result.data.length < pageSize) {
      return {
        ...result,
        data: trials,
        empty: trials.length === 0,
      };
    }
  }

  return {
    success: true,
    data: trials,
    status: 200,
    empty: trials.length === 0,
  };
}

function collectError<T>(errors: SourceError[], source: string, result: ApiResult<T>, required = false) {
  if (result.success) {
    return;
  }
  if (!required && result.error.kind === 'not_found') {
    return;
  }
  errors.push({ source, error: result.error });
}

function buildSummary(state: OptimizationDetailState, optimizationRunId: string) {
  const run = state.detail?.run;
  const request = run?.request ?? {};
  const requestedSpaces = Array.isArray(request.spaces) ? request.spaces : null;
  const spaces = run?.spaces ?? requestedSpaces;
  const epochsRequested = run?.epochs_requested ?? numericValue(request.epochs) ?? state.status?.epochs_total ?? null;
  const epochsCompleted = run?.epochs_completed ?? state.status?.epochs_completed ?? null;

  return {
    id: optimizationRunId,
    strategyName: run?.strategy_name ?? 'Not recorded',
    pairs: run?.pairs?.length ? run.pairs.join(', ') : 'Not recorded',
    timeframe: run?.timeframe ?? 'Not recorded',
    status: run?.status ?? state.status?.status ?? 'unknown',
    resultStatus: run?.result_status ?? state.comparison?.result_status ?? 'Not recorded',
    epochs: epochsRequested == null && epochsCompleted == null
      ? 'Not recorded'
      : `${epochsCompleted ?? 0}/${epochsRequested ?? 'unknown'}`,
    spaces: spaces?.length ? spaces.join(', ') : 'Not recorded',
    createdAt: run?.created_at ?? state.status?.created_at ?? null,
    updatedAt: run?.updated_at ?? state.status?.updated_at ?? null,
  };
}

function buildTimeline(state: OptimizationDetailState): UiTimelineStage[] {
  if (state.detail?.stages?.length) {
    return toTimelineStages(state.detail.stages);
  }
  const progress = state.status?.stage_progress;
  if (!progress) {
    return [];
  }
  return Object.entries(progress).map(([key, value], index) => ({
    id: `${key}-${index}`,
    key,
    name: labelize(key),
    order: index,
    status: String(value),
    uiStatus: toUiStatus({ status: String(value) }),
    startedAt: null,
    completedAt: null,
    durationMs: null,
    message: null,
    errorCode: state.status?.current_stage === key ? state.status.error_code : null,
    warnings: [],
    errors: state.status?.current_stage === key && state.status.error_code ? [state.status.error_code] : [],
    details: {},
  }));
}

function filterTrials(trials: OptimizationTrial[], filter: TrialFilter, query: string) {
  const normalizedQuery = query.trim().toLowerCase();
  return trials.filter((trial) => {
    const matchesFilter = matchesTrialFilter(trial, filter);
    const searchText = [
      trial.id,
      trial.trial_number,
      trial.status,
      trial.rejection_reason,
      trial.failure_reason,
      trial.is_best ? 'best' : '',
      trial.is_selected_for_validation ? 'selected' : '',
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return matchesFilter && (!normalizedQuery || searchText.includes(normalizedQuery));
  });
}

function matchesTrialFilter(trial: OptimizationTrial, filter: TrialFilter) {
  if (filter === 'all') {
    return true;
  }
  if (filter === 'best') {
    return trial.is_best || trial.status === 'best';
  }
  return trial.status === filter;
}

function buildTrialCharts(trials: OptimizationTrial[]) {
  return {
    profitFactor: chartPoints(trials, 'profit_factor'),
    expectancy: chartPoints(trials, 'expectancy'),
    drawdown: chartPoints(trials, 'max_drawdown'),
    lossScore: chartPoints(trials, 'loss_score'),
  };
}

function chartPoints(trials: OptimizationTrial[], key: keyof OptimizationTrial): ChartPoint[] {
  return trials
    .flatMap((trial) => {
      const value = trial[key];
      return typeof value === 'number' && Number.isFinite(value)
        ? [{ trialNumber: trial.trial_number, value }]
        : [];
    })
    .sort((left, right) => left.trialNumber - right.trialNumber);
}

function buildComparisonRows(comparison: OptimizationComparison | null) {
  if (!comparison) {
    return [];
  }
  return [
    {
      key: 'profit_factor',
      label: 'Profit factor',
      baseline: comparison.baseline_metrics?.profit_factor,
      optimized: comparison.optimized_metrics?.profit_factor,
      delta: comparison.delta_profit_factor,
      indicator: compareValues(comparison.baseline_metrics?.profit_factor, comparison.optimized_metrics?.profit_factor, true),
    },
    {
      key: 'expectancy',
      label: 'Expectancy',
      baseline: comparison.baseline_metrics?.expectancy,
      optimized: comparison.optimized_metrics?.expectancy,
      delta: comparison.delta_expectancy,
      indicator: compareValues(comparison.baseline_metrics?.expectancy, comparison.optimized_metrics?.expectancy, true),
    },
    {
      key: 'drawdown',
      label: 'Drawdown',
      baseline: comparison.baseline_metrics?.max_drawdown,
      optimized: comparison.optimized_metrics?.max_drawdown,
      delta: comparison.delta_drawdown,
      indicator: compareValues(comparison.baseline_metrics?.max_drawdown, comparison.optimized_metrics?.max_drawdown, false),
    },
    {
      key: 'trade_count',
      label: 'Trade count',
      baseline: comparison.baseline_metrics?.trade_count,
      optimized: comparison.optimized_metrics?.trade_count,
      delta: comparison.delta_trade_count,
      indicator: compareValues(comparison.baseline_metrics?.trade_count, comparison.optimized_metrics?.trade_count, true),
    },
    {
      key: 'win_rate',
      label: 'Win rate',
      baseline: comparison.baseline_metrics?.win_rate,
      optimized: comparison.optimized_metrics?.win_rate,
      indicator: compareValues(comparison.baseline_metrics?.win_rate, comparison.optimized_metrics?.win_rate, true),
    },
    {
      key: 'classification',
      label: 'Classification',
      baseline: comparison.baseline_classification,
      optimized: comparison.optimized_classification,
      indicator: compareClassifications(comparison.baseline_classification, comparison.optimized_classification),
    },
  ];
}

function SummaryField({
  label,
  value,
  action,
  mono = false,
}: {
  label: string;
  value: ReactNode;
  action?: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <p className="text-xs font-medium uppercase text-[var(--app-text-subtle)]">{label}</p>
      <div className="mt-2 flex min-w-0 items-center gap-2">
        <div className={['min-w-0 truncate text-sm text-[var(--app-text)]', mono ? 'font-mono' : ''].join(' ')}>
          {value}
        </div>
        {action}
      </div>
    </div>
  );
}

function TimelineItem({ stage }: { stage: UiTimelineStage }) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={stage.status} tone={statusTone(stage.status, null)} />
            <span className="font-mono text-xs text-[var(--app-text-subtle)]">{stage.key}</span>
          </div>
          <h3 className="mt-2 text-sm font-semibold text-[var(--app-text)]">{stage.name}</h3>
          {stage.message && <p className="mt-1 text-sm leading-6 text-[var(--app-text-muted)]">{stage.message}</p>}
          {stage.errorCode && <p className="mt-1 font-mono text-xs text-[var(--app-danger)]">{stage.errorCode}</p>}
        </div>
        <div className="text-left text-xs leading-5 text-[var(--app-text-subtle)] md:text-right">
          <p>{formatDateTime(stage.startedAt)}</p>
          <p>{formatDuration(stage.durationMs)}</p>
        </div>
      </div>
    </div>
  );
}

function TrialLineChart({
  title,
  points,
  valueLabel,
  percent = false,
}: {
  title: string;
  points: ChartPoint[];
  valueLabel: string;
  percent?: boolean;
}) {
  if (points.length < 2) {
    return (
      <EmptyState
        title={title}
        description={`Not enough real ${valueLabel.toLowerCase()} values were returned to draw this chart.`}
      />
    );
  }

  const width = 640;
  const height = 220;
  const padding = 34;
  const minX = Math.min(...points.map((point) => point.trialNumber));
  const maxX = Math.max(...points.map((point) => point.trialNumber));
  const minY = Math.min(...points.map((point) => point.value));
  const maxY = Math.max(...points.map((point) => point.value));
  const xRange = Math.max(1, maxX - minX);
  const yRange = Math.max(1, maxY - minY);
  const coordinates = points.map((point) => {
    const x = padding + ((point.trialNumber - minX) / xRange) * (width - padding * 2);
    const y = height - padding - ((point.value - minY) / yRange) * (height - padding * 2);
    return `${x},${y}`;
  });

  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="mb-3 flex items-start justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
        <span className="text-xs text-[var(--app-text-subtle)]">{points.length} points</span>
      </div>
      <svg viewBox={`0 0 ${width} ${height}`} className="h-56 w-full" role="img" aria-label={title}>
        <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--app-border)" />
        <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="var(--app-border)" />
        <polyline points={coordinates.join(' ')} fill="none" stroke="var(--app-accent)" strokeWidth="2.5" />
        {points.map((point) => {
          const x = padding + ((point.trialNumber - minX) / xRange) * (width - padding * 2);
          const y = height - padding - ((point.value - minY) / yRange) * (height - padding * 2);
          return <circle key={`${title}-${point.trialNumber}`} cx={x} cy={y} r="3" fill="var(--app-accent)" />;
        })}
        <text x={padding} y={height - 8} fill="var(--app-text-subtle)" fontSize="12">
          trial {minX}
        </text>
        <text x={width - padding - 72} y={height - 8} fill="var(--app-text-subtle)" fontSize="12">
          trial {maxX}
        </text>
        <text x={padding + 4} y={padding - 10} fill="var(--app-text-subtle)" fontSize="12">
          {percent ? formatPercent(maxY) : formatNumber(maxY)}
        </text>
        <text x={padding + 4} y={height - padding - 6} fill="var(--app-text-subtle)" fontSize="12">
          {percent ? formatPercent(minY) : formatNumber(minY)}
        </text>
      </svg>
    </div>
  );
}

function BestTrialPanel({
  trial,
  report,
  optimizedRunId,
  decisionResult,
}: {
  trial: OptimizationTrial;
  report: JsonObject | null;
  optimizedRunId: string | null;
  decisionResult: string | null;
}) {
  const params = summarizeParams(trial);
  const whySelected = stringValue(report?.why_selected) ?? stringValue(report?.best_trial_reason);
  return (
    <div className="space-y-5">
      <ControlledFailureBanner title="Best trial warning">
        Best Hyperopt trial is only candidate evidence. HER still requires optimized backtest
        validation, comparison, and decision evidence before any approval claim.
      </ControlledFailureBanner>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Trial number" value={trial.trial_number} />
        <MetricCard label="Profit factor" value={formatNumber(trial.profit_factor)} />
        <MetricCard label="Expectancy" value={formatNumber(trial.expectancy)} />
        <MetricCard label="Loss score" value={formatNumber(trial.loss_score)} />
        <MetricCard label="Max drawdown" value={formatPercent(trial.max_drawdown)} />
        <MetricCard label="Trade count" value={trial.trade_count} />
        <MetricCard label="Win rate" value={formatPercent(trial.win_rate)} />
        <MetricCard label="Profit total" value={formatNumber(trial.profit_total)} />
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <SummaryField label="Best trial ID" value={trial.id} action={<CopyButton value={trial.id} label="Copy ID" />} mono />
        <SummaryField label="Optimized backtest run" value={optimizedRunId ?? 'Not provided by backend.'} mono />
        <SummaryField label="Decision result" value={decisionResult ?? 'Not provided by backend.'} />
        <SummaryField label="Created" value={formatDateTime(trial.created_at)} />
      </div>
      <ListBlock title="Params summary" items={params} empty="No parameter groups were returned for the best trial." />
      <ListBlock title="Why selected" items={whySelected ? [whySelected] : []} empty="Not provided by backend." />
      <ParamsViewer sections={trialParamSections(trial)} />
    </div>
  );
}

function TrialDetailContent({
  state,
}: {
  state: TrialDetailState;
}) {
  if (state.loading) {
    return <LoadingSkeleton lines={8} />;
  }
  if (state.error) {
    return <ErrorBanner title="Trial detail unavailable">{state.error.message}</ErrorBanner>;
  }

  const trial = state.detail?.trial;
  if (!trial) {
    return <EmptyState title="No trial selected" description="Select a trial row to inspect full persisted details." />;
  }

  return (
    <div className="space-y-4">
      <SummaryField label="Trial ID" value={trial.id} action={<CopyButton value={trial.id} label="Copy ID" />} mono />
      <SummaryField label="Trial number" value={`#${trial.trial_number}`} />
      <SummaryField label="Status" value={<StatusBadge status={trial.status} tone={trialTone(trial)} />} />
      <div className="grid gap-3 md:grid-cols-2">
        <SummaryField label="Is best" value={yesNo(trial.is_best)} />
        <SummaryField label="Selected for validation" value={yesNo(trial.is_selected_for_validation)} />
        <SummaryField label="Created" value={formatDateTime(trial.created_at)} />
      </div>
      <div className="grid gap-3">
        <MetricCard label="Profit factor" value={formatNumber(trial.profit_factor)} />
        <MetricCard label="Expectancy" value={formatNumber(trial.expectancy)} />
        <MetricCard label="Max drawdown" value={formatPercent(trial.max_drawdown)} />
        <MetricCard label="Trade count" value={trial.trade_count} />
        <MetricCard label="Win rate" value={formatPercent(trial.win_rate)} />
        <MetricCard label="Loss score" value={formatNumber(trial.loss_score)} />
        <MetricCard label="Profit total" value={formatNumber(trial.profit_total)} />
      </div>
      <ListBlock title="Rejection reason" items={trial.rejection_reason ? [trial.rejection_reason] : []} empty="Not provided by backend." />
      <ListBlock title="Failure reason" items={trial.failure_reason ? [trial.failure_reason] : []} empty="Not provided by backend." />
      <ListBlock title="Parameter groups" items={summarizeParams(trial)} empty="No parameter groups returned." />
      <ParamsViewer
        sections={[
          ...trialParamSections(trial),
          { title: 'Metrics JSON', value: trial.metrics },
          { title: 'Raw safe summary', value: summarizeRawTrial(trial.raw_trial) },
        ]}
      />
      <ListBlock title="Artifact paths" items={[...(state.detail?.artifact_paths ?? []), ...trial.artifact_paths]} empty="No trial artifacts returned." />
    </div>
  );
}

function ListBlock({ title, items, empty }: { title: string; items: string[]; empty: string }) {
  return (
    <div>
      <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
      {items.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--app-text-muted)]">{empty}</p>
      ) : (
        <ul className="mt-2 list-inside list-disc space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  );
}

function summarizeParams(trial: OptimizationTrial): string[] {
  return [
    ['all', trial.params],
    ['buy', trial.buy_params],
    ['sell', trial.sell_params],
    ['roi', trial.roi_params],
    ['stoploss', trial.stoploss_params],
    ['trailing', trial.trailing_params],
  ].flatMap(([label, value]) => {
    if (!value || typeof value !== 'object') {
      return [];
    }
    const count = Object.keys(value).length;
    return count === 0 ? [] : [`${label}: ${count} parameter${count === 1 ? '' : 's'}`];
  });
}

function trialParamSections(trial: OptimizationTrial) {
  return [
    { title: 'Full params', value: trial.params },
    { title: 'Buy params', value: trial.buy_params },
    { title: 'Sell params', value: trial.sell_params },
    { title: 'ROI params', value: trial.roi_params },
    { title: 'Stoploss params', value: trial.stoploss_params },
    { title: 'Trailing params', value: trial.trailing_params },
  ];
}

function summarizeRawTrial(rawTrial: JsonObject | null): JsonObject | null {
  if (!rawTrial) {
    return null;
  }
  return {
    top_level_keys: Object.keys(rawTrial),
    value_types: Object.fromEntries(
      Object.entries(rawTrial).map(([key, value]) => [
        key,
        Array.isArray(value) ? `array(${value.length})` : value === null ? 'null' : typeof value,
      ]),
    ),
  };
}

function buildArtifactEvidenceRows(state: OptimizationDetailState): ArtifactEvidenceRow[] {
  const rows: ArtifactEvidenceRow[] = [];
  const report = state.report?.report ?? null;
  const allPaths = uniqueStrings([
    ...(state.detail?.artifact_paths ?? []),
    ...(state.bestTrial?.artifact_paths ?? []),
    state.detail?.run.report_artifact_path ?? null,
    state.report?.report_artifact_path ?? null,
    ...collectStringValues(report),
  ]);

  const addRow = (label: string, keywords: string[], source: string, note: string) => {
    const path = findPath(allPaths, keywords);
    rows.push({
      key: label.toLowerCase().replace(/\s+/g, '-'),
      label,
      status: path ? 'path provided' : 'not provided',
      path,
      source,
      note,
    });
  };

  addRow('Command metadata', ['command_metadata'], 'Hyperopt artifacts', 'Command metadata path when backend report or artifact metadata exposes it.');
  addRow('Stdout artifact', ['stdout'], 'Backtest or Hyperopt artifacts', 'Stdout path presence only. The dashboard does not open large logs by default.');
  addRow('Stderr artifact', ['stderr'], 'Backtest or Hyperopt artifacts', 'Stderr path presence only. The dashboard does not open large logs by default.');
  addRow('Optimization report', ['optimization_report'], 'Optimization report endpoint', 'Optimization report artifact metadata or path.');
  addRow('Optimized params artifact', ['params', 'optimized'], 'Optimized backtest artifacts', 'Optimized parameter artifact path when returned by backend evidence.');
  addRow('Normalized result', ['normalized'], 'Parsed result artifacts', 'Normalized parsed result path when returned by backend evidence.');
  addRow('Decision report', ['decision'], 'Decision artifacts', 'Decision report path when returned by optimized validation evidence.');

  return rows;
}

function collectStringValues(value: unknown): string[] {
  if (typeof value === 'string') {
    return [value];
  }
  if (Array.isArray(value)) {
    return value.flatMap(collectStringValues);
  }
  if (value && typeof value === 'object') {
    return Object.values(value as JsonObject).flatMap(collectStringValues);
  }
  return [];
}

function uniqueStrings(values: Array<string | null | undefined>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value))));
}

function findPath(paths: string[], keywords: string[]): string | null {
  const normalizedKeywords = keywords.map((keyword) => keyword.toLowerCase());
  return paths.find((path) => {
    const normalizedPath = path.toLowerCase();
    return normalizedKeywords.every((keyword) => normalizedPath.includes(keyword));
  }) ?? null;
}

function statusLabel(status: string, resultStatus: string | null): string {
  const uiStatus = toUiStatus({ status, resultStatus });
  if (uiStatus === 'optimization_rejected') {
    return 'rejected result';
  }
  if (uiStatus === 'pipeline_completed') {
    return 'completed pipeline';
  }
  if (uiStatus === 'controlled_failure') {
    return 'controlled failure';
  }
  if (uiStatus === 'system_failed') {
    return 'failed pipeline';
  }
  return uiStatus;
}

function statusTone(
  status: string,
  resultStatus: string | null,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  const uiStatus = toUiStatus({ status, resultStatus });
  if (uiStatus === 'pipeline_completed') {
    return 'success';
  }
  if (uiStatus === 'running') {
    return 'info';
  }
  if (uiStatus === 'controlled_failure') {
    return 'warning';
  }
  if (uiStatus === 'optimization_rejected') {
    return 'optimization';
  }
  if (uiStatus === 'system_failed' || uiStatus === 'strategy_rejected') {
    return 'danger';
  }
  return 'neutral';
}

function trialTone(trial: OptimizationTrial): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  if (trial.is_best || trial.status === 'best') {
    return 'optimization';
  }
  if (trial.status === 'completed' || trial.status === 'selected_for_validation') {
    return 'success';
  }
  if (trial.status === 'rejected') {
    return 'warning';
  }
  if (trial.status === 'failed') {
    return 'danger';
  }
  if (trial.status === 'ignored') {
    return 'neutral';
  }
  return 'info';
}

function comparisonTone(indicator: 'improved' | 'worsened' | 'unchanged' | 'unavailable'): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  switch (indicator) {
    case 'improved':
      return 'success';
    case 'worsened':
      return 'danger';
    case 'unchanged':
    case 'unavailable':
      return 'neutral';
    default:
      return 'neutral';
  }
}

function numericValue(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function yesNo(value: boolean) {
  return value ? 'yes' : 'no';
}

function labelize(key: string) {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatValue(value: unknown): string | number {
  if (value == null) {
    return 'Not recorded';
  }
  if (typeof value === 'number') {
    return formatNumber(value);
  }
  return String(value);
}

function formatNumber(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'Not recorded';
  }
  return new Intl.NumberFormat(undefined, { maximumFractionDigits: 4 }).format(value);
}

function formatPercent(value: unknown): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return 'Not recorded';
  }
  return `${new Intl.NumberFormat(undefined, { maximumFractionDigits: 2 }).format(value)}%`;
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'Not recorded';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}

function formatDuration(value: number | null | undefined): string {
  if (value == null) {
    return 'Duration not recorded';
  }
  if (value < 1000) {
    return `${value} ms`;
  }
  return `${(value / 1000).toFixed(2)} s`;
}
