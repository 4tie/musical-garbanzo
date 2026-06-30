/**
 * Recovery suggestions for common failure scenarios
 * These are safe, actionable suggestions that do not suggest live trading or bypassing validation
 */

export interface RecoverySuggestion {
  errorPattern: string;
  suggestion: string;
}

const RECOVERY_SUGGESTIONS: RecoverySuggestion[] = [
  {
    errorPattern: 'missing data|no data|data not found|data unavailable',
    suggestion: 'Enable "Download Missing Data" and rerun.',
  },
  {
    errorPattern: 'invalid strategy|strategy not found|strategy file not found',
    suggestion: 'Check strategy name and verify strategy file exists.',
  },
  {
    errorPattern: 'hyperopt|hyperopt dependency|hyperopt not installed',
    suggestion: 'Install backend requirements with Hyperopt extras: pip install -e .[hyperopt]',
  },
  {
    errorPattern: 'no trials|no best trial|trials empty|trials not found',
    suggestion: 'Inspect Hyperopt stderr artifact for details.',
  },
  {
    errorPattern: 'invalid pair|pair format|pair not found',
    suggestion: 'Check pair format (e.g., BTC/USDT) and verify exchange supports the pair.',
  },
  {
    errorPattern: 'invalid timeframe|timeframe not supported',
    suggestion: 'Check timeframe is one of the supported values (1m, 3m, 5m, 15m, 30m, 1h, 4h, 1d).',
  },
  {
    errorPattern: 'exchange error|exchange not available|exchange connection',
    suggestion: 'Check exchange configuration and network connectivity.',
  },
  {
    errorPattern: 'permission|access denied|unauthorized',
    suggestion: 'Check file permissions and directory access.',
  },
  {
    errorPattern: 'memory|out of memory|oom',
    suggestion: 'Reduce epochs or data range, or increase available memory.',
  },
  {
    errorPattern: 'timeout|time out|took too long',
    suggestion: 'Reduce epochs or data range, or increase timeout configuration.',
  },
];

/**
 * Get recovery suggestions based on error message
 */
export function getRecoverySuggestion(errorMessage: string): string | null {
  const lowerError = errorMessage.toLowerCase();
  
  for (const { errorPattern, suggestion } of RECOVERY_SUGGESTIONS) {
    const pattern = new RegExp(errorPattern, 'i');
    if (pattern.test(lowerError)) {
      return suggestion;
    }
  }
  
  return null;
}

/**
 * Get all recovery suggestions that match any of the error messages
 */
export function getRecoverySuggestions(errorMessages: string[]): string[] {
  const suggestions: string[] = [];
  const seen = new Set<string>();
  
  for (const error of errorMessages) {
    const suggestion = getRecoverySuggestion(error);
    if (suggestion && !seen.has(suggestion)) {
      suggestions.push(suggestion);
      seen.add(suggestion);
    }
  }
  
  return suggestions;
}

/**
 * Get generic recovery suggestion when no specific match is found
 */
export function getGenericRecoverySuggestion(): string {
  return 'Review error details and check backend logs for more information.';
}
