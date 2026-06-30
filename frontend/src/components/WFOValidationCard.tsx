import SectionCard from './SectionCard';
import type { ValidationEvidence } from '@/lib/api/types';

interface WFOValidationCardProps {
  evidence?: ValidationEvidence;
  windows?: ValidationEvidence[];
}

export default function WFOValidationCard({ evidence, windows }: WFOValidationCardProps) {
  if (!evidence && (!windows || windows.length === 0)) {
    return (
      <SectionCard title="Walk-Forward Validation">
        <div className="text-sm text-gray-500">No WFO evidence available</div>
      </SectionCard>
    );
  }

  const isPassed = evidence?.status === 'wfo_passed';

  const totalWindows = windows?.length || 0;
  const passedWindows = windows?.filter(w => w.status === 'wfo_passed').length || 0;
  const failedWindows = windows?.filter(w => w.status === 'wfo_failed').length || 0;
  const passRate = totalWindows > 0 ? (passedWindows / totalWindows) * 100 : 0;

  return (
    <SectionCard title="Walk-Forward Validation">
      <div className="space-y-4">
        <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
          isPassed ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
        }`}>
          {isPassed ? 'Passed' : 'Failed'}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-500">Total Windows</div>
            <div className="text-lg font-semibold">{totalWindows}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Passed</div>
            <div className="text-lg font-semibold text-green-600">{passedWindows}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Failed</div>
            <div className="text-lg font-semibold text-red-600">{failedWindows}</div>
          </div>
        </div>

        <div>
          <div className="text-sm text-gray-500">Pass Rate</div>
          <div className="text-lg font-semibold">{passRate.toFixed(1)}%</div>
        </div>

        {windows && windows.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700 mb-2">Window Results</div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Window</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Timerange</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="px-3 py-2 text-left text-xs font-medium text-gray-500 uppercase">Profit Factor</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {windows.map((window, idx) => {
                    const metrics = window.metrics as Record<string, unknown>;
                    return (
                      <tr key={idx} className="hover:bg-gray-50">
                        <td className="px-3 py-2 text-sm text-gray-900">{window.window_index}</td>
                        <td className="px-3 py-2 text-sm text-gray-500">{window.timerange}</td>
                        <td className="px-3 py-2 text-sm">
                          <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                            window.status === 'wfo_passed' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {window.status}
                          </span>
                        </td>
                        <td className="px-3 py-2 text-sm text-gray-900">
                          {metrics.profit_factor !== undefined ? String(metrics.profit_factor) : 'N/A'}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {evidence?.issues && evidence.issues.length > 0 && (
          <div>
            <div className="text-sm font-medium text-gray-700">Issues</div>
            <ul className="mt-1 list-disc list-inside space-y-1 text-sm text-gray-600">
              {evidence.issues.map((issue, idx) => (
                <li key={idx}>{issue.message}</li>
              ))}
            </ul>
          </div>
        )}

        {evidence?.warnings && evidence.warnings.length > 0 && (
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
