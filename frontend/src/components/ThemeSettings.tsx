'use client';

import { ACCENT_PRESETS, AccentPreset, ThemeMode, useThemeSettings } from './ThemeProvider';

interface ThemeSettingsProps {
  compact?: boolean;
}

const themeModes: ThemeMode[] = ['dark', 'light', 'system'];

export default function ThemeSettings({ compact = false }: ThemeSettingsProps) {
  const { mode, accent, density, reducedMotion, setMode, setAccent, setDensity, setReducedMotion } =
    useThemeSettings();

  return (
    <div className={compact ? 'flex items-center gap-2' : 'grid gap-4 md:grid-cols-2'}>
      <label className={compact ? 'sr-only' : 'grid gap-2 text-sm text-[var(--app-text-muted)]'}>
        {!compact && <span>Theme mode</span>}
        <select
          value={mode}
          onChange={(event) => setMode(event.target.value as ThemeMode)}
          className="h-9 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-2 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
          aria-label="Theme mode"
        >
          {themeModes.map((item) => (
            <option key={item} value={item}>
              {labelize(item)}
            </option>
          ))}
        </select>
      </label>

      <label className={compact ? 'sr-only' : 'grid gap-2 text-sm text-[var(--app-text-muted)]'}>
        {!compact && <span>Accent color</span>}
        <select
          value={accent}
          onChange={(event) => setAccent(event.target.value as AccentPreset)}
          className="h-9 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-2 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
          aria-label="Accent color"
        >
          {ACCENT_PRESETS.map((item) => (
            <option key={item} value={item}>
              {labelize(item)}
            </option>
          ))}
        </select>
      </label>

      {!compact && (
        <>
          <label className="grid gap-2 text-sm text-[var(--app-text-muted)]">
            <span>Table density</span>
            <select
              value={density}
              onChange={(event) =>
                setDensity(event.target.value === 'compact' ? 'compact' : 'comfortable')
              }
              className="h-9 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-2 text-sm text-[var(--app-text)] outline-none focus:border-[var(--app-accent-border)]"
            >
              <option value="comfortable">Comfortable</option>
              <option value="compact">Compact</option>
            </select>
          </label>

          <label className="flex items-center justify-between gap-4 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 py-2 text-sm text-[var(--app-text-muted)]">
            <span>Reduced motion</span>
            <input
              type="checkbox"
              checked={reducedMotion}
              onChange={(event) => setReducedMotion(event.target.checked)}
              className="h-4 w-4 accent-[var(--app-accent)]"
            />
          </label>
        </>
      )}
    </div>
  );
}

function labelize(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
