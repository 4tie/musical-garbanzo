import { ReactNode } from 'react';

interface ControlledFailureBannerProps {
  title?: string;
  children: ReactNode;
}

export default function ControlledFailureBanner({
  title = 'Controlled validation outcome',
  children,
}: ControlledFailureBannerProps) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[rgb(245_158_11_/_0.38)] bg-[rgb(245_158_11_/_0.12)] p-4 text-sm">
      <p className="font-semibold text-[var(--app-warning)]">{title}</p>
      <div className="mt-1 leading-6 text-[var(--app-text-muted)]">{children}</div>
    </div>
  );
}
