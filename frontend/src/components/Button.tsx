import { ButtonHTMLAttributes, ReactNode } from 'react';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger';
type ButtonSize = 'sm' | 'md';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  children: ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
}

const variantClasses: Record<ButtonVariant, string> = {
  primary:
    'border-[var(--app-accent-border)] bg-[var(--app-accent)] text-white hover:bg-[var(--app-accent-strong)] shadow-sm',
  secondary:
    'border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-text)] hover:border-[var(--app-border-strong)] hover:bg-[var(--app-surface-card)]',
  ghost:
    'border-transparent bg-transparent text-[var(--app-text-muted)] hover:bg-[var(--app-surface-muted)] hover:text-[var(--app-text)]',
  danger:
    'border-[rgb(239_68_68_/_0.30)] bg-[rgb(239_68_68_/_0.09)] text-[var(--app-danger)] hover:bg-[rgb(239_68_68_/_0.16)]',
};

const sizeClasses: Record<ButtonSize, string> = {
  sm: 'h-8 px-3 text-xs gap-1.5',
  md: 'h-9 px-3.5 text-sm gap-2',
};

export default function Button({
  children,
  className = '',
  variant = 'secondary',
  size = 'md',
  type = 'button',
  ...props
}: ButtonProps) {
  return (
    <button
      type={type}
      className={[
        'inline-flex items-center justify-center rounded-[var(--app-radius)] border font-medium transition-colors',
        'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]',
        'disabled:cursor-not-allowed disabled:opacity-45',
        variantClasses[variant],
        sizeClasses[size],
        className,
      ].join(' ')}
      {...props}
    >
      {children}
    </button>
  );
}
