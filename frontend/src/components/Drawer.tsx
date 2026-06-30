'use client';

import { useEffect } from 'react';
import { ReactNode } from 'react';
import Button from './Button';

interface DrawerProps {
  open: boolean;
  title: string;
  children: ReactNode;
  onClose: () => void;
}

export default function Drawer({ open, title, children, onClose }: DrawerProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onClose();
      }
    }

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onClose]);

  if (!open) {
    return null;
  }

  return (
    <aside className="drawer-panel w-full border-l border-[var(--app-border)] bg-[var(--app-surface)] shadow-[var(--app-shadow)] md:w-96">
      <div className="flex h-full flex-col">
        <div className="flex items-center justify-between border-b border-[var(--app-border)] px-4 py-3">
          <h2 className="text-sm font-semibold text-[var(--app-text)]">{title}</h2>
          <Button size="sm" variant="ghost" onClick={onClose} aria-label="Close drawer">
            Close
          </Button>
        </div>
        <div className="flex-1 overflow-auto p-4">{children}</div>
      </div>
    </aside>
  );
}
