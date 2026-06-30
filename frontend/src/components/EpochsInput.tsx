interface EpochsInputProps {
  value: number;
  onChange: (value: number) => void;
  error?: string;
  disabled?: boolean;
  placeholder?: string;
  min?: number;
  max?: number;
}

export default function EpochsInput({ value, onChange, error, disabled, placeholder, min = 1, max = 200 }: EpochsInputProps) {
  return (
    <div className="flex flex-col gap-1.5">
      <input
        type="number"
        min={min}
        max={max}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className={[
          'h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] placeholder:text-[var(--app-text-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-50',
          error ? 'border-[var(--app-danger)]' : '',
        ].join(' ')}
      />
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        Number of hyperopt epochs (1-200). Higher values take longer but may find better parameters.
      </p>
    </div>
  );
}
