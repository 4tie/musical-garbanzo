import { ReactNode } from 'react';

interface NextAction {
  id: string;
  label: string;
  description: string;
  onClick?: () => void;
  href?: string;
  disabled?: boolean;
  tone?: 'primary' | 'secondary' | 'warning';
}

interface NextActionPanelProps {
  title?: string;
  message?: string;
  actions?: NextAction[];
  children?: ReactNode;
}

export default function NextActionPanel({
  title = 'Next safe action',
  message,
  actions = [],
  children,
}: NextActionPanelProps) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] p-4">
      <div className="flex items-start gap-3">
        {/* Icon */}
        <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)]">
          <svg
            className="h-3 w-3 text-[var(--app-accent)]"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M2 6h8M7 3l3 3-3 3" />
          </svg>
        </div>

        <div className="min-w-0 flex-1">
          <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--app-accent)]">
            {title}
          </h3>
          {message && (
            <p className="mt-1 text-xs leading-5 text-[var(--app-text-muted)]">{message}</p>
          )}
          {children && <div className="mt-2">{children}</div>}

          {actions.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {actions.map((action) => {
                const base =
                  'inline-flex items-center rounded-[var(--app-radius-sm)] px-3 py-1.5 text-xs font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-45';
                const toneClass =
                  action.tone === 'primary'
                    ? 'bg-[var(--app-accent)] text-white hover:bg-[var(--app-accent-strong)]'
                    : action.tone === 'warning'
                    ? 'border border-[rgb(245_158_11_/_0.36)] bg-[rgb(245_158_11_/_0.09)] text-[var(--app-warning)] hover:bg-[rgb(245_158_11_/_0.16)]'
                    : 'border border-[var(--app-border)] bg-[var(--app-surface)] text-[var(--app-text-muted)] hover:text-[var(--app-text)]';

                if (action.href && !action.disabled) {
                  return (
                    <a key={action.id} href={action.href} className={`${base} ${toneClass}`}>
                      {action.label}
                    </a>
                  );
                }

                return (
                  <div key={action.id} className="group relative">
                    <button
                      onClick={action.onClick}
                      disabled={action.disabled}
                      className={`${base} ${toneClass}`}
                    >
                      {action.label}
                    </button>
                    {action.description && (
                      <div className="absolute bottom-full left-0 z-10 mb-1.5 hidden w-56 rounded-[var(--app-radius-sm)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] p-2.5 text-[11px] leading-4 text-[var(--app-text-muted)] shadow-lg group-hover:block">
                        {action.description}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
