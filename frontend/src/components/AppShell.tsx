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
    <div className="app-shell-root flex h-screen overflow-hidden text-[var(--app-text)]">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopHeader
          pageTitle={pageTitle}
          systemStatus={systemStatus}
          onRefresh={onRefresh}
          refreshDisabled={refreshDisabled}
        />
        <div className="flex min-h-0 flex-1">
          <main className="app-main-scroll min-w-0 flex-1 overflow-y-auto">
            <div className="page-fade mx-auto w-full max-w-[1400px] px-4 py-5 sm:px-5 lg:px-7 lg:py-6">
              {children}
            </div>
          </main>
          {drawer}
        </div>
      </div>
    </div>
  );
}
