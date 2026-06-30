'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

interface NavItem {
  name: string;
  path: string;
  code: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
}

const navGroups: NavGroup[] = [
  {
    label: 'Discover',
    items: [
      { name: 'Dashboard', path: '/', code: 'DB' },
      { name: 'Strategy Journey', path: '/journey', code: 'JN' },
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
    <aside className="flex w-60 shrink-0 flex-col border-r border-[var(--app-border)] bg-[var(--app-surface-muted)]">
      <div className="border-b border-[var(--app-border)] px-4 py-4">
        <div className="flex items-center gap-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-xs font-bold tracking-wider text-[var(--app-accent)]">
            HER
          </div>
          <div>
            <h1 className="text-sm font-semibold text-[var(--app-text)]">Command Center</h1>
            <p className="text-[11px] text-[var(--app-text-subtle)]">Strategy discovery</p>
          </div>
        </div>
      </div>

      <nav className="flex-1 overflow-auto px-3 py-3" aria-label="Primary navigation">
        <div className="space-y-5">
          {navGroups.map((group) => (
            <div key={group.label}>
              <p className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-widest text-[var(--app-text-subtle)]">
                {group.label}
              </p>
              <ul className="space-y-0.5">
                {group.items.map((item) => {
                  const active = isActive(item.path);
                  return (
                    <li key={item.path}>
                      <Link
                        href={item.path}
                        className={[
                          'flex h-9 items-center gap-2.5 rounded-[var(--app-radius)] px-2.5 text-sm font-medium transition-colors',
                          active
                            ? 'border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
                            : 'border border-transparent text-[var(--app-text-muted)] hover:bg-[var(--app-surface)] hover:text-[var(--app-text)]',
                        ].join(' ')}
                      >
                        <span className={[
                          'flex h-5 w-6 items-center justify-center rounded text-[9px] font-semibold',
                          active
                            ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
                            : 'bg-[var(--app-surface)] text-[var(--app-text-subtle)]',
                        ].join(' ')}>
                          {item.code}
                        </span>
                        {item.name}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </div>
      </nav>

      <div className="border-t border-[var(--app-border)] p-3">
        <p className="text-[11px] leading-5 text-[var(--app-text-subtle)]">
          Evidence only. No live trading actions.
        </p>
      </div>
    </aside>
  );
}
