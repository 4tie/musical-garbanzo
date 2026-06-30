import { ReactNode } from 'react';
import Button from './Button';

type ActionStatus = 'idle' | 'pending' | 'accepted' | 'running' | 'completed' | 'controlled_failure' | 'failed' | 'rejected' | 'optimization_rejected';

interface ActionProgressPanelProps {
  status: ActionStatus;
  runId?: string;
  runType?: 'baseline' | 'optimization';
  currentStage?: string;
  resultStatus?: string;
  classification?: string;
  createdAt?: string;
  updatedAt?: string;
  detailHref?: string;
  isPolling?: boolean;
  onRefresh?: () => void;
  children?: ReactNode;
}

const statusConfig: Record<ActionStatus, { label: string; tone: 'neutral' | 'good' | 'warning' | 'danger' }> = {
  idle: { label: 'Idle', tone: 'neutral' },
  pending: { label: 'Pending', tone: 'neutral' },
  accepted: { label: 'Accepted', tone: 'good' },
  running: { label: 'Running', tone: 'neutral' },
  completed: { label: 'Completed', tone: 'good' },
  controlled_failure: { label: 'Controlled Failure', tone: 'warning' },
  failed: { label: 'Failed', tone: 'danger' },
  rejected: { label: 'Rejected', tone: 'warning' },
  optimization_rejected: { label: 'Optimization Rejected', tone: 'warning' },
};

export default function ActionProgressPanel({
  status,
  runId,
  runType,
  currentStage,
  resultStatus,
  classification,
  createdAt,
  updatedAt,
  detailHref,
  isPolling = false,
  onRefresh,
  children,
}: ActionProgressPanelProps) {
  const config = statusConfig[status];

  // Determine if controlled failure - show retry copy
  const isControlledFailure = status === 'controlled_failure' || status === 'rejected' || status === 'optimization_rejected';

  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-5">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-[var(--app-text-muted)]">Status</span>
            <span className="text-sm font-medium text-[var(--app-text)]">{config.label}</span>
            {isPolling && (
              <span className="flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-2 w-2 rounded-full bg-[var(--app-accent)] opacity-75"></span>
                <span className="relative inline-flex rounded-full h-2 w-2 bg-[var(--app-accent)]"></span>
              </span>
            )}
          </div>

          {runType && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-[var(--app-text-muted)]">Type</span>
              <span className="text-sm text-[var(--app-text)]">{runType === 'baseline' ? 'Baseline Evaluation' : 'Optimization'}</span>
            </div>
          )}

          {runId && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-[var(--app-text-muted)]">Run ID</span>
              <code className="text-sm font-mono text-[var(--app-text)]">{runId}</code>
            </div>
          )}

          {currentStage && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-[var(--app-text-muted)]">Current Stage</span>
              <span className="text-sm text-[var(--app-text)]">{currentStage}</span>
            </div>
          )}

          {resultStatus && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-[var(--app-text-muted)]">Result Status</span>
              <span className="text-sm text-[var(--app-text)]">{resultStatus}</span>
            </div>
          )}

          {classification && (
            <div className="mt-2 flex items-center gap-2">
              <span className="text-sm text-[var(--app-text-muted)]">Classification</span>
              <span className="text-sm text-[var(--app-text)]">{classification}</span>
            </div>
          )}

          {(createdAt || updatedAt) && (
            <div className="mt-3 space-y-1 text-xs text-[var(--app-text-muted)]">
              {createdAt && <div>Created: {new Date(createdAt).toLocaleString()}</div>}
              {updatedAt && <div>Updated: {new Date(updatedAt).toLocaleString()}</div>}
            </div>
          )}

          {isControlledFailure && (
            <div className="mt-3 text-xs leading-5 text-[var(--app-warning)]">
              This is a controlled validation outcome, not a system failure. You may retry with different parameters.
            </div>
          )}
        </div>

        <div className="flex shrink-0 flex-col gap-2">
          {onRefresh && (
            <Button variant="secondary" size="sm" onClick={onRefresh} disabled={isPolling}>
              {isPolling ? 'Refreshing...' : 'Refresh'}
            </Button>
          )}
          {detailHref && (status === 'completed' || status === 'controlled_failure' || status === 'rejected' || status === 'optimization_rejected') && (
            <a
              href={detailHref}
              className="inline-flex items-center justify-center rounded-[var(--app-radius)] bg-[var(--app-accent)] px-3 py-1.5 text-sm font-medium text-[var(--app-surface)] hover:bg-[var(--app-accent-hover)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-50"
            >
              View Details
            </a>
          )}
        </div>
      </div>

      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
