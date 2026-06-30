'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import CopyButton from '@/components/CopyButton';
import DataTable, { DataTableColumn } from '@/components/DataTable';
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
  ArtifactListItem,
  BacktestCombinedResult,
  BaselineReport,
  BaselineRunDetail,
  BaselineStatusResponse,
  DecisionRecord,
  JsonObject,
  MetricSnapshot,
  PairResult,
  ResultQualityFlag,
  ResultQualityReport,
  RunRead,
  RunStageRead,
  TradeSummary,
  UiTimelineStage,
  getBacktestResults,
  getBaselineReport,
  getBaselineRunDetail,
  getBaselineStatus,
  getLatestMetrics,
  getLatestRunDecision,
  getResultQuality,
  getRun,
  getTradeSummary,
  listPairResults,
  listRunArtifacts,
  listRunStages,
  toTimelineStages,
  toUiStatus,
} from '@/lib/api';
import { startValidation } from '@/lib/api/validation';
import ValidationConfirmationDialog from '@/components/ValidationConfirmationDialog';

interface BaselineDetailClientProps {
  runId: string;
}

interface SourceError {
  source: string;
  error: ApiError;
}

interface BaselineDetailState {
  run: RunRead | null;
  detail: BaselineRunDetail | null;
  status: BaselineStatusResponse | null;
  stages: RunStageRead[];
  metrics: MetricSnapshot | null;
  pairResults: PairResult[];
  tradeSummary: TradeSummary | null;
  quality: ResultQualityReport | null;
  combinedResult: BacktestCombinedResult | null;
  decision: DecisionRecord | null;
  artifacts: ArtifactListItem[];
  report: BaselineReport | null;
  errors: SourceError[];
  loadedAt: string | null;
  validationDialogOpen: boolean;
}

interface ArtifactRow {
  id: string;
  type: string;
  label: string;
  path: string;
  description: string | null;
  createdAt: string | null;
}

const emptyState: BaselineDetailState = {
  run: null,
  detail: null,
  status: null,
  stages: [],
  metrics: null,
  pairResults: [],
  tradeSummary: null,
  quality: null,
  combinedResult: null,
  decision: null,
  artifacts: [],
  report: null,
  errors: [],
  loadedAt: null,
  validationDialogOpen: false,
};

const coreSources = new Set(['Run metadata', 'Baseline detail']);

export default function BaselineDetailClient({ runId }: BaselineDetailClientProps) {
  const router = useRouter();
  const [state, setState] = useState<BaselineDetailState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const loadBaseline = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const [
      runResult,
      detailResult,
      statusResult,
      stagesResult,
      metricsResult,
      pairResultsResult,
      tradeSummaryResult,
      qualityResult,
      combinedResult,
      decisionResult,
      artifactsResult,
      reportResult,
    ] = await Promise.all([
      getRun(runId),
      getBaselineRunDetail(runId),
      getBaselineStatus(runId),
      listRunStages(runId),
      getLatestMetrics(runId),
      listPairResults(runId),
      getTradeSummary(runId),
      getResultQuality(runId),
      getBacktestResults(runId),
      getLatestRunDecision(runId),
      listRunArtifacts(runId),
      getBaselineReport(runId),
    ]);

    const errors: SourceError[] = [];
    collectError(errors, 'Run metadata', runResult, true);
    collectError(errors, 'Baseline detail', detailResult, true);
    collectError(errors, 'Baseline status', statusResult);
    collectError(errors, 'Pipeline stages', stagesResult);
    collectError(errors, 'Latest metrics', metricsResult);
    collectError(errors, 'Pair results', pairResultsResult);
    collectError(errors, 'Trade summary', tradeSummaryResult);
    collectError(errors, 'Result quality', qualityResult);
    collectError(errors, 'Combined backtest result', combinedResult);
    collectError(errors, 'Latest decision', decisionResult);
    collectError(errors, 'Artifacts', artifactsResult);
    collectError(errors, 'Baseline report', reportResult);

    setState({
      run: runResult.success ? runResult.data : null,
      detail: detailResult.success ? detailResult.data : null,
      status: statusResult.success ? statusResult.data : null,
      stages: stagesResult.success ? stagesResult.data : [],
      metrics: metricsResult.success ? metricsResult.data : null,
      pairResults: pairResultsResult.success ? pairResultsResult.data : [],
      tradeSummary: tradeSummaryResult.success ? tradeSummaryResult.data : null,
      quality: qualityResult.success ? qualityResult.data : null,
      combinedResult: combinedResult.success ? combinedResult.data : null,
      decision: decisionResult.success ? decisionResult.data : null,
      artifacts: artifactsResult.success ? artifactsResult.data : [],
      report: reportResult.success ? reportResult.data : null,
      errors,
      loadedAt: new Date().toISOString(),
      validationDialogOpen: false,
    });
    setLoading(false);
    if (markRefreshing) {
      setRefreshing(false);
    }
  }, [runId]);

  const handleRunValidation = useCallback(async () => {
    if (!state.run) {
      return;
    }

    const request = {
      source_type: 'baseline_run' as const,
      source_run_id: runId,
      strategy_name: state.run.strategy_id || '',
      pairs: state.run.pairs || [],
      timeframe: state.run.timeframe || '',
      exchange: state.run.exchange || 'binance',
      risk_profile: state.run.risk_profile || 'balanced',
      timerange: state.run.timerange || '',
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
  }, [state.run, runId, router]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadBaseline(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadBaseline]);

  const summary = useMemo(() => buildSummary(state, runId), [runId, state]);
  const metricCards = useMemo(() => buildMetricCards(state), [state]);
  const decision = useMemo(() => buildDecisionSummary(state), [state]);
  const timeline = useMemo(() => buildTimeline(state), [state]);
  const qualityFlags = useMemo(() => buildQualityFlags(state), [state]);
  const artifactRows = useMemo(() => buildArtifactRows(state), [state]);
  const blockingErrors = state.errors.filter((item) => coreSources.has(item.source));
  const partialErrors = state.errors.filter((item) => !coreSources.has(item.source));

  const pairColumns = useMemo<DataTableColumn<PairResult>[]>(
    () => [
      { id: 'pair', header: 'Pair', sortValue: (row) => row.pair, render: (row) => row.pair },
      { id: 'trades', header: 'Trades', sortValue: (row) => row.trade_count ?? -1, render: (row) => formatValue(row.trade_count) },
      { id: 'profit', header: 'Profit', sortValue: (row) => row.net_profit ?? -Infinity, render: (row) => formatNumber(row.net_profit) },
      { id: 'profit_factor', header: 'Profit factor', sortValue: (row) => row.profit_factor ?? -Infinity, render: (row) => formatNumber(row.profit_factor) },
      { id: 'drawdown', header: 'Drawdown', sortValue: (row) => row.max_drawdown ?? Infinity, render: (row) => formatPercent(row.max_drawdown) },
      { id: 'win_rate', header: 'Win rate', sortValue: (row) => row.win_rate ?? -Infinity, render: (row) => formatPercent(row.win_rate) },
    ],
    [],
  );

  const artifactColumns = useMemo<DataTableColumn<ArtifactRow>[]>(
    () => [
      { id: 'type', header: 'Type', sortValue: (row) => row.type, render: (row) => <StatusBadge status={row.type} tone="neutral" /> },
      { id: 'label', header: 'Artifact', sortValue: (row) => row.label, render: (row) => row.label },
      { id: 'path', header: 'Location', sortValue: (row) => row.path, render: (row) => <span className="font-mono text-xs">{row.path}</span> },
      { id: 'description', header: 'Description', sortValue: (row) => row.description ?? '', render: (row) => row.description ?? 'Metadata only' },
      { id: 'created', header: 'Created', sortValue: (row) => timestamp(row.createdAt), render: (row) => formatDateTime(row.createdAt) },
    ],
    [],
  );

  return (
    <AppShell
      pageTitle="Baseline Detail"
      onRefresh={() => {
        void loadBaseline(true);
      }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Baseline run detail"
          description="Read-only evidence view for a baseline evaluation run. Every value on this page comes from backend APIs."
          actions={
            <>
              {state.loadedAt && (
                <span className="text-xs text-[var(--app-text-subtle)]">
                  Updated {formatDateTime(state.loadedAt)}
                </span>
              )}
              {state.run && state.run.strategy_id && state.run.pairs && state.run.timeframe && (
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
          <ErrorBanner title="Baseline run could not be loaded">
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
          <ControlledFailureBanner title="Some baseline evidence is unavailable">
            <ul className="list-inside list-disc">
              {partialErrors.map((item) => (
                <li key={`${item.source}-${item.error.kind}`}>
                  {item.source}: {item.error.message}
                </li>
              ))}
            </ul>
          </ControlledFailureBanner>
        )}

        <ControlledFailureBanner title="Pipeline completed, strategy rejected">
          This is not a system failure. A completed pipeline means the validation workflow reached its end. It does not mean the strategy is approved, profitable, exportable, or live-ready. A rejected strategy is a validation result, not a system failure.
        </ControlledFailureBanner>

        <SectionCard title="Header summary" description="Run identity, current state, and recorded setup metadata.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <SummaryField label="Run ID" value={summary.runId} action={<CopyButton value={summary.runId} label="Copy ID" />} mono />
              <SummaryField label="Strategy" value={summary.strategyName} />
              <SummaryField label="Pairs" value={summary.pairs} />
              <SummaryField label="Timeframe" value={summary.timeframe} />
              <SummaryField label="Status" value={<StatusBadge status={summary.status} label={statusLabel(summary.status, summary.classification)} tone={statusTone(summary.status, summary.classification)} />} />
              <SummaryField label="Classification" value={summary.classification} />
              <SummaryField label="Created" value={formatDateTime(summary.createdAt)} />
              <SummaryField label="Updated" value={formatDateTime(summary.updatedAt)} />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Metrics" description="Latest persisted baseline metrics. Missing cards are not inferred.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : metricCards.length === 0 ? (
            <EmptyState title="No metrics found" description="No persisted baseline metric snapshot was returned for this run." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              {metricCards.map((card) => (
                <MetricCard
                  key={card.key}
                  label={card.label}
                  value={card.value}
                  helper={card.helper}
                  tone={card.tone}
                />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Decision panel" description="Persisted validation decision details when available.">
          {loading ? (
            <LoadingSkeleton lines={5} />
          ) : !decision.hasDecision ? (
            <EmptyState title="No decision found" description="No persisted decision payload was returned for this baseline run." />
          ) : (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-3">
                <SummaryField label="Classification" value={decision.classification} />
                <SummaryField label="Confidence score" value={formatNumber(decision.confidenceScore)} />
                <SummaryField label="Policy" value={decision.policyName} />
              </div>
              <ListBlock title="Blocking failures" items={decision.blockingFailures} empty="No blocking failures returned." />
              <ListBlock title="Warnings" items={decision.warnings} empty="No decision warnings returned." />
              <ListBlock title="Reasons" items={decision.reasons} empty="No decision reasons returned." />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Pipeline timeline" description="Only stages present in backend API data are shown.">
          {loading ? (
            <LoadingSkeleton lines={8} />
          ) : timeline.length === 0 ? (
            <EmptyState title="No stage data found" description="The backend did not return baseline stage records for this run." />
          ) : (
            <div className="space-y-3">
              {timeline.map((stage) => (
                <TimelineItem key={stage.id} stage={stage} />
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Pair results" description="Per-pair results from persisted parser output.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <DataTable
              rows={state.pairResults}
              columns={pairColumns}
              getRowKey={(row) => row.id}
              initialSortColumn="profit"
              initialSortDirection="desc"
              emptyState={<EmptyState title="No pair results found" description="No per-pair result rows were returned for this baseline run." />}
            />
          )}
        </SectionCard>

        <SectionCard title="Trade summary" description="Aggregate trade outcome data when parser evidence exists.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : !state.tradeSummary ? (
            <EmptyState title="No trade summary found" description="No persisted trade summary was returned for this baseline run." />
          ) : (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
              <MetricCard label="Wins" value={state.tradeSummary.wins} />
              <MetricCard label="Losses" value={state.tradeSummary.losses} />
              <MetricCard label="Draws" value={state.tradeSummary.draws} />
              <MetricCard label="Average duration" value={state.tradeSummary.avg_duration} />
              <MetricCard label="Best pair" value={state.tradeSummary.best_pair} />
              <MetricCard label="Worst pair" value={state.tradeSummary.worst_pair} />
              <MetricCard label="Total trades" value={state.tradeSummary.total_trades} />
            </div>
          )}
        </SectionCard>

        <SectionCard title="Quality flags" description="Parser and result-quality flags. These explain evidence quality and risk; they are not fabricated.">
          {loading ? (
            <LoadingSkeleton lines={4} />
          ) : qualityFlags.length === 0 ? (
            <EmptyState title="No quality flags found" description="The backend did not return negative expectancy, high drawdown, single-pair dependency, or parse warning flags for this run." />
          ) : (
            <div className="space-y-3">
              {qualityFlags.map((flag, index) => (
                <div key={`${flag.code}-${flag.message}-${index}`} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <StatusBadge status={flag.severity} tone={qualityTone(flag.severity)} />
                    <span className="font-mono text-xs text-[var(--app-text-muted)]">{flag.code}</span>
                  </div>
                  <p className="mt-2 text-sm leading-6 text-[var(--app-text)]">{flag.message}</p>
                </div>
              ))}
            </div>
          )}
        </SectionCard>

        <SectionCard title="Artifacts and report metadata" description="Artifact locations and metadata only. Huge raw logs are not loaded by default.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <DataTable
              rows={artifactRows}
              columns={artifactColumns}
              getRowKey={(row) => row.id}
              initialSortColumn="created"
              initialSortDirection="desc"
              emptyState={<EmptyState title="No artifacts found" description="No normalized result, decision result, report, or raw artifact metadata was returned for this run." />}
            />
          )}
        </SectionCard>

        <ValidationConfirmationDialog
          open={state.validationDialogOpen}
          strategyName={state.run?.strategy_id || ''}
          sourceType="baseline_run"
          sourceRunId={runId}
          pairs={state.run?.pairs || []}
          timeframe={state.run?.timeframe || ''}
          riskProfile={state.run?.risk_profile || 'balanced'}
          onConfirm={handleRunValidation}
          onCancel={() => setState((prev) => ({ ...prev, validationDialogOpen: false }))}
        />
      </div>
    </AppShell>
  );
}

function collectError<T>(
  errors: SourceError[],
  source: string,
  result: ApiResult<T>,
  required = false,
) {
  if (result.success) {
    return;
  }
  if (!required && result.error.kind === 'not_found') {
    return;
  }
  errors.push({ source, error: result.error });
}

function buildSummary(state: BaselineDetailState, runId: string) {
  const run = state.run;
  const detail = state.detail;
  const status = state.status;
  return {
    runId,
    strategyName: run?.name || run?.strategy_id || 'Not recorded',
    pairs: run?.pairs?.length ? run.pairs.join(', ') : 'Not recorded',
    timeframe: run?.timeframe || 'Not recorded',
    status: detail?.status || status?.status || run?.status || 'unknown',
    classification: detail?.classification || status?.classification || run?.classification || 'Not recorded',
    createdAt: run?.created_at || detail?.created_at || null,
    updatedAt: run?.updated_at || detail?.updated_at || null,
  };
}

function buildMetricCards(state: BaselineDetailState) {
  const source = normalizeMetricSource(state.metrics ?? state.detail?.metrics ?? state.status?.metrics ?? state.combinedResult?.latest_metrics);
  const definitions = [
    { key: 'profit_factor', label: 'Profit factor', helper: 'Higher than 1.0 is generally better.' },
    { key: 'expectancy', label: 'Expectancy', helper: 'Average expected outcome per trade.' },
    { key: 'max_drawdown', label: 'Max drawdown', helper: 'Lower drawdown is better.', percent: true },
    { key: 'trade_count', label: 'Trade count', helper: 'Persisted number of parsed trades.' },
    { key: 'win_rate', label: 'Win rate', helper: 'Percentage of winning trades.', percent: true },
    { key: 'net_profit', label: 'Net profit', helper: 'Net profit from parsed result evidence.' },
    { key: 'sharpe', label: 'Sharpe', helper: 'Only shown if returned by backend.' },
    { key: 'calmar', label: 'Calmar', helper: 'Only shown if returned by backend.' },
  ];

  return definitions.flatMap((definition) => {
    const value = source[definition.key];
    if (value == null) {
      return [];
    }
    const numeric = typeof value === 'number' ? value : Number(value);
    return [
      {
        key: definition.key,
        label: definition.label,
        value: definition.percent ? formatPercent(value) : formatValue(value),
        helper: definition.helper,
        tone: metricTone(definition.key, Number.isFinite(numeric) ? numeric : null),
      },
    ];
  });
}

function normalizeMetricSource(source: MetricSnapshot | JsonObject | null | undefined): JsonObject {
  if (!source) {
    return {};
  }
  const raw = 'raw_json' in source && source.raw_json ? source.raw_json : {};
  return {
    ...(raw as JsonObject),
    ...source,
  };
}

function buildDecisionSummary(state: BaselineDetailState) {
  const detailDecision = state.detail?.decision ?? {};
  const statusDecision = state.status?.decision ?? {};
  const latestDecision = state.decision ?? {};
  const merged = {
    ...detailDecision,
    ...statusDecision,
    ...latestDecision,
  };
  const classification = stringValue(merged.classification) ?? state.detail?.classification ?? state.status?.classification ?? state.run?.classification ?? null;
  const confidenceScore = numericValue(merged.confidence_score) ?? state.detail?.confidence_score ?? null;
  const warnings = stringList(merged.warnings);
  const blockingFailures = stringList(merged.blocking_failures);
  const reasons = reasonList(merged.reasons);

  return {
    hasDecision: Boolean(classification || confidenceScore != null || warnings.length || blockingFailures.length || reasons.length),
    classification: classification ?? 'Not recorded',
    confidenceScore,
    policyName: stringValue(merged.policy_name) ?? 'Not recorded',
    warnings,
    blockingFailures,
    reasons,
  };
}

function buildTimeline(state: BaselineDetailState): UiTimelineStage[] {
  if (state.stages.length > 0) {
    return toTimelineStages(state.stages);
  }
  if (state.status?.stage_results?.length) {
    return toTimelineStages(state.status.stage_results);
  }
  if (state.detail?.stages?.length) {
    return toTimelineStages(state.detail.stages);
  }
  return [];
}

function buildQualityFlags(state: BaselineDetailState): ResultQualityFlag[] {
  const flags = state.quality?.flags ?? state.combinedResult?.quality_report?.flags ?? [];
  const warnings = [
    ...(state.quality?.warnings ?? []),
    ...(state.combinedResult?.warnings ?? []),
    ...(state.detail?.warnings ?? []),
    ...(state.status?.warnings ?? []),
  ];
  const errors = [
    ...(state.quality?.errors ?? []),
    ...(state.detail?.errors ?? []),
    ...(state.status?.errors ?? []),
  ];

  return [
    ...flags,
    ...warnings.map((message) => ({
      code: inferQualityCode(message),
      severity: 'warning' as const,
      message,
    })),
    ...errors.map((message) => ({
      code: 'parse_error',
      severity: 'error' as const,
      message,
    })),
  ];
}

function buildArtifactRows(state: BaselineDetailState): ArtifactRow[] {
  const rows = new Map<string, ArtifactRow>();
  for (const artifact of state.artifacts) {
    rows.set(`artifact-${artifact.id}`, {
      id: `artifact-${artifact.id}`,
      type: artifact.artifact_type,
      label: artifact.file_path.split('/').at(-1) || artifact.file_path,
      path: artifact.file_path,
      description: artifact.description,
      createdAt: artifact.created_at,
    });
  }

  for (const path of state.detail?.artifacts ?? []) {
    rows.set(`path-${path}`, {
      id: `path-${path}`,
      type: inferArtifactType(path),
      label: path.split('/').at(-1) || path,
      path,
      description: 'Raw artifact location from baseline detail',
      createdAt: null,
    });
  }

  if (state.combinedResult?.normalized_result_path) {
    const path = state.combinedResult.normalized_result_path;
    rows.set(`normalized-${path}`, {
      id: `normalized-${path}`,
      type: 'normalized_result',
      label: path.split('/').at(-1) || path,
      path,
      description: 'Normalized parsed backtest result',
      createdAt: null,
    });
  }

  const decisionPath = extractDecisionArtifactPath(state.decision);
  if (decisionPath) {
    rows.set(`decision-${decisionPath}`, {
      id: `decision-${decisionPath}`,
      type: 'decision_result',
      label: decisionPath.split('/').at(-1) || decisionPath,
      path: decisionPath,
      description: 'Persisted decision result artifact',
      createdAt: null,
    });
  }

  if (state.report) {
    rows.set(`report-${state.report.artifact_id}`, {
      id: `report-${state.report.artifact_id}`,
      type: state.report.artifact_type || 'report',
      label: state.report.file_path.split('/').at(-1) || state.report.file_path,
      path: state.report.file_path,
      description: state.report.description,
      createdAt: state.report.created_at,
    });
  }

  return Array.from(rows.values());
}

function SummaryField({
  label,
  value,
  action,
  mono = false,
}: {
  label: string;
  value: React.ReactNode;
  action?: React.ReactNode;
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

function TimelineItem({ stage }: { stage: UiTimelineStage }) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <StatusBadge status={stage.status} label={stage.status} tone={timelineTone(stage.uiStatus)} />
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
      {(stage.warnings.length > 0 || stage.errors.length > 0) && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          <ListBlock title="Warnings" items={stage.warnings} empty="No warnings." />
          <ListBlock title="Errors" items={stage.errors} empty="No errors." />
        </div>
      )}
    </div>
  );
}

function statusLabel(status: string, classification: string): string {
  const uiStatus = toUiStatus({
    status,
    classification: classification === 'Not recorded' ? null : classification,
  });
  if (uiStatus === 'pipeline_completed') {
    return 'completed pipeline';
  }
  if (uiStatus === 'strategy_rejected') {
    return 'rejected strategy';
  }
  if (uiStatus === 'controlled_failure') {
    return 'controlled failure';
  }
  if (uiStatus === 'system_failed') {
    return 'system failure';
  }
  return uiStatus;
}

function statusTone(
  status: string,
  classification: string,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  return timelineTone(
    toUiStatus({
      status,
      classification: classification === 'Not recorded' ? null : classification,
    }),
  );
}

function timelineTone(
  status: string,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  if (status === 'pipeline_completed') {
    return 'success';
  }
  if (status === 'running') {
    return 'info';
  }
  if (status === 'controlled_failure') {
    return 'warning';
  }
  if (status === 'system_failed' || status === 'strategy_rejected') {
    return 'danger';
  }
  return 'neutral';
}

function metricTone(key: string, value: number | null): 'neutral' | 'good' | 'warning' | 'danger' {
  if (value == null) {
    return 'neutral';
  }
  if (key === 'max_drawdown') {
    return value > 35 ? 'danger' : value > 20 ? 'warning' : 'good';
  }
  if (key === 'profit_factor') {
    return value >= 1.2 ? 'good' : value < 1 ? 'danger' : 'neutral';
  }
  if (key === 'expectancy' || key === 'net_profit' || key === 'sharpe' || key === 'calmar') {
    return value > 0 ? 'good' : value < 0 ? 'danger' : 'neutral';
  }
  return 'neutral';
}

function qualityTone(severity: string): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  if (severity === 'critical' || severity === 'error') {
    return 'danger';
  }
  if (severity === 'warning') {
    return 'warning';
  }
  if (severity === 'info') {
    return 'info';
  }
  return 'neutral';
}

function reasonList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.map((item) => {
    if (typeof item === 'string') {
      return item;
    }
    if (item && typeof item === 'object') {
      const record = item as JsonObject;
      return [record.code, record.message].filter(Boolean).join(': ') || JSON.stringify(record);
    }
    return String(item);
  });
}

function stringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value.flatMap((item) => (typeof item === 'string' ? [item] : [JSON.stringify(item)]));
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function numericValue(value: unknown): number | null {
  return typeof value === 'number' ? value : null;
}

function inferQualityCode(message: string): string {
  const normalized = message.toLowerCase();
  if (normalized.includes('negative') && normalized.includes('expectancy')) {
    return 'negative_expectancy';
  }
  if (normalized.includes('drawdown')) {
    return 'high_drawdown';
  }
  if (normalized.includes('single') && normalized.includes('pair')) {
    return 'single_pair_dependency';
  }
  return 'parse_warning';
}

function inferArtifactType(path: string): string {
  if (path.toLowerCase().includes('decision')) {
    return 'decision_result';
  }
  if (path.toLowerCase().includes('normalized')) {
    return 'normalized_result';
  }
  if (path.toLowerCase().includes('report')) {
    return 'report';
  }
  return path.split('.').at(-1) || 'artifact';
}

function extractDecisionArtifactPath(decision: DecisionRecord | null): string | null {
  if (!decision) {
    return null;
  }
  const direct = decision.decision_report_path;
  if (typeof direct === 'string') {
    return direct;
  }
  const evidence = decision.evidence;
  if (evidence && typeof evidence === 'object' && 'normalized_result_artifact_path' in evidence) {
    const path = (evidence as JsonObject).normalized_result_artifact_path;
    return typeof path === 'string' ? path : null;
  }
  return null;
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

function timestamp(value: string | null | undefined): number {
  return value ? new Date(value).getTime() : 0;
}
