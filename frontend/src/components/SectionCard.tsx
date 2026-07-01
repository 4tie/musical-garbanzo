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
        'app-panel-highlight rounded-[var(--app-radius)] border border-[var(--app-border)] shadow-[var(--app-shadow-card)]',
        accent ? 'border-t-2 border-t-[var(--app-accent)]' : '',
        noPad ? '' : 'p-5',
        className,
      ].join(' ')}
    >
      {(title || description || actions) && (
        <div className={['flex items-start justify-between gap-4 border-b border-[var(--app-border)]', noPad ? 'px-5 pt-5 pb-4' : '-mx-5 -mt-5 mb-5 px-5 py-4'].join(' ')}>
          <div className="min-w-0">
            {title && (
              <h2 className="text-sm font-semibold tracking-normal text-[var(--app-text)]">{title}</h2>
            )}
            {description && (
              <p className="mt-1 text-xs leading-5 text-[var(--app-text-muted)]">{description}</p>
            )}
          </div>
          {actions && <div className="shrink-0">{actions}</div>}
        </div>
      )}
      {children}
    </section>
  );
}
