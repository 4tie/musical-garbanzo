'use client';

import AppShell from '@/components/AppShell';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';

export default function Reports() {
  return (
    <AppShell pageTitle="Reports">
      <div className="space-y-6">
        <PageHeader
          title="Reports"
          description="Report and artifact metadata access."
        />

        <ControlledFailureBanner title="Report access limitation">
          The backend does not currently provide a dedicated reports list endpoint. Reports are accessed
          through individual run detail pages:
        </ControlledFailureBanner>

        <SectionCard title="Available report types" description="Reports are accessible via run detail pages.">
          <div className="space-y-4">
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <h3 className="text-sm font-semibold text-[var(--app-text)]">Baseline reports</h3>
              <p className="mt-2 text-sm text-[var(--app-text-muted)]">
                Access via baseline run detail pages at <code className="rounded bg-[var(--app-surface)] px-1 py-0.5 text-xs">/baseline/[runId]</code>
              </p>
            </div>
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <h3 className="text-sm font-semibold text-[var(--app-text)]">Optimization reports</h3>
              <p className="mt-2 text-sm text-[var(--app-text-muted)]">
                Access via optimization run detail pages at <code className="rounded bg-[var(--app-surface)] px-1 py-0.5 text-xs">/optimization/[optimizationRunId]</code>
              </p>
            </div>
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <h3 className="text-sm font-semibold text-[var(--app-text)]">Decision reports</h3>
              <p className="mt-2 text-sm text-[var(--app-text-muted)]">
                Available in baseline and optimization run detail pages when decision evaluation has completed.
              </p>
            </div>
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <h3 className="text-sm font-semibold text-[var(--app-text)]">Normalized result reports</h3>
              <p className="mt-2 text-sm text-[var(--app-text-muted)]">
                Available in run detail pages when result parsing has completed.
              </p>
            </div>
            <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
              <h3 className="text-sm font-semibold text-[var(--app-text)]">Artifact metadata</h3>
              <p className="mt-2 text-sm text-[var(--app-text-muted)]">
                Safe artifact paths and metadata are shown in run detail pages. Raw logs are not loaded by default.
              </p>
            </div>
          </div>
        </SectionCard>

        <SectionCard title="Report safety notes" description="Important context about report access and interpretation.">
          <div className="space-y-3 text-sm text-[var(--app-text-muted)]">
            <p>• Reports are read-only evidence of past pipeline executions.</p>
            <p>• Pipeline completion does not imply profitability, approval, or live-readiness.</p>
            <p>• <code className="rounded bg-[var(--app-surface)] px-1 py-0.5 text-xs">optimization_rejected</code> is a valid completed result, not a system failure.</p>
            <p>• Raw artifacts are local runtime files and are not committed to version control.</p>
            <p>• This dashboard does not provide live trading actions, strategy approval, or export controls.</p>
          </div>
        </SectionCard>
      </div>
    </AppShell>
  );
}
