'use client';

import { usePathname } from 'next/navigation';
import Button from './Button';
import StatusBadge from './StatusBadge';
import ThemeSettings from './ThemeSettings';
import { SystemStatusResponse } from '@/lib/types';

interface TopHeaderProps {
  pageTitle?: string;
  systemStatus?: SystemStatusResponse | null;
  onRefresh?: () => void;
  refreshDisabled?: boolean;
}

const routeTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/runs': 'Runs',
  '/baseline': 'Baseline',
  '/optimization': 'Optimization',
  '/strategies': 'Strategies',
  '/reports': 'Reports',
  '/settings': 'Settings',
};

export default function TopHeader({
  pageTitle,
  systemStatus,
  onRefresh,
  refreshDisabled = false,
}: TopHeaderProps) {
  const pathname = usePathname();
  const resolvedTitle = pageTitle ?? routeTitles[pathname] ?? 'HER Command Center';
  const backendStatus = systemStatus?.backend ?? 'unknown';

  return (
    <header className="flex min-h-16 flex-col gap-3 border-b border-[var(--app-border)] bg-[var(--app-surface)] px-4 py-3 lg:flex-row lg:items-center lg:justify-between">
      <div className="min-w-0">
        <p className="text-xs font-medium uppercase text-[var(--app-text-subtle)]">
          HER Command Center
        </p>
        <h1 className="truncate text-lg font-semibold text-[var(--app-text)]">{resolvedTitle}</h1>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <StatusBadge status={backendStatus} label={`Backend: ${backendStatus}`} />
        <label className="relative min-w-48">
          <span className="sr-only">Search placeholder</span>
          <input
            type="search"
            placeholder="Search arrives with real data"
            disabled
            className="h-9 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text-muted)] outline-none"
          />
        </label>
        <Button
          size="sm"
          variant="secondary"
          onClick={onRefresh ?? (() => window.location.reload())}
          disabled={refreshDisabled}
        >
          Refresh
        </Button>
        <ThemeSettings compact />
      </div>
    </header>
  );
}
