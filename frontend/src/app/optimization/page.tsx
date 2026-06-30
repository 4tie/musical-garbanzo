'use client';

import { useCallback, useState } from 'react';
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
import RunActionCard from '@/components/RunActionCard';
import SectionCard from '@/components/SectionCard';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import StrategyReadinessBlockedBanner from '@/components/StrategyReadinessBlockedBanner';
import { StrategySummary, isStrategySelectableForRun } from '@/lib/api';
import { startOptimization } from '@/lib/api/optimization';
import { validateOptimizationPreConfirm, validateOptimizationRequest, type OptimizationFormInput } from '@/lib/api/validators';
import { buildOptimizationRequest } from '@/lib/api/builders';
import { useRunPolling } from '@/hooks/useRunPolling';

export default function OptimizationStartPage() {
  const [initialStrategyName] = useState(getInitialStrategyName);

  // Form state
  const [formData, setFormData] = useState<OptimizationFormInput>({
    strategy_name: initialStrategyName,
    pairs: '',
    timeframe: '',
    exchange: 'binance',
    days: 30,
    timerange: '',
    risk_profile: 'balanced',
    baseline_run_id: '',
    run_baseline_first: true,
    download_missing_data: false,
    user_confirmed: false,
    epochs: 20,
    spaces: ['buy', 'sell'],
    max_open_trades: 3,
    stake_currency: 'USDT',
    stake_amount: 100,
    trading_mode: 'spot',
    apply_decision_to_run: false,
    notes: '',
  });

  // UI state
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiErrors, setApiErrors] = useState<string[]>([]);
  const [apiWarnings, setApiWarnings] = useState<string[]>([]);
  const [apiNextActions, setApiNextActions] = useState<string[]>([]);
  const [selectedFromWorkspace, setSelectedFromWorkspace] = useState(Boolean(initialStrategyName));
  const [selectedStrategy, setSelectedStrategy] = useState<StrategySummary | null>(null);
  const [blockedReadiness, setBlockedReadiness] = useState<{
    strategyName: string;
    readiness: string;
    issues: string[];
    warnings: string[];
    nextActions: string[];
  } | null>(null);

  // Validation state
  const [validationErrors, setValidationErrors] = useState<string[]>([]);

  // Use polling hook
  const polling = useRunPolling('optimization', runId, { interval: 2000, enabled: !!runId });

  const handleSelectedStrategyChange = useCallback((strategy: StrategySummary | null) => {
    setSelectedStrategy(strategy);
  }, []);

  // Handle form input changes
  const handleInputChange = (field: keyof OptimizationFormInput, value: string | number | boolean | string[]) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    if (field === 'strategy_name') {
      setSelectedFromWorkspace(false);
    }
    // Clear validation errors when user changes input
    if (validationErrors.length > 0) {
      setValidationErrors([]);
    }
  };

  // Validate form (pre-confirm)
  const validateForm = (): boolean => {
    const result = validateOptimizationPreConfirm(formData);
    if (!result.valid) {
      setValidationErrors(result.errors.map((e) => `${e.field}: ${e.message}`));
      return false;
    }
    setValidationErrors([]);
    return true;
  };

  // Validate form (final-submit)
  const validateFinalSubmit = (): boolean => {
    const result = validateOptimizationRequest(formData);
    if (!result.valid) {
      setValidationErrors(result.errors.map((e) => `${e.field}: ${e.message}`));
      return false;
    }
    setValidationErrors([]);
    return true;
  };

  // Handle start button click
  const handleStart = () => {
    if (!validateForm()) {
      return;
    }
    setShowConfirmation(true);
  };

  // Handle confirmation dialog confirm
  const handleConfirm = async () => {
    if (!validateFinalSubmit()) {
      return;
    }
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
        // Check if this is a strategy_not_ready error
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

  // Handle confirmation dialog cancel
  const handleCancel = () => {
    setShowConfirmation(false);
  };

  // Parse pairs for display
  const pairs = formData.pairs.split(',').map((p) => p.trim().toUpperCase()).filter((p) => p.length > 0);
  const readinessWarning = strategyReadinessWarning(selectedStrategy, formData.strategy_name);

  // Determine result type for banner
  const getResultType = (): 'success' | 'controlled_failure' | 'error' => {
    if (polling.status === 'failed') return 'error';
    if (polling.status === 'completed' && polling.classification === 'optimization_rejected') return 'controlled_failure';
    if (polling.status === 'completed') return 'success';
    return 'error';
  };

  return (
    <AppShell pageTitle="Start Safe Optimization">
      <RunActionFormShell
        title="Start Safe Optimization"
        description="Run Hyperopt to optimize strategy parameters. This is resource-intensive and may take significant time."
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
            status={polling.status as 'idle' | 'running' | 'completed' | 'failed' | 'rejected' | 'controlled_failure' | 'optimization_rejected'}
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
                The optimization completed successfully. The best trial is not automatically approved and
                may still be rejected by decision gates.
              </>
            )}
            {polling.status === 'failed' && <>The optimization failed due to a system error.</>}
          </ActionResultBanner>
        )}

        {/* Controlled Failure Banner for Rejected Result */}
        {runId && polling.status === 'completed' && polling.classification === 'optimization_rejected' && (
          <ControlledFailureBanner title="Optimization Result Rejected">
            The optimization completed but the result was rejected by decision gates. This is expected
            behavior and not a system failure. The best trial may still have performance issues or fail
            safety checks.
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

        {/* Form */}
        {!runId && (
          <>
            {/* Resource Warning */}
            <SectionCard title="Resource Warning" description="Important information about resource usage">
              <ul className="space-y-2 text-sm leading-6 text-[var(--app-text-muted)]">
                <li>• Hyperopt can take significant time to complete.</li>
                <li>• More epochs means longer runtime and higher resource usage.</li>
                <li>• This may create runtime artifacts and temporary files.</li>
                <li>• Best Hyperopt trial is not automatically approved.</li>
                <li>• Optimized result may still be rejected by decision gates.</li>
              </ul>
            </SectionCard>

            <RunActionCard title="Strategy Configuration" description="Select the strategy to optimize">
              <FormField label="Strategy" required error={validationErrors.find((e) => e.startsWith('strategy_name'))?.split(': ')[1]}>
                <StrategySelect
                  value={formData.strategy_name}
                  onChange={(value) => handleInputChange('strategy_name', value)}
                  onSelectedStrategyChange={handleSelectedStrategyChange}
                  error={validationErrors.find((e) => e.startsWith('strategy_name'))?.split(': ')[1]}
                />
              </FormField>
              {(selectedFromWorkspace || selectedStrategy) && (
                <div className="rounded-[var(--app-radius)] border border-[var(--app-accent-border)] bg-[var(--app-accent-soft)] p-3 text-sm leading-6 text-[var(--app-text-muted)]">
                  <p className="font-medium text-[var(--app-text)]">Selected from Strategy Workspace</p>
                  <p>
                    This prefilled the strategy name only. It does not auto-start, skip confirmation, approve the strategy, or prove profitability.
                  </p>
                </div>
              )}
              {readinessWarning && (
                <ControlledFailureBanner title="Strategy readiness warning">
                  {readinessWarning} Inspect the strategy detail page before starting. HER will still require confirmation and validation evidence.
                </ControlledFailureBanner>
              )}

              <FormField label="Trading Pairs" required error={validationErrors.find((e) => e.startsWith('pairs'))?.split(': ')[1]}>
                <PairInput
                  value={formData.pairs}
                  onChange={(value) => handleInputChange('pairs', value)}
                  error={validationErrors.find((e) => e.startsWith('pairs'))?.split(': ')[1]}
                />
              </FormField>

              <FormField label="Timeframe" required error={validationErrors.find((e) => e.startsWith('timeframe'))?.split(': ')[1]}>
                <TimeframeSelect
                  value={formData.timeframe}
                  onChange={(value) => handleInputChange('timeframe', value)}
                  error={validationErrors.find((e) => e.startsWith('timeframe'))?.split(': ')[1]}
                />
              </FormField>

              <FormField label="Risk Profile" required error={validationErrors.find((e) => e.startsWith('risk_profile'))?.split(': ')[1]}>
                <RiskProfileSelect
                  value={formData.risk_profile || 'balanced'}
                  onChange={(value) => handleInputChange('risk_profile', value)}
                  error={validationErrors.find((e) => e.startsWith('risk_profile'))?.split(': ')[1]}
                />
              </FormField>
            </RunActionCard>

            <RunActionCard title="Hyperopt Configuration" description="Configure Hyperopt parameters">
              <FormField label="Epochs" required error={validationErrors.find((e) => e.startsWith('epochs'))?.split(': ')[1]}>
                <EpochsInput
                  value={formData.epochs || 20}
                  onChange={(value) => handleInputChange('epochs', value)}
                  error={validationErrors.find((e) => e.startsWith('epochs'))?.split(': ')[1]}
                />
              </FormField>

              <FormField label="Search Spaces" required error={validationErrors.find((e) => e.startsWith('spaces'))?.split(': ')[1]}>
                <SpacesSelect
                  value={formData.spaces || ['buy', 'sell']}
                  onChange={(value) => handleInputChange('spaces', value)}
                  error={validationErrors.find((e) => e.startsWith('spaces'))?.split(': ')[1]}
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
                  <span>Run baseline evaluation before optimization (recommended)</span>
                </label>
              </FormField>
            </RunActionCard>

            <RunActionCard title="Data Configuration" description="Configure data parameters for optimization">
              <FormField label="Days">
                <input
                  type="number"
                  min="1"
                  value={formData.days}
                  onChange={(e) => handleInputChange('days', parseInt(e.target.value, 10) || 0)}
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              <FormField label="Timerange (optional)">
                <input
                  type="text"
                  value={formData.timerange}
                  onChange={(e) => handleInputChange('timerange', e.target.value)}
                  placeholder="20230101-20231231"
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] placeholder:text-[var(--app-text-muted)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              <FormField label="Download Missing Data">
                <label className="flex items-center gap-2 text-sm text-[var(--app-text)]">
                  <input
                    type="checkbox"
                    checked={formData.download_missing_data}
                    onChange={(e) => handleInputChange('download_missing_data', e.target.checked)}
                    className="h-4 w-4 rounded border-[var(--app-border)] bg-[var(--app-surface-raised)] text-[var(--app-accent)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                  />
                  <span>Download missing data before optimization</span>
                </label>
              </FormField>

              {pairs.length > 0 && formData.timeframe && (
                <DataAvailabilityPreview
                  exchange={formData.exchange || 'binance'}
                  pairs={pairs}
                  timeframes={[formData.timeframe]}
                  tradingMode={formData.trading_mode}
                  timerange={formData.timerange}
                  downloadAllowed={formData.download_missing_data}
                />
              )}
            </RunActionCard>

            <RunActionCard title="Advanced Options" description="Optional configuration parameters">
              <FormField label="Exchange">
                <input
                  type="text"
                  value={formData.exchange}
                  onChange={(e) => handleInputChange('exchange', e.target.value)}
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              <FormField label="Max Open Trades">
                <input
                  type="number"
                  min="1"
                  value={formData.max_open_trades}
                  onChange={(e) => handleInputChange('max_open_trades', parseInt(e.target.value, 10) || 0)}
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              <FormField label="Stake Amount">
                <input
                  type="text"
                  value={formData.stake_amount}
                  onChange={(e) => handleInputChange('stake_amount', e.target.value)}
                  className="h-10 w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>

              <FormField label="Notes">
                <textarea
                  value={formData.notes}
                  onChange={(e) => handleInputChange('notes', e.target.value)}
                  rows={3}
                  className="w-full rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-raised)] px-3 py-2 text-sm text-[var(--app-text)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[var(--app-accent)]"
                />
              </FormField>
            </RunActionCard>

            <SectionCard title="Action Audit" description="What this action will do">
              <ul className="space-y-2 text-sm leading-6 text-[var(--app-text-muted)]">
                <li>• Run a local Hyperopt optimization workflow on your strategy.</li>
                <li>• Test multiple parameter combinations across search spaces.</li>
                <li>• Generate trial results and identify best parameters.</li>
                <li>• Create run artifacts in artifacts/runs/ directory.</li>
                <li>• Store results in database for inspection.</li>
              </ul>
              <div className="mt-3 space-y-2 text-sm leading-6 text-[var(--app-text-muted)]">
                <p className="font-medium text-[var(--app-text)]">This will NOT:</p>
                <ul className="space-y-1 ml-4">
                  <li>• Place live trades on exchanges</li>
                  <li>• Connect to exchange APIs for trading</li>
                  <li>• Approve or export strategies automatically</li>
                  <li>• Modify your strategy files</li>
                  <li>• Send data to external services</li>
                </ul>
              </div>
              <div className="mt-3 text-sm leading-6 text-[var(--app-text-muted)]">
                <p className="font-medium text-[var(--app-text)]">To inspect result:</p>
                <p>• View details page after completion</p>
                <p>• Check artifacts/runs/ directory for logs and reports</p>
              </div>
            </SectionCard>

            <SectionCard title="Safety Information" description="Important safety information">
              <ul className="space-y-2 text-sm leading-6 text-[var(--app-text-muted)]">
                <li>• This runs a local Hyperopt workflow.</li>
                <li>• This does not place trades.</li>
                <li>• Best trial is not automatically approved.</li>
                <li>• Optimized result may still be rejected.</li>
                <li>• No export or approval will occur automatically.</li>
              </ul>
            </SectionCard>

            <div className="flex justify-end gap-3">
              <Button variant="primary" onClick={handleStart} disabled={isSubmitting}>
                {isSubmitting ? 'Starting...' : 'Start Optimization'}
              </Button>
            </div>
          </>
        )}

        {/* Confirmation Dialog */}
        <ConfirmationDialog
          isOpen={showConfirmation}
          onClose={handleCancel}
          onConfirm={handleConfirm}
          title="Confirm Optimization"
          actionName="Hyperopt Optimization"
          strategyName={formData.strategy_name}
          pairs={pairs}
          timeframe={formData.timeframe}
          days={formData.days}
          timerange={formData.timerange}
          downloadMissingData={formData.download_missing_data}
          isHyperopt={true}
          isLoading={isSubmitting}
          confirmEnabled={formData.user_confirmed}
        >
          {readinessWarning && (
            <ControlledFailureBanner title="Strategy readiness warning">
              {readinessWarning} This workflow can still be confirmed, but HER is not treating the strategy as ready.
            </ControlledFailureBanner>
          )}
          <ConfirmationChecklist
            checked={formData.user_confirmed}
            onChange={(checked) => handleInputChange('user_confirmed', checked)}
            error={validationErrors.find((e) => e.startsWith('user_confirmed'))?.split(': ')[1]}
          />
        </ConfirmationDialog>
      </RunActionFormShell>
    </AppShell>
  );
}

function strategyReadinessWarning(
  selectedStrategy: StrategySummary | null,
  strategyName: string,
): string | null {
  if (!strategyName.trim()) {
    return null;
  }
  if (!selectedStrategy) {
    return 'Strategy readiness is not verified by the Strategy Workspace response.';
  }
  if (isStrategySelectableForRun(selectedStrategy)) {
    return null;
  }
  return `Strategy readiness is ${readinessLabel(selectedStrategy.readiness)}, not ready.`;
}

function readinessLabel(readiness: StrategySummary['readiness']): string {
  return readiness.replaceAll('_', ' ');
}

function getInitialStrategyName(): string {
  if (typeof window === 'undefined') {
    return '';
  }
  return new URLSearchParams(window.location.search).get('strategy')?.trim() ?? '';
}
