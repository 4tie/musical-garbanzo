type StatusTone = 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral';

interface StatusBadgeProps {
  status: string;
  label?: string;
  tone?: StatusTone;
  /** Show a colored dot indicator before the label */
  dot?: boolean;
}

const toneClasses: Record<StatusTone, string> = {
  success:      'border-[rgb(34_197_94_/_0.28)]  bg-[rgb(34_197_94_/_0.09)]  text-[var(--app-success)]',
  info:         'border-[rgb(56_189_248_/_0.28)]  bg-[rgb(56_189_248_/_0.09)]  text-[var(--app-info)]',
  warning:      'border-[rgb(245_158_11_/_0.30)]  bg-[rgb(245_158_11_/_0.09)]  text-[var(--app-warning)]',
  danger:       'border-[rgb(239_68_68_/_0.30)]   bg-[rgb(239_68_68_/_0.09)]   text-[var(--app-danger)]',
  optimization: 'border-[rgb(168_85_247_/_0.30)]  bg-[rgb(168_85_247_/_0.09)]  text-[var(--app-optimization)]',
  neutral:      'border-[var(--app-border)]        bg-[var(--app-surface-muted)] text-[var(--app-text-muted)]',
};

const dotClasses: Record<StatusTone, string> = {
  success:      'bg-[var(--app-success)]',
  info:         'bg-[var(--app-info)]',
  warning:      'bg-[var(--app-warning)]',
  danger:       'bg-[var(--app-danger)]',
  optimization: 'bg-[var(--app-optimization)]',
  neutral:      'bg-[var(--app-text-subtle)]',
};

export default function StatusBadge({ status, label, tone, dot = false }: StatusBadgeProps) {
  const resolvedTone = tone ?? inferTone(status);

  return (
    <span
      className={[
        'inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium',
        toneClasses[resolvedTone],
      ].join(' ')}
    >
      {dot && (
        <span
          className={['h-1.5 w-1.5 shrink-0 rounded-full', dotClasses[resolvedTone]].join(' ')}
          aria-hidden="true"
        />
      )}
      {label || status}
    </span>
  );
}

function inferTone(status: string): StatusTone {
  const s = status.toLowerCase();
  if (['healthy', 'configured', 'completed', 'passed', 'validated', 'ready', 'ok'].includes(s)) return 'success';
  if (['running', 'pending', 'queued', 'info', 'active'].includes(s)) return 'info';
  if (['warning', 'unknown', 'failed_controlled', 'confirmation_required', 'missing_sidecar'].includes(s)) return 'warning';
  if (['failed', 'missing', 'rejected', 'system_failed', 'error', 'invalid', 'parse_error', 'unsafe'].includes(s)) return 'danger';
  if (s.includes('optim')) return 'optimization';
  return 'neutral';
}
