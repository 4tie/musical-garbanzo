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
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import {
  ApiError,
  UnifiedRunRow,
  listBaselineRuns,
  listOptimizationRuns,
  mergeUnifiedRunRows,
} from '@/lib/api';

type RunFilter =
  | 'all'
  | 'baseline'
  | 'optimization'
  | 'completed'
  | 'failed'
  | 'rejected'
  | 'controlled_failure';

interface RunsState {
  rows: UnifiedRunRow[];
  errors: SourceError[];
  loadedAt: string | null;
}

interface SourceError {
  source: string;
  error: ApiError;
}

const EMPTY_COPY = 'No runs found. This dashboard is read-only and does not start pipelines yet.';

const filters: Array<{ id: RunFilter; label: string }> = [
  { id: 'all', label: 'All' },
  { id: 'baseline', label: 'Baseline' },
  { id: 'optimization', label: 'Optimization' },
  { id: 'completed', label: 'Completed' },
  { id: 'failed', label: 'Failed' },
  { id: 'rejected', label: 'Rejected' },
  { id: 'controlled_failure', label: 'Controlled failure' },
];

const initialState: RunsState = {
  rows: [],
  errors: [],
  loadedAt: null,
};

export default function Runs() {
  const router = useRouter();
  const [state, setState] = useState<RunsState>(initialState);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState<RunFilter>('all');

  const loadRuns = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const [baselineResult, optimizationResult] = await Promise.all([
      listBaselineRuns({ limit: 500 }),
      listOptimizationRuns({ limit: 500 }),
    ]);

    const errors: SourceError[] = [];
    if (!baselineResult.success) {
      errors.push({ source: 'Baseline runs', error: baselineResult.error });
    }
    if (!optimizationResult.success) {
      errors.push({ source: 'Optimization runs', error: optimizationResult.error });
    }

    setState({
      rows: mergeUnifiedRunRows(
        baselineResult.success ? baselineResult.data : [],
        optimizationResult.success ? optimizationResult.data : [],
      ),
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
      void loadRuns(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadRuns]);

  const visibleRows = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return state.rows.filter((row) => {
      const matchesSearch = !normalizedQuery || row.searchText.includes(normalizedQuery);
      return matchesSearch && matchesFilter(row, filter);
    });
  }, [filter, query, state.rows]);

  const columns = useMemo<DataTableColumn<UnifiedRunRow>[]>(
    () => [
      {
        id: 'id',
        header: 'Run ID',
        sortValue: (row) => row.id,
        render: (row) => (
          <div className="flex max-w-52 items-center gap-2">
            <span className="truncate font-mono text-xs text-[var(--app-text)]">{row.id}</span>
            <span onClick={(event) => event.stopPropagation()}>
              <CopyButton value={row.id} label="Copy" />
            </span>
          </div>
        ),
      },
      {
        id: 'type',
        header: 'Type',
        sortValue: (row) => row.type,
        render: (row) => <StatusBadge status={row.type} tone={row.type === 'optimization' ? 'optimization' : 'info'} />,
      },
      {
        id: 'strategy',
        header: 'Strategy',
        sortValue: (row) => row.strategyName ?? '',
        render: (row) => <span className="text-[var(--app-text)]">{row.strategyName ?? 'Not recorded'}</span>,
      },
      {
        id: 'pairs',
        header: 'Pairs',
        sortValue: (row) => row.pairs.join(', '),
        render: (row) => row.pairs.length > 0 ? row.pairs.join(', ') : 'Not recorded',
      },
      {
        id: 'timeframe',
        header: 'Timeframe',
        sortValue: (row) => row.timeframe ?? '',
        render: (row) => row.timeframe ?? 'Not recorded',
      },
      {
        id: 'status',
        header: 'Status',
        sortValue: (row) => statusLabel(row),
        render: (row) => <StatusBadge status={row.status} label={statusLabel(row)} tone={statusTone(row)} />,
      },
      {
        id: 'result',
        header: 'Classification / result',
        sortValue: (row) => row.resultStatus ?? row.classification ?? '',
        render: (row) => resultLabel(row),
      },
      {
        id: 'trials',
        header: 'Trials',
        sortValue: (row) => row.trialsCount ?? -1,
        render: (row) => row.trialsCount ?? 'n/a',
      },
      {
        id: 'best',
        header: 'Best trial',
        sortValue: (row) => row.bestTrialId ?? '',
        render: (row) => row.bestTrialId ? (
          <span className="font-mono text-xs text-[var(--app-text-muted)]">{row.bestTrialId}</span>
        ) : (
          'n/a'
        ),
      },
      {
        id: 'created',
        header: 'Created',
        sortValue: (row) => timestamp(row.createdAt),
        render: (row) => formatDateTime(row.createdAt),
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
          <span onClick={(event) => event.stopPropagation()}>
            <Button size="sm" variant="ghost" onClick={() => router.push(row.detailHref)}>
              View
            </Button>
          </span>
        ),
      },
    ],
    [router],
  );

  return (
    <AppShell
      pageTitle="Runs"
      onRefresh={() => {
        void loadRuns(true);
      }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Runs"
          description="Read-only unified list of baseline and optimization runs from backend APIs."
          actions={
            state.loadedAt ? (
              <span className="text-xs text-[var(--app-text-subtle)]">
                Updated {formatDateTime(state.loadedAt)}
              </span>
            ) : null
          }
        />

        {state.errors.length > 0 && (
          <ControlledFailureBanner title="Partial run data loaded">
            <ul className="list-inside list-disc">
              {state.errors.map((item) => (
                <li key={item.source}>
                  {item.source}: {item.error.message}
                </li>
              ))}
            </ul>
          </ControlledFailureBanner>
        )}

        {state.errors.length === 2 && (
          <ErrorBanner title="Runs are unavailable">
            Both baseline and optimization run sources failed. No fallback or mock data is shown.
          </ErrorBanner>
        )}

        <SectionCard
          title="Unified run records"
          description="Search, filter, sort, copy IDs, or open read-only detail routes. The table does not start or mutate pipelines."
        >
          <div className="mb-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <label className="min-w-0 flex-1">
              <span className="sr-only">Search runs</span>
              <input
                type="search"
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search ID, type, strategy, pair, status, result"
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
            <LoadingSkeleton lines={6} />
          ) : (
            <DataTable
              rows={visibleRows}
              columns={columns}
              getRowKey={(row) => `${row.type}-${row.id}`}
              onRowClick={(row) => router.push(row.detailHref)}
              initialSortColumn="created"
              initialSortDirection="desc"
              emptyState={<EmptyState title="No runs found" description={EMPTY_COPY} />}
            />
          )}
        </SectionCard>
      </div>
    </AppShell>
  );
}

function matchesFilter(row: UnifiedRunRow, filter: RunFilter): boolean {
  switch (filter) {
    case 'baseline':
      return row.type === 'baseline';
    case 'optimization':
      return row.type === 'optimization';
    case 'completed':
      return row.uiStatus === 'pipeline_completed';
    case 'failed':
      return row.uiStatus === 'system_failed';
    case 'rejected':
      return row.uiStatus === 'strategy_rejected' || row.uiStatus === 'optimization_rejected';
    case 'controlled_failure':
      return row.uiStatus === 'controlled_failure';
    default:
      return true;
  }
}

function statusLabel(row: UnifiedRunRow): string {
  switch (row.uiStatus) {
    case 'pipeline_completed':
      return 'completed pipeline';
    case 'optimization_rejected':
      return 'rejected result';
    case 'strategy_rejected':
      return 'rejected result';
    case 'controlled_failure':
      return 'controlled failure';
    case 'system_failed':
      return 'failed pipeline';
    case 'running':
      return 'running';
    case 'pending':
      return 'pending';
    default:
      return row.status;
  }
}

function statusTone(
  row: UnifiedRunRow,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  switch (row.uiStatus) {
    case 'pipeline_completed':
      return 'success';
    case 'running':
      return 'info';
    case 'controlled_failure':
      return 'warning';
    case 'optimization_rejected':
      return 'optimization';
    case 'strategy_rejected':
    case 'system_failed':
      return 'danger';
    default:
      return 'neutral';
  }
}

function resultLabel(row: UnifiedRunRow): string {
  if (row.resultStatus === 'optimization_rejected') {
    return 'Optimization completed, but validation rejected the optimized result.';
  }
  return row.resultStatus ?? row.classification ?? 'Not recorded';
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
