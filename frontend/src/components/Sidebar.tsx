'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { name: 'Dashboard', path: '/', code: 'DB' },
  { name: 'Runs', path: '/runs', code: 'RN' },
  { name: 'Baseline', path: '/baseline', code: 'BL' },
  { name: 'Optimization', path: '/optimization', code: 'OP' },
  { name: 'Validation', path: '/validation', code: 'VL' },
  { name: 'Strategies', path: '/strategies', code: 'ST' },
  { name: 'Reports', path: '/reports', code: 'RP' },
  { name: 'Settings', path: '/settings', code: 'SE' },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r border-[var(--app-border)] bg-[var(--app-surface-muted)]">
      <div className="border-b border-[var(--app-border)] px-5 py-5">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-sm font-semibold text-[var(--app-accent)]">
            HER
          </div>
          <div>
            <h1 className="text-base font-semibold text-[var(--app-text)]">Command Center</h1>
            <p className="text-xs text-[var(--app-text-subtle)]">Validation dashboard</p>
          </div>
        </div>
      </div>
      <nav className="flex-1 overflow-auto p-3" aria-label="Primary navigation">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              item.path === '/' ? pathname === '/' : pathname.startsWith(item.path);
            return (
              <li key={item.path}>
                <Link
                  href={item.path}
                  className={[
                    'flex h-10 items-center gap-3 rounded-[var(--app-radius)] px-3 text-sm font-medium transition-colors',
                    isActive
                      ? 'border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
                      : 'border border-transparent text-[var(--app-text-muted)] hover:bg-[var(--app-surface)] hover:text-[var(--app-text)]',
                  ].join(' ')}
                >
                  <span className="flex h-6 w-7 items-center justify-center rounded-[6px] bg-[var(--app-surface)] text-[10px] font-semibold">
                    {item.code}
                  </span>
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="border-t border-[var(--app-border)] p-4">
        <p className="text-xs leading-5 text-[var(--app-text-subtle)]">
          Read-only foundation. No live trading actions are available.
        </p>
      </div>
    </aside>
  );
}
