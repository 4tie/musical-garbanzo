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

const routeMeta: Record<string, { section: string; title: string }> = {
  '/':            { section: 'Discover', title: 'Dashboard' },
  '/journey':     { section: 'Discover', title: 'Strategy Journey' },
  '/strategies':  { section: 'Discover', title: 'Strategies' },
  '/runs':        { section: 'Test',     title: 'Runs' },
  '/baseline':    { section: 'Test',     title: 'Baseline' },
  '/optimization':{ section: 'Test',     title: 'Optimization' },
  '/validation':  { section: 'Test',     title: 'Validation' },
  '/results':     { section: 'Evidence', title: 'Results' },
  '/reports':     { section: 'Evidence', title: 'Reports' },
  '/settings':    { section: 'System',   title: 'Settings' },
};

function resolveMeta(pathname: string, overrideTitle?: string) {
  const exact = routeMeta[pathname];
  if (exact) return { section: exact.section, title: overrideTitle ?? exact.title };

  // Dynamic segments — match prefix
  for (const [key, meta] of Object.entries(routeMeta)) {
    if (key !== '/' && pathname.startsWith(key)) {
      return { section: meta.section, title: overrideTitle ?? meta.title };
    }
  }
  return { section: 'HER', title: overrideTitle ?? 'Command Center' };
}

export default function TopHeader({
  pageTitle,
  systemStatus,
  onRefresh,
  refreshDisabled = false,
}: TopHeaderProps) {
  const pathname = usePathname();
  const { section, title } = resolveMeta(pathname, pageTitle);

  // Derive backend health from systemStatus if available, else mark unknown
  const backendStatus = systemStatus?.backend ?? 'unknown';
  const backendTone =
    backendStatus === 'healthy' || backendStatus === 'configured' ? 'success' :
    backendStatus === 'unknown' ? 'warning' : 'danger';

  return (
    <header
      className="flex shrink-0 items-center justify-between border-b border-[var(--app-border)] bg-[var(--app-surface-glass)] px-5 backdrop-blur"
      style={{ height: 'var(--app-header-height)' }}
    >
      {/* Left: breadcrumb + page title */}
      <div className="min-w-0">
        <div className="flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-widest text-[var(--app-text-subtle)]">
          <span>HER</span>
          <svg
            className="h-3 w-3 opacity-40"
            viewBox="0 0 12 12"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.7"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M4.5 2.5 7.5 6l-3 3.5" />
          </svg>
          <span>{section}</span>
        </div>
        <h1 className="mt-1 truncate text-[15px] font-semibold leading-none text-[var(--app-text)]">
          {title}
        </h1>
      </div>

      {/* Right: status + controls */}
      <div className="flex shrink-0 items-center gap-2">
        <StatusBadge
          status={backendStatus}
          tone={backendTone}
          label={`Backend: ${backendStatus}`}
          dot
        />
        <div className="mx-1 h-4 w-px bg-[var(--app-border)]" />
        <Button
          size="sm"
          variant="ghost"
          onClick={onRefresh ?? (() => window.location.reload())}
          disabled={refreshDisabled}
          title="Refresh page data"
        >
          <svg
            className="h-3.5 w-3.5"
            viewBox="0 0 16 16"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M13.65 2.35A8 8 0 1 0 14 8" />
            <path d="M14 2v4h-4" />
          </svg>
          Refresh
        </Button>
        <ThemeSettings compact />
      </div>
    </header>
  );
}
