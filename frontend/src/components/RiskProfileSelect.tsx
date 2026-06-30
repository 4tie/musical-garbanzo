interface RiskProfileSelectProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
}

// Risk profiles matching backend schema values
// Backend uses: conservative, balanced, aggressive
const RISK_PROFILES = [
  { value: 'conservative', label: 'Conservative' },
  { value: 'balanced', label: 'Balanced' },
  { value: 'aggressive', label: 'Aggressive' },
] as const;

export default function RiskProfileSelect({ value, onChange, error, disabled }: RiskProfileSelectProps) {
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
        <option value="">Select risk profile</option>
        {RISK_PROFILES.map((rp) => (
          <option key={rp.value} value={rp.value}>
            {rp.label}
          </option>
        ))}
      </select>
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        Risk profile for decision evaluation (default: balanced)
      </p>
    </div>
  );
}
