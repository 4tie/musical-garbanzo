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
  return (
    <div className="flex flex-col rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <p className="text-[10px] font-semibold uppercase tracking-widest text-[var(--app-text-subtle)]">
        {label}
      </p>
      <p
        className={[
          'mt-2.5 text-2xl font-semibold leading-none',
          mono ? 'font-mono' : '',
          toneValueClasses[tone] ?? toneValueClasses.neutral,
        ].join(' ')}
      >
        {value ?? <span className="text-lg text-[var(--app-text-subtle)]">—</span>}
      </p>
      {helper && (
        <p className="mt-2 text-[11px] leading-5 text-[var(--app-text-subtle)]">{helper}</p>
      )}
    </div>
  );
}
