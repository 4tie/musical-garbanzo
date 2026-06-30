'use client';

import { useEffect, useState } from 'react';
import { ReactNode } from 'react';
import { checkDataAvailability } from '../lib/api/freqtrade';

interface DataAvailabilityPreviewProps {
  exchange: string;
  pairs: string[];
  timeframes: string[];
  tradingMode?: string;
  timerange?: string;
  autoCheck?: boolean;
  downloadAllowed?: boolean;
  children?: ReactNode;
}

type DataStatus = 'unknown' | 'available' | 'missing' | 'error' | 'checking';

export default function DataAvailabilityPreview({
  exchange,
  pairs,
  timeframes,
  tradingMode = 'spot',
  timerange,
  autoCheck = true,
  downloadAllowed = false,
  children,
}: DataAvailabilityPreviewProps) {
  const [status, setStatus] = useState<DataStatus>('unknown');
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!autoCheck || pairs.length === 0 || timeframes.length === 0) {
      const timeoutId = setTimeout(() => {
        setStatus('unknown');
        setError(null);
      }, 0);
      return () => clearTimeout(timeoutId);
    }

    let isMounted = true;

    // Set checking state in next tick
    const statusTimeout = setTimeout(() => {
      if (isMounted) {
        setStatus('checking');
        setError(null);
      }
    }, 0);

    async function checkData() {
      try {
        const result = await checkDataAvailability({
          exchange,
          trading_mode: tradingMode,
          pairs,
          timeframes,
          timerange,
          user_confirmed: false, // Read-only check
        });

        if (isMounted) {
          if (result.success) {
            const data = result.data;
            if (data.freqtrade_visible && data.errors.length === 0) {
              setStatus('available');
            } else {
              setStatus('missing');
            }
            if (data.errors.length > 0) {
              setError(data.errors.join(', '));
            }
          } else {
            setStatus('error');
            setError(result.error?.message || 'Failed to check data availability');
          }
        }
      } catch {
        if (isMounted) {
          setStatus('error');
          setError('Failed to check data availability');
        }
      }
    }

    checkData();

    return () => {
      isMounted = false;
      clearTimeout(statusTimeout);
    };
  }, [exchange, tradingMode, pairs, timeframes, timerange, autoCheck]);

  const statusConfig: Record<DataStatus, { label: string; color: string }> = {
    unknown: { label: 'Unknown', color: 'text-[var(--app-text-muted)]' },
    checking: { label: 'Checking...', color: 'text-[var(--app-text-muted)]' },
    available: { label: 'Available', color: 'text-[rgb(34_197_94)]' },
    missing: { label: 'Missing', color: 'text-[var(--app-warning)]' },
    error: { label: 'Error', color: 'text-[var(--app-danger)]' },
  };

  const config = statusConfig[status];

  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-5">
      <h3 className="text-base font-semibold text-[var(--app-text)]">Data Availability</h3>

      <div className="mt-4 space-y-3">
        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--app-text-muted)]">Exchange</span>
          <span className="font-medium text-[var(--app-text)]">{exchange}</span>
        </div>

        <div className="flex items-start justify-between text-sm">
          <span className="text-[var(--app-text-muted)]">Pairs</span>
          <span className="font-medium text-[var(--app-text)]">{pairs.join(', ')}</span>
        </div>

        <div className="flex items-start justify-between text-sm">
          <span className="text-[var(--app-text-muted)]">Timeframes</span>
          <span className="font-medium text-[var(--app-text)]">{timeframes.join(', ')}</span>
        </div>

        {timerange && (
          <div className="flex items-start justify-between text-sm">
            <span className="text-[var(--app-text-muted)]">Timerange</span>
            <span className="font-medium text-[var(--app-text)]">{timerange}</span>
          </div>
        )}

        <div className="flex items-center justify-between text-sm">
          <span className="text-[var(--app-text-muted)]">Status</span>
          <span className={`font-medium ${config.color}`}>{config.label}</span>
        </div>

        {downloadAllowed && status === 'missing' && (
          <div className="flex items-center justify-between text-sm">
            <span className="text-[var(--app-text-muted)]">Download</span>
            <span className="font-medium text-[var(--app-accent)]">Allowed</span>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-3 text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}

      {status === 'missing' && !downloadAllowed && (
        <p className="mt-3 text-xs leading-5 text-[var(--app-text-muted)]">
          Data is missing. Enable &quot;Download missing data&quot; in the form if needed.
        </p>
      )}

      {status === 'available' && (
        <p className="mt-3 text-xs leading-5 text-[rgb(34_197_94)]">
          All required data is available locally.
        </p>
      )}

      {children && <div className="mt-4">{children}</div>}
    </div>
  );
}
