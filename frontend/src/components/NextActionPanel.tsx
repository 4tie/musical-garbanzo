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
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-5">
      <div className="flex items-start gap-3">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[rgb(56_189_248_/_0.32)] bg-[rgb(56_189_248_/_0.10)]">
          <span className="text-xs font-bold text-[var(--app-info)]">→</span>
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
          {message && (
            <p className="mt-1 text-sm leading-6 text-[var(--app-text-muted)]">{message}</p>
          )}
          {children && <div className="mt-2">{children}</div>}
          {actions.length > 0 && (
            <div className="mt-4 flex flex-wrap gap-2">
              {actions.map((action) => {
                const baseClasses = 'rounded-[var(--app-radius)] px-3.5 py-2 text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed';
                const toneClasses =
                  action.tone === 'primary'
                    ? 'bg-[var(--app-accent)] text-[var(--app-accent-text)] hover:bg-[var(--app-accent-strong)]'
                    : action.tone === 'warning'
                    ? 'border border-[rgb(245_158_11_/_0.4)] bg-[rgb(245_158_11_/_0.10)] text-[var(--app-warning)] hover:bg-[rgb(245_158_11_/_0.18)]'
                    : 'border border-[var(--app-border)] bg-[var(--app-surface-muted)] text-[var(--app-text-muted)] hover:text-[var(--app-text)]';

                if (action.href && !action.disabled) {
                  return (
                    <a key={action.id} href={action.href} className={`${baseClasses} ${toneClasses}`}>
                      {action.label}
                    </a>
                  );
                }
                return (
                  <div key={action.id} className="group relative">
                    <button
                      onClick={action.onClick}
                      disabled={action.disabled}
                      className={`${baseClasses} ${toneClasses}`}
                    >
                      {action.label}
                    </button>
                    {action.description && (
                      <div className="absolute bottom-full left-0 mb-1 hidden w-64 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] p-2 text-xs text-[var(--app-text-muted)] shadow-lg group-hover:block z-10">
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
