import { ReactNode } from 'react';

interface ErrorBannerProps {
  title?: string;
  children: ReactNode;
}

export default function ErrorBanner({ title = 'Unable to load this view', children }: ErrorBannerProps) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[rgb(239_68_68_/_0.34)] bg-[rgb(239_68_68_/_0.1)] p-4 text-sm text-[var(--app-text)]">
      <p className="font-semibold text-[var(--app-danger)]">{title}</p>
      <div className="mt-1 leading-6 text-[var(--app-text-muted)]">{children}</div>
    </div>
  );
}
