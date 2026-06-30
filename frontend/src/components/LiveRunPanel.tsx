'use client';

import { useRunPolling, RunType } from '@/hooks/useRunPolling';
import StatusBadge from './StatusBadge';

interface LiveRunPanelProps {
  runType: RunType;
  runId: string;
  label?: string;
}

const STAGE_LABEL: Record<string, string> = {
  data_download: 'Downloading data',
  backtest: 'Running backtest',
  parse_result: 'Parsing results',
  evaluate: 'Evaluating metrics',
  decision: 'Recording decision',
  hyperopt: 'Running hyperopt',
  validate_candidate: 'Validating candidate',
  optimize: 'Optimizing',
  compare: 'Comparing results',
};

function stageLabel(key: string | undefined): string {
  if (!key) return 'Processing';
  return STAGE_LABEL[key] ?? key.replace(/_/g, ' ');
}

function isTerminal(status: string): boolean {
  return ['completed', 'failed', 'optimization_rejected', 'rejected', 'controlled_failure', 'error'].includes(status);
}

export default function LiveRunPanel({ runType, runId, label }: LiveRunPanelProps) {
  const { status, currentStage, updatedAt, isPolling, error, refresh } = useRunPolling(runType, runId);

  const terminal = isTerminal(status);
  const alive = !terminal && status !== 'idle';

  function updatedLabel(): string {
    if (!updatedAt) return '';
    try {
      return new Date(updatedAt).toLocaleTimeString(undefined, { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    } catch {
      return updatedAt;
    }
  }

  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3 min-w-0">
          {alive && (
            <span className="relative flex h-2.5 w-2.5 shrink-0">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--app-accent)] opacity-60" />
              <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-[var(--app-accent)]" />
            </span>
          )}
          <div className="min-w-0">
            <p className="text-sm font-semibold text-[var(--app-accent)]">
              {label ?? (runType === 'baseline' ? 'Baseline run' : 'Optimization run')}
            </p>
            <p className="mt-0.5 font-mono text-[11px] text-[var(--app-text-subtle)]">{runId}</p>
          </div>
        </div>
        <StatusBadge status={status} tone={alive ? 'info' : terminal ? (status === 'completed' ? 'success' : 'warning') : 'neutral'} />
      </div>

      {currentStage && (
        <div className="mt-3 flex items-center gap-2">
          <span className="text-xs text-[var(--app-text-muted)]">Current stage:</span>
          <span className="text-xs font-medium text-[var(--app-text)]">{stageLabel(currentStage)}</span>
        </div>
      )}

      <div className="mt-3 flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          {isPolling && (
            <span className="text-[11px] text-[var(--app-text-subtle)]">Polling every 2 s</span>
          )}
          {updatedAt && (
            <span className="text-[11px] text-[var(--app-text-subtle)]">
              Last updated {updatedLabel()}
            </span>
          )}
        </div>
        {!isPolling && (
          <button
            onClick={refresh}
            className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-2.5 py-1 text-xs text-[var(--app-text-muted)] hover:text-[var(--app-text)] transition-colors"
          >
            Retry
          </button>
        )}
      </div>

      {error && (
        <p className="mt-2 text-xs text-[var(--app-danger)]">Polling error: {error}</p>
      )}
    </div>
  );
}
