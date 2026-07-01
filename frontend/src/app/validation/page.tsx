'use client';

/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import DataTable, { DataTableColumn } from '@/components/DataTable';
import SectionCard from '@/components/SectionCard';
import EmptyState from '@/components/EmptyState';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import PageHeader from '@/components/PageHeader';
import StatusBadge from '@/components/StatusBadge';
import { listValidationRuns } from '@/lib/api/validation';
import type { ValidationRunListItem } from '@/lib/api/types';

export default function ValidationListPage() {
  const [runs, setRuns] = useState<ValidationRunListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadValidationRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    const result = await listValidationRuns({ limit: 50 });
    if (result.success) {
      setRuns(result.data);
    } else {
      setError(result.error.message);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    loadValidationRuns();
  }, [loadValidationRuns]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleString();
  };

  const columns: DataTableColumn<ValidationRunListItem>[] = [
    {
      id: 'id',
      header: 'Validation Run ID',
      sortValue: (run) => run.validation_run_id,
      render: (run) => <span className="font-mono text-xs text-[var(--app-text)]">{run.validation_run_id}</span>,
    },
    {
      id: 'strategy',
      header: 'Strategy',
      sortValue: (run) => run.strategy_name,
      render: (run) => <span className="font-medium text-[var(--app-text)]">{run.strategy_name}</span>,
    },
    {
      id: 'source',
      header: 'Source',
      sortValue: (run) => run.source_type,
      render: (run) => run.source_type,
    },
    {
      id: 'pairs',
      header: 'Pairs',
      sortValue: (run) => run.pairs.join(', '),
      render: (run) => (run.pairs.length > 0 ? run.pairs.join(', ') : 'Not recorded'),
    },
    {
      id: 'timeframe',
      header: 'Timeframe',
      sortValue: (run) => run.timeframe,
      render: (run) => run.timeframe || 'Not recorded',
    },
    {
      id: 'status',
      header: 'Status',
      sortValue: (run) => run.status,
      render: (run) => <StatusBadge status={run.status} dot />,
    },
    {
      id: 'decision',
      header: 'Decision',
      sortValue: (run) => run.decision_status ?? '',
      render: (run) => run.decision_status ? <StatusBadge status={run.decision_status} dot /> : 'Not available yet',
    },
    {
      id: 'created',
      header: 'Created',
      sortValue: (run) => run.created_at,
      render: (run) => formatDate(run.created_at),
    },
    {
      id: 'updated',
      header: 'Updated',
      sortValue: (run) => run.updated_at,
      render: (run) => formatDate(run.updated_at),
    },
    {
      id: 'actions',
      header: 'Actions',
      render: (run) => (
        <a
          href={`/validation/${run.validation_run_id}`}
          className="inline-flex h-8 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-2.5 text-xs font-medium text-[var(--app-text)] transition-colors hover:border-[var(--app-accent-border)]"
        >
          View
        </a>
      ),
    },
  ];

  const header = (
    <PageHeader
      title="Validation Runs"
      description="View OOS, WFO, and robustness evidence collected by backend validation pipelines."
      actions={<Button onClick={loadValidationRuns} variant="secondary">Refresh</Button>}
    />
  );

  if (loading) {
    return (
      <AppShell>
        <div className="space-y-6">
          {header}
          <SectionCard title="Validation evidence">
            <LoadingSkeleton lines={5} />
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="space-y-6">
          {header}
          <SectionCard title="Validation evidence">
            <EmptyState
              title="Error loading validation runs"
              description={error}
            />
            <div className="mt-4">
              <Button onClick={loadValidationRuns}>Retry</Button>
            </div>
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  if (runs.length === 0) {
    return (
      <AppShell>
        <div className="space-y-6">
          {header}
          <SectionCard title="Validation evidence">
            <EmptyState
              title="No validation runs found"
              description="Start a validation run from the baseline or optimization detail pages"
            />
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell>
      <div className="space-y-6">
        {header}

        <SectionCard title="Validation evidence" description="Read-only validation records from the backend.">
          <DataTable
            rows={runs}
            columns={columns}
            getRowKey={(run) => run.validation_run_id}
            emptyState={
              <EmptyState
                title="No validation runs found"
                description="Start a validation run from the baseline or optimization detail pages"
              />
            }
            initialSortColumn="created"
            initialSortDirection="desc"
          />
        </SectionCard>
      </div>
    </AppShell>
  );
}
