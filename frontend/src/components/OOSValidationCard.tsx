import SectionCard from './SectionCard';
import type { ValidationEvidence } from '@/lib/api/types';

interface OOSValidationCardProps {
  evidence?: ValidationEvidence;
}

export default function OOSValidationCard({ evidence }: OOSValidationCardProps) {
  if (!evidence) {
    return (
      <SectionCard title="Out-of-Sample Validation">
        <div className="text-sm text-gray-500">No OOS evidence available</div>
      </SectionCard>
    );
  }

  const metrics = evidence.metrics as Record<string, unknown>;
  const isPassed = evidence.status === 'oos_passed';

  return (
    <SectionCard title="Out-of-Sample Validation">
      <div className="space-y-4">
        <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
          isPassed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {isPassed ? 'Passed' : 'Failed'}
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <div className="text-sm text-gray-500">Profit Factor</div>
            <div className="text-lg font-semibold">
              {metrics.profit_factor !== undefined ? String(metrics.profit_factor) : 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Trades</div>
            <div className="text-lg font-semibold">
              {metrics.trade_count !== undefined ? String(metrics.trade_count) : 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Expectancy</div>
            <div className="text-lg font-semibold">
              {metrics.expectancy !== undefined ? String(metrics.expectancy) : 'N/A'}
            </div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Drawdown</div>
            <div className="text-lg font-semibold">
              {metrics.max_drawdown_pct !== undefined ? `${String(metrics.max_drawdown_pct)}%` : 'N/A'}
            </div>
          </div>
        </div>

        {evidence.timerange && (
          <div>
            <div className="text-sm text-gray-500">Timerange</div>
            <div className="text-sm font-medium">{evidence.timerange}</div>
          </div>
        )}

        {evidence.issues && evidence.issues.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700">Issues</div>
            <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-gray-600">
              {evidence.issues.map((issue, idx) => (
                <li key={idx}>{issue.message}</li>
              ))}
            </ul>
          </div>
        )}

        {evidence.warnings && evidence.warnings.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700">Warnings</div>
            <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-gray-600">
              {evidence.warnings.map((warning, idx) => (
                <li key={idx}>{warning}</li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </SectionCard>
  );
}
