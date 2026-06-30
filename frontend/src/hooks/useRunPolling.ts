import { useState, useEffect, useCallback, useRef } from 'react';
import { getBaselineStatus } from '@/lib/api/baseline';
import { getOptimizationStatus } from '@/lib/api/optimization';

export type RunType = 'baseline' | 'optimization';

export interface PollingOptions {
  interval?: number;
  enabled?: boolean;
  respectReducedMotion?: boolean;
}

export interface PollingResult {
  status: string;
  currentStage?: string;
  resultStatus?: string;
  classification?: string;
  updatedAt?: string;
  isPolling: boolean;
  error: string | null;
  refresh: () => void;
}

// Terminal states - polling stops when these are reached
const BASELINE_TERMINAL_STATES = ['completed', 'failed', 'rejected', 'controlled_failure', 'error'];
const OPTIMIZATION_TERMINAL_STATES = ['completed', 'optimization_rejected', 'failed', 'controlled_failure', 'error'];

function isTerminalState(status: string, runType: RunType): boolean {
  const terminalStates = runType === 'baseline' ? BASELINE_TERMINAL_STATES : OPTIMIZATION_TERMINAL_STATES;
  return terminalStates.includes(status);
}

export function useRunPolling(runType: RunType, runId: string | null, options: PollingOptions = {}): PollingResult {
  const {
    interval = 2000,
    enabled = true,
    respectReducedMotion = true,
  } = options;

  const [status, setStatus] = useState<string>('idle');
  const [currentStage, setCurrentStage] = useState<string | undefined>();
  const [resultStatus, setResultStatus] = useState<string | undefined>();
  const [classification, setClassification] = useState<string | undefined>();
  const [updatedAt, setUpdatedAt] = useState<string | undefined>();
  const [isPolling, setIsPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const intervalRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Check if user prefers reduced motion
  const prefersReducedMotion = respectReducedMotion
    ? typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    : false;

  // Adjust interval for reduced motion
  const effectiveInterval = prefersReducedMotion ? interval * 2 : interval;

  // Fetch status function using API client
  const fetchStatus = useCallback(async () => {
    if (!runId || !isMountedRef.current) return;

    try {
      let data;
      if (runType === 'baseline') {
        const result = await getBaselineStatus(runId);
        if (!result.success) {
          throw new Error(result.error?.message || 'Failed to fetch baseline status');
        }
        data = result.data;
      } else {
        const result = await getOptimizationStatus(runId);
        if (!result.success) {
          throw new Error(result.error?.message || 'Failed to fetch optimization status');
        }
        data = result.data;
      }

      if (isMountedRef.current && data) {
        setStatus(data.status || 'unknown');
        setCurrentStage(data.current_stage || undefined);
        // result_status only exists in OptimizationRunListItem, not status responses
        setResultStatus(data.status);
        // classification only exists for baseline runs
        if (runType === 'baseline' && 'classification' in data) {
          setClassification((data as { classification?: string | null }).classification || data.status);
        } else {
          setClassification(data.status);
        }
        // updated_at only exists for optimization runs
        if (runType === 'optimization' && 'updated_at' in data) {
          setUpdatedAt((data as { updated_at?: string }).updated_at);
        } else {
          setUpdatedAt(undefined);
        }

        // Clear error on successful fetch
        setError(null);

        // Check if terminal state reached
        if (isTerminalState(data.status || 'unknown', runType)) {
          setIsPolling(false);
          if (intervalRef.current) {
            clearInterval(intervalRef.current);
            intervalRef.current = null;
          }
        }
      }
    } catch (e) {
      if (isMountedRef.current) {
        setError(e instanceof Error ? e.message : 'Failed to fetch status');
        // Don't stop polling on network errors - may be transient
      }
    }
  }, [runId, runType]);

  // Manual refresh function
  const refresh = useCallback(() => {
    if (!isPolling) {
      setIsPolling(true);
    }
    fetchStatus();
  }, [isPolling, fetchStatus]);

  // Start polling
  useEffect(() => {
    if (!runId || !enabled || isTerminalState(status, runType)) {
      return;
    }

    // Set up interval first
    intervalRef.current = setInterval(() => {
      fetchStatus();
    }, effectiveInterval);

    // Set polling state and initial fetch in next tick to avoid synchronous setState
    const timeoutId = setTimeout(() => {
      setIsPolling(true);
      fetchStatus();
    }, 0);

    // Cleanup on unmount
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
      clearTimeout(timeoutId);
      isMountedRef.current = false;
    };
  }, [runId, runType, enabled, effectiveInterval, status, fetchStatus]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  return {
    status,
    currentStage,
    resultStatus,
    classification,
    updatedAt,
    isPolling,
    error,
    refresh,
  };
}
