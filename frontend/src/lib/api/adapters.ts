import {
  ArtifactListItem,
  BaselineRunDetail,
  BaselineStageResult,
  JsonObject,
  MetricSnapshot,
  OptimizationComparison,
  OptimizationRunDetail,
  OptimizationRunListItem,
  OptimizationTrial,
  OptimizationTrialDetail,
  RunListItem,
  RunStageRead,
  UiArtifactLink,
  UiComparisonRow,
  UiMetricCard,
  UiRunListItem,
  UiStatus,
  UiTimelineStage,
  UiTrialRow,
  UnifiedRunRow,
} from './types';

const REJECTED_CLASSIFICATIONS = new Set(['rejected', 'invalid', 'unsafe', 'not_accepted']);
const OPTIMIZATION_REJECTED_STATUSES = new Set([
  'optimization_rejected',
  'not_improved',
  'overfit_suspected',
  'invalid_optimization',
]);

export function toUiStatus(input: {
  status?: string | null;
  classification?: string | null;
  resultStatus?: string | null;
  failureReason?: string | null;
}): UiStatus {
  const status = normalize(input.status);
  const classification = normalize(input.classification);
  const resultStatus = normalize(input.resultStatus);

  if (resultStatus === 'optimization_rejected') {
    return 'optimization_rejected';
  }

  if (resultStatus && OPTIMIZATION_REJECTED_STATUSES.has(resultStatus)) {
    return 'strategy_rejected';
  }

  if (status === 'failed_controlled' || status === 'confirmation_required') {
    return 'controlled_failure';
  }

  if (status === 'failed' || status === 'system_failed' || input.failureReason) {
    return 'system_failed';
  }

  if (status === 'running') {
    return 'running';
  }

  if (status === 'created' || status === 'pending') {
    return 'pending';
  }

  if (classification && REJECTED_CLASSIFICATIONS.has(classification)) {
    return 'strategy_rejected';
  }

  return 'pipeline_completed';
}

export function toRunListItem(run: RunListItem): UiRunListItem {
  return {
    id: run.id,
    label: run.name || run.id,
    mode: run.mode,
    status: run.status,
    uiStatus: toUiStatus({
      status: run.status,
      classification: run.classification,
    }),
    classification: run.classification,
    strategyId: run.strategy_id,
    parentRunId: run.parent_run_id,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    startedAt: run.started_at,
    completedAt: run.completed_at,
  };
}

export function toBaselineDetail(detail: BaselineRunDetail) {
  return {
    id: detail.run_id,
    status: detail.status,
    uiStatus: toUiStatus({
      status: detail.status,
      classification: detail.classification,
    }),
    classification: detail.classification,
    confidenceScore: detail.confidence_score ?? null,
    stages: toTimelineStages(detail.stages),
    metrics: detail.metrics,
    metricCards: toMetricCards(detail.metrics),
    decision: detail.decision,
    artifacts: detail.artifacts.map((path) => toPathArtifact(path, detail.run_id)),
    warnings: detail.warnings,
    errors: detail.errors,
  };
}

export function toOptimizationDetail(detail: OptimizationRunDetail) {
  return {
    id: detail.run.id,
    strategyName: detail.run.strategy_name,
    status: detail.run.status,
    resultStatus: detail.run.result_status,
    uiStatus: toUiStatus({
      status: detail.run.status,
      resultStatus: detail.run.result_status,
    }),
    baselineRunId: detail.run.baseline_run_id,
    optimizedRunId: detail.run.optimized_run_id,
    bestTrial: detail.best_trial ? toTrialRow(detail.best_trial) : null,
    comparisonRows: detail.comparison ? toComparisonRows(detail.comparison) : [],
    stages: toTimelineStages(detail.stages),
    artifacts: detail.artifact_paths.map((path) => toPathArtifact(path, detail.run.id)),
    raw: detail,
  };
}

export function toTrialRow(trial: OptimizationTrial): UiTrialRow {
  return {
    id: trial.id,
    trialNumber: trial.trial_number,
    status: trial.status,
    uiStatus: toUiStatus({
      status: trial.status,
      failureReason: trial.failure_reason,
      resultStatus: trial.rejection_reason ? 'not_improved' : null,
    }),
    isBest: trial.is_best,
    isSelectedForValidation: trial.is_selected_for_validation,
    lossScore: trial.loss_score,
    profitTotal: trial.profit_total,
    profitFactor: trial.profit_factor,
    expectancy: trial.expectancy,
    maxDrawdown: trial.max_drawdown,
    tradeCount: trial.trade_count,
    winRate: trial.win_rate,
    rejectionReason: trial.rejection_reason,
    failureReason: trial.failure_reason,
    createdAt: trial.created_at,
  };
}

export function toTrialDetail(detail: OptimizationTrialDetail) {
  return {
    row: toTrialRow(detail.trial),
    params: {
      all: detail.trial.params,
      buy: detail.trial.buy_params,
      sell: detail.trial.sell_params,
      roi: detail.trial.roi_params,
      stoploss: detail.trial.stoploss_params,
      trailing: detail.trial.trailing_params,
    },
    metrics: detail.trial.metrics,
    rawTrial: detail.trial.raw_trial,
    artifacts: [
      ...detail.artifact_paths.map((path) => toPathArtifact(path, detail.trial.optimization_run_id)),
      ...detail.trial.artifact_paths.map((path) => toPathArtifact(path, detail.trial.optimization_run_id)),
    ],
  };
}

export function toMetricCard(key: string, value: unknown, source?: string): UiMetricCard {
  const numeric = typeof value === 'number' ? value : null;
  return {
    key,
    label: labelize(key),
    value: typeof value === 'string' || typeof value === 'number' ? value : null,
    unit: metricUnit(key),
    tone: metricTone(key, numeric),
    source,
  };
}

export function toMetricCards(metrics: MetricSnapshot | JsonObject | null | undefined): UiMetricCard[] {
  if (!metrics) {
    return [];
  }

  return [
    'net_profit',
    'profit_total',
    'profit_factor',
    'expectancy',
    'max_drawdown',
    'win_rate',
    'trade_count',
    'sharpe',
    'calmar',
  ].flatMap((key) => {
    const value = (metrics as JsonObject)[key];
    return value === undefined || value === null ? [] : [toMetricCard(key, value, 'backend')];
  });
}

export function toComparisonRows(comparison: OptimizationComparison): UiComparisonRow[] {
  const rows: UiComparisonRow[] = [
    {
      metric: 'profit_factor',
      baseline: comparison.baseline_metrics?.profit_factor ?? null,
      optimized: comparison.optimized_metrics?.profit_factor ?? null,
      delta: comparison.delta_profit_factor,
      tone: deltaTone(comparison.delta_profit_factor, true),
    },
    {
      metric: 'expectancy',
      baseline: comparison.baseline_metrics?.expectancy ?? null,
      optimized: comparison.optimized_metrics?.expectancy ?? null,
      delta: comparison.delta_expectancy,
      tone: deltaTone(comparison.delta_expectancy, true),
    },
    {
      metric: 'max_drawdown',
      baseline: comparison.baseline_metrics?.max_drawdown ?? null,
      optimized: comparison.optimized_metrics?.max_drawdown ?? null,
      delta: comparison.delta_drawdown,
      tone: deltaTone(comparison.delta_drawdown, false),
    },
    {
      metric: 'trade_count',
      baseline: comparison.baseline_metrics?.trade_count ?? null,
      optimized: comparison.optimized_metrics?.trade_count ?? null,
      delta: comparison.delta_trade_count,
      tone: 'neutral',
    },
  ];

  return rows;
}

export function toTimelineStages(stages: Array<RunStageRead | BaselineStageResult>): UiTimelineStage[] {
  return stages
    .map((stage, index) => normalizeStage(stage, index))
    .sort((left, right) => left.order - right.order);
}

export function toArtifactLinks(artifacts: ArtifactListItem[]): UiArtifactLink[] {
  return artifacts.map((artifact) => ({
    id: artifact.id,
    label: artifact.file_path.split('/').at(-1) || artifact.file_path,
    type: artifact.artifact_type,
    path: artifact.file_path,
    description: artifact.description,
    createdAt: artifact.created_at,
    runId: artifact.run_id,
    strategyId: artifact.strategy_id,
  }));
}

export function toUnifiedBaselineRunRow(run: RunListItem): UnifiedRunRow {
  const uiStatus = toUiStatus({
    status: run.status,
    classification: run.classification,
  });

  const row: UnifiedRunRow = {
    id: run.id,
    type: 'baseline',
    detailHref: `/baseline/${encodeURIComponent(run.id)}`,
    strategyName: run.name || run.strategy_id,
    pairs: [],
    timeframe: null,
    status: run.status,
    uiStatus,
    classification: run.classification,
    resultStatus: null,
    trialsCount: null,
    bestTrialId: null,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    searchText: '',
  };

  return {
    ...row,
    searchText: buildUnifiedRunSearchText(row),
  };
}

export function toUnifiedOptimizationRunRow(run: OptimizationRunListItem): UnifiedRunRow {
  const uiStatus = toUiStatus({
    status: run.status,
    resultStatus: run.result_status,
  });

  const row: UnifiedRunRow = {
    id: run.id,
    type: 'optimization',
    detailHref: `/optimization/${encodeURIComponent(run.id)}`,
    strategyName: run.strategy_name,
    pairs: run.pairs,
    timeframe: run.timeframe,
    status: run.status,
    uiStatus,
    classification: null,
    resultStatus: run.result_status,
    trialsCount: run.epochs_completed,
    bestTrialId: run.best_trial_id,
    createdAt: run.created_at,
    updatedAt: run.updated_at,
    searchText: '',
  };

  return {
    ...row,
    searchText: buildUnifiedRunSearchText(row),
  };
}

export function mergeUnifiedRunRows(
  baselineRuns: RunListItem[],
  optimizationRuns: OptimizationRunListItem[],
): UnifiedRunRow[] {
  return [
    ...baselineRuns.map(toUnifiedBaselineRunRow),
    ...optimizationRuns.map(toUnifiedOptimizationRunRow),
  ].sort((left, right) => compareTimestampDesc(left.createdAt, right.createdAt));
}

function buildUnifiedRunSearchText(row: UnifiedRunRow): string {
  return [
    row.id,
    row.type,
    row.strategyName,
    row.pairs.join(' '),
    row.timeframe,
    row.status,
    row.classification,
    row.resultStatus,
    row.bestTrialId,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
}

function compareTimestampDesc(left: string | null | undefined, right: string | null | undefined): number {
  return new Date(right ?? 0).getTime() - new Date(left ?? 0).getTime();
}

function normalizeStage(stage: RunStageRead | BaselineStageResult, index: number): UiTimelineStage {
  if ('stage_key' in stage) {
    return {
      id: stage.id,
      key: stage.stage_key,
      name: stage.stage_name,
      order: stage.order_index,
      status: stage.status,
      uiStatus: toUiStatus({ status: stage.status, failureReason: stringifyMaybe(stage.error) }),
      startedAt: stage.started_at,
      completedAt: stage.completed_at,
      durationMs: stage.duration_ms,
      message: stage.logs_summary,
      errorCode: extractErrorCode(stage.error),
      warnings: [],
      errors: stage.error ? [stringifyMaybe(stage.error)] : [],
      details: stage.output ?? stage.error ?? stage.input,
    };
  }

  return {
    id: `${stage.stage_name}-${index}`,
    key: stage.stage_name,
    name: stage.stage_name,
    order: index,
    status: stage.status,
    uiStatus: toUiStatus({ status: stage.status }),
    startedAt: stage.started_at ?? null,
    completedAt: stage.completed_at ?? null,
    durationMs: stage.duration_seconds == null ? null : Math.round(stage.duration_seconds * 1000),
    message: stage.message ?? null,
    errorCode: stage.error_code ?? null,
    warnings: stage.warnings ?? [],
    errors: stage.errors ?? [],
    details: stage.details ?? {},
  };
}

function toPathArtifact(path: string, runId: string): UiArtifactLink {
  return {
    id: path,
    label: path.split('/').at(-1) || path,
    type: inferArtifactType(path),
    path,
    description: null,
    createdAt: null,
    runId,
  };
}

function inferArtifactType(path: string): string {
  if (path.endsWith('.json')) {
    return 'json';
  }
  if (path.endsWith('.log')) {
    return 'log';
  }
  if (path.endsWith('.md')) {
    return 'report';
  }
  return 'artifact';
}

function normalize(value: string | null | undefined): string | null {
  return value?.trim().toLowerCase() || null;
}

function labelize(key: string): string {
  return key.replace(/_/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function metricUnit(key: string): string | undefined {
  if (key.includes('rate') || key.includes('drawdown')) {
    return '%';
  }
  if (key.includes('trade_count')) {
    return 'trades';
  }
  return undefined;
}

function metricTone(
  key: string,
  value: number | null,
): 'neutral' | 'good' | 'warning' | 'danger' {
  if (value == null) {
    return 'neutral';
  }
  if (key.includes('drawdown')) {
    return value > 20 ? 'danger' : value > 10 ? 'warning' : 'good';
  }
  if (key.includes('profit') || key.includes('expectancy') || key.includes('sharpe')) {
    return value > 0 ? 'good' : value < 0 ? 'danger' : 'neutral';
  }
  return 'neutral';
}

function deltaTone(
  delta: number | null,
  higherIsBetter: boolean,
): 'neutral' | 'good' | 'warning' | 'danger' {
  if (delta == null || delta === 0) {
    return 'neutral';
  }
  const improved = higherIsBetter ? delta > 0 : delta < 0;
  return improved ? 'good' : 'danger';
}

function extractErrorCode(value: unknown): string | null {
  if (typeof value === 'object' && value !== null && 'error_code' in value) {
    const code = (value as { error_code?: unknown }).error_code;
    return typeof code === 'string' ? code : null;
  }
  return null;
}

function stringifyMaybe(value: unknown): string {
  if (typeof value === 'string') {
    return value;
  }
  if (value == null) {
    return '';
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
}
