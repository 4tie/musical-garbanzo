import { ChangeEvent } from 'react';

interface ConfirmationChecklistProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  error?: string;
}

export default function ConfirmationChecklist({ checked, onChange, error }: ConfirmationChecklistProps) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    onChange(e.target.checked);
  };

  return (
    <div className="flex flex-col gap-1.5">
      <label className="flex items-start gap-3 text-sm text-[var(--app-text)]">
        <input
          type="checkbox"
          checked={checked}
          onChange={handleChange}
          className="mt-0.5 h-4 w-4 shrink-0 rounded border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
        />
        <span className="leading-6">
          I understand this will run a local validation workflow and may take time.
        </span>
      </label>
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
