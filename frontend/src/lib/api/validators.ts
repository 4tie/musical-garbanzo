import {
  BaselineFormInput,
  OptimizationFormInput,
} from './builders';

// Re-export types for convenience
export type { BaselineFormInput, OptimizationFormInput };

export interface ValidationError {
  field: string;
  message: string;
}

export interface ValidationResult {
  valid: boolean;
  errors: ValidationError[];
}

const ALLOWED_RISK_PROFILES = ['conservative', 'balanced', 'aggressive'] as const;
const ALLOWED_SPACES = ['buy', 'sell'] as const;
const ALLOWED_TRADING_MODES = ['spot'] as const;

// Validate pair format: BASE/QUOTE (e.g., BTC/USDT)
function isValidPairFormat(pair: string): boolean {
  const trimmed = pair.trim();
  if (!trimmed) return false;
  const parts = trimmed.split('/');
  if (parts.length !== 2) return false;
  const [base, quote] = parts;
  return base.length > 0 && quote.length > 0 && /^[A-Z0-9]+$/.test(base) && /^[A-Z0-9]+$/.test(quote);
}

// Pre-confirm validation: checks basic form validity without requiring user_confirmed
export function validateBaselinePreConfirm(input: BaselineFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  // Strategy name is required
  if (!input.strategy_name || input.strategy_name.trim().length === 0) {
    errors.push({ field: 'strategy_name', message: 'Strategy name is required' });
  }

  // At least one pair is required
  const pairs = input.pairs
    .split(',')
    .map(p => p.trim())
    .filter(p => p.length > 0);
  if (pairs.length === 0) {
    errors.push({ field: 'pairs', message: 'At least one trading pair is required' });
  } else {
    // Validate pair format
    const invalidPairs = pairs.filter(p => !isValidPairFormat(p));
    if (invalidPairs.length > 0) {
      errors.push({
        field: 'pairs',
        message: `Invalid pair format: ${invalidPairs.join(', ')}. Use BASE/QUOTE format (e.g., BTC/USDT)`,
      });
    }
  }

  // Timeframe is required
  if (!input.timeframe || input.timeframe.trim().length === 0) {
    errors.push({ field: 'timeframe', message: 'Timeframe is required' });
  }

  // Days must be positive if provided
  if (input.days !== undefined && input.days !== null) {
    if (input.days <= 0) {
      errors.push({ field: 'days', message: 'Days must be a positive number' });
    }
  }

  // Risk profile must be valid if provided
  if (input.risk_profile && !ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    errors.push({
      field: 'risk_profile',
      message: `Risk profile must be one of: ${ALLOWED_RISK_PROFILES.join(', ')}`,
    });
  }

  // Trading mode must be valid if provided
  if (input.trading_mode && !ALLOWED_TRADING_MODES.includes(input.trading_mode as 'spot')) {
    errors.push({
      field: 'trading_mode',
      message: `Trading mode must be: ${ALLOWED_TRADING_MODES.join(', ')}`,
    });
  }

  // Max open trades must be positive if provided
  if (input.max_open_trades !== undefined && input.max_open_trades !== null) {
    if (input.max_open_trades <= 0) {
      errors.push({ field: 'max_open_trades', message: 'Max open trades must be a positive number' });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// Final-submit validation: requires user_confirmed=true
export function validateBaselineRequest(input: BaselineFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  // First run pre-confirm validation
  const preConfirmResult = validateBaselinePreConfirm(input);
  errors.push(...preConfirmResult.errors);

  // User confirmation is required for final submit
  if (!input.user_confirmed) {
    errors.push({
      field: 'user_confirmed',
      message: 'User confirmation is required before starting evaluation',
    });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// Pre-confirm validation: checks basic form validity without requiring user_confirmed
export function validateOptimizationPreConfirm(input: OptimizationFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  // Strategy name is required
  if (!input.strategy_name || input.strategy_name.trim().length === 0) {
    errors.push({ field: 'strategy_name', message: 'Strategy name is required' });
  }

  // At least one pair is required
  const pairs = input.pairs
    .split(',')
    .map(p => p.trim())
    .filter(p => p.length > 0);
  if (pairs.length === 0) {
    errors.push({ field: 'pairs', message: 'At least one trading pair is required' });
  } else {
    // Validate pair format
    const invalidPairs = pairs.filter(p => !isValidPairFormat(p));
    if (invalidPairs.length > 0) {
      errors.push({
        field: 'pairs',
        message: `Invalid pair format: ${invalidPairs.join(', ')}. Use BASE/QUOTE format (e.g., BTC/USDT)`,
      });
    }
  }

  // Timeframe is required
  if (!input.timeframe || input.timeframe.trim().length === 0) {
    errors.push({ field: 'timeframe', message: 'Timeframe is required' });
  }

  // Days must be positive if provided
  if (input.days !== undefined && input.days !== null) {
    if (input.days <= 0) {
      errors.push({ field: 'days', message: 'Days must be a positive number' });
    }
  }

  // Risk profile must be valid if provided
  if (input.risk_profile && !ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    errors.push({
      field: 'risk_profile',
      message: `Risk profile must be one of: ${ALLOWED_RISK_PROFILES.join(', ')}`,
    });
  }

  // Epochs must be positive and <= 200 if provided
  if (input.epochs !== undefined && input.epochs !== null) {
    if (input.epochs <= 0) {
      errors.push({ field: 'epochs', message: 'Epochs must be a positive number' });
    } else if (input.epochs > 200) {
      errors.push({ field: 'epochs', message: 'Epochs cannot exceed 200' });
    }
  }

  // Spaces must be subset of allowed values (only buy/sell are selectable)
  if (input.spaces && input.spaces.length > 0) {
    const invalidSpaces = input.spaces.filter(s => !ALLOWED_SPACES.includes(s as 'buy' | 'sell'));
    if (invalidSpaces.length > 0) {
      errors.push({
        field: 'spaces',
        message: `Invalid spaces: ${invalidSpaces.join(', ')}. Only buy and sell spaces are available for selection`,
      });
    }
  }

  // Max open trades must be positive if provided
  if (input.max_open_trades !== undefined && input.max_open_trades !== null) {
    if (input.max_open_trades <= 0) {
      errors.push({ field: 'max_open_trades', message: 'Max open trades must be a positive number' });
    }
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

// Final-submit validation: requires user_confirmed=true
export function validateOptimizationRequest(input: OptimizationFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  // First run pre-confirm validation
  const preConfirmResult = validateOptimizationPreConfirm(input);
  errors.push(...preConfirmResult.errors);

  // User confirmation is required for final submit
  if (!input.user_confirmed) {
    errors.push({
      field: 'user_confirmed',
      message: 'User confirmation is required before starting optimization',
    });
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}
