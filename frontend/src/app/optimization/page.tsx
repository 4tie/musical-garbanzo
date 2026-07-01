'use client';

import { useCallback, useEffect, useRef, useState } from 'react';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import FormField from '@/components/FormField';
import PairInput from '@/components/PairInput';
import TimeframeSelect from '@/components/TimeframeSelect';
import RiskProfileSelect from '@/components/RiskProfileSelect';
import StrategySelect from '@/components/StrategySelect';
import SpacesSelect from '@/components/SpacesSelect';
import EpochsInput from '@/components/EpochsInput';
import ConfirmationDialog from '@/components/ConfirmationDialog';
import ConfirmationChecklist from '@/components/ConfirmationChecklist';
import ActionProgressPanel from '@/components/ActionProgressPanel';
import ActionResultBanner from '@/components/ActionResultBanner';
import ActionErrorDetails from '@/components/ActionErrorDetails';
import ValidationSummary from '@/components/ValidationSummary';
import DataAvailabilityPreview from '@/components/DataAvailabilityPreview';
import RunActionFormShell from '@/components/RunActionFormShell';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import StrategyReadinessBlockedBanner from '@/components/StrategyReadinessBlockedBanner';
import { StrategySummary, isStrategySelectableForRun } from '@/lib/api';
import { startOptimization, listSupportedExchanges, getAvailablePairs } from '@/lib/api/optimization';
import { validateOptimizationPreConfirm, validateOptimizationRequest } from '@/lib/api/validators';
import {
  OptimizationFormInput,
  buildOptimizationRequest,
  RISK_PROFILE_TIMEFRAME,
  RISK_PROFILE_DAYS,
  daysToTimerange,
  datesToTimerange,
  daysAgoStr,
  todayStr,
  timerangeLabel,
} from '@/lib/api/builders';
import { useRunPolling } from '@/hooks/useRunPolling';

// ---------------------------------------------------------------------------
// Static fallback list — used only when the exchanges endpoint is unavailable.
// ---------------------------------------------------------------------------
const FALLBACK_EXCHANGES = [
  { id: 'binance',     name: 'Binance' },
  { id: 'kraken',      name: 'Kraken' },
  { id: 'bybit',       name: 'Bybit' },
  { id: 'okx',         name: 'OKX' },
  { id: 'gateio',      name: 'Gate.io' },
  { id: 'bitfinex',    name: 'Bitfinex' },
  { id: 'coinbasepro', name: 'Coinbase Advanced Trade' },
];

const TOP_N_OPTIONS = [10, 20, 50, 100] as const;

function getAutoTimeframe(rp: string): string {
  return RISK_PROFILE_TIMEFRAME[rp] ?? '30m';
}

function getAutoTimerange(rp: string): string {
  const days = RISK_PROFILE_DAYS[rp] ?? 270;
  return daysToTimerange(days);
}

function getInitialStartDate(rp: string): string {
  return daysAgoStr(RISK_PROFILE_DAYS[rp] ?? 270);
}

function buildInitialFormData(strategyName: string): OptimizationFormInput {
  const rp = 'balanced';
  return {
    strategy_name:       strategyName,
    risk_profile:        rp,
    exchange:            'binance',
    quote_currency:      'USDT',
    pair_selection_mode: 'manual',
    pairs:               '',
    top_pairs_count:     50,
    timeframe_mode:      'auto',
    timeframe:           getAutoTimeframe(rp),
    timerange_mode:      'auto',
    timerange:           getAutoTimerange(rp),
    start_date:          getInitialStartDate(rp),
    end_date:            todayStr(),
    max_open_trades:     3,
    stake_amount:        100,
    stake_currency:      'USDT',
    epochs:              50,
    spaces:              ['buy', 'sell'],
    run_baseline_first:  true,
    experiment_notes:    '',
    user_confirmed:      false,
  };
}

export default function OptimizationStartPage() {
  const [initialStrategyName] = useState(getInitialStrategyName);
  const [formData, setFormData] = useState<OptimizationFormInput>(() =>
    buildInitialFormData(initialStrategyName),
  );

  // UI state
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiErrors, setApiErrors] = useState<string[]>([]);
  const [apiWarnings, setApiWarnings] = useState<string[]>([]);
  const [apiNextActions, setApiNextActions] = useState<string[]>([]);
  const [validationErrors, setValidationErrors] = useState<string[]>([]);
  const [selectedStrategy, setSelectedStrategy] = useState<StrategySummary | null>(null);
  const [blockedReadiness, setBlockedReadiness] = useState<{
    strategyName: string;
    readiness: string;
    issues: string[];
    warnings: string[];
    nextActions: string[];
  } | null>(null);

  // Exchanges
  const [exchanges, setExchanges] = useState<{ id: string; name: string }[]>(FALLBACK_EXCHANGES);

  // Pair loading state
  const [pairsLoading, setPairsLoading] = useState(false);
  const [pairsMessage, setPairsMessage] = useState<string | null>(null);
  const [pairsError, setPairsError] = useState<string | null>(null);

  // Hyperopt section collapsed by default
  const [hyperoptExpanded, setHyperoptExpanded] = useState(false);

  const polling = useRunPolling('optimization', runId, { interval: 2000, enabled: !!runId });

  // Load supported exchanges on mount
  useEffect(() => {
    listSupportedExchanges().then((res) => {
      if (res.success && res.data?.exchanges?.length) {
        setExchanges(res.data.exchanges.map((e) => ({ id: e.id, name: e.name })));
      }
    });
  }, []);

  const handleSelectedStrategyChange = useCallback((strategy: StrategySummary | null) => {
    setSelectedStrategy(strategy);
  }, []);

  // ---------------------------------------------------------------------------
  // Smart input handler — handles risk profile cascade and date-to-timerange sync
  // ---------------------------------------------------------------------------
  const handleInputChange = useCallback(
    (field: keyof OptimizationFormInput, value: string | number | boolean | string[]) => {
      setFormData((prev) => {
        const next: OptimizationFormInput = { ...prev, [field]: value };

        // When risk profile changes, cascade to auto timeframe + auto timerange
        if (field === 'risk_profile' && typeof value === 'string') {
          if (prev.timeframe_mode === 'auto') {
            next.timeframe = getAutoTimeframe(value);
          }
          if (prev.timerange_mode === 'auto') {
            next.timerange = getAutoTimerange(value);
            next.start_date = getInitialStartDate(value);
          }
        }

        // Switching timeframe mode to 'auto' — reset to risk profile default
        if (field === 'timeframe_mode' && value === 'auto') {
          next.timeframe = getAutoTimeframe(prev.risk_profile);
        }

        // Switching timerange mode to 'auto' — reset to risk profile default
        if (field === 'timerange_mode' && value === 'auto') {
          next.timerange = getAutoTimerange(prev.risk_profile);
          next.start_date = getInitialStartDate(prev.risk_profile);
          next.end_date = todayStr();
        }

        // Manual date changes — recompute timerange string
        if ((field === 'start_date' || field === 'end_date') && prev.timerange_mode === 'manual') {
          const sd = field === 'start_date' ? String(value) : prev.start_date;
          const ed = field === 'end_date' ? String(value) : prev.end_date;
          if (sd && ed) next.timerange = datesToTimerange(sd, ed);
        }

        return next;
      });

      if (validationErrors.length > 0) setValidationErrors([]);
    },
    [validationErrors.length],
  );

  // ---------------------------------------------------------------------------
  // Load available pairs from local data
  // ---------------------------------------------------------------------------
  const handleLoadAvailablePairs = async () => {
    setPairsLoading(true);
    setPairsMessage(null);
    setPairsError(null);
    try {
      const res = await getAvailablePairs(
        formData.exchange || 'binance',
        formData.quote_currency || 'USDT',
        formData.top_pairs_count,
      );
      if (res.success && res.data) {
        if (res.data.pairs.length > 0) {
          handleInputChange('pairs', res.data.pairs.join(', '));
          setPairsMessage(res.data.message);
        } else {
          setPairsError(res.data.message);
        }
      } else {
        setPairsError('Unable to load pairs from local exchange data.');
      }
    } catch {
      setPairsError('Request failed. Check backend connectivity.');
    } finally {
      setPairsLoading(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Form validation
  // ---------------------------------------------------------------------------
  const validateForm = (): boolean => {
    const result = validateOptimizationPreConfirm(formData);
    if (!result.valid) {
      setValidationErrors(result.errors.map((e) => `${e.field}: ${e.message}`));
      return false;
    }
    setValidationErrors([]);
    return true;
  };

  const validateFinalSubmit = (): boolean => {
    const result = validateOptimizationRequest(formData);
    if (!result.valid) {
      setValidationErrors(result.errors.map((e) => `${e.field}: ${e.message}`));
      return false;
    }
    setValidationErrors([]);
    return true;
  };

  const handleStart = () => {
    if (!validateForm()) return;
    setShowConfirmation(true);
  };

  const handleConfirm = async () => {
    if (!validateFinalSubmit()) return;
    setShowConfirmation(false);
    setIsSubmitting(true);
    setApiError(null);
    setApiErrors([]);
    setApiWarnings([]);
    setApiNextActions([]);
    setBlockedReadiness(null);

    try {
      const request = buildOptimizationRequest(formData);
      const result = await startOptimization(request);

      if (result.success && result.data) {
        setRunId(result.data.run_id);
        setApiErrors(result.data.errors || []);
        setApiWarnings(result.data.warnings || []);
        setApiNextActions(result.data.next_actions || []);
      } else if (!result.success && result.error) {
        if (result.error.kind === 'strategy_not_ready' && result.error.detail) {
          const detail = result.error.detail as {
            strategy_name?: string;
            readiness?: string;
            issues?: string[];
            warnings?: string[];
            next_actions?: string[];
          };
          setBlockedReadiness({
            strategyName: detail.strategy_name || formData.strategy_name,
            readiness: detail.readiness || 'unknown',
            issues: detail.issues || [],
            warnings: detail.warnings || [],
            nextActions: detail.next_actions || [],
          });
        } else {
          setApiError(result.error.message || 'Failed to start optimization');
        }
      } else {
        setApiError('Failed to start optimization');
      }
    } catch {
      setApiError('An unexpected error occurred');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleCancel = () => setShowConfirmation(false);

  const parsedPairs = formData.pairs
    .split(',')
    .map((p) => p.trim().toUpperCase())
    .filter((p) => p.length > 0);

  const readinessWarning = strategyReadinessWarning(selectedStrategy, formData.strategy_name);

  const getResultType = (): 'success' | 'controlled_failure' | 'error' => {
    if (polling.status === 'failed') return 'error';
    if (polling.status === 'completed' && polling.classification === 'optimization_rejected')
      return 'controlled_failure';
    if (polling.status === 'completed') return 'success';
    return 'error';
  };

  const resolvedTimerangeLabel = timerangeLabel(formData.timerange);
  const riskProfileLabel =
    formData.risk_profile === 'conservative'
      ? 'Conservative'
      : formData.risk_profile === 'aggressive'
        ? 'Aggressive'
        : 'Balanced';

  return (
    <AppShell pageTitle="Start Optimization">
      <RunActionFormShell
        title="Start Safe Optimization"
        description="Configure Hyperopt to optimize strategy parameters against historical data."
      >
        {/* Validation Summary */}
        {(validationErrors.length > 0 || readinessWarning) && (
          <ValidationSummary
            errors={validationErrors}
            warnings={readinessWarning ? [readinessWarning] : []}
            title="Form Validation"
          />
        )}

        {/* Progress Panel */}
        {runId && (
          <ActionProgressPanel
            status={
              polling.status as
                | 'idle'
                | 'running'
                | 'completed'
                | 'failed'
                | 'rejected'
                | 'controlled_failure'
                | 'optimization_rejected'
            }
            runId={runId}
            runType="optimization"
            currentStage={polling.currentStage}
            resultStatus={polling.resultStatus}
            classification={polling.classification}
            updatedAt={polling.updatedAt}
            detailHref={`/optimization/${runId}`}
            isPolling={polling.isPolling}
            onRefresh={polling.refresh}
          />
        )}

        {/* Result Banner */}
        {runId && (polling.status === 'completed' || polling.status === 'failed') && (
          <ActionResultBanner
            type={getResultType()}
            title={polling.status === 'completed' ? 'Optimization Complete' : 'Optimization Failed'}
            runId={runId}
            detailHref={`/optimization/${runId}`}
          >
            {polling.status === 'completed' && polling.classification === 'optimization_rejected' && (
              <>
                The optimization result was rejected by decision gates. This is a controlled validation
                outcome, not a system failure. The best trial is not automatically approved.
              </>
            )}
            {polling.status === 'completed' && polling.classification !== 'optimization_rejected' && (
              <>
                Optimization completed. The best trial is not automatically approved and may still be
                rejected by decision gates.
              </>
            )}
            {polling.status === 'failed' && <>The optimization failed due to a system error.</>}
          </ActionResultBanner>
        )}

        {/* Controlled Failure Banner */}
        {runId && polling.status === 'completed' && polling.classification === 'optimization_rejected' && (
          <ControlledFailureBanner title="Optimization Result Rejected">
            The optimization completed but the result was rejected by decision gates. This is expected
            behavior and not a system failure.
          </ControlledFailureBanner>
        )}

        {/* Error Details */}
        {(apiErrors.length > 0 || apiWarnings.length > 0 || apiNextActions.length > 0) && (
          <ActionErrorDetails
            errors={apiErrors}
            warnings={apiWarnings}
            nextActions={apiNextActions}
          />
        )}

        {/* API Error */}
        {apiError && (
          <div className="rounded-[var(--app-radius)] border border-[rgb(239_68_68_/_0.38)] bg-[rgb(239_68_68_/_0.12)] p-4 text-sm">
            <p className="font-semibold text-[var(--app-danger)]">Error</p>
            <p className="mt-1 leading-6 text-[var(--app-text-muted)]">{apiError}</p>
          </div>
        )}

        {/* Strategy Readiness Blocked Banner */}
        {blockedReadiness && (
          <StrategyReadinessBlockedBanner
            strategyName={blockedReadiness.strategyName}
            readiness={blockedReadiness.readiness}
            issues={blockedReadiness.issues}
            warnings={blockedReadiness.warnings}
            nextActions={blockedReadiness.nextActions}
          />
        )}

        {/* ================================================================
            FORM — only shown before a run is started
        ================================================================ */}
        {!runId && (
          <div className="space-y-5">
            {/* ── SECTION 1: Strategy ──────────────────────────────────── */}
            <Section
              title="Strategy"
              description="Select the strategy you want to optimize."
            >
              <FormField
                label="Strategy"
                required
                error={fieldError(validationErrors, 'strategy_name')}
              >
                <StrategySelect
                  value={formData.strategy_name}
                  onChange={(v) => handleInputChange('strategy_name', v)}
                  onSelectedStrategyChange={handleSelectedStrategyChange}
                  error={fieldError(validationErrors, 'strategy_name')}
                />
              </FormField>

              {readinessWarning && (
                <ControlledFailureBanner title="Strategy readiness warning">
                  {readinessWarning} Inspect the strategy detail page before starting.
                </ControlledFailureBanner>
              )}
            </Section>

            {/* ── SECTION 2: Risk Profile ───────────────────────────────── */}
            <Section
              title="Risk Profile"
              description="Sets the default timeframe and data window. You can override each individually below."
            >
              <RiskProfileCards
                value={formData.risk_profile}
                onChange={(v) => handleInputChange('risk_profile', v)}
              />
            </Section>

            {/* ── SECTION 3: Market Selection ───────────────────────────── */}
            <Section
              title="Market Selection"
              description="Choose the exchange and trading pairs to include in the optimization run."
            >
              {/* Exchange */}
              <FormField label="Exchange">
                <select
                  value={formData.exchange}
                  onChange={(e) => handleInputChange('exchange', e.target.value)}
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                >
                  {exchanges.map((ex) => (
                    <option key={ex.id} value={ex.id}>
                      {ex.name}
                    </option>
                  ))}
                </select>
              </FormField>

              {/* Quote currency */}
              <FormField label="Quote Currency" description="Filter pairs by this quote currency (e.g. USDT)">
                <input
                  type="text"
                  value={formData.quote_currency}
                  onChange={(e) => handleInputChange('quote_currency', e.target.value.toUpperCase())}
                  placeholder="USDT"
                  className="h-10 w-48 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              {/* Pair mode toggle */}
              <FormField label="Pair Selection">
                <div className="flex gap-2">
                  <ModeTab
                    active={formData.pair_selection_mode === 'manual'}
                    onClick={() => handleInputChange('pair_selection_mode', 'manual')}
                  >
                    Manual Input
                  </ModeTab>
                  <ModeTab
                    active={formData.pair_selection_mode === 'top'}
                    onClick={() => handleInputChange('pair_selection_mode', 'top')}
                  >
                    Load from Local Data
                  </ModeTab>
                </div>
              </FormField>

              {/* Top-N loader */}
              {formData.pair_selection_mode === 'top' && (
                <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
                  <p className="text-xs text-[var(--app-text-muted)] leading-5 mb-3">
                    Loads pairs that have real locally-downloaded OHLCV data for the selected exchange
                    and quote currency. If no data has been downloaded yet, this will return an empty
                    list with instructions.
                  </p>
                  <div className="flex flex-wrap items-center gap-3">
                    <FormField label="Load up to">
                      <select
                        value={formData.top_pairs_count}
                        onChange={(e) =>
                          handleInputChange('top_pairs_count', Number(e.target.value) as 20 | 50 | 100)
                        }
                        className="h-9 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                      >
                        {TOP_N_OPTIONS.map((n) => (
                          <option key={n} value={n}>
                            {n} pairs
                          </option>
                        ))}
                      </select>
                    </FormField>
                    <Button
                      variant="secondary"
                      onClick={handleLoadAvailablePairs}
                      disabled={pairsLoading}
                    >
                      {pairsLoading ? 'Loading…' : `Load ${formData.top_pairs_count} Pairs`}
                    </Button>
                  </div>
                  {pairsMessage && (
                    <p className="mt-2 text-xs text-[var(--app-accent)]">{pairsMessage}</p>
                  )}
                  {pairsError && (
                    <p className="mt-2 text-xs text-[var(--app-danger)]">{pairsError}</p>
                  )}
                </div>
              )}

              {/* Pair input — always visible so user can edit after loading */}
              <FormField
                label="Trading Pairs"
                required
                error={fieldError(validationErrors, 'pairs')}
                description={
                  parsedPairs.length > 50
                    ? `${parsedPairs.length} pairs — this may significantly increase runtime`
                    : parsedPairs.length > 0
                      ? `${parsedPairs.length} pair${parsedPairs.length === 1 ? '' : 's'} selected`
                      : undefined
                }
              >
                <PairInput
                  value={formData.pairs}
                  onChange={(v) => handleInputChange('pairs', v)}
                  error={fieldError(validationErrors, 'pairs')}
                />
              </FormField>
            </Section>

            {/* ── SECTION 4: Time Configuration ─────────────────────────── */}
            <Section
              title="Time Configuration"
              description="Timeframe and data window. Auto mode derives sensible defaults from the risk profile."
            >
              {/* Timeframe */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--app-text)]">Timeframe</label>
                  <div className="flex gap-2">
                    <ModeTab
                      active={formData.timeframe_mode === 'auto'}
                      onClick={() => handleInputChange('timeframe_mode', 'auto')}
                    >
                      Auto ({getAutoTimeframe(formData.risk_profile)})
                    </ModeTab>
                    <ModeTab
                      active={formData.timeframe_mode === 'manual'}
                      onClick={() => handleInputChange('timeframe_mode', 'manual')}
                    >
                      Manual
                    </ModeTab>
                  </div>
                </div>
                {formData.timeframe_mode === 'manual' ? (
                  <TimeframeSelect
                    value={formData.timeframe}
                    onChange={(v) => handleInputChange('timeframe', v)}
                    error={fieldError(validationErrors, 'timeframe')}
                  />
                ) : (
                  <div className="flex h-10 items-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text-muted)]">
                    {formData.timeframe}
                    <span className="ml-2 text-xs text-[var(--app-text-subtle)]">— from {riskProfileLabel} profile</span>
                  </div>
                )}
              </div>

              {/* Timerange */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <label className="text-sm font-medium text-[var(--app-text)]">Data Window</label>
                  <div className="flex gap-2">
                    <ModeTab
                      active={formData.timerange_mode === 'auto'}
                      onClick={() => handleInputChange('timerange_mode', 'auto')}
                    >
                      Auto ({RISK_PROFILE_DAYS[formData.risk_profile] ?? 270}d)
                    </ModeTab>
                    <ModeTab
                      active={formData.timerange_mode === 'manual'}
                      onClick={() => handleInputChange('timerange_mode', 'manual')}
                    >
                      Manual Dates
                    </ModeTab>
                  </div>
                </div>

                {formData.timerange_mode === 'manual' ? (
                  <div className="space-y-2">
                    <div className="flex flex-wrap gap-3">
                      <div className="flex flex-col gap-1">
                        <label className="text-xs text-[var(--app-text-muted)]">Start date</label>
                        <input
                          type="date"
                          value={formData.start_date}
                          max={formData.end_date}
                          onChange={(e) => handleInputChange('start_date', e.target.value)}
                          className="h-10 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                        />
                      </div>
                      <div className="flex flex-col gap-1">
                        <label className="text-xs text-[var(--app-text-muted)]">End date</label>
                        <input
                          type="date"
                          value={formData.end_date}
                          min={formData.start_date}
                          max={todayStr()}
                          onChange={(e) => handleInputChange('end_date', e.target.value)}
                          className="h-10 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                        />
                      </div>
                    </div>
                    {fieldError(validationErrors, 'start_date') && (
                      <p className="text-xs text-[var(--app-danger)]">{fieldError(validationErrors, 'start_date')}</p>
                    )}
                    {fieldError(validationErrors, 'end_date') && (
                      <p className="text-xs text-[var(--app-danger)]">{fieldError(validationErrors, 'end_date')}</p>
                    )}
                    {formData.timerange && (
                      <p className="text-xs text-[var(--app-text-subtle)]">
                        Freqtrade timerange: <span className="font-mono text-[var(--app-text-muted)]">{formData.timerange}</span>
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="flex h-10 items-center rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-3 text-sm text-[var(--app-text-muted)]">
                    <span className="font-mono text-xs mr-2">{formData.timerange}</span>
                    <span className="text-xs text-[var(--app-text-subtle)]">
                      ({resolvedTimerangeLabel})
                    </span>
                  </div>
                )}
              </div>

              {/* Data availability preview */}
              {parsedPairs.length > 0 && formData.timeframe && (
                <DataAvailabilityPreview
                  exchange={formData.exchange || 'binance'}
                  pairs={parsedPairs}
                  timeframes={[formData.timeframe]}
                  tradingMode="spot"
                  timerange={formData.timerange}
                  downloadAllowed={true}
                />
              )}
            </Section>

            {/* ── SECTION 5: Capital & Execution ────────────────────────── */}
            <Section
              title="Capital & Execution"
              description="Risk parameters applied during backtesting. These do not control live capital."
            >
              <div className="grid grid-cols-2 gap-4">
                <FormField
                  label="Max Open Trades"
                  description="Maximum concurrent positions"
                  error={fieldError(validationErrors, 'max_open_trades')}
                >
                  <input
                    type="number"
                    min="1"
                    max="999"
                    value={formData.max_open_trades}
                    onChange={(e) =>
                      handleInputChange('max_open_trades', parseInt(e.target.value, 10) || 1)
                    }
                    className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                  />
                </FormField>

                <FormField
                  label="Stake Amount"
                  description={`Amount per trade in ${formData.stake_currency}`}
                >
                  <input
                    type="text"
                    value={formData.stake_amount}
                    onChange={(e) => handleInputChange('stake_amount', e.target.value)}
                    placeholder="100"
                    className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                  />
                </FormField>
              </div>
            </Section>

            {/* ── SECTION 6: Hyperopt Settings (collapsible) ─────────────── */}
            <Section
              title="Hyperopt Settings"
              description="Optimization algorithm configuration."
              collapsible
              expanded={hyperoptExpanded}
              onToggle={() => setHyperoptExpanded((v) => !v)}
            >
              <FormField
                label="Epochs"
                required
                error={fieldError(validationErrors, 'epochs')}
                description="Number of parameter combinations to test (1 – 200)"
              >
                <EpochsInput
                  value={formData.epochs || 50}
                  onChange={(v) => handleInputChange('epochs', v)}
                  error={fieldError(validationErrors, 'epochs')}
                />
              </FormField>

              <FormField
                label="Search Spaces"
                required
                error={fieldError(validationErrors, 'spaces')}
                description="Which parameter groups Hyperopt will optimize"
              >
                <SpacesSelect
                  value={formData.spaces || ['buy', 'sell']}
                  onChange={(v) => handleInputChange('spaces', v)}
                  error={fieldError(validationErrors, 'spaces')}
                />
              </FormField>

              <FormField label="Run Baseline First">
                <label className="flex items-center gap-2 text-sm text-[var(--app-text)]">
                  <input
                    type="checkbox"
                    checked={formData.run_baseline_first}
                    onChange={(e) => handleInputChange('run_baseline_first', e.target.checked)}
                    className="h-4 w-4 rounded border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                  />
                  <span>Run baseline evaluation before Hyperopt (recommended)</span>
                </label>
                <p className="mt-1 text-xs text-[var(--app-text-subtle)]">
                  Creates a baseline run to compare optimization results against.
                </p>
              </FormField>
            </Section>

            {/* ── SECTION 7: Experiment Notes ───────────────────────────── */}
            <Section
              title="Experiment Notes"
              description="Optional. Describe your hypothesis or what you're testing in this run."
            >
              <textarea
                value={formData.experiment_notes}
                onChange={(e) => handleInputChange('experiment_notes', e.target.value)}
                rows={3}
                placeholder="e.g. Testing tighter stop loss parameters on BTC during trending market conditions…"
                className="w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 py-2 text-sm text-[var(--app-text)] placeholder:text-[var(--app-text-subtle)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
              />
              <p className="text-xs text-[var(--app-text-subtle)]">
                Notes are stored with the run record for audit purposes. They do not affect metrics
                or decisions.
              </p>
            </Section>

            {/* ── DATA DOWNLOAD NOTE ────────────────────────────────────── */}
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] px-4 py-3 text-xs leading-5 text-[var(--app-text-muted)]">
              <span className="font-medium text-[var(--app-text)]">Data download: </span>
              If market data is missing for the selected pairs and timeframe, HER will download it
              automatically after you confirm. No manual intervention needed.
            </div>

            {/* ── START BUTTON ──────────────────────────────────────────── */}
            <div className="flex justify-end">
              <Button variant="primary" onClick={handleStart} disabled={isSubmitting}>
                {isSubmitting ? 'Starting…' : 'Review and Start Optimization'}
              </Button>
            </div>
          </div>
        )}

        {/* ================================================================
            CONFIRMATION DIALOG
        ================================================================ */}
        <ConfirmationDialog
          isOpen={showConfirmation}
          onClose={handleCancel}
          onConfirm={handleConfirm}
          title="Confirm Optimization Run"
          actionName="Hyperopt Optimization"
          strategyName={formData.strategy_name}
          pairs={parsedPairs}
          timeframe={formData.timeframe}
          timerange={formData.timerange}
          riskProfile={formData.risk_profile}
          exchange={formData.exchange}
          epochsCount={formData.epochs}
          autoDataDownload={true}
          isHyperopt={true}
          isLoading={isSubmitting}
          confirmEnabled={formData.user_confirmed}
        >
          {readinessWarning && (
            <ControlledFailureBanner title="Strategy readiness warning">
              {readinessWarning} This run can still be confirmed, but HER is not treating the
              strategy as ready.
            </ControlledFailureBanner>
          )}
          <ConfirmationChecklist
            checked={formData.user_confirmed}
            onChange={(checked) => handleInputChange('user_confirmed', checked)}
            error={fieldError(validationErrors, 'user_confirmed')}
          />
        </ConfirmationDialog>
      </RunActionFormShell>
    </AppShell>
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function strategyReadinessWarning(
  selectedStrategy: StrategySummary | null,
  strategyName: string,
): string | null {
  if (!strategyName.trim()) return null;
  if (!selectedStrategy)
    return 'Strategy readiness is not verified by the Strategy Workspace response.';
  if (isStrategySelectableForRun(selectedStrategy)) return null;
  return `Strategy readiness is ${selectedStrategy.readiness.replaceAll('_', ' ')}, not ready.`;
}

function fieldError(validationErrors: string[], field: string): string | undefined {
  const match = validationErrors.find((e) => e.startsWith(`${field}:`));
  return match ? match.split(': ').slice(1).join(': ') : undefined;
}

function getInitialStrategyName(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('strategy')?.trim() ?? '';
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function Section({
  title,
  description,
  children,
  collapsible = false,
  expanded = true,
  onToggle,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  collapsible?: boolean;
  expanded?: boolean;
  onToggle?: () => void;
}) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] overflow-hidden">
      <div
        className={[
          'flex items-center justify-between px-5 py-4 border-b border-[var(--app-border)]',
          collapsible ? 'cursor-pointer select-none hover:bg-[var(--app-surface-muted)]' : '',
        ].join(' ')}
        onClick={collapsible ? onToggle : undefined}
      >
        <div>
          <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
          <p className="mt-0.5 text-xs text-[var(--app-text-subtle)]">{description}</p>
        </div>
        {collapsible && (
          <svg
            className={`h-4 w-4 text-[var(--app-text-muted)] transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        )}
      </div>
      {(!collapsible || expanded) && (
        <div className="space-y-4 p-5">{children}</div>
      )}
    </div>
  );
}

function ModeTab({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'rounded-[var(--app-radius)] border px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'border-[var(--app-accent)] bg-[var(--app-accent-soft)] text-[var(--app-accent)]'
          : 'border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-text-muted)] hover:text-[var(--app-text)]',
      ].join(' ')}
    >
      {children}
    </button>
  );
}

const RISK_CARDS = [
  {
    value: 'conservative',
    label: 'Conservative',
    timeframe: RISK_PROFILE_TIMEFRAME.conservative,
    days: RISK_PROFILE_DAYS.conservative,
    note: 'Slower timeframe, longer data window. Lower false-positive rate.',
    accent: 'text-sky-400',
    border: 'border-sky-600/40',
    activeBg: 'bg-sky-950/40',
  },
  {
    value: 'balanced',
    label: 'Balanced',
    timeframe: RISK_PROFILE_TIMEFRAME.balanced,
    days: RISK_PROFILE_DAYS.balanced,
    note: 'Mid-range timeframe and window. Good general starting point.',
    accent: 'text-violet-400',
    border: 'border-violet-600/40',
    activeBg: 'bg-violet-950/40',
  },
  {
    value: 'aggressive',
    label: 'Aggressive',
    timeframe: RISK_PROFILE_TIMEFRAME.aggressive,
    days: RISK_PROFILE_DAYS.aggressive,
    note: 'Faster timeframe, shorter window. Higher sensitivity, more noise.',
    accent: 'text-amber-400',
    border: 'border-amber-600/40',
    activeBg: 'bg-amber-950/40',
  },
] as const;

function RiskProfileCards({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
      {RISK_CARDS.map((card) => {
        const active = value === card.value;
        return (
          <button
            key={card.value}
            type="button"
            onClick={() => onChange(card.value)}
            className={[
              'rounded-[var(--app-radius)] border p-4 text-left transition-all',
              active
                ? `${card.border} ${card.activeBg}`
                : 'border-[var(--app-border)] hover:border-[var(--app-border-strong)] bg-[var(--app-surface-raised)]',
            ].join(' ')}
          >
            <div className="flex items-center justify-between">
              <span className={`text-sm font-semibold ${active ? card.accent : 'text-[var(--app-text)]'}`}>
                {card.label}
              </span>
              {active && (
                <svg className={`h-4 w-4 ${card.accent}`} fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                    clipRule="evenodd"
                  />
                </svg>
              )}
            </div>
            <div className="mt-2 space-y-0.5 text-xs text-[var(--app-text-muted)]">
              <div>
                Timeframe: <span className="font-mono text-[var(--app-text)]">{card.timeframe}</span>
              </div>
              <div>
                Window: <span className="font-mono text-[var(--app-text)]">{card.days}d</span>
              </div>
            </div>
            <p className="mt-2 text-xs leading-4 text-[var(--app-text-subtle)]">{card.note}</p>
          </button>
        );
      })}
    </div>
  );
}
