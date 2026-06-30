import SectionCard from './SectionCard';

interface MetricCardProps {
  label: string;
  value?: string | number | null;
  helper?: string;
  tone?: 'neutral' | 'good' | 'warning' | 'danger';
}

const toneClasses = {
  neutral: 'text-[var(--app-text)]',
  good: 'text-[var(--app-success)]',
  warning: 'text-[var(--app-warning)]',
  danger: 'text-[var(--app-danger)]',
};

export default function MetricCard({ label, value = null, helper, tone = 'neutral' }: MetricCardProps) {
  return (
    <SectionCard className="p-4">
      <p className="text-xs font-medium uppercase text-[var(--app-text-subtle)]">{label}</p>
      <p className={`mt-3 text-2xl font-semibold ${toneClasses[tone]}`}>
        {value ?? 'No real data yet'}
      </p>
      {helper && <p className="mt-2 text-xs leading-5 text-[var(--app-text-muted)]">{helper}</p>}
    </SectionCard>
  );
}
