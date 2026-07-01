import { ReactNode } from 'react';

interface SectionCardProps {
  children: ReactNode;
  title?: string;
  description?: string;
  actions?: ReactNode;
  /** Remove internal padding — use for full-bleed tables or custom layouts */
  noPad?: boolean;
  /** Draw a 2px accent top-border to visually highlight this card */
  accent?: boolean;
  className?: string;
}

export default function SectionCard({
  children,
  title,
  description,
  actions,
  noPad = false,
  accent = false,
  className = '',
}: SectionCardProps) {
  return (
    <section
      className={[
        'rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)]',
        accent ? 'border-t-2 border-t-[var(--app-accent)]' : '',
        noPad ? '' : 'p-5',
        className,
      ].join(' ')}
    >
      {(title || description || actions) && (
        <div className={['flex items-start justify-between gap-4', noPad ? 'px-5 pt-5 pb-4' : 'mb-4'].join(' ')}>
          <div className="min-w-0">
            {title && (
              <h2 className="text-sm font-semibold text-[var(--app-text)]">{title}</h2>
            )}
            {description && (
              <p className="mt-0.5 text-xs leading-5 text-[var(--app-text-subtle)]">{description}</p>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
