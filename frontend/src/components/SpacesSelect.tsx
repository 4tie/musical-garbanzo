import { ChangeEvent } from 'react';

interface SpacesSelectProps {
  value: string[];
  onChange: (value: string[]) => void;
  error?: string;
}

const ALLOWED_SPACES = [
  { value: 'buy', label: 'Buy signals' },
  { value: 'sell', label: 'Sell signals' },
] as const;

const LOCKED_SPACES = [
  { value: 'roi', label: 'ROI (locked)' },
  { value: 'stoploss', label: 'Stoploss (locked)' },
  { value: 'trailing', label: 'Trailing stop (locked)' },
  { value: 'protection', label: 'Protection (locked)' },
] as const;

export default function SpacesSelect({ value, onChange, error }: SpacesSelectProps) {
  // Sanitize value to only include allowed spaces
  const sanitizedValue = value.filter((s) => ALLOWED_SPACES.some((as) => as.value === s));

  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const space = e.target.value;
    if (e.target.checked) {
      onChange([...sanitizedValue, space]);
    } else {
      onChange(sanitizedValue.filter((s) => s !== space));
    }
  };

  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex flex-wrap gap-3">
        {ALLOWED_SPACES.map((space) => (
          <label key={space.value} className="flex items-center gap-2 text-sm text-[var(--app-text)]">
            <input
              type="checkbox"
              value={space.value}
              checked={sanitizedValue.includes(space.value)}
              onChange={handleChange}
              className="h-4 w-4 rounded border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
            />
            <span>{space.label}</span>
          </label>
        ))}
        {LOCKED_SPACES.map((space) => (
          <span key={space.value} className="flex items-center gap-2 text-sm text-[var(--app-text-muted)]">
            <span className="h-4 w-4 rounded border border-[var(--app-border)] bg-[var(--app-surface-disabled)] flex items-center justify-center text-[var(--app-text-muted)] text-xs">
              🔒
            </span>
            <span>{space.label}</span>
          </span>
        ))}
      </div>
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        Select which parameter spaces to optimize. Buy and sell are recommended for most strategies. ROI, stoploss, trailing, and protection are locked.
      </p>
    </div>
  );
}
