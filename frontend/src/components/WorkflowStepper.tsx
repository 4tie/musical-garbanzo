import { ReactNode } from 'react';

export type StepStatus = 'not_started' | 'running' | 'passed' | 'failed' | 'blocked' | 'skipped';

export interface WorkflowStep {
  id: string;
  label: string;
  status: StepStatus;
  message?: string;
  timestamp?: string | null;
  href?: string;
}

interface WorkflowStepperProps {
  steps: WorkflowStep[];
  orientation?: 'horizontal' | 'vertical';
}

interface StepConfig {
  icon: ReactNode;
  circleClasses: string;
  connectorClasses: string;
  labelClasses: string;
}

const stepConfig: Record<StepStatus, StepConfig> = {
  not_started: {
    icon: <span className="text-[10px] font-semibold text-[var(--app-text-subtle)]">–</span>,
    circleClasses: 'border-[var(--app-border)] bg-[var(--app-surface-muted)]',
    connectorClasses: 'bg-[var(--app-border)]',
    labelClasses: 'text-[var(--app-text-subtle)]',
  },
  running: {
    icon: (
      <span className="relative flex h-2.5 w-2.5">
        <span className="absolute inset-0 animate-ping rounded-full bg-[var(--app-info)] opacity-60" />
        <span className="h-2.5 w-2.5 rounded-full bg-[var(--app-info)]" />
      </span>
    ),
    circleClasses: 'border-[rgb(56_189_248_/_0.36)] bg-[rgb(56_189_248_/_0.10)]',
    connectorClasses: 'bg-[var(--app-info)] opacity-30',
    labelClasses: 'text-[var(--app-info)]',
  },
  passed: {
    icon: (
      <svg className="h-3.5 w-3.5 text-[var(--app-success)]" viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M2.5 7.5L5.5 10.5L11.5 4" />
      </svg>
    ),
    circleClasses: 'border-[rgb(34_197_94_/_0.36)] bg-[rgb(34_197_94_/_0.10)]',
    connectorClasses: 'bg-[var(--app-success)] opacity-30',
    labelClasses: 'text-[var(--app-text)]',
  },
  failed: {
    icon: (
      <svg className="h-3 w-3 text-[var(--app-danger)]" viewBox="0 0 12 12" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
        <path d="M2 2l8 8M10 2l-8 8" />
      </svg>
    ),
    circleClasses: 'border-[rgb(239_68_68_/_0.36)] bg-[rgb(239_68_68_/_0.10)]',
    connectorClasses: 'bg-[var(--app-danger)] opacity-20',
    labelClasses: 'text-[var(--app-text)]',
  },
  blocked: {
    icon: <span className="text-[11px] font-semibold text-[var(--app-warning)]">!</span>,
    circleClasses: 'border-[rgb(245_158_11_/_0.36)] bg-[rgb(245_158_11_/_0.10)]',
    connectorClasses: 'bg-[var(--app-warning)] opacity-20',
    labelClasses: 'text-[var(--app-text)]',
  },
  skipped: {
    icon: <span className="text-[10px] text-[var(--app-text-subtle)]">›</span>,
    circleClasses: 'border-[var(--app-border)] bg-[var(--app-surface-muted)]',
    connectorClasses: 'bg-[var(--app-border)]',
    labelClasses: 'text-[var(--app-text-subtle)]',
  },
};

function fmtTs(ts: string | null | undefined): string | null {
  if (!ts) return null;
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit',
    });
  } catch { return ts; }
}

export default function WorkflowStepper({ steps, orientation = 'vertical' }: WorkflowStepperProps) {
  if (orientation === 'horizontal') {
    return (
      <div className="flex items-start gap-0 overflow-x-auto">
        {steps.map((step, index) => {
          const cfg = stepConfig[step.status];
          const isLast = index === steps.length - 1;
          return (
            <div key={step.id} className="flex min-w-0 shrink-0 items-start">
              <div className="flex flex-col items-center">
                <div className={[
                  'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2',
                  cfg.circleClasses,
                ].join(' ')}>
                  {cfg.icon}
                </div>
                <div className="mt-2 px-2 text-center">
                  {step.href ? (
                    <a href={step.href} className={['text-xs font-semibold transition-colors hover:text-[var(--app-accent)]', cfg.labelClasses].join(' ')}>
                      {step.label}
                    </a>
                  ) : (
                    <p className={['text-xs font-semibold', cfg.labelClasses].join(' ')}>{step.label}</p>
                  )}
                  {step.message && (
                    <p className="mt-0.5 text-[11px] text-[var(--app-text-subtle)]">{step.message}</p>
                  )}
                  {step.timestamp && (
                    <p className="mt-0.5 text-[10px] text-[var(--app-text-subtle)]">{fmtTs(step.timestamp)}</p>
                  )}
                </div>
              </div>
              {!isLast && (
                <div className={['mt-4 h-0.5 w-10 shrink-0', cfg.connectorClasses].join(' ')} />
              )}
            </div>
          );
        })}
      </div>
    );
  }

  // Vertical (default)
  return (
    <div className="space-y-0">
      {steps.map((step, index) => {
        const cfg = stepConfig[step.status];
        const isLast = index === steps.length - 1;
        const ts = fmtTs(step.timestamp);
        return (
          <div key={step.id} className="flex gap-4">
            {/* Icon + connector */}
            <div className="flex flex-col items-center">
              <div className={[
                'flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 shadow-sm',
                cfg.circleClasses,
              ].join(' ')}>
                {cfg.icon}
              </div>
              {!isLast && (
                <div className={['my-0.5 w-0.5 flex-1', cfg.connectorClasses].join(' ')} style={{ minHeight: '20px' }} />
              )}
            </div>

            {/* Content */}
            <div className={['min-w-0 flex-1', isLast ? 'pb-0' : 'pb-5'].join(' ')}>
              <div className="flex items-baseline justify-between gap-3 pt-1.5">
                {step.href ? (
                  <a
                    href={step.href}
                    className={[
                      'text-sm font-semibold transition-colors hover:text-[var(--app-accent)]',
                      cfg.labelClasses,
                    ].join(' ')}
                  >
                    {step.label}
                    <span className="ml-1 text-[var(--app-text-subtle)] opacity-60">↗</span>
                  </a>
                ) : (
                  <p className={['text-sm font-semibold', cfg.labelClasses].join(' ')}>{step.label}</p>
                )}
                {ts && (
                  <span className="shrink-0 text-[10px] text-[var(--app-text-subtle)]">{ts}</span>
                )}
              </div>
              {step.message && (
                <p className="mt-0.5 text-xs leading-5 text-[var(--app-text-muted)]">{step.message}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
