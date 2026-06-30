import { ReactNode } from 'react';

interface SectionCardProps {
  children: ReactNode;
  title?: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}

export default function SectionCard({
  children,
  title,
  description,
  actions,
  className = '',
}: SectionCardProps) {
  return (
    <section
      className={[
        'card-hover rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-5',
        className,
      ].join(' ')}
    >
      {(title || description || actions) && (
        <div className="mb-4 flex items-start justify-between gap-4">
          <div className="min-w-0">
            {title && <h2 className="text-base font-semibold text-[var(--app-text)]">{title}</h2>}
            {description && (
              <p className="mt-1 text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
