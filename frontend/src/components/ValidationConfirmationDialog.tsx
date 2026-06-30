'use client';

import { useEffect } from 'react';
import Button from './Button';

interface ValidationConfirmationDialogProps {
  open: boolean;
  strategyName: string;
  sourceType: string;
  sourceRunId: string | null;
  pairs: string[];
  timeframe: string;
  riskProfile: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function ValidationConfirmationDialog({
  open,
  strategyName,
  sourceType,
  sourceRunId,
  pairs,
  timeframe,
  riskProfile,
  onConfirm,
  onCancel,
}: ValidationConfirmationDialogProps) {
  useEffect(() => {
    if (!open) {
      return;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        onCancel();
      }
    }

    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [open, onCancel]);

  if (!open) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg border border-[var(--app-border)] bg-[var(--app-surface)] p-6 shadow-[var(--app-shadow)]">
        <h2 className="mb-4 text-lg font-semibold text-[var(--app-text)]">
          Run Validation
        </h2>

        <div className="mb-6 space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-[var(--app-text-muted)]">Strategy:</span>
            <span className="font-medium text-[var(--app-text)]">{strategyName}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--app-text-muted)]">Source Type:</span>
            <span className="font-medium text-[var(--app-text)]">{sourceType}</span>
          </div>
          {sourceRunId && (
            <div className="flex justify-between">
              <span className="text-[var(--app-text-muted)]">Source Run ID:</span>
              <span className="font-medium text-[var(--app-text)]">{sourceRunId}</span>
            </div>
          )}
          <div className="flex justify-between">
            <span className="text-[var(--app-text-muted)]">Pairs:</span>
            <span className="font-medium text-[var(--app-text)]">{pairs.join(', ')}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--app-text-muted)]">Timeframe:</span>
            <span className="font-medium text-[var(--app-text)]">{timeframe}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-[var(--app-text-muted)]">Risk Profile:</span>
            <span className="font-medium text-[var(--app-text)]">{riskProfile}</span>
          </div>
        </div>

        <div className="mb-6 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-3 text-xs text-yellow-600 dark:text-yellow-400">
          <p className="font-semibold mb-1">Important:</p>
          <p>Validation is evidence only. It is not strategy approval, export, live-trading authorization, or a guarantee of future performance.</p>
        </div>

        <div className="flex justify-end gap-3">
          <Button variant="ghost" onClick={onCancel}>
            Cancel
          </Button>
          <Button variant="primary" onClick={onConfirm}>
            Run Validation
          </Button>
        </div>
      </div>
    </div>
  );
}
