import SectionCard from './SectionCard';
import type { ValidationEvidence } from '@/lib/api/types';

interface RobustnessValidationCardProps {
  checks?: ValidationEvidence[];
}

export default function RobustnessValidationCard({ checks }: RobustnessValidationCardProps) {
  if (!checks || checks.length === 0) {
    return (
      <SectionCard title="Robustness Checks">
        <div className="text-sm text-gray-500">No robustness evidence available</div>
      </SectionCard>
    );
  }

  const criticalFailures = checks.filter(c => c.status === 'robustness_failed').length;
  const warnings = checks.filter(c => c.status === 'robustness_warning').length;
  const passed = checks.filter(c => c.status === 'robustness_passed').length;

  const overallStatus = criticalFailures > 0 ? 'failed' : warnings > 0 ? 'warning' : 'passed';

  return (
    <SectionCard title="Robustness Checks">
      <div className="space-y-4">
        <div className={`inline-flex items-center rounded-full px-3 py-1 text-sm font-medium ${
          overallStatus === 'passed' ? 'bg-green-100 text-green-800' :
          overallStatus === 'warning' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          {overallStatus === 'passed' ? 'Passed' :
           overallStatus === 'warning' ? 'Warning' :
           'Failed'}
        </div>

        <div className="grid grid-cols-3 gap-4">
          <div>
            <div className="text-sm text-gray-500">Passed</div>
            <div className="text-lg font-semibold text-green-600">{passed}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Warnings</div>
            <div className="text-lg font-semibold text-yellow-600">{warnings}</div>
          </div>
          <div>
            <div className="text-sm text-gray-500">Critical Failures</div>
            <div className="text-lg font-semibold text-red-600">{criticalFailures}</div>
          </div>
        </div>

        <div>
          <div className="text-sm font-medium text-gray-700 mb-2">Check Results</div>
          <div className="space-y-2">
            {checks.map((check, idx) => (
              <div key={idx} className="rounded border border-gray-200 p-3">
                <div className="flex items-center justify-between">
                  <div className="font-medium text-sm">{check.check_name}</div>
                  <span className={`inline-flex rounded-full px-2 py-1 text-xs font-medium ${
                    check.status === 'robustness_passed' ? 'bg-green-100 text-green-800' :
                    check.status === 'robustness_warning' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-red-100 text-red-800'
                  }`}>
                    {check.status}
                  </span>
                </div>
                {check.timerange && (
                  <div className="mt-1 text-xs text-gray-500">{check.timerange}</div>
                )}
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
                {check.warnings && check.warnings.length > 0 && (
                  <div className="mt-2">
                    <div className="text-xs font-medium text-gray-700">Warnings</div>
                    <ul className="mt-1 list-disc list-inside space-y-1 text-xs text-gray-600">
                      {check.warnings.map((warning, i) => (
                        <li key={i}>{warning}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
}
