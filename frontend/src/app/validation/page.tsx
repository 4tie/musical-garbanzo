'use client';

/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from 'react';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import SectionCard from '@/components/SectionCard';
import EmptyState from '@/components/EmptyState';
import LoadingSkeleton from '@/components/LoadingSkeleton';
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

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'text-green-600';
      case 'failed_controlled':
      case 'validation_error':
        return 'text-red-600';
      case 'running':
        return 'text-blue-600';
      case 'confirmation_required':
        return 'text-yellow-600';
      default:
        return 'text-gray-600';
    }
  };

  const getDecisionStatusColor = (decisionStatus?: string) => {
    if (!decisionStatus) return 'text-gray-400';
    switch (decisionStatus) {
      case 'validated':
        return 'text-green-600';
      case 'rejected':
        return 'text-red-600';
      default:
        return 'text-gray-600';
    }
  };

  if (loading) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Runs</h1>
            <p className="text-gray-600 mt-1">View validation evidence for strategies</p>
          </div>
          <LoadingSkeleton />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Runs</h1>
            <p className="text-gray-600 mt-1">View validation evidence for strategies</p>
          </div>
          <SectionCard>
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
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Runs</h1>
            <p className="text-gray-600 mt-1">View validation evidence for strategies</p>
          </div>
          <SectionCard>
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
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Runs</h1>
            <p className="text-gray-600 mt-1">View validation evidence for strategies</p>
          </div>
          <Button onClick={loadValidationRuns} variant="secondary">
            Refresh
          </Button>
        </div>

        <SectionCard>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Validation Run ID
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Strategy
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Pairs
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Timeframe
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Status
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Decision
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Created
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Updated
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {runs.map((run) => (
                  <tr key={run.validation_run_id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {run.validation_run_id}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {run.strategy_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {run.source_type}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {run.pairs.join(', ')}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {run.timeframe}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={getStatusColor(run.status)}>{run.status}</span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <span className={getDecisionStatusColor(run.decision_status)}>
                        {run.decision_status || 'N/A'}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(run.created_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {formatDate(run.updated_at)}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      <a
                        href={`/validation/${run.validation_run_id}`}
                        className="inline-flex items-center justify-center gap-2 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-text)] hover:border-[var(--app-accent-border)] h-8 px-2.5 text-xs font-medium transition-colors"
                      >
                        View
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}
