import { ReactNode } from 'react';

interface RunActionCardProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  children: ReactNode;
  className?: string;
}

export default function RunActionCard({
  title,
  description,
  icon,
  children,
  className = '',
}: RunActionCardProps) {
  return (
    <div
      className={[
        'rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-6',
        className,
      ].join(' ')}
    >
      <div className="mb-4 flex items-start gap-3">
        {icon && <div className="text-[var(--app-accent)]">{icon}</div>}
        <div className="min-w-0 flex-1">
          <h3 className="text-base font-semibold text-[var(--app-text)]">{title}</h3>
          {description && (
            <p className="mt-1 text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
          )}
        </div>
      </div>
      {children}
    </div>
  );
}
