interface TimeframeSelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

// UI-allowed timeframes for safe run controls
// These are frontend constants for UI selection
// Backend may support additional timeframes
const TIMEFRAMES = [
  '1m',
  '3m',
  '5m',
  '15m',
  '30m',
  '1h',
  '4h',
  '1d',
] as const;

export default function TimeframeSelect({ value, onChange, error, disabled }: TimeframeSelectProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <select
        value={value}
        disabled={disabled}
        onChange={(e) => onChange(e.target.value)}
        className={[
          'h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-50',
          error ? 'border-[var(--app-danger)]' : '',
        ].join(' ')}
      >
        <option value="">Select timeframe</option>
        {TIMEFRAMES.map((tf) => (
          <option key={tf} value={tf}>
            {tf}
          </option>
        ))}
      </select>
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        Select the candlestick timeframe for backtesting
      </p>
    </div>
  );
}
