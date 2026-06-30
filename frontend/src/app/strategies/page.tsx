'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import DataTable, { DataTableColumn } from '@/components/DataTable';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import {
  ApiError,
  StrategyReadiness,
  UiStrategyRow,
  isStrategySelectableForRun,
  listStrategies,
  toStrategyRows,
} from '@/lib/api';

type ReadinessFilter = 'all' | StrategyReadiness;
type SidecarFilter = 'all' | 'with_sidecar' | 'missing_sidecar';

interface StrategyLibraryState {
  rows: UiStrategyRow[];
  error: ApiError | null;
  loadedAt: string | null;
}

const readinessFilters: Array<{ id: ReadinessFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'ready', label: 'Ready' },
  { id: 'warning', label: 'Warning' },
  { id: 'missing_sidecar', label: 'Missing sidecar' },
  { id: 'invalid', label: 'Invalid' },
  { id: 'parse_error', label: 'Parse error' },
  { id: 'unsafe', label: 'Unsafe' },
];

const sidecarFilters: Array<{ id: SidecarFilter; label: string }> = [
  { id: 'all', label: 'Any sidecar' },
  { id: 'with_sidecar', label: 'Has sidecar' },
  { id: 'missing_sidecar', label: 'No sidecar' },
];

const initialState: StrategyLibraryState = {
  rows: [],
  error: null,
  loadedAt: null,
};

export default function Strategies() {
  const router = useRouter();
  const [state, setState] = useState<StrategyLibraryState>(initialState);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');
  const [readinessFilter, setReadinessFilter] = useState<ReadinessFilter>('all');
  const [sidecarFilter, setSidecarFilter] = useState<SidecarFilter>('all');

  const loadStrategies = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const result = await listStrategies({ limit: 500 });
    if (result.success) {
      setState({
        rows: toStrategyRows(result.data),
        error: null,
        loadedAt: new Date().toISOString(),
      });
    } else {
      setState({
        rows: [],
        error: result.error,
        loadedAt: new Date().toISOString(),
      });
    }

    setLoading(false);
    if (markRefreshing) {
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStrategies(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadStrategies]);

  const visibleRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return state.rows.filter((row) => {
      const matchesSearch =
        !normalizedQuery ||
        [
          row.name,
          row.strategyFilePath,
          row.sidecarJsonPath ?? '',
          row.readiness,
          row.timeframe ?? '',
          row.sectionsPresent.join(' '),
        ]
          .join(' ')
          .toLowerCase()
          .includes(normalizedQuery);

      const matchesReadiness =
        readinessFilter === 'all' || row.readiness === readinessFilter;
      const matchesSidecar =
        sidecarFilter === 'all' ||
        (sidecarFilter === 'with_sidecar' && row.hasSidecar) ||
        (sidecarFilter === 'missing_sidecar' && !row.hasSidecar);

      return matchesSearch && matchesReadiness && matchesSidecar;
    });
  }, [query, readinessFilter, sidecarFilter, state.rows]);

  const openDetails = useCallback(
    (strategyName: string) => {
      router.push(`/strategies/${encodeURIComponent(strategyName)}`);
    },
    [router],
  );

  const navigateToBaseline = useCallback(
    (strategyName: string) => {
      router.push(`/baseline?strategy=${encodeURIComponent(strategyName)}`);
    },
    [router],
  );

  const navigateToOptimization = useCallback(
    (strategyName: string) => {
      router.push(`/optimization?strategy=${encodeURIComponent(strategyName)}`);
    },
    [router],
  );

  const columns = useMemo<DataTableColumn<UiStrategyRow>[]>(
    () => [
      {
        id: 'name',
        header: 'Strategy',
        sortValue: (row) => row.name,
        render: (row) => (
          <div className="min-w-48">
            <p className="font-medium text-[var(--app-text)]">{row.name}</p>
            <p className="mt-1 max-w-72 truncate font-mono text-xs text-[var(--app-text-subtle)]">
              {row.strategyFilePath}
            </p>
          </div>
        ),
      },
      {
        id: 'readiness',
        header: 'Readiness',
        sortValue: (row) => readinessRank(row.readiness),
        render: (row) => (
          <StatusBadge
            status={row.readiness}
            label={row.status.label}
            tone={readinessTone(row.readiness)}
          />
        ),
      },
      {
        id: 'sidecar',
        header: 'Sidecar',
        sortValue: (row) => Number(row.hasSidecar),
        render: (row) => (
          <div className="min-w-32">
            <StatusBadge
              status={row.hasSidecar ? 'configured' : 'missing'}
              label={row.hasSidecar ? 'Present' : 'Missing'}
              tone={row.hasSidecar ? 'success' : 'warning'}
            />
            <p className="mt-1 max-w-48 truncate font-mono text-xs text-[var(--app-text-subtle)]">
              {row.sidecarJsonPath ?? 'No sidecar JSON'}
            </p>
          </div>
        ),
      },
      {
        id: 'params',
        header: 'Params',
        sortValue: (row) => row.sectionsPresent.length,
        render: (row) =>
          row.sectionsPresent.length > 0 ? (
            <span className="text-[var(--app-text-muted)]">
              {row.sectionsPresent.join(', ')}
            </span>
          ) : (
            <span className="text-[var(--app-text-subtle)]">Not available</span>
          ),
      },
      {
        id: 'issues',
        header: 'Issues',
        sortValue: (row) => row.issueCount,
        render: (row) => issueCountLabel(row.issueCount),
      },
      {
        id: 'warnings',
        header: 'Warnings',
        sortValue: (row) => row.warningCount,
        render: (row) => warningCountLabel(row.warningCount),
      },
      {
        id: 'timeframe',
        header: 'Timeframe',
        sortValue: (row) => row.timeframe ?? '',
        render: (row) => row.timeframe ?? 'Unknown',
      },
      {
        id: 'can_short',
        header: 'Can short',
        sortValue: (row) => booleanSort(row.canShort),
        render: (row) => formatBoolean(row.canShort),
      },
      {
        id: 'updated',
        header: 'Updated',
        sortValue: (row) => timestamp(row.updatedAt),
        render: (row) => formatDateTime(row.updatedAt),
      },
      {
        id: 'actions',
        header: 'Actions',
        render: (row) => (
          <div
            className="flex flex-wrap gap-2"
            onClick={(event) => event.stopPropagation()}
          >
            <Button size="sm" variant="ghost" onClick={() => openDetails(row.name)}>
              View details
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={!isStrategySelectableForRun(row.raw)}
              onClick={() => navigateToBaseline(row.name)}
            >
              Use in Baseline
            </Button>
            <Button
              size="sm"
              variant="secondary"
              disabled={!isStrategySelectableForRun(row.raw)}
              onClick={() => navigateToOptimization(row.name)}
            >
              Use in Optimization
            </Button>
          </div>
        ),
      },
    ],
    [navigateToBaseline, navigateToOptimization, openDetails],
  );

  const noSidecarsFound = state.rows.length > 0 && state.rows.every((row) => !row.hasSidecar);

  return (
    <AppShell
      pageTitle="Strategies"
      onRefresh={() => {
        void loadStrategies(true);
      }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Strategy Library"
          description="Real local Freqtrade strategy files inspected by the backend workspace service."
          actions={
            state.loadedAt ? (
              <span className="text-xs text-[var(--app-text-subtle)]">
                Updated {formatDateTime(state.loadedAt)}
              </span>
            ) : null
          }
        />

        <div className="grid gap-3 lg:grid-cols-3">
          <SafetyNote title="Strategy readiness is not profitability." />
          <SafetyNote title="Ready means the file is structurally usable for validation." />
          <SafetyNote title="HER still requires baseline/optimization validation." />
        </div>

        {state.error && (
          <ErrorBanner title={errorTitle(state.error)}>
            {state.error.message}. No fallback or mock strategy data is shown.
          </ErrorBanner>
        )}

        {noSidecarsFound && (
          <ControlledFailureBanner title="No sidecar JSON found">
            Strategies were found, but none have matching sidecar JSON files. HER shows them as-is and does not invent params.
          </ControlledFailureBanner>
        )}

        <SectionCard
          title="Workspace strategies"
          description="Search, filter, sort, inspect readiness evidence, or pass ready strategies into safe run forms."
        >
          <div className="mb-4 grid gap-3 xl:grid-cols-[minmax(220px,1fr)_auto_auto] xl:items-center">
            <label className="min-w-0">
              <span className="sr-only">Search strategies</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search strategy, file path, readiness, timeframe, params"
                className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
              />
            </label>

            <div className="flex flex-wrap gap-2">
              {readinessFilters.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={readinessFilter === item.id ? 'primary' : 'secondary'}
                  onClick={() => setReadinessFilter(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              {sidecarFilters.map((item) => (
                <Button
                  key={item.id}
                  size="sm"
                  variant={sidecarFilter === item.id ? 'primary' : 'secondary'}
                  onClick={() => setSidecarFilter(item.id)}
                >
                  {item.label}
                </Button>
              ))}
            </div>
          </div>

          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : (
            <DataTable
              rows={visibleRows}
              columns={columns}
              getRowKey={(row) => row.name}
              onRowClick={(row) => openDetails(row.name)}
              initialSortColumn="name"
              initialSortDirection="asc"
              emptyState={
                <EmptyState
                  title={emptyTitle(state)}
                  description={emptyDescription(state, query, readinessFilter, sidecarFilter)}
                />
              }
            />
          )}
        </SectionCard>
      </div>
    </AppShell>
  );
}

function SafetyNote({ title }: { title: string }) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-4 py-3 text-sm font-medium text-[var(--app-text)]">
      {title}
    </div>
  );
}

function errorTitle(error: ApiError): string {
  const message = error.message.toLowerCase();
  if (error.kind === 'network' || error.kind === 'timeout') {
    return 'Backend unavailable';
  }
  if (message.includes('permission') || message.includes('read')) {
    return 'Strategy workspace read error';
  }
  if (message.includes('directory') || message.includes('workspace')) {
    return 'Strategy directory missing';
  }
  return 'Strategies are unavailable';
}

function emptyTitle(state: StrategyLibraryState): string {
  if (state.error) {
    return errorTitle(state.error);
  }
  return 'No strategies found';
}

function emptyDescription(
  state: StrategyLibraryState,
  query: string,
  readinessFilter: ReadinessFilter,
  sidecarFilter: SidecarFilter,
): string {
  if (state.error) {
    return 'The backend did not return a strategy list. HER does not show fake strategy entries.';
  }
  if (query.trim() || readinessFilter !== 'all' || sidecarFilter !== 'all') {
    return 'No real workspace strategies match the current filters.';
  }
  return 'The backend returned an empty strategy workspace. Add real strategy files to the configured Freqtrade strategies directory, then refresh.';
}

function readinessTone(
  readiness: StrategyReadiness,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  switch (readiness) {
    case 'ready':
      return 'success';
    case 'warning':
    case 'missing_sidecar':
      return 'warning';
    case 'invalid':
    case 'parse_error':
    case 'unsafe':
      return 'danger';
    default:
      return 'neutral';
  }
}

function readinessRank(readiness: StrategyReadiness): number {
  const ranks: Record<StrategyReadiness, number> = {
    ready: 0,
    warning: 1,
    missing_sidecar: 2,
    invalid: 3,
    parse_error: 4,
    unsafe: 5,
  };
  return ranks[readiness];
}

function issueCountLabel(count: number): string {
  return count === 0 ? 'None' : String(count);
}

function warningCountLabel(count: number): string {
  return count === 0 ? 'None' : String(count);
}

function formatBoolean(value: boolean | null): string {
  if (value === true) {
    return 'Yes';
  }
  if (value === false) {
    return 'No';
  }
  return 'Unknown';
}

function booleanSort(value: boolean | null): number {
  if (value === true) {
    return 2;
  }
  if (value === false) {
    return 1;
  }
  return 0;
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

function timestamp(value: string | null | undefined): number {
  return value ? new Date(value).getTime() : 0;
}
