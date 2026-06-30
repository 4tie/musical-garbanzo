import { ReactNode } from 'react';

interface ValidationDecisionBannerProps {
  decisionStatus?: string;
  children?: ReactNode;
}

export default function ValidationDecisionBanner({
  decisionStatus,
  children,
}: ValidationDecisionBannerProps) {
  const getBannerColor = () => {
    switch (decisionStatus) {
      case 'validated':
        return 'border-green-200 bg-green-50 text-green-800';
      case 'rejected':
        return 'border-red-200 bg-red-50 text-red-800';
      default:
        return 'border-gray-200 bg-gray-50 text-gray-800';
    }
  };

  const getIcon = () => {
    switch (decisionStatus) {
      case 'validated':
        return '✓';
      case 'rejected':
        return '✗';
      default:
        return 'ℹ';
    }
  };

  return (
    <div className={`rounded-lg border p-4 ${getBannerColor()}`}>
      <div className="flex items-start gap-3">
        <div className="flex h-6 w-6 items-center justify-center rounded-full border-2 border-current font-semibold">
          {getIcon()}
        </div>
        <div className="flex-1">
          <h3 className="font-semibold">
            {decisionStatus === 'validated' ? 'Validation Passed' : 
             decisionStatus === 'rejected' ? 'Validation Failed' : 
             'Validation Status'}
          </h3>
          <div className="mt-2 text-sm">
            <p className="font-medium">Important Notes:</p>
            <ul className="mt-1 list-disc list-inside space-y-1">
              <li>Validation is evidence, not a profit guarantee</li>
              <li>No live trading happened during validation</li>
              <li>No approval or export happened during validation</li>
              <li>Results are based on historical backtest data only</li>
            </ul>
          </div>
          {children && <div className="mt-3">{children}</div>}
        </div>
      </div>
    </div>
  );
}
