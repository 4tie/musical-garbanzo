import { ReactNode } from 'react';

interface ValidationSummaryProps {
  errors: string[];
  warnings?: string[];
  title?: string;
  children?: ReactNode;
}

export default function ValidationSummary({
  errors,
  warnings = [],
  title = 'Form Validation',
  children,
}: ValidationSummaryProps) {
  const hasErrors = errors.length > 0;
  const hasWarnings = warnings.length > 0;
  const hasIssues = hasErrors || hasWarnings;

  if (!hasIssues && !children) {
    return null;
  }

  return (
    <div
      className={[
        'rounded-[var(--app-radius)] border p-4',
        hasErrors
          ? 'border-[rgb(239_68_68_/_0.38)] bg-[rgb(239_68_68_/_0.12)]'
          : hasWarnings
          ? 'border-[rgb(245_158_11_/_0.38)] bg-[rgb(245_158_11_/_0.12)]'
          : 'border-[var(--app-border)] bg-[var(--app-surface-muted)]',
      ].join(' ')}
    >
      <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>

      {hasErrors && (
        <div className="mt-3">
          <h4 className="text-xs font-medium text-[var(--app-danger)]">
            {errors.length === 1 ? 'Error' : 'Errors'} ({errors.length})
          </h4>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--app-text-muted)]">
            {errors.map((error, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-danger)]">•</span>
                <span>{error}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {hasWarnings && (
        <div className="mt-3">
          <h4 className="text-xs font-medium text-[var(--app-warning)]">
            {warnings.length === 1 ? 'Warning' : 'Warnings'} ({warnings.length})
          </h4>
          <ul className="mt-2 space-y-1 text-xs leading-5 text-[var(--app-text-muted)]">
            {warnings.map((warning, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-warning)]">•</span>
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {children && <div className="mt-3">{children}</div>}
    </div>
  );
}
