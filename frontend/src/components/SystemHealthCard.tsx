import StatusBadge from './StatusBadge';
import SectionCard from './SectionCard';

interface SystemHealthCardProps {
  name: string;
  status: string;
  details?: string;
}

export default function SystemHealthCard({ name, status, details }: SystemHealthCardProps) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--app-text)]">{name}</h3>
        <StatusBadge status={status} />
      </div>
      {details && <p className="mt-2 text-xs leading-5 text-[var(--app-text-muted)]">{details}</p>}
    </div>
  );
}
