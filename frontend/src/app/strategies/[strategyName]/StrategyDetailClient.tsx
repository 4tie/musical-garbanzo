'use client';

import { ReactNode, useCallback, useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import AppShell from '@/components/AppShell';
import Button from '@/components/Button';
import ControlledFailureBanner from '@/components/ControlledFailureBanner';
import CopyButton from '@/components/CopyButton';
import EmptyState from '@/components/EmptyState';
import ErrorBanner from '@/components/ErrorBanner';
import LoadingSkeleton from '@/components/LoadingSkeleton';
import PageHeader from '@/components/PageHeader';
import SectionCard from '@/components/SectionCard';
import StatusBadge from '@/components/StatusBadge';
import {
  ApiError,
  JsonObject,
  StrategyDetail,
  StrategyIssue,
  StrategyIssueSeverity,
  StrategyReadiness,
  getStrategy,
  isStrategySelectableForRun,
  toStrategyStatus,
  validateStrategy,
} from '@/lib/api';

interface StrategyDetailClientProps {
  strategyName: string;
}

interface StrategyDetailState {
  detail: StrategyDetail | null;
  error: ApiError | null;
  revalidateError: ApiError | null;
  loadedAt: string | null;
}

interface ParamsSection {
  key: string;
  label: string;
  value: unknown;
  present: boolean;
}

type StatusTone = 'success' | 'info' | 'warning' | 'danger' | 'optimization' | 'neutral';

const emptyState: StrategyDetailState = {
  detail: null,
  error: null,
  revalidateError: null,
  loadedAt: null,
};

const issueSeverities: StrategyIssueSeverity[] = ['critical', 'error', 'warning', 'info'];

export default function StrategyDetailClient({ strategyName }: StrategyDetailClientProps) {
  const router = useRouter();
  const [state, setState] = useState<StrategyDetailState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [revalidating, setRevalidating] = useState(false);

  const loadStrategy = useCallback(async (markRefreshing = true) => {
    if (markRefreshing) {
      setRefreshing(true);
    }

    const result = await getStrategy(strategyName);
    if (result.success) {
      setState({
        detail: result.data,
        error: null,
        revalidateError: null,
        loadedAt: new Date().toISOString(),
      });
    } else {
      setState({
        detail: null,
        error: result.error,
        revalidateError: null,
        loadedAt: new Date().toISOString(),
      });
    }

    setLoading(false);
    if (markRefreshing) {
      setRefreshing(false);
    }
  }, [strategyName]);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      void loadStrategy(false);
    }, 0);

    return () => window.clearTimeout(timer);
  }, [loadStrategy]);

  const detail = state.detail;
  const status = detail ? toStrategyStatus(detail.readiness) : null;
  const paramsSections = useMemo(() => buildParamsSections(detail), [detail]);
  const groupedIssues = useMemo(() => groupIssues(detail?.issues ?? []), [detail?.issues]);
  const selectable = detail ? isStrategySelectableForRun(detail) : false;

  const handleRevalidate = useCallback(async () => {
    setRevalidating(true);
    const result = await validateStrategy(strategyName);
    if (result.success) {
      setState({
        detail: result.data,
        error: null,
        revalidateError: null,
        loadedAt: new Date().toISOString(),
      });
    } else {
      setState((current) => ({
        ...current,
        revalidateError: result.error,
        loadedAt: new Date().toISOString(),
      }));
    }
    setRevalidating(false);
  }, [strategyName]);

  const navigateToBaseline = useCallback(() => {
    router.push(`/baseline?strategy=${encodeURIComponent(strategyName)}`);
  }, [router, strategyName]);

  const navigateToOptimization = useCallback(() => {
    router.push(`/optimization?strategy=${encodeURIComponent(strategyName)}`);
  }, [router, strategyName]);

  return (
    <AppShell
      pageTitle="Strategy Detail"
      onRefresh={() => {
        void loadStrategy(true);
      }}
      refreshDisabled={refreshing}
    >
      <div className="space-y-6">
        <PageHeader
          title={detail?.strategy_name ?? strategyName}
          description="Static readiness evidence for one local strategy workspace file."
          actions={
            <>
              {state.loadedAt && (
                <span className="text-xs text-[var(--app-text-subtle)]">
                  Updated {formatDateTime(state.loadedAt)}
                </span>
              )}
              <Button variant="secondary" onClick={() => router.push('/strategies')}>
                Back to Strategies
              </Button>
              <Button
                variant="secondary"
                onClick={() => void handleRevalidate()}
                disabled={revalidating || loading}
              >
                {revalidating ? 'Revalidating...' : 'Revalidate'}
              </Button>
            </>
          }
        />

        <div className="grid gap-3 lg:grid-cols-4">
          <SafetyNote title="This page inspects strategy readiness only." />
          <SafetyNote title="It does not execute trades." />
          <SafetyNote title="It does not prove profitability." />
          <SafetyNote title="Run baseline/optimization for evidence." />
        </div>

        {state.error && (
          <ErrorBanner title={state.error.kind === 'not_found' ? 'Strategy not found' : 'Strategy detail unavailable'}>
            {state.error.message}. No fallback or mock strategy detail is shown.
          </ErrorBanner>
        )}

        {state.revalidateError && (
          <ControlledFailureBanner title="Revalidate did not complete">
            {state.revalidateError.message}. Existing detail remains visible until the backend returns a new validation payload.
          </ControlledFailureBanner>
        )}

        <SectionCard title="Readiness summary" description="Backend-computed structural status and source file evidence.">
          {loading ? (
            <LoadingSkeleton lines={6} />
          ) : !detail ? (
            <EmptyState
              title="No strategy detail"
              description="The backend did not return this strategy. HER does not synthesize strategy details."
            />
          ) : (
            <div className="space-y-5">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <SummaryField
                  label="Readiness"
                  value={
                    <StatusBadge
                      status={detail.readiness}
                      label={status?.label}
                      tone={readinessTone(detail.readiness)}
                    />
                  }
                />
                <SummaryField label="Strategy file" value={detail.strategy_file_path} action={<CopyButton value={detail.strategy_file_path} label="Copy path" />} mono />
                <SummaryField label="Sidecar JSON" value={detail.sidecar_json_path ?? 'Missing'} mono />
                <SummaryField label="Class name" value={detail.class_name ?? 'Unknown'} />
                <SummaryField label="Syntax" value={detail.syntax_valid ? 'Valid Python syntax' : 'Syntax not valid'} />
                <SummaryField label="Timeframe" value={detail.params_summary.timeframe ?? stringValue(detail.metadata.timeframe) ?? 'Unknown'} />
                <SummaryField label="Can short" value={formatBoolean(booleanValue(detail.metadata.can_short))} />
                <SummaryField label="Updated" value={formatDateTime(detail.updated_at)} />
              </div>

              <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
                <h3 className="text-sm font-semibold text-[var(--app-text)]">Readiness explanation</h3>
                <p className="mt-2 text-sm leading-6 text-[var(--app-text-muted)]">
                  {readinessExplanation(detail.readiness)}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Button variant="secondary" disabled={!selectable} onClick={navigateToBaseline}>
                  Use in Baseline
                </Button>
                <Button variant="secondary" disabled={!selectable} onClick={navigateToOptimization}>
                  Use in Optimization
                </Button>
              </div>
            </div>
          )}
        </SectionCard>

        {detail && (
          <>
            <SectionCard title="Metadata" description="Static metadata extracted without importing or executing the strategy.">
              <div className="grid gap-4 lg:grid-cols-2">
                <KeyValuePanel title="Strategy metadata" value={detail.metadata} />
                <KeyValuePanel title="Static checks" value={detail.static_checks} />
              </div>
            </SectionCard>

            <SectionCard title="Issues and warnings" description="Inspection findings grouped by severity. Suggestions are informational only.">
              <div className="grid gap-4 lg:grid-cols-2">
                {issueSeverities.map((severity) => (
                  <IssueGroup
                    key={severity}
                    severity={severity}
                    issues={groupedIssues[severity]}
                  />
                ))}
              </div>

              {detail.warnings.length > 0 ? (
                <div className="mt-4 rounded-[var(--app-radius)] border border-[rgb(245_158_11_/_0.34)] bg-[rgb(245_158_11_/_0.1)] p-4">
                  <h3 className="text-sm font-semibold text-[var(--app-warning)]">
                    Backend warnings ({detail.warnings.length})
                  </h3>
                  <ul className="mt-3 space-y-2 text-sm leading-6 text-[var(--app-text-muted)]">
                    {detail.warnings.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-4 text-sm text-[var(--app-text-subtle)]">No standalone backend warnings were returned.</p>
              )}
            </SectionCard>

            <SectionCard title="Params summary" description="Read-only sidecar JSON summary. Values are backend-provided and bounded.">
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <SummaryField label="Sidecar exists" value={detail.params_summary.exists ? 'Yes' : 'No'} />
                <SummaryField label="Parse status" value={detail.params_summary.parse_success ? 'Parsed' : 'Not parsed'} />
                <SummaryField label="Sections" value={detail.params_summary.sections_present.length > 0 ? detail.params_summary.sections_present.join(', ') : 'None'} />
                <SummaryField label="Timeframe" value={detail.params_summary.timeframe ?? 'Not recorded'} />
                <SummaryField label="Max open trades" value={formatValue(detail.params_summary.max_open_trades)} />
                <SummaryField label="Sidecar path" value={detail.params_summary.sidecar_json_path ?? 'Missing'} mono />
              </div>

              {detail.params_summary.issues.length > 0 && (
                <div className="mt-4">
                  <IssueGroup severity="error" issues={detail.params_summary.issues} title="Params issues" />
                </div>
              )}
            </SectionCard>

            <SectionCard title="Safe params preview" description="Top-level params only. Editing is intentionally unavailable in Part 11.">
              <div className="grid gap-4 lg:grid-cols-2">
                {paramsSections.map((section) => (
                  <ParamsPreviewPanel key={section.key} section={section} />
                ))}
              </div>
            </SectionCard>
          </>
        )}
      </div>
    </AppShell>
  );
}

function SafetyNote({ title }: { title: string }) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] px-4 py-3 text-sm font-medium text-[var(--app-text)]">
      {title}
    </div>
  );
}

function SummaryField({
  label,
  value,
  action,
  mono = false,
}: {
  label: string;
  value: ReactNode;
  action?: ReactNode;
  mono?: boolean;
}) {
  return (
    <div className="min-w-0 rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-xs font-medium uppercase text-[var(--app-text-subtle)]">{label}</p>
        {action}
      </div>
      <div
        className={[
          'mt-2 break-words text-sm text-[var(--app-text)]',
          mono ? 'font-mono text-xs leading-5' : '',
        ].join(' ')}
      >
        {value}
      </div>
    </div>
  );
}

function KeyValuePanel({ title, value }: { title: string; value: JsonObject | Record<string, boolean> }) {
  const entries = Object.entries(value);
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <h3 className="text-sm font-semibold text-[var(--app-text)]">{title}</h3>
      {entries.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--app-text-subtle)]">No values returned.</p>
      ) : (
        <dl className="mt-3 grid gap-3 sm:grid-cols-2">
          {entries.map(([key, item]) => (
            <div key={key} className="min-w-0">
              <dt className="text-xs font-medium uppercase text-[var(--app-text-subtle)]">{labelize(key)}</dt>
              <dd className="mt-1 break-words font-mono text-xs leading-5 text-[var(--app-text-muted)]">
                {formatJsonInline(item)}
              </dd>
            </div>
          ))}
        </dl>
      )}
    </div>
  );
}

function IssueGroup({
  severity,
  issues,
  title,
}: {
  severity: StrategyIssueSeverity;
  issues: StrategyIssue[];
  title?: string;
}) {
  const tone = severityTone(severity);
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--app-text)]">
          {title ?? labelize(severity)} ({issues.length})
        </h3>
        <StatusBadge status={severity} label={labelize(severity)} tone={tone} />
      </div>
      {issues.length === 0 ? (
        <p className="mt-3 text-sm text-[var(--app-text-subtle)]">No {labelize(severity).toLowerCase()} issues.</p>
      ) : (
        <ul className="mt-3 space-y-3">
          {issues.map((issue, index) => (
            <li key={`${issue.code}-${index}`} className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface)] p-3">
              <p className="font-mono text-xs text-[var(--app-text-subtle)]">{issue.code}</p>
              <p className="mt-1 text-sm font-medium text-[var(--app-text)]">{issue.message}</p>
              {Object.keys(issue.details).length > 0 && (
                <pre className="mt-2 max-h-32 overflow-auto rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-bg-subtle)] p-3 text-xs leading-5 text-[var(--app-text-muted)]">
                  {stringifyPreview(issue.details)}
                </pre>
              )}
              <p className="mt-2 text-xs leading-5 text-[var(--app-text-subtle)]">
                Suggestion: {suggestIssueAction(issue)}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function ParamsPreviewPanel({ section }: { section: ParamsSection }) {
  return (
    <div className="rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-surface-muted)] p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-semibold text-[var(--app-text)]">{section.label}</h3>
        <StatusBadge
          status={section.present ? 'configured' : 'missing'}
          label={section.present ? 'Present' : 'Missing'}
          tone={section.present ? 'success' : 'neutral'}
        />
      </div>
      {section.present ? (
        <pre className="mt-3 max-h-72 overflow-auto rounded-[var(--app-radius)] border border-[var(--app-border)] bg-[var(--app-bg-subtle)] p-3 text-xs leading-5 text-[var(--app-text-muted)]">
          {stringifyPreview(section.value)}
        </pre>
      ) : (
        <p className="mt-3 text-sm text-[var(--app-text-subtle)]">Not present in the sidecar preview.</p>
      )}
    </div>
  );
}

function buildParamsSections(detail: StrategyDetail | null): ParamsSection[] {
  const preview = detail?.params_summary.preview ?? {};
  return [
    { key: 'buy', label: 'Buy params', value: preview.buy, present: Object.hasOwn(preview, 'buy') },
    { key: 'sell', label: 'Sell params', value: preview.sell, present: Object.hasOwn(preview, 'sell') },
    { key: 'roi', label: 'ROI', value: preview.roi, present: Object.hasOwn(preview, 'roi') },
    { key: 'stoploss', label: 'Stoploss', value: preview.stoploss, present: Object.hasOwn(preview, 'stoploss') },
    { key: 'trailing', label: 'Trailing', value: preview.trailing, present: Object.hasOwn(preview, 'trailing') },
    {
      key: 'protections',
      label: 'Protections',
      value: preview.protections ?? preview.protection,
      present: Object.hasOwn(preview, 'protections') || Object.hasOwn(preview, 'protection'),
    },
    {
      key: 'max_open_trades',
      label: 'Max open trades',
      value: preview.max_open_trades ?? detail?.params_summary.max_open_trades,
      present: Object.hasOwn(preview, 'max_open_trades') || detail?.params_summary.max_open_trades != null,
    },
    {
      key: 'timeframe',
      label: 'Timeframe',
      value: preview.timeframe ?? detail?.params_summary.timeframe,
      present: Object.hasOwn(preview, 'timeframe') || Boolean(detail?.params_summary.timeframe),
    },
  ];
}

function groupIssues(issues: StrategyIssue[]): Record<StrategyIssueSeverity, StrategyIssue[]> {
  return {
    critical: issues.filter((issue) => issue.severity === 'critical'),
    error: issues.filter((issue) => issue.severity === 'error'),
    warning: issues.filter((issue) => issue.severity === 'warning'),
    info: issues.filter((issue) => issue.severity === 'info'),
  };
}

function readinessTone(readiness: StrategyReadiness): StatusTone {
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

function severityTone(severity: StrategyIssueSeverity): StatusTone {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'info':
      return 'info';
    default:
      return 'neutral';
  }
}

function readinessExplanation(readiness: StrategyReadiness): string {
  switch (readiness) {
    case 'ready':
      return 'The backend found a readable strategy file, valid Python syntax, static strategy structure, and a parseable sidecar JSON. This does not prove profitability.';
    case 'warning':
      return 'The strategy is structurally readable, but the backend found non-blocking warnings that should be reviewed before validation.';
    case 'missing_sidecar':
      return 'The strategy file is present and readable, but HER did not find the deterministic sidecar JSON for params.';
    case 'invalid':
      return 'The backend could read the file, but required static strategy structure was missing or incomplete.';
    case 'parse_error':
      return 'The backend could not parse the Python strategy or sidecar JSON safely.';
    case 'unsafe':
      return 'The backend found an unsafe path, unsupported file condition, or suspicious static pattern. HER will not mark it ready.';
    default:
      return 'The backend returned an unknown readiness state.';
  }
}

function suggestIssueAction(issue: StrategyIssue): string {
  if (issue.code.includes('sidecar')) {
    return 'Review the deterministic sidecar JSON file and revalidate after correcting it outside HER.';
  }
  if (issue.code.includes('syntax') || issue.code.includes('parse')) {
    return 'Open the source file in an editor, fix the parse problem manually, then revalidate.';
  }
  if (issue.code.includes('unsafe')) {
    return 'Inspect the flagged code or path manually. HER will not auto-repair or execute it.';
  }
  if (issue.code.includes('strategy_class') || issue.code.includes('structure')) {
    return 'Confirm the strategy class and required Freqtrade hooks are present.';
  }
  return 'Review the issue evidence manually. HER does not auto-fix strategies in Part 11.';
}

function stringifyPreview(value: unknown): string {
  return JSON.stringify(redactSecretLike(value), null, 2);
}

function redactSecretLike(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map(redactSecretLike);
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>).map(([key, item]) => [
        key,
        isSecretKey(key) ? '[redacted]' : redactSecretLike(item),
      ]),
    );
  }
  return value;
}

function isSecretKey(key: string): boolean {
  return /secret|token|password|passphrase|api[_-]?key|private[_-]?key/i.test(key);
}

function stringValue(value: unknown): string | null {
  return typeof value === 'string' && value.trim() ? value : null;
}

function booleanValue(value: unknown): boolean | null {
  return typeof value === 'boolean' ? value : null;
}

function formatBoolean(value: boolean | null): string {
  if (value === true) {
    return 'Yes';
  }
  if (value === false) {
    return 'No';
  }
  return 'Unknown';
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) {
    return 'Not recorded';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return formatJsonInline(value);
}

function formatJsonInline(value: unknown): string {
  if (value === null || value === undefined) {
    return 'null';
  }
  if (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean') {
    return String(value);
  }
  return stringifyPreview(value);
}

function labelize(value: string): string {
  return value
    .replaceAll('_', ' ')
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return 'Not recorded';
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date);
}
