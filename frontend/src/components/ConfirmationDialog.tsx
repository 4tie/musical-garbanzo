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
  days?: number;
  timerange?: string;
  downloadMissingData?: boolean;
  isHyperopt?: boolean;
  isLoading?: boolean;
  confirmEnabled?: boolean;
  children?: ReactNode;
}

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
  downloadMissingData = false,
  isHyperopt = false,
  isLoading = false,
  confirmEnabled = false,
  children,
}: ConfirmationDialogProps) {
  // Handle Escape key to close dialog
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !isLoading) {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose, isLoading]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirmation-title"
    >
      <div className="mx-4 max-w-lg w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-6 shadow-lg">
        <h2 id="confirmation-title" className="text-lg font-semibold text-[var(--app-text)]">
          {title}
        </h2>

        <div className="mt-4 space-y-4">
          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
            <h3 className="text-sm font-medium text-[var(--app-text)]">Action Summary</h3>
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-[var(--app-text-muted)]">Action</dt>
                <dd className="font-medium text-[var(--app-text)]">{actionName}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--app-text-muted)]">Strategy</dt>
                <dd className="font-medium text-[var(--app-text)]">{strategyName}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--app-text-muted)]">Pairs</dt>
                <dd className="font-medium text-[var(--app-text)]">{pairs.join(', ')}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-[var(--app-text-muted)]">Timeframe</dt>
                <dd className="font-medium text-[var(--app-text)]">{timeframe}</dd>
              </div>
              {days && (
                <div className="flex justify-between">
                  <dt className="text-[var(--app-text-muted)]">Days</dt>
                  <dd className="font-medium text-[var(--app-text)]">{days}</dd>
                </div>
              )}
              {timerange && (
                <div className="flex justify-between">
                  <dt className="text-[var(--app-text-muted)]">Timerange</dt>
                  <dd className="font-medium text-[var(--app-text)]">{timerange}</dd>
                </div>
              )}
              {downloadMissingData && (
                <div className="flex justify-between">
                  <dt className="text-[var(--app-text-muted)]">Data Download</dt>
                  <dd className="font-medium text-[var(--app-warning)]">Allowed</dd>
                </div>
              )}
              {isHyperopt && (
                <div className="flex justify-between">
                  <dt className="text-[var(--app-text-muted)]">Hyperopt</dt>
                  <dd className="font-medium text-[var(--app-accent)]">Enabled</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="rounded-[var(--app-radius)] border border-[rgb(245_158_11_/_0.38)] bg-[rgb(245_158_11_/_0.12)] p-4">
            <h3 className="text-sm font-medium text-[var(--app-warning)]">Resource Warning</h3>
            <p className="mt-1 text-sm leading-6 text-[var(--app-text-muted)]">
              This action will run a local validation workflow that may take significant time and
              computational resources depending on your configuration.
            </p>
          </div>

          <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
            <h3 className="text-sm font-medium text-[var(--app-text)]">Safety Notes</h3>
            <ul className="mt-2 space-y-1 text-sm leading-6 text-[var(--app-text-muted)]">
              <li>• No live trading will be performed</li>
              <li>• No exchange orders will be placed</li>
              <li>• The result may be rejected by decision gates</li>
              <li>• A completed pipeline does not mean the strategy is approved</li>
            </ul>
          </div>

          {children}
        </div>

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="ghost" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm} disabled={isLoading || !confirmEnabled}>
            {isLoading ? 'Starting...' : 'Confirm and Start'}
          </Button>
        </div>
      </div>
    </div>
  );
}
