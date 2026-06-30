'use client';

/* eslint-disable react-hooks/set-state-in-effect */
import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import SectionCard from '@/components/SectionCard';
import EmptyState from '@/components/EmptyState';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import ValidationDecisionBanner from '@/components/ValidationDecisionBanner';
import OOSValidationCard from '@/components/OOSValidationCard';
import WFOValidationCard from '@/components/WFOValidationCard';
import RobustnessValidationCard from '@/components/RobustnessValidationCard';
import { getValidationRun, getValidationEvidence } from '@/lib/api/validation';
import type { ValidationRunDetail, ValidationEvidence } from '@/lib/api/types';

export default function ValidationDetailPage() {
  const params = useParams();
  const validationRunId = params.validationRunId as string;

  const [detail, setDetail] = useState<ValidationRunDetail | null>(null);
  const [evidence, setEvidence] = useState<ValidationEvidence[] | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadValidationData = useCallback(async () => {
    setLoading(true);
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
  }, [validationRunId]);

  useEffect(() => {
    loadValidationData();
  }, [loadValidationData]);

  if (loading) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Detail</h1>
            <p className="text-gray-600 mt-1">View validation evidence for this run</p>
          </div>
          <LoadingSkeleton />
        </div>
      </AppShell>
    );
  }

  if (error) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Detail</h1>
            <p className="text-gray-600 mt-1">View validation evidence for this run</p>
          </div>
          <SectionCard>
            <EmptyState
              title="Error loading validation data"
              description={error}
            />
            <div className="mt-4">
              <Button onClick={loadValidationData}>Retry</Button>
            </div>
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  if (!detail) {
    return (
      <AppShell>
        <div className="space-y-6">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Detail</h1>
            <p className="text-gray-600 mt-1">View validation evidence for this run</p>
          </div>
          <SectionCard>
            <EmptyState
              title="Validation run not found"
              description={`Validation run ${validationRunId} could not be found`}
            />
          </SectionCard>
        </div>
      </AppShell>
    );
  }

  const oosEvidence = evidence?.find(e => e.evidence_type === 'oos');
  const wfoSummary = evidence?.find(e => e.evidence_type === 'wfo_summary');
  const wfoWindows = evidence?.filter(e => e.evidence_type === 'wfo_window');
  const robustnessChecks = evidence?.filter(e => e.evidence_type === 'robustness');
  const sensitivityChecks = evidence?.filter(e => e.evidence_type === 'sensitivity');

  return (
    <AppShell>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">Validation Detail</h1>
            <p className="text-gray-600 mt-1">
              {detail.run.strategy_name} • {detail.run.source_type}
            </p>
          </div>
          <Button onClick={loadValidationData} variant="secondary">
            Refresh
          </Button>
        </div>

        <ValidationDecisionBanner decisionStatus={detail.run.decision_status} />

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <OOSValidationCard evidence={oosEvidence} />
          <WFOValidationCard evidence={wfoSummary} windows={wfoWindows} />
        </div>

        <RobustnessValidationCard checks={robustnessChecks} />

        {sensitivityChecks && sensitivityChecks.length > 0 && (
          <SectionCard title="Sensitivity Checks">
            <div className="space-y-2">
              {sensitivityChecks.map((check, idx) => (
                <div key={idx} className="rounded border border-gray-200 p-3">
                  <div className="flex items-center justify-between">
                    <div className="font-medium text-sm">{check.check_name}</div>
                    <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                      check.status === 'sensitivity_passed' ? 'bg-green-100 text-green-800' :
                      'bg-yellow-100 text-yellow-800'
                    }`}>
                      {check.status}
                    </span>
                  </div>
                  {check.issues && check.issues.length > 0 && (
                    <div className="mt-2">
                      <div className="text-xs font-medium text-gray-700">Issues</div>
                      <ul className="mt-1 list-disc list-inside space-y-1 text-xs text-gray-600">
                        {check.issues.map((issue, i) => (
                          <li key={i}>{issue.message}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </SectionCard>
        )}

        {(detail.warnings.length > 0 || detail.errors.length > 0 || detail.next_actions.length > 0) && (
          <SectionCard title="Warnings, Errors, and Next Actions">
            <div className="space-y-4">
              {detail.warnings.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700">Warnings</div>
                  <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-gray-600">
                    {detail.warnings.map((warning, idx) => (
                      <li key={idx}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.errors.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700">Errors</div>
                  <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-red-600">
                    {detail.errors.map((error, idx) => (
                      <li key={idx}>{error}</li>
                    ))}
                  </ul>
                </div>
              )}
              {detail.next_actions.length > 0 && (
                <div>
                  <div className="text-sm font-medium text-gray-700">Next Actions</div>
                  <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-gray-600">
                    {detail.next_actions.map((action, idx) => (
                      <li key={idx}>{action}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </SectionCard>
        )}

        {detail.report_path && (
          <SectionCard title="Report Artifact">
            <div className="text-sm">
              <div className="text-gray-500">Report Path:</div>
              <div className="font-mono text-xs mt-1">{detail.report_path}</div>
            </div>
          </SectionCard>
        )}
      </div>
    </AppShell>
  );
}
