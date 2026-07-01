interface MetricCardProps {
  label: string;
  value?: string | number | null;
  helper?: string;
  tone?: 'neutral' | 'good' | 'warning' | 'danger';
  mono?: boolean;
}

const toneValueClasses: Record<string, string> = {
  neutral: 'text-[var(--app-text)]',
  good:    'text-[var(--app-success)]',
  warning: 'text-[var(--app-warning)]',
  danger:  'text-[var(--app-danger)]',
};

export default function MetricCard({
  label,
  value = null,
  helper,
  tone = 'neutral',
  mono = false,
}: MetricCardProps) {
  const hasValue = value !== null && value !== undefined;

  return (
    <div className="flex min-h-[116px] flex-col justify-between rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4 shadow-[var(--app-shadow-sm)]">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">
        {label}
      </p>
      <p
        className={[
          'mt-3 text-2xl font-semibold leading-none',
          mono ? 'font-mono' : '',
          hasValue ? toneValueClasses[tone] ?? toneValueClasses.neutral : 'text-[var(--app-text-subtle)]',
        ].join(' ')}
      >
        {hasValue ? value : <span className="text-sm font-medium">Not available yet</span>}
      </p>
      {helper && (
        <p className="mt-2 text-[11px] leading-5 text-[var(--app-text-subtle)]">{helper}</p>
      )}
    </div>
  );
}
