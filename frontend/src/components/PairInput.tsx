import { useMemo } from 'react';

interface PairInputProps {
  value: string;
  onChange: (value: string) => void;
  error?: string;
  disabled?: boolean;
  placeholder?: string;
}

// Validate pair format: BASE/QUOTE (e.g., BTC/USDT)
function isValidPairFormat(pair: string): boolean {
  const trimmed = pair.trim();
  if (!trimmed) return false;
  const parts = trimmed.split('/');
  if (parts.length !== 2) return false;
  const [base, quote] = parts;
  return base.length > 0 && quote.length > 0 && /^[A-Z0-9]+$/.test(base) && /^[A-Z0-9]+$/.test(quote);
}

export default function PairInput({ value, onChange, error, disabled, placeholder }: PairInputProps) {
  // Parse and normalize pairs
  const parsedPairs = useMemo(() => {
    if (!value) return [];
    return value
      .split(',')
      .map((p) => p.trim().toUpperCase())
      .filter((p) => p.length > 0);
  }, [value]);

  // Remove duplicates
  const uniquePairs = useMemo(() => {
    return Array.from(new Set(parsedPairs));
  }, [parsedPairs]);

  // Validate each pair format
  const invalidPairs = useMemo(() => {
    return uniquePairs.filter((p) => !isValidPairFormat(p));
  }, [uniquePairs]);

  const pairCount = uniquePairs.length;

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    onChange(newValue);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <input
        type="text"
        value={value}
        disabled={disabled}
        placeholder={placeholder}
        onChange={handleChange}
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
      {invalidPairs.length > 0 && (
        <p className="text-xs leading-5 text-[var(--app-warning)]">
          Invalid format: {invalidPairs.join(', ')} (use BASE/QUOTE format)
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        {pairCount > 0
          ? `${pairCount} pair${pairCount === 1 ? '' : 's'}: ${uniquePairs.join(', ')}`
          : 'Enter trading pairs separated by commas (e.g., BTC/USDT,ETH/USDT)'}
      </p>
    </div>
  );
}
