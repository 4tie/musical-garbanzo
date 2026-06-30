'use client';

import { useEffect, useState } from 'react';
import StatusBadge from './StatusBadge';
import {
  StrategyReadiness,
  StrategySummary,
  isStrategySelectableForRun,
  listStrategies,
  toStrategyStatus,
} from '../lib/api';

interface StrategySelectProps {
  value: string;
  onChange: (value: string) => void;
  onSelectedStrategyChange?: (strategy: StrategySummary | null) => void;
  error?: string;
  disabled?: boolean;
}

export default function StrategySelect({
  value,
  onChange,
  onSelectedStrategyChange,
  error,
  disabled = false,
}: StrategySelectProps) {
  const [strategies, setStrategies] = useState<StrategySummary[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    async function loadStrategies() {
      setIsLoading(true);
      setLoadError(null);
      try {
        const result = await listStrategies({ limit: 500 });
        if (result.success) {
          setStrategies(result.data);
        } else {
          setStrategies([]);
          setLoadError(result.error?.message || 'Failed to load strategies');
        }
      } catch {
        setLoadError('Failed to load strategies');
        setStrategies([]);
      } finally {
        setIsLoading(false);
      }
    }

    loadStrategies();
  }, []);

  useEffect(() => {
    const selected = strategies.find((strategy) => strategy.strategy_name === value) ?? null;
    onSelectedStrategyChange?.(selected);
  }, [onSelectedStrategyChange, strategies, value]);

  const hasStrategies = strategies.length > 0;
  const selectedStrategy = strategies.find((strategy) => strategy.strategy_name === value) ?? null;
  const selectedStatus = selectedStrategy ? toStrategyStatus(selectedStrategy.readiness) : null;
  const hasUnverifiedValue = Boolean(value) && !selectedStrategy;

  return (
    <div className="flex flex-col gap-2">
      <select
        value={value}
        disabled={disabled || isLoading}
        onChange={(e) => onChange(e.target.value)}
        className={[
          'h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)] disabled:cursor-not-allowed disabled:opacity-50',
          error ? 'border-[var(--app-danger)]' : '',
        ].join(' ')}
      >
        <option value="">Select strategy</option>
        {hasUnverifiedValue && (
          <option value={value}>{value} (not verified in workspace)</option>
        )}
        {isLoading ? (
          <option disabled>Loading strategies...</option>
        ) : hasStrategies ? (
          strategies.map((strategy) => (
            <option key={strategy.strategy_name} value={strategy.strategy_name}>
              {strategy.strategy_name} - {readinessLabel(strategy.readiness)}
            </option>
          ))
        ) : (
          <option disabled value="">
            {loadError ? 'Error loading strategies' : 'No strategies found'}
          </option>
        )}
      </select>
      {selectedStrategy && selectedStatus && (
        <div className="flex flex-wrap items-center gap-2 text-xs leading-5 text-[var(--app-text-muted)]">
          <StatusBadge
            status={selectedStrategy.readiness}
            label={selectedStatus.label}
            tone={readinessTone(selectedStrategy.readiness)}
          />
          <span>
            {selectedStrategy.has_sidecar ? 'Sidecar present' : 'Sidecar missing'}
            {selectedStrategy.params_summary.timeframe ? ` · ${selectedStrategy.params_summary.timeframe}` : ''}
          </span>
          <a
            href={`/strategies/${encodeURIComponent(selectedStrategy.strategy_name)}`}
            className="font-medium text-[var(--app-accent)] hover:underline"
          >
            Inspect details
          </a>
        </div>
      )}
      {selectedStrategy && !isStrategySelectableForRun(selectedStrategy) && (
        <p className="text-xs leading-5 text-[var(--app-warning)]" role="alert">
          This strategy is not ready. Inspect details before starting a validation workflow.
        </p>
      )}
      {hasUnverifiedValue && (
        <p className="text-xs leading-5 text-[var(--app-warning)]" role="alert">
          Current strategy is not verified by the Strategy Workspace response.
        </p>
      )}
      {error && (
        <p className="text-xs leading-5 text-[var(--app-danger)]" role="alert">
          {error}
        </p>
      )}
      <p className="text-xs leading-5 text-[var(--app-text-muted)]">
        {hasStrategies
          ? `Select a real strategy from the Strategy Workspace (${strategies.length} available)`
          : loadError
          ? `Could not load strategies: ${loadError}`
          : 'No strategies found in Strategy Workspace'}
      </p>
    </div>
  );
}

function readinessLabel(readiness: StrategyReadiness): string {
  switch (readiness) {
    case 'ready':
      return 'Ready';
    case 'warning':
      return 'Warning';
    case 'missing_sidecar':
      return 'Missing sidecar';
    case 'invalid':
      return 'Invalid';
    case 'parse_error':
      return 'Parse error';
    case 'unsafe':
      return 'Unsafe';
    default:
      return readiness;
  }
}

function readinessTone(
  readiness: StrategyReadiness,
): 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral' {
  switch (readiness) {
    case 'ready':
      return 'success';
    case 'warning':
    case 'missing_sidecar':
      return 'warning';
    case 'invalid':
    case 'parse_error':
    case 'unsafe':
      return 'danger';
    default:
      return 'neutral';
  }
}
