import SectionCard from './SectionCard';
import StatusBadge from './StatusBadge';
import type { ValidationEvidence } from '@/lib/api/types';

interface RobustnessValidationCardProps {
  checks?: ValidationEvidence[];
}

export default function RobustnessValidationCard({ checks }: RobustnessValidationCardProps) {
  if (!checks || checks.length === 0) {
    return (
      <SectionCard title="Robustness Checks">
        <p className="text-sm text-[var(--app-text-subtle)]">No robustness evidence available from the backend for this run.</p>
      </SectionCard>
    );
  }

  const criticalFailures = checks.filter((c) => c.status === 'robustness_failed').length;
  const warnings = checks.filter((c) => c.status === 'robustness_warning').length;
  const passed = checks.filter((c) => c.status === 'robustness_passed').length;
  const overallStatus: 'passed' | 'warning' | 'failed' =
    criticalFailures > 0 ? 'failed' : warnings > 0 ? 'warning' : 'passed';

  const overallTone =
    overallStatus === 'passed' ? 'success' : overallStatus === 'warning' ? 'warning' : 'danger';

  return (
    <SectionCard
      title="Robustness Checks"
      description="Robustness checks verify the strategy behaves consistently under varied conditions."
      actions={<StatusBadge status={overallStatus} tone={overallTone} label={overallStatus === 'passed' ? 'Passed' : overallStatus === 'warning' ? 'Warning' : 'Failed'} />}
    >
      <div className="space-y-4">
        <div className="grid grid-cols-3 gap-3">
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Passed</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-success)]">{passed}</p>
          </div>
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Warnings</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-warning)]">{warnings}</p>
          </div>
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <p className="text-xs text-[var(--app-text-subtle)]">Failures</p>
            <p className="mt-1 text-lg font-semibold text-[var(--app-danger)]">{criticalFailures}</p>
          </div>
        </div>

        <div className="space-y-2">
          {checks.map((check, idx) => {
            const passed = check.status === 'robustness_passed';
            const warning = check.status === 'robustness_warning';
            const tone = passed ? 'success' : warning ? 'warning' : 'danger';
            return (
              <div
                key={idx}
                className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3"
              >
                <div className="flex items-center justify-between gap-3">
                  <p className="text-sm font-medium text-[var(--app-text)]">
                    {check.check_name ?? `Check ${idx + 1}`}
                  </p>
                  <StatusBadge status={check.status} tone={tone} label={passed ? 'Passed' : warning ? 'Warning' : 'Failed'} />
                </div>
                {check.timerange && (
                  <p className="mt-1 font-mono text-xs text-[var(--app-text-subtle)]">{check.timerange}</p>
                )}
                {check.issues && check.issues.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-[var(--app-danger)] mb-1">Issues</p>
                    <ul className="space-y-0.5">
                      {check.issues.map((issue, i) => (
                        <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                          <span className="text-[var(--app-danger)] shrink-0">•</span>
                          {issue.message}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
                {check.warnings && check.warnings.length > 0 && (
                  <div className="mt-2">
                    <p className="text-xs font-semibold text-[var(--app-warning)] mb-1">Warnings</p>
                    <ul className="space-y-0.5">
                      {check.warnings.map((warning, i) => (
                        <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                          <span className="text-[var(--app-warning)] shrink-0">•</span>
                          {warning}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </SectionCard>
  );
}
