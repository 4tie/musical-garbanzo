import SectionCard from './SectionCard';
import StatusBadge from './StatusBadge';
import type { ValidationEvidence } from '@/lib/api/types';

interface WFOValidationCardProps {
  evidence?: ValidationEvidence;
  windows?: ValidationEvidence[];
}

function fmt(val: unknown): string {
  if (val === undefined || val === null) return 'N/A';
  const n = Number(val);
  if (!isFinite(n)) return String(val);
  return n.toFixed(3);
}

export default function WFOValidationCard({ evidence, windows }: WFOValidationCardProps) {
  if (!evidence && (!windows || windows.length === 0)) {
    return (
      <SectionCard title="Walk-Forward Validation">
        <p className="text-sm text-[var(--app-text-subtle)]">No WFO evidence available from the backend for this run.</p>
      </SectionCard>
    );
  }

  const isPassed = evidence?.status === 'wfo_passed';
  const totalWindows = windows?.length ?? 0;
  const passedWindows = windows?.filter((w) => w.status === 'wfo_passed').length ?? 0;
  const failedWindows = windows?.filter((w) => w.status === 'wfo_failed').length ?? 0;
  const passRate = totalWindows > 0 ? (passedWindows / totalWindows) * 100 : 0;

  return (
    <SectionCard
      title="Walk-Forward Validation"
      description="WFO evaluates strategy consistency across sequential time windows."
      actions={<StatusBadge status={isPassed ? 'passed' : 'failed'} tone={isPassed ? 'success' : 'danger'} label={isPassed ? 'Passed' : 'Failed'} />}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Windows</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-text)]">{totalWindows}</p>
          </div>
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Passed</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-success)]">{passedWindows}</p>
          </div>
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Failed</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-danger)]">{failedWindows}</p>
          </div>
        </div>

        <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
          <p className="text-xs text-[var(--app-text-subtle)]">Pass rate</p>
          <p className="mt-1 text-xl font-semibold text-[var(--app-text)]">{passRate.toFixed(1)}%</p>
          <div className="mt-2 h-1.5 rounded-full bg-[var(--app-border)]">
            <div
              className="h-1.5 rounded-full transition-all"
              style={{
                width: `${passRate}%`,
                background: passRate >= 60 ? 'var(--app-success)' : passRate >= 40 ? 'var(--app-warning)' : 'var(--app-danger)',
              }}
            />
          </div>
        </div>

        {windows && windows.length > 0 && (
          <div>
            <p className="mb-2 text-xs font-semibold text-[var(--app-text-muted)]">Window results</p>
            <div className="overflow-x-auto rounded-[var(--app-radius)] border border-[var(--app-border)]">
              <table className="min-w-full text-xs">
                <thead>
                  <tr className="border-b border-[var(--app-border)] bg-[var(--app-surface-muted)]">
                    <th className="px-3 py-2 text-left font-semibold text-[var(--app-text-subtle)]">Window</th>
                    <th className="px-3 py-2 text-left font-semibold text-[var(--app-text-subtle)]">Timerange</th>
                    <th className="px-3 py-2 text-left font-semibold text-[var(--app-text-subtle)]">Status</th>
                    <th className="px-3 py-2 text-left font-semibold text-[var(--app-text-subtle)]">Profit factor</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[var(--app-border)]">
                  {windows.map((win, idx) => {
                    const m = win.metrics as Record<string, unknown>;
                    const passed = win.status === 'wfo_passed';
                    return (
                      <tr key={idx} className="bg-[var(--app-surface)] hover:bg-[var(--app-surface-raised)]">
                        <td className="px-3 py-2 text-[var(--app-text)]">{win.window_index ?? idx + 1}</td>
                        <td className="px-3 py-2 font-mono text-[var(--app-text-subtle)]">{win.timerange ?? '—'}</td>
                        <td className="px-3 py-2">
                          <StatusBadge status={win.status} tone={passed ? 'success' : 'danger'} label={passed ? 'Passed' : 'Failed'} />
                        </td>
                        <td className="px-3 py-2 text-[var(--app-text)]">{fmt(m.profit_factor)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {evidence?.issues && evidence.issues.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-[var(--app-danger)] mb-1">Issues</p>
            <ul className="space-y-1">
              {evidence.issues.map((issue, idx) => (
                <li key={idx} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                  <span className="text-[var(--app-danger)] shrink-0">•</span>
                  {issue.message}
                </li>
              ))}
            </ul>
          </div>
        )}

        {evidence?.warnings && evidence.warnings.length > 0 && (
          <div>
            <p className="text-xs font-semibold text-[var(--app-warning)] mb-1">Warnings</p>
            <ul className="space-y-1">
              {evidence.warnings.map((warning, idx) => (
                <li key={idx} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                  <span className="text-[var(--app-warning)] shrink-0">•</span>
                  {warning}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
