import { ReactNode } from 'react';

type ActionResultType = 'success' | 'controlled_failure' | 'error';

interface ActionResultBannerProps {
  type: ActionResultType;
  title: string;
  children: ReactNode;
  runId?: string;
  detailHref?: string;
}

const typeConfig: Record<ActionResultType, { borderColor: string; bgColor: string; textColor: string }> = {
  success: {
    borderColor: 'rgb(34_197_94_/_0.38)',
    bgColor: 'rgb(34_197_94_/_0.12)',
    textColor: 'rgb(34_197_94)',
  },
  controlled_failure: {
    borderColor: 'rgb(245_158_11_/_0.38)',
    bgColor: 'rgb(245_158_11_/_0.12)',
    textColor: 'rgb(245_158_11)',
  },
  error: {
    borderColor: 'rgb(239_68_68_/_0.38)',
    bgColor: 'rgb(239_68_68_/_0.12)',
    textColor: 'rgb(239_68_68)',
  },
};

export default function ActionResultBanner({
  type,
  title,
  children,
  runId,
  detailHref,
}: ActionResultBannerProps) {
  const config = typeConfig[type];

  return (
    <div
      className="rounded-[var(--app-radius)] border p-4 text-sm"
      style={{
        borderColor: config.borderColor,
        backgroundColor: config.bgColor,
      }}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0 flex-1">
          <p className="font-semibold" style={{ color: config.textColor }}>
            {title}
          </p>
          <div className="mt-1 leading-6 text-[var(--app-text-muted)]">{children}</div>
          {runId && (
            <p className="mt-2 text-xs text-[var(--app-text-muted)]">
              Run ID: <code className="font-mono">{runId}</code>
            </p>
          )}
        </div>
        {detailHref && (
          <a
            href={detailHref}
            className="shrink-0 text-sm font-medium text-[var(--app-accent)] hover:underline"
          >
            View Details
          </a>
        )}
      </div>
    </div>
  );
}
