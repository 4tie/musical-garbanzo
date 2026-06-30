import { ReactNode } from 'react';

interface FormFieldProps {
  label: string;
  htmlFor?: string;
  required?: boolean;
  error?: string;
  description?: string;
  children: ReactNode;
  className?: string;
}

export default function FormField({
  label,
  htmlFor,
  required = false,
  error,
  description,
  children,
  className = '',
}: FormFieldProps) {
  return (
    <div className={['flex flex-col gap-1.5', className].join(' ')}>
      <label htmlFor={htmlFor} className="text-sm font-medium text-[var(--app-text)]">
        {label}
        {required && <span className="ml-1 text-[var(--app-danger)]">*</span>}
      </label>
      {children}
      {description && (
        <p className="text-xs leading-5 text-[var(--app-text-muted)]">{description}</p>
      )}
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
