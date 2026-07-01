'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  name: string;
  path: string;
  code: string;
  primary?: boolean;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Discover',
    items: [
      { name: 'Strategy Journey', path: '/journey', code: 'JN', primary: true },
      { name: 'Dashboard', path: '/', code: 'DB' },
      { name: 'Strategies', path: '/strategies', code: 'ST' },
    ],
  },
  {
    label: 'Test',
    items: [
      { name: 'Runs', path: '/runs', code: 'RN' },
      { name: 'Baseline', path: '/baseline', code: 'BL' },
      { name: 'Optimization', path: '/optimization', code: 'OP' },
      { name: 'Validation', path: '/validation', code: 'VL' },
    ],
  },
  {
    label: 'Evidence',
    items: [
      { name: 'Results', path: '/results', code: 'RS' },
      { name: 'Reports', path: '/reports', code: 'RP' },
    ],
  },
  {
    label: 'System',
    items: [
      { name: 'Settings', path: '/settings', code: 'SE' },
    ],
  },
];

export default function Sidebar() {
  const pathname = usePathname();

  function isActive(path: string) {
    return path === '/' ? pathname === '/' : pathname.startsWith(path);
  }

  return (
    <aside
      className="hidden flex-col border-r border-[var(--app-border)] bg-[var(--app-bg-rail)] shadow-[var(--app-shadow-sm)] lg:flex"
      style={{ width: 'var(--app-sidebar-width)' }}
    >
      {/* Brand */}
      <div className="border-b border-[var(--app-border)] px-4 py-4">
        <div className="flex items-center gap-3">
        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-[11px] font-bold tracking-wider text-[var(--app-accent)] shadow-sm">
          HER
        </div>
        <div className="min-w-0">
          <p className="text-sm font-semibold leading-none text-[var(--app-text)]">AutoQuant</p>
          <p className="mt-1 text-[10px] font-medium uppercase leading-none tracking-[0.14em] text-[var(--app-text-subtle)]">Strategy Lab</p>
        </div>
        </div>
        <div className="mt-4 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 py-2">
          <p className="text-[11px] leading-4 text-[var(--app-text-muted)]">Local validation cockpit. Backend evidence remains the source of truth.</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-auto px-2.5 py-3" aria-label="Primary navigation">
        <div className="space-y-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1.5 px-2.5 text-[9px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">
                {group.label}
              </p>
              <ul className="space-y-px">
                {group.items.map((item) => {
                  const active = isActive(item.path);
                  return (
                    <li key={item.path}>
                      <Link
                        href={item.path}
                        className={[
                          'group flex h-9 items-center gap-2.5 rounded-[var(--app-radius)] px-2.5 text-[13px] font-medium transition-colors',
                          active
                            ? 'border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-[var(--app-accent)] shadow-[var(--app-shadow-sm)]'
                            : item.primary
                            ? 'border border-transparent text-[var(--app-text-muted)] hover:border-[var(--app-border)] hover:bg-[var(--app-surface-card)] hover:text-[var(--app-text)]'
                            : 'border border-transparent text-[var(--app-text-subtle)] hover:border-[var(--app-border)] hover:bg-[var(--app-surface-card)] hover:text-[var(--app-text-muted)]',
                        ].join(' ')}
                      >
                        <span
                          className={[
                            'flex h-[19px] w-[24px] shrink-0 items-center justify-center rounded-[var(--app-radius-sm)] text-[9px] font-semibold',
                            active
                              ? 'bg-[var(--app-accent)] text-[var(--app-accent-text)]'
                              : 'bg-[var(--app-border)] text-[var(--app-text-subtle)] group-hover:text-[var(--app-text-muted)]',
                          ].join(' ')}
                        >
                          {item.code}
                        </span>
                        <span className="min-w-0 truncate">{item.name}</span>
                        {item.primary && !active && (
                          <span className="ml-auto h-1 w-1 shrink-0 rounded-full bg-[var(--app-accent)] opacity-50" />
                        )}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="border-t border-[var(--app-border)] px-4 py-3">
        <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
          <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-[var(--app-text-subtle)]">Safety mode</p>
          <p className="mt-1 text-[11px] leading-4 text-[var(--app-text-muted)]">
            Evidence only. No live trading actions.
          </p>
        </div>
      </div>
    </aside>
  );
}
