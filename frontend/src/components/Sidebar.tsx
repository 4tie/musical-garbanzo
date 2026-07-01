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
      className="flex flex-col border-r border-[var(--app-border)] bg-[var(--app-surface-muted)]"
      style={{ width: 'var(--app-sidebar-width)' }}
    >
      {/* Brand */}
      <div className="flex items-center gap-3 border-b border-[var(--app-border)] px-4 py-[14px]">
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--app-radius-sm)] bg-[var(--app-accent)] text-[11px] font-bold tracking-wider text-white shadow-sm">
          HER
        </div>
        <div className="min-w-0">
          <p className="text-[13px] font-semibold leading-none text-[var(--app-text)]">AutoQuant</p>
          <p className="mt-0.5 text-[10px] leading-none text-[var(--app-text-subtle)]">Strategy Lab</p>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-auto px-2.5 py-3" aria-label="Primary navigation">
        <div className="space-y-4">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1 px-2.5 text-[9px] font-semibold uppercase tracking-[0.12em] text-[var(--app-text-subtle)]">
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
                          'group flex h-8 items-center gap-2.5 rounded-[var(--app-radius-sm)] px-2.5 text-[13px] font-medium transition-colors',
                          active
                            ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
                            : item.primary
                            ? 'text-[var(--app-text-muted)] hover:bg-[var(--app-surface-card)] hover:text-[var(--app-text)]'
                            : 'text-[var(--app-text-subtle)] hover:bg-[var(--app-surface-card)] hover:text-[var(--app-text-muted)]',
                        ].join(' ')}
                      >
                        <span
                          className={[
                            'flex h-[18px] w-[22px] shrink-0 items-center justify-center rounded text-[9px] font-semibold',
                            active
                              ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
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
        <p className="text-[10px] leading-4 text-[var(--app-text-subtle)]">
          Evidence only.
          <br />
          No live trading actions.
        </p>
      </div>
    </aside>
  );
}
