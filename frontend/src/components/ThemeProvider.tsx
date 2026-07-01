'use client';

import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from 'react';

export type ThemeMode = 'dark' | 'light' | 'system';
export type AccentPreset = 'emerald' | 'blue' | 'purple' | 'amber' | 'rose' | 'cyan' | 'neutral';
export type TableDensity = 'comfortable' | 'compact';

interface ThemeSettingsState {
  mode: ThemeMode;
  accent: AccentPreset;
  reducedMotion: boolean;
  density: TableDensity;
}

interface ThemeContextValue extends ThemeSettingsState {
  setMode: (mode: ThemeMode) => void;
  setAccent: (accent: AccentPreset) => void;
  setReducedMotion: (enabled: boolean) => void;
  setDensity: (density: TableDensity) => void;
}

const STORAGE_KEY = 'her-command-center-theme-v1';
const DEFAULT_SETTINGS: ThemeSettingsState = {
  mode: 'dark',
  accent: 'cyan',
  reducedMotion: false,
  density: 'comfortable',
};

const ThemeContext = createContext<ThemeContextValue | null>(null);

export const ACCENT_PRESETS: AccentPreset[] = [
  'emerald',
  'blue',
  'purple',
  'amber',
  'rose',
  'cyan',
  'neutral',
];

export function useThemeSettings() {
  const context = useContext(ThemeContext);
  if (!context) {
    throw new Error('useThemeSettings must be used inside ThemeProvider');
  }
  return context;
}

export default function ThemeProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<ThemeSettingsState>(() => readStoredSettings());

  useEffect(() => {
    const root = document.documentElement;
    const media = window.matchMedia('(prefers-color-scheme: dark)');

    const apply = () => {
      const effectiveTheme =
        settings.mode === 'system' ? (media.matches ? 'dark' : 'light') : settings.mode;

      root.dataset.theme = effectiveTheme;
      root.dataset.themeMode = settings.mode;
      root.dataset.accent = settings.accent;
      root.dataset.reducedMotion = String(settings.reducedMotion);
      root.dataset.density = settings.density;
    };

    apply();
    media.addEventListener('change', apply);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(settings));

    return () => media.removeEventListener('change', apply);
  }, [settings]);

  const value = useMemo<ThemeContextValue>(
    () => ({
      ...settings,
      setMode: (mode) => setSettings((current) => ({ ...current, mode })),
      setAccent: (accent) => setSettings((current) => ({ ...current, accent })),
      setReducedMotion: (reducedMotion) =>
        setSettings((current) => ({ ...current, reducedMotion })),
      setDensity: (density) => setSettings((current) => ({ ...current, density })),
    }),
    [settings],
  );

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

function readStoredSettings(): ThemeSettingsState {
  if (typeof window === 'undefined') {
    return DEFAULT_SETTINGS;
  }

  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) {
      return DEFAULT_SETTINGS;
    }

    const parsed = JSON.parse(raw) as Partial<ThemeSettingsState>;
    return {
      mode: isThemeMode(parsed.mode) ? parsed.mode : DEFAULT_SETTINGS.mode,
      accent: isAccentPreset(parsed.accent) ? parsed.accent : DEFAULT_SETTINGS.accent,
      reducedMotion:
        typeof parsed.reducedMotion === 'boolean'
          ? parsed.reducedMotion
          : DEFAULT_SETTINGS.reducedMotion,
      density: isTableDensity(parsed.density) ? parsed.density : DEFAULT_SETTINGS.density,
    };
  } catch {
    return DEFAULT_SETTINGS;
  }
}

function isThemeMode(value: unknown): value is ThemeMode {
  return value === 'dark' || value === 'light' || value === 'system';
}

function isAccentPreset(value: unknown): value is AccentPreset {
  return ACCENT_PRESETS.includes(value as AccentPreset);
}

function isTableDensity(value: unknown): value is TableDensity {
  return value === 'comfortable' || value === 'compact';
}
