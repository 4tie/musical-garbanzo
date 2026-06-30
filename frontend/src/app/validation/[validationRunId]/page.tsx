'use client';

import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import CopyButton from '@/components/CopyButton';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import OOSValidationCard from '@/components/OOSValidationCard';
import PageHeader from '@/components/PageHeader';
import RobustnessValidationCard from '@/components/RobustnessValidationCard';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import ValidationDecisionBanner from '@/components/ValidationDecisionBanner';
import WFOValidationCard from '@/components/WFOValidationCard';
import { getValidationRun, getValidationEvidence } from '@/lib/api/validation';
import type { ValidationRunDetail, ValidationEvidence, ValidationDecision } from '@/lib/api/types';

function fmtTs(ts: string | null | undefined): string {
  if (!ts) return '—';
  try {
    return new Date(ts).toLocaleString(undefined, {
      month: 'short', day: 'numeric', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch {
    return ts;
  }
}

function Field({ label, children, mono = false }: { label: string; children: React.ReactNode; mono?: boolean }) {
  return (
    <div>
      <p className="text-xs font-semibold text-[var(--app-text-subtle)]">{label}</p>
      <div className={`mt-1 text-sm text-[var(--app-text)] ${mono ? 'font-mono' : ''}`}>
        {children}
      </div>
    </div>
  );
}

export default function ValidationDetailPage() {
  const params = useParams();
  const validationRunId = params.validationRunId as string;

  const [detail, setDetail] = useState<ValidationRunDetail | null>(null);
  const [evidence, setEvidence] = useState<ValidationEvidence[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) setRefreshing(true);
    setError(null);

    const [detailResult, evidenceResult] = await Promise.all([
      getValidationRun(validationRunId),
      getValidationEvidence(validationRunId),
    ]);

    if (detailResult.success) {
      setDetail(detailResult.data);
    } else {
      setError(detailResult.error.message);
    }

    if (evidenceResult.success) {
      setEvidence(evidenceResult.data.evidence);
    }

    setLoading(false);
    if (markRefreshing) setRefreshing(false);
  }, [validationRunId]);

  useEffect(() => {
    const t = window.setTimeout(() => { void load(false); }, 0);
    return () => window.clearTimeout(t);
  }, [load]);

  const oosEvidence = evidence?.find((e) => e.evidence_type === 'oos');
  const wfoSummary = evidence?.find((e) => e.evidence_type === 'wfo_summary');
  const wfoWindows = evidence?.filter((e) => e.evidence_type === 'wfo_window');
  const robustnessChecks = evidence?.filter((e) => e.evidence_type === 'robustness');
  const sensitivityChecks = evidence?.filter((e) => e.evidence_type === 'sensitivity');

  const finalDecision = detail?.final_decision as ValidationDecision | null | undefined;

  if (loading) {
    return (
      <AppShell pageTitle="Validation Detail">
        <div className="space-y-6">
          <PageHeader title="Validation detail" description="Loading validation evidence…" />
          <LoadingSkeleton lines={6} />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell pageTitle="Validation Detail">
        <div className="space-y-6">
          <PageHeader title="Validation detail" description="Validation evidence could not be loaded." />
          <ErrorBanner title="Error loading validation data">
            <p>{error}</p>
          </ErrorBanner>
          <div>
            <Button onClick={() => { void load(true); }}>Retry</Button>
          </div>
        </div>
      </AppShell>
    );
  }

  if (!detail) {
    return (
      <AppShell pageTitle="Validation Detail">
        <div className="space-y-6">
          <PageHeader title="Validation detail" />
          <SectionCard>
            <EmptyState
              title="Validation run not found"
              description={`Validation run ${validationRunId} could not be found.`}
            />
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  return (
    <AppShell
      pageTitle="Validation Detail"
      onRefresh={() => { void load(true); }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title="Validation detail"
          description="Read-only validation evidence. OOS, WFO, and robustness results are from real backend data only."
          actions={
            <>
              <CopyButton value={validationRunId} label="Copy run ID" />
              <Button variant="secondary" onClick={() => { void load(true); }} disabled={refreshing}>
                Refresh
              </Button>
            </>
          }
        />

        <ControlledFailureBanner title="Validation is evidence only">
          Validation is evidence only. It is not strategy approval, export, live-trading authorization, or a guarantee of future performance.
        </ControlledFailureBanner>

        <ValidationDecisionBanner decisionStatus={detail.run.decision_status} />

        <SectionCard title="Run summary" description="Identity, scope, and status metadata for this validation run.">
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
            <Field label="Validation run ID" mono>
              <span className="truncate block">{validationRunId}</span>
            </Field>
            <Field label="Strategy">
              {detail.run.strategy_name || '—'}
            </Field>
            <Field label="Source type">
              {detail.run.source_type || '—'}
            </Field>
            <Field label="Source run ID" mono>
              {detail.run.source_run_id
                ? <span className="flex items-center gap-2">
                    <span className="truncate">{detail.run.source_run_id}</span>
                    <CopyButton value={detail.run.source_run_id} label="Copy" />
                  </span>
                : '—'}
            </Field>
            <Field label="Status">
              <StatusBadge status={detail.run.status} />
            </Field>
            <Field label="Decision status">
              {detail.run.decision_status
                ? <StatusBadge status={detail.run.decision_status} />
                : <span className="text-[var(--app-text-subtle)]">Not recorded</span>}
            </Field>
            <Field label="Pairs">
              {detail.run.pairs?.join(', ') || '—'}
            </Field>
            <Field label="Timeframe">
              {detail.run.timeframe || '—'}
            </Field>
            <Field label="Exchange">
              {detail.run.exchange || '—'}
            </Field>
            <Field label="Risk profile">
              {detail.run.risk_profile || '—'}
            </Field>
            <Field label="Created">
              {fmtTs(detail.run.created_at)}
            </Field>
            <Field label="Updated">
              {fmtTs(detail.run.updated_at)}
            </Field>
          </div>
          {detail.run.oos_timerange && (
            <div className="mt-4">
              <Field label="OOS timerange" mono>
                {detail.run.oos_timerange}
              </Field>
            </div>
          )}
        </SectionCard>

        <div className="grid gap-6 xl:grid-cols-2">
          <OOSValidationCard evidence={oosEvidence} />
          <WFOValidationCard evidence={wfoSummary} windows={wfoWindows} />
        </div>

        <RobustnessValidationCard checks={robustnessChecks} />

        {sensitivityChecks && sensitivityChecks.length > 0 && (
          <SectionCard title="Sensitivity checks" description="Sensitivity analysis tests how the strategy responds to parameter variations.">
            <div className="space-y-2">
              {sensitivityChecks.map((check, idx) => {
                const isPassed = check.status === 'sensitivity_passed';
                return (
                  <div
                    key={idx}
                    className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <p className="text-sm font-medium text-[var(--app-text)]">
                        {check.check_name ?? `Check ${idx + 1}`}
                      </p>
                      <StatusBadge
                        status={check.status}
                        tone={isPassed ? 'success' : 'warning'}
                        label={isPassed ? 'Passed' : check.status}
                      />
                    </div>
                    {check.issues && check.issues.length > 0 && (
                      <ul className="mt-2 space-y-1">
                        {check.issues.map((issue, i) => (
                          <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                            <span className="text-[var(--app-warning)] shrink-0">•</span>
                            {issue.message}
                          </li>
                        ))}
                      </ul>
                    )}
                  </div>
                );
              })}
            </div>
          </SectionCard>
        )}

        {finalDecision && (
          <SectionCard
            title="Final decision"
            description="The validation engine's final evidence-based decision. This is not an approval."
          >
            <div className="space-y-4">
              <div className="grid gap-4 md:grid-cols-3">
                <div>
                  <p className="text-xs text-[var(--app-text-subtle)]">Decision status</p>
                  <div className="mt-1">
                    <StatusBadge status={finalDecision.decision_status} />
                  </div>
                </div>
                {finalDecision.confidence_score != null && (
                  <div>
                    <p className="text-xs text-[var(--app-text-subtle)]">Confidence score</p>
                    <p className="mt-1 text-sm font-semibold text-[var(--app-text)]">
                      {Number(finalDecision.confidence_score).toFixed(3)}
                    </p>
                  </div>
                )}
                {finalDecision.policy_name && (
                  <div>
                    <p className="text-xs text-[var(--app-text-subtle)]">Policy</p>
                    <p className="mt-1 text-sm text-[var(--app-text)]">{finalDecision.policy_name}</p>
                  </div>
                )}
              </div>
              {finalDecision.blocking_failures && finalDecision.blocking_failures.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-danger)] mb-1">Blocking failures</p>
                  <ul className="space-y-1">
                    {finalDecision.blocking_failures.map((f, i) => (
                      <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-danger)] shrink-0">•</span>{f}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {finalDecision.reasons && finalDecision.reasons.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-text-muted)] mb-1">Reasons</p>
                  <ul className="space-y-1">
                    {finalDecision.reasons.map((r, i) => (
                      <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-text-subtle)] shrink-0">•</span>{r}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {finalDecision.warnings && finalDecision.warnings.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-warning)] mb-1">Warnings</p>
                  <ul className="space-y-1">
                    {finalDecision.warnings.map((w, i) => (
                      <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-warning)] shrink-0">•</span>{w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {finalDecision.next_actions && finalDecision.next_actions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-info)] mb-1">Next actions</p>
                  <ul className="space-y-1">
                    {finalDecision.next_actions.map((a, i) => (
                      <li key={i} className="text-xs text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-info)] shrink-0">→</span>{a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </SectionCard>
        )}

        {(detail.warnings.length > 0 || detail.errors.length > 0 || detail.next_actions.length > 0) && (
          <SectionCard title="Warnings, errors, and next actions" description="Validation pipeline messages and suggested next steps.">
            <div className="space-y-4">
              {detail.errors.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-danger)] mb-1">Errors</p>
                  <ul className="space-y-1">
                    {detail.errors.map((e, idx) => (
                      <li key={idx} className="text-sm text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-danger)] shrink-0">•</span>{e}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.warnings.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-warning)] mb-1">Warnings</p>
                  <ul className="space-y-1">
                    {detail.warnings.map((w, idx) => (
                      <li key={idx} className="text-sm text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-warning)] shrink-0">•</span>{w}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.next_actions.length > 0 && (
                <div>
                  <p className="text-xs font-semibold text-[var(--app-info)] mb-1">Next actions</p>
                  <ul className="space-y-1">
                    {detail.next_actions.map((a, idx) => (
                      <li key={idx} className="text-sm text-[var(--app-text-muted)] flex gap-2">
                        <span className="text-[var(--app-info)] shrink-0">→</span>{a}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </SectionCard>
        )}

        {detail.report_path && (
          <SectionCard title="Report artifact" description="Local artifact path for the validation report file.">
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs text-[var(--app-text-muted)]">{detail.report_path}</span>
              <CopyButton value={detail.report_path} label="Copy path" />
            </div>
          </SectionCard>
        )}
      </div>
    </AppShell>
  );
}
