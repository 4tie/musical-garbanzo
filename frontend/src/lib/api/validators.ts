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

// ---------------------------------------------------------------------------
// Baseline validation (unchanged)
// ---------------------------------------------------------------------------

export function validateBaselinePreConfirm(input: BaselineFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  if (!input.strategy_name || input.strategy_name.trim().length === 0) {
    errors.push({ field: 'strategy_name', message: 'Strategy name is required' });
  }

  const pairs = input.pairs.split(',').map(p => p.trim()).filter(p => p.length > 0);
  if (pairs.length === 0) {
    errors.push({ field: 'pairs', message: 'At least one trading pair is required' });
  } else {
    const invalidPairs = pairs.filter(p => !isValidPairFormat(p));
    if (invalidPairs.length > 0) {
      errors.push({
        field: 'pairs',
        message: `Invalid pair format: ${invalidPairs.join(', ')}. Use BASE/QUOTE format (e.g., BTC/USDT)`,
      });
    }
  }

  if (!input.timeframe || input.timeframe.trim().length === 0) {
    errors.push({ field: 'timeframe', message: 'Timeframe is required' });
  }

  if (input.days !== undefined && input.days !== null && input.days <= 0) {
    errors.push({ field: 'days', message: 'Days must be a positive number' });
  }

  if (input.risk_profile && !ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    errors.push({ field: 'risk_profile', message: `Risk profile must be one of: ${ALLOWED_RISK_PROFILES.join(', ')}` });
  }

  if (input.trading_mode && !ALLOWED_TRADING_MODES.includes(input.trading_mode as 'spot')) {
    errors.push({ field: 'trading_mode', message: `Trading mode must be: ${ALLOWED_TRADING_MODES.join(', ')}` });
  }

  if (input.max_open_trades !== undefined && input.max_open_trades !== null && input.max_open_trades <= 0) {
    errors.push({ field: 'max_open_trades', message: 'Max open trades must be a positive number' });
  }

  return { valid: errors.length === 0, errors };
}

export function validateBaselineRequest(input: BaselineFormInput): ValidationResult {
  const errors: ValidationError[] = [];
  const preConfirmResult = validateBaselinePreConfirm(input);
  errors.push(...preConfirmResult.errors);

  if (!input.user_confirmed) {
    errors.push({ field: 'user_confirmed', message: 'User confirmation is required before starting evaluation' });
  }

  return { valid: errors.length === 0, errors };
}

// ---------------------------------------------------------------------------
// Optimization validation — redesigned for new form
// ---------------------------------------------------------------------------

export function validateOptimizationPreConfirm(input: OptimizationFormInput): ValidationResult {
  const errors: ValidationError[] = [];

  // Strategy
  if (!input.strategy_name || input.strategy_name.trim().length === 0) {
    errors.push({ field: 'strategy_name', message: 'Strategy name is required' });
  }

  // Pairs
  const pairs = input.pairs.split(',').map(p => p.trim()).filter(p => p.length > 0);
  if (pairs.length === 0) {
    errors.push({ field: 'pairs', message: 'At least one trading pair is required' });
  } else {
    const invalidPairs = pairs.filter(p => !isValidPairFormat(p));
    if (invalidPairs.length > 0) {
      errors.push({
        field: 'pairs',
        message: `Invalid pair format: ${invalidPairs.join(', ')}. Use BASE/QUOTE format (e.g., BTC/USDT)`,
      });
    }
    if (pairs.length > 50) {
      errors.push({ field: 'pairs', message: `${pairs.length} pairs selected — this may significantly increase runtime` });
    }
  }

  // Timeframe
  if (!input.timeframe || input.timeframe.trim().length === 0) {
    errors.push({ field: 'timeframe', message: 'Timeframe is required' });
  }

  // Timerange (manual mode: validate dates)
  if (input.timerange_mode === 'manual') {
    if (!input.start_date) {
      errors.push({ field: 'start_date', message: 'Start date is required in manual timerange mode' });
    }
    if (!input.end_date) {
      errors.push({ field: 'end_date', message: 'End date is required in manual timerange mode' });
    }
    if (input.start_date && input.end_date && input.start_date >= input.end_date) {
      errors.push({ field: 'end_date', message: 'End date must be after start date' });
    }
  }

  // Risk profile
  if (!ALLOWED_RISK_PROFILES.includes(input.risk_profile)) {
    errors.push({ field: 'risk_profile', message: `Risk profile must be one of: ${ALLOWED_RISK_PROFILES.join(', ')}` });
  }

  // Epochs
  if (input.epochs !== undefined && input.epochs !== null) {
    if (input.epochs <= 0) errors.push({ field: 'epochs', message: 'Epochs must be a positive number' });
    else if (input.epochs > 200) errors.push({ field: 'epochs', message: 'Epochs cannot exceed 200' });
  }

  // Spaces
  if (input.spaces && input.spaces.length > 0) {
    const invalidSpaces = input.spaces.filter(s => !ALLOWED_SPACES.includes(s as 'buy' | 'sell'));
    if (invalidSpaces.length > 0) {
      errors.push({ field: 'spaces', message: `Invalid spaces: ${invalidSpaces.join(', ')}. Only buy and sell are available` });
    }
  }

  // Max open trades
  if (input.max_open_trades !== undefined && input.max_open_trades !== null && input.max_open_trades <= 0) {
    errors.push({ field: 'max_open_trades', message: 'Max open trades must be a positive number' });
  }

  return { valid: errors.length === 0, errors };
}

export function validateOptimizationRequest(input: OptimizationFormInput): ValidationResult {
  const errors: ValidationError[] = [];
  const preConfirmResult = validateOptimizationPreConfirm(input);
  errors.push(...preConfirmResult.errors);

  if (!input.user_confirmed) {
    errors.push({ field: 'user_confirmed', message: 'User confirmation is required before starting optimization' });
  }

  return { valid: errors.length === 0, errors };
}
