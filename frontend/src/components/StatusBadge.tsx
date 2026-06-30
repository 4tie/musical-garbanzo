type StatusTone = 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral';

interface StatusBadgeProps {
  status: string;
  label?: string;
  tone?: StatusTone;
}

const toneClasses: Record<StatusTone, string> = {
  success: 'border-[rgb(34_197_94_/_0.32)] bg-[rgb(34_197_94_/_0.12)] text-[var(--app-success)]',
  info: 'border-[rgb(56_189_248_/_0.32)] bg-[rgb(56_189_248_/_0.12)] text-[var(--app-info)]',
  warning: 'border-[rgb(245_158_11_/_0.34)] bg-[rgb(245_158_11_/_0.12)] text-[var(--app-warning)]',
  danger: 'border-[rgb(239_68_68_/_0.34)] bg-[rgb(239_68_68_/_0.12)] text-[var(--app-danger)]',
  optimization:
    'border-[rgb(168_85_247_/_0.34)] bg-[rgb(168_85_247_/_0.12)] text-[var(--app-optimization)]',
  neutral: 'border-[var(--app-border)] bg-[var(--app-surface-muted)] text-[var(--app-text-muted)]',
};

export default function StatusBadge({ status, label, tone }: StatusBadgeProps) {
  const resolvedTone = tone ?? inferTone(status);

  return (
    <span
      className={[
        'inline-flex min-h-6 items-center rounded-full border px-2 py-0.5 text-xs font-medium',
        toneClasses[resolvedTone],
      ].join(' ')}
    >
      {label || status}
    </span>
  );
}

function inferTone(status: string): StatusTone {
  const normalized = status.toLowerCase();
  if (['healthy', 'configured', 'completed', 'passed', 'validated'].includes(normalized)) {
    return 'success';
  }
  if (['running', 'info'].includes(normalized)) {
    return 'info';
  }
  if (['warning', 'unknown', 'failed_controlled', 'confirmation_required'].includes(normalized)) {
    return 'warning';
  }
  if (['failed', 'missing', 'rejected', 'system_failed'].includes(normalized)) {
    return 'danger';
  }
  if (normalized.includes('optimization')) {
    return 'optimization';
  }
  return 'neutral';
}
