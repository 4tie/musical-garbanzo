import { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
}

export default function EmptyState({ title, description, icon }: EmptyStateProps) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-[var(--app-radius)] border border-dashed border-[var(--app-border)] bg-[var(--app-surface-muted)] p-8 text-center">
      <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-sm font-semibold text-[var(--app-accent)]">
        {icon ?? 'HER'}
      </div>
      <h3 className="text-base font-semibold text-[var(--app-text)]">{title}</h3>
      <p className="mt-2 max-w-xl text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
    </div>
  );
}
