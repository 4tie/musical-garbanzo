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

const statusConfig: Record<StepStatus, { icon: ReactNode; classes: string; dotClasses: string }> = {
  not_started: {
    icon: <span className="text-[10px] font-bold">–</span>,
    classes: 'border-[var(--app-border)] bg-[var(--app-surface-muted)] text-[var(--app-text-subtle)]',
    dotClasses: 'bg-[var(--app-border)]',
  },
  running: {
    icon: <span className="text-[10px] font-bold animate-pulse">▶</span>,
    classes: 'border-[rgb(56_189_248_/_0.4)] bg-[rgb(56_189_248_/_0.10)] text-[var(--app-info)]',
    dotClasses: 'bg-[var(--app-info)]',
  },
  passed: {
    icon: <span className="text-[10px] font-bold">✓</span>,
    classes: 'border-[rgb(34_197_94_/_0.4)] bg-[rgb(34_197_94_/_0.10)] text-[var(--app-success)]',
    dotClasses: 'bg-[var(--app-success)]',
  },
  failed: {
    icon: <span className="text-[10px] font-bold">✕</span>,
    classes: 'border-[rgb(239_68_68_/_0.4)] bg-[rgb(239_68_68_/_0.10)] text-[var(--app-danger)]',
    dotClasses: 'bg-[var(--app-danger)]',
  },
  blocked: {
    icon: <span className="text-[10px] font-bold">⊘</span>,
    classes: 'border-[rgb(245_158_11_/_0.4)] bg-[rgb(245_158_11_/_0.10)] text-[var(--app-warning)]',
    dotClasses: 'bg-[var(--app-warning)]',
  },
  skipped: {
    icon: <span className="text-[10px] font-bold">→</span>,
    classes: 'border-[var(--app-border)] bg-[var(--app-surface-muted)] text-[var(--app-text-subtle)]',
    dotClasses: 'bg-[var(--app-border)]',
  },
};

function formatTs(ts: string | null | undefined): string | null {
  if (!ts) return null;
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

export default function WorkflowStepper({ steps, orientation = 'vertical' }: WorkflowStepperProps) {
  if (orientation === 'horizontal') {
    return (
      <div className="flex items-start gap-0 overflow-x-auto">
        {steps.map((step, index) => {
          const cfg = statusConfig[step.status];
          const isLast = index === steps.length - 1;
          return (
            <div key={step.id} className="flex min-w-0 shrink-0 items-start">
              <div className="flex flex-col items-center">
                <div className={[
                  'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border',
                  cfg.classes,
                ].join(' ')}>
                  {cfg.icon}
                </div>
                <div className="mt-2 px-2 text-center">
                  {step.href ? (
                    <a href={step.href} className="text-xs font-medium text-[var(--app-text)] hover:text-[var(--app-accent)] transition-colors">
                      {step.label}
                    </a>
                  ) : (
                    <p className="text-xs font-medium text-[var(--app-text-muted)]">{step.label}</p>
                  )}
                  {step.message && (
                    <p className="mt-0.5 text-[11px] text-[var(--app-text-subtle)]">{step.message}</p>
                  )}
                  {step.timestamp && (
                    <p className="mt-0.5 text-[10px] text-[var(--app-text-subtle)]">{formatTs(step.timestamp)}</p>
                  )}
                </div>
              </div>
              {!isLast && (
                <div className="mt-4 h-px w-8 shrink-0 bg-[var(--app-border)]" />
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return (
    <div className="space-y-0">
      {steps.map((step, index) => {
        const cfg = statusConfig[step.status];
        const isLast = index === steps.length - 1;
        return (
          <div key={step.id} className="flex gap-3">
            <div className="flex flex-col items-center">
              <div className={[
                'flex h-8 w-8 shrink-0 items-center justify-center rounded-full border',
                cfg.classes,
              ].join(' ')}>
                {cfg.icon}
              </div>
              {!isLast && (
                <div className="w-px flex-1 bg-[var(--app-border)] my-1" style={{ minHeight: '24px' }} />
              )}
            </div>
            <div className="min-w-0 pb-5 pt-1">
              {step.href ? (
                <a href={step.href} className="text-sm font-semibold text-[var(--app-text)] hover:text-[var(--app-accent)] transition-colors">
                  {step.label}
                </a>
              ) : (
                <p className="text-sm font-semibold text-[var(--app-text)]">{step.label}</p>
              )}
              {step.message && (
                <p className="mt-0.5 text-xs leading-5 text-[var(--app-text-muted)]">{step.message}</p>
              )}
              {step.timestamp && (
                <p className="mt-0.5 text-[11px] text-[var(--app-text-subtle)]">{formatTs(step.timestamp)}</p>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
