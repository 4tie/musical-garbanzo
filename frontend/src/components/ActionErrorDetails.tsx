import { ReactNode, useState } from 'react';
import Button from './Button';

interface ActionErrorDetailsProps {
  title?: string;
  stage?: string;
  errorCode?: string;
  runId?: string;
  artifactLink?: string;
  reportLink?: string;
  errors: string[];
  warnings?: string[];
  nextActions?: string[];
  technicalDetails?: string;
  children?: ReactNode;
}

export default function ActionErrorDetails({
  title = 'Error Details',
  stage,
  errorCode,
  runId,
  artifactLink,
  reportLink,
  errors,
  warnings = [],
  nextActions = [],
  technicalDetails,
  children,
}: ActionErrorDetailsProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyDebug = () => {
    const debugInfo = {
      actionType: title,
      runId: runId || 'N/A',
      stage: stage || 'N/A',
      errorCode: errorCode || 'N/A',
      status: 'failed',
      error: errors[0] || 'N/A',
      timestamp: new Date().toISOString(),
    };
    
    navigator.clipboard.writeText(JSON.stringify(debugInfo, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-5">
      <div className="flex items-start justify-between gap-4">
        <h3 className="text-base font-semibold text-[var(--app-text)]">{title}</h3>
        <Button variant="secondary" size="sm" onClick={handleCopyDebug}>
          {copied ? 'Copied!' : 'Copy Debug Info'}
        </Button>
      </div>

      {(stage || errorCode || runId) && (
        <div className="mt-4 grid grid-cols-2 gap-2 text-xs">
          {stage && (
            <div>
              <span className="text-[var(--app-text-muted)]">Stage:</span>
              <span className="ml-2 text-[var(--app-text)]">{stage}</span>
            </div>
          )}
          {errorCode && (
            <div>
              <span className="text-[var(--app-text-muted)]">Error Code:</span>
              <span className="ml-2 text-[var(--app-text)]">{errorCode}</span>
            </div>
          )}
          {runId && (
            <div>
              <span className="text-[var(--app-text-muted)]">Run ID:</span>
              <span className="ml-2 text-[var(--app-text)] font-mono">{runId}</span>
            </div>
          )}
        </div>
      )}

      {errors.length > 0 && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-danger)]">Errors</h4>
          <ul className="mt-2 space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
            {errors.map((error, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-[var(--app-danger)]">•</span>
                <span>{error}</span>
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
          <h4 className="text-sm font-medium text-[var(--app-text)]">Suggested Next Actions</h4>
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

      {(artifactLink || reportLink) && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-text)]">Links</h4>
          <div className="mt-2 space-y-1 text-sm">
            {artifactLink && (
              <a href={artifactLink} className="text-[var(--app-accent)] hover:underline">
                View Artifact
              </a>
            )}
            {reportLink && (
              <a href={reportLink} className="text-[var(--app-accent)] hover:underline">
                View Report
              </a>
            )}
          </div>
        </div>
      )}

      {technicalDetails && (
        <div className="mt-4">
          <h4 className="text-sm font-medium text-[var(--app-text)]">Technical Details</h4>
          <div className="mt-2 rounded-[var(--app-radius)] bg-[var(--app-surface-raised)] p-3 text-xs font-mono text-[var(--app-text-muted)]">
            {technicalDetails}
          </div>
        </div>
      )}

      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
