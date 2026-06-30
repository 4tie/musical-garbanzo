'use client';

import { ReactNode } from 'react';

interface TabItem {
  id: string;
  label: string;
}

interface TabsProps {
  items: TabItem[];
  activeId: string;
  onChange: (id: string) => void;
  children?: ReactNode;
}

export default function Tabs({ items, activeId, onChange, children }: TabsProps) {
  return (
    <div>
      <div className="flex gap-1 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-1">
        {items.map((item) => {
          const active = item.id === activeId;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => onChange(item.id)}
              className={[
                'h-8 rounded-[6px] px-3 text-sm font-medium transition-colors',
                active
                  ? 'bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
                  : 'text-[var(--app-text-muted)] hover:text-[var(--app-text)]',
              ].join(' ')}
            >
              {item.label}
            </button>
          );
        })}
      </div>
      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
