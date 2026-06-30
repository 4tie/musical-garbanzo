interface StrategyReadinessBlockedBannerProps {
  strategyName: string;
  readiness: string;
  issues: string[];
  warnings: string[];
  nextActions: string[];
}

export default function StrategyReadinessBlockedBanner({
  strategyName,
  readiness,
  issues,
  warnings,
  nextActions,
}: StrategyReadinessBlockedBannerProps) {
  const readinessLabel = readiness.replaceAll('_', ' ');
  const strategyDetailHref = `/strategies/${encodeURIComponent(strategyName)}`;

  return (
    <div className="rounded-[var(--app-radius)] border border-[rgb(239_68_68_/_0.38)] bg-[rgb(239_68_68_/_0.12)] p-5 text-sm">
      <div className="flex items-start justify-between gap-4">
        <div className="flex-1">
          <h3 className="text-base font-semibold text-[var(--app-danger)]">Strategy Not Ready</h3>
          <p className="mt-2 leading-6 text-[var(--app-text-muted)]">
            The strategy <span className="font-mono font-medium text-[var(--app-text)]">{strategyName}</span> is not ready for this action.
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <div>
          <span className="text-[var(--app-text-muted)]">Strategy:</span>
          <span className="ml-2 font-mono text-[var(--app-text)]">{strategyName}</span>
        </div>
        <div>
          <span className="text-[var(--app-text-muted)]">Readiness:</span>
          <span className="ml-2 font-medium text-[var(--app-danger)]">{readinessLabel}</span>
        </div>
      </div>

      {issues.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-danger)]">Issues</h4>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
            {issues.map((issue, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-danger)]">•</span>
                <span>{issue}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {warnings.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-warning)]">Warnings</h4>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
            {warnings.map((warning, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-warning)]">•</span>
                <span>{warning}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {nextActions.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-text)]">Next Actions</h4>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
            {nextActions.map((action, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-accent)]">→</span>
                <span>{action}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      <div className="mt-4 rounded-[var(--app-radius)] border border-[rgb(239_68_68_/_0.2)] bg-[rgb(239_68_68_/_0.05)] p-3 text-xs leading-5 text-[var(--app-text-muted)]">
        <p className="font-medium text-[var(--app-text)]">What happened:</p>
        <ul className="mt-1 space-y-1 ml-4">
          <li>• No run was started</li>
          <li>• No Freqtrade command was executed</li>
          <li>• No data was downloaded</li>
          <li>• No artifacts were created</li>
        </ul>
        <p className="mt-2 font-medium text-[var(--app-text)]">To fix:</p>
        <p className="mt-1">
          Fix the strategy in the Strategy Workspace first, then revalidate before starting this action.
        </p>
        <a
          href={strategyDetailHref}
          className="mt-2 inline-block text-[var(--app-accent)] hover:underline"
        >
          View Strategy in Workspace →
        </a>
      </div>
    </div>
  );
}
