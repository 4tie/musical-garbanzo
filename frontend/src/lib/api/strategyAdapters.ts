import {
  StrategyReadiness,
  StrategySummary,
  UiStrategyRow,
  UiStrategyStatus,
  UiStrategyStatusTone,
} from './types';

const STATUS_META: Record<
  StrategyReadiness,
  { label: string; tone: UiStrategyStatusTone; selectableForRun: boolean }
> = {
  ready: {
    label: 'Ready',
    tone: 'success',
    selectableForRun: true,
  },
  warning: {
    label: 'Warning',
    tone: 'warning',
    selectableForRun: true,
  },
  missing_sidecar: {
    label: 'Missing sidecar',
    tone: 'warning',
    selectableForRun: false,
  },
  invalid: {
    label: 'Invalid',
    tone: 'danger',
    selectableForRun: false,
  },
  parse_error: {
    label: 'Parse error',
    tone: 'danger',
    selectableForRun: false,
  },
  unsafe: {
    label: 'Unsafe',
    tone: 'danger',
    selectableForRun: false,
  },
};

export function toStrategyStatus(readiness: StrategyReadiness): UiStrategyStatus {
  return {
    readiness,
    ...STATUS_META[readiness],
  };
}

export function isStrategySelectableForRun(strategy: Pick<StrategySummary, 'readiness'>): boolean {
  return STATUS_META[strategy.readiness].selectableForRun;
}

export function toStrategyRow(strategy: StrategySummary): UiStrategyRow {
  return {
    name: strategy.strategy_name,
    strategyFilePath: strategy.strategy_file_path,
    sidecarJsonPath: strategy.sidecar_json_path,
    hasSidecar: strategy.has_sidecar,
    readiness: strategy.readiness,
    status: toStrategyStatus(strategy.readiness),
    issueCount: strategy.issues.length,
    warningCount: strategy.warnings.length,
    sectionsPresent: strategy.params_summary.sections_present,
    timeframe: strategy.params_summary.timeframe ?? stringMetadata(strategy.metadata.timeframe),
    canShort: booleanMetadata(strategy.metadata.can_short),
    updatedAt: strategy.updated_at,
    raw: strategy,
  };
}

export function toStrategyRows(strategies: StrategySummary[]): UiStrategyRow[] {
  return strategies.map(toStrategyRow);
}

function stringMetadata(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function booleanMetadata(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}
