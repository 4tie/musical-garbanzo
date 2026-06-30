'use client';

import { ReactNode } from 'react';
import Sidebar from './Sidebar';
import TopHeader from './TopHeader';
import { SystemStatusResponse } from '@/lib/types';

interface AppShellProps {
  children: ReactNode;
  pageTitle?: string;
  systemStatus?: SystemStatusResponse | null;
  drawer?: ReactNode;
  onRefresh?: () => void;
  refreshDisabled?: boolean;
}

export default function AppShell({
  children,
  pageTitle,
  systemStatus,
  drawer,
  onRefresh,
  refreshDisabled = false,
}: AppShellProps) {
  return (
    <div className="flex h-screen bg-[var(--app-bg)] text-[var(--app-text)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <TopHeader
          pageTitle={pageTitle}
          systemStatus={systemStatus}
          onRefresh={onRefresh}
          refreshDisabled={refreshDisabled}
        />
        <div className="flex min-h-0 flex-1">
          <main className="min-w-0 flex-1 overflow-auto">
            <div className="page-fade mx-auto w-full max-w-7xl p-5 lg:p-6">{children}</div>
          </main>
          {drawer}
        </div>
      </div>
    </div>
  );
}
