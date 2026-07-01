import { ReactNode, useEffect } from 'react';
import Button from './Button';

interface ConfirmationDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  actionName: string;
  strategyName: string;
  pairs: string[];
  timeframe: string;
  /** Legacy: display as "Days" row when provided and timerange not provided */
  days?: number;
  timerange?: string;
  /** When true, show "Data checked and downloaded automatically" instead of download row */
  autoDataDownload?: boolean;
  /** Legacy: shows "Data Download: Allowed" warning row */
  downloadMissingData?: boolean;
  /** Optimization-specific: show Risk Profile row */
  riskProfile?: string;
  /** Optimization-specific: show Exchange row */
  exchange?: string;
  /** Optimization-specific: show Epochs row */
  epochsCount?: number;
  isHyperopt?: boolean;
  isLoading?: boolean;
  confirmEnabled?: boolean;
  safetyDisclaimer?: string;
  children?: ReactNode;
}

const RISK_LABELS: Record<string, string> = {
  conservative: 'Conservative (Lower Risk)',
  balanced: 'Balanced',
  aggressive: 'Aggressive',
};

export default function ConfirmationDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  actionName,
  strategyName,
  pairs,
  timeframe,
  days,
  timerange,
  autoDataDownload = false,
  downloadMissingData = false,
  riskProfile,
  exchange,
  epochsCount,
  isHyperopt = false,
  isLoading = false,
  confirmEnabled = false,
  safetyDisclaimer,
  children,
}: ConfirmationDialogProps) {
  useEffect(() => {
    if (!isOpen) return;
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) onClose();
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  const pairDisplay = pairs.length > 6
    ? `${pairs.slice(0, 5).join(', ')} + ${pairs.length - 5} more`
    : pairs.join(', ');

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirmation-title"
    >
      <div className="mx-4 max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 id="confirmation-title" className="text-base font-semibold text-[var(--app-text)]">
          {title}
        </h2>

        <div className="mt-4 space-y-3">
          {/* Action Summary */}
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--app-text-subtle)]">
              Configuration
            </h3>
            <dl className="mt-3 space-y-2 text-sm">
              <Row label="Action" value={actionName} />
              <Row label="Strategy" value={strategyName} />
              {riskProfile && (
                <Row label="Risk Profile" value={RISK_LABELS[riskProfile] ?? riskProfile} />
              )}
              {exchange && (
                <Row label="Exchange" value={exchange.charAt(0).toUpperCase() + exchange.slice(1)} />
              )}
              <Row label="Pairs" value={`${pairs.length} pair${pairs.length === 1 ? '' : 's'}: ${pairDisplay}`} />
              <Row label="Timeframe" value={timeframe} />
              {timerange && <Row label="Timerange" value={timerange} />}
              {!timerange && days && <Row label="Days" value={String(days)} />}
              {epochsCount && <Row label="Epochs" value={String(epochsCount)} />}
              {isHyperopt && <Row label="Hyperopt" value="Enabled" accent />}
              {autoDataDownload && (
                <Row label="Data Download" value="Automatic — checked and downloaded if missing" />
              )}
              {!autoDataDownload && downloadMissingData && (
                <Row label="Data Download" value="Allowed" warn />
              )}
            </dl>
          </div>

          {/* Resource Warning */}
          <div className="rounded-[var(--app-radius)] border border-[rgb(245_158_11_/_0.30)] bg-[rgb(245_158_11_/_0.08)] p-3">
            <h3 className="text-xs font-semibold text-[var(--app-warning)]">Resource Warning</h3>
            <p className="mt-1 text-xs leading-5 text-[var(--app-text-muted)]">
              This will run a local validation workflow that may take significant time and computational
              resources depending on your configuration.
            </p>
          </div>

          {/* Safety Disclaimer */}
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
            <h3 className="text-xs font-semibold text-[var(--app-text)]">Safety</h3>
            <p className="mt-1.5 text-xs leading-5 text-[var(--app-text-muted)]">
              {safetyDisclaimer ??
                'Optimization is historical evidence only. It is not strategy approval, export, ' +
                'live-trading authorization, or a guarantee of future performance.'}
            </p>
            <ul className="mt-2 space-y-0.5 text-xs leading-5 text-[var(--app-text-subtle)]">
              <li>• No live trades will be placed</li>
              <li>• No exchange orders will be created</li>
              <li>• Best trial is not automatically approved</li>
              <li>• Result may still be rejected by decision gates</li>
            </ul>
          </div>

          {children}
        </div>

        <div className="mt-5 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} disabled={isLoading || !confirmEnabled}>
            {isLoading ? 'Starting…' : 'Confirm and Start'}
          </Button>
        </div>
      </div>
    </div>
  );
}

function Row({
  label,
  value,
  accent = false,
  warn = false,
}: {
  label: string;
  value: string;
  accent?: boolean;
  warn?: boolean;
}) {
  return (
    <div className="flex justify-between gap-3">
      <dt className="text-[var(--app-text-muted)]">{label}</dt>
      <dd
        className={[
          'text-right font-medium',
          accent ? 'text-[var(--app-accent)]' : warn ? 'text-[var(--app-warning)]' : 'text-[var(--app-text)]',
        ].join(' ')}
      >
        {value}
      </dd>
    </div>
  );
}
