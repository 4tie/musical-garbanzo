import SectionCard from './SectionCard';
import StatusBadge from './StatusBadge';
import type { ValidationEvidence } from '@/lib/api/types';

interface OOSValidationCardProps {
  evidence?: ValidationEvidence;
}

function fmt(val: unknown, percent = false): string {
  if (val === undefined || val === null) return 'N/A';
  const n = Number(val);
  if (!isFinite(n)) return String(val);
  if (percent) return `${n.toFixed(1)}%`;
  return n.toFixed(3);
}

export default function OOSValidationCard({ evidence }: OOSValidationCardProps) {
  if (!evidence) {
    return (
      <SectionCard title="Out-of-Sample Validation">
        <p className="text-sm text-[var(--app-text-subtle)]">No OOS evidence available from the backend for this run.</p>
      </SectionCard>
    );
  }

  const metrics = evidence.metrics as Record<string, unknown>;
  const isPassed = evidence.status === 'oos_passed';

  return (
    <SectionCard
      title="Out-of-Sample Validation"
      description="OOS tests strategy performance on unseen historical data withheld from training."
      actions={<StatusBadge status={isPassed ? 'passed' : 'failed'} tone={isPassed ? 'success' : 'danger'} label={isPassed ? 'Passed' : 'Failed'} />}
    >
      <div className="space-y-4">
        {evidence.timerange && (
          <div>
            <p className="text-xs text-[var(--app-text-subtle)]">OOS timerange</p>
            <p className="mt-0.5 font-mono text-sm text-[var(--app-text)]">{evidence.timerange}</p>
          </div>
        )}

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: 'Profit factor', key: 'profit_factor' },
            { label: 'Expectancy', key: 'expectancy' },
            { label: 'Max drawdown', key: 'max_drawdown_pct', percent: true },
            { label: 'Trades', key: 'trade_count' },
          ].map(({ label, key, percent }) => (
            <div key={key} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
              <p className="text-xs text-[var(--app-text-subtle)]">{label}</p>
              <p className="mt-1 text-lg font-semibold text-[var(--app-text)]">{fmt(metrics[key], percent)}</p>
            </div>
          ))}
        </div>

        {evidence.issues && evidence.issues.length > 0 && (
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

        {evidence.warnings && evidence.warnings.length > 0 && (
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
