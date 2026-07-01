import { ReactNode } from 'react';

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
}

export default function EmptyState({ title, description, icon, action }: EmptyStateProps) {
  return (
    <div className="flex min-h-48 flex-col items-center justify-center rounded-[var(--app-radius)] border border-dashed border-[var(--app-border-strong)] bg-[var(--app-surface-muted)] p-8 text-center shadow-[var(--app-shadow-sm)]">
      <div className="mb-4 flex h-11 w-11 items-center justify-center rounded-full border border-[var(--app-border)] bg-[var(--app-surface)] text-[var(--app-text-subtle)]">
        {icon ?? (
          <svg viewBox="0 0 40 40" fill="none" className="h-8 w-8 opacity-70" aria-hidden="true">
            <circle cx="20" cy="20" r="18" stroke="currentColor" strokeWidth="1.5" />
            <path d="M13 20h14M20 13v14" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeDasharray="3 3" />
          </svg>
        )}
      </div>
      <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
      <p className="mt-1.5 max-w-sm text-xs leading-5 text-[var(--app-text-subtle)]">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
