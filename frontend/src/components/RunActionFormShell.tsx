import { ReactNode } from 'react';

interface RunActionFormShellProps {
  title: string;
  description?: string;
  children: ReactNode;
  actions?: ReactNode;
  className?: string;
}

export default function RunActionFormShell({
  title,
  description,
  children,
  actions,
  className = '',
}: RunActionFormShellProps) {
  return (
    <div className={['max-w-2xl mx-auto', className].join(' ')}>
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-[var(--app-text)]">{title}</h1>
        {description && (
          <p className="mt-2 text-sm leading-6 text-[var(--app-text-muted)]">{description}</p>
        )}
      </div>
      <div className="space-y-6">{children}</div>
      {actions && <div className="mt-6 flex justify-end gap-3">{actions}</div>}
    </div>
  );
}
