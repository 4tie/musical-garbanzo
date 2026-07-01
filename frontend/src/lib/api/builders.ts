import {
  BaselineEvaluationRequest,
  OptimizationRequest,
} from './types';

const ALLOWED_RISK_PROFILES = ['conservative', 'balanced', 'aggressive'] as const;
const ALLOWED_SPACES = ['buy', 'sell'] as const;
const ALLOWED_TRADING_MODES = ['spot'] as const;

export interface BaselineFormInput {
  strategy_name: string;
  pairs: string;
  timeframe: string;
  exchange?: string;
  days?: number;
  timerange?: string;
  risk_profile?: string;
  stake_currency?: string;
  stake_amount?: number | string;
  max_open_trades?: number;
  trading_mode?: string;
  download_missing_data?: boolean;
  user_confirmed: boolean;
  apply_decision_to_run?: boolean;
  force_parse?: boolean;
  notes?: string;
}

// ---------------------------------------------------------------------------
// OptimizationFormInput — drives the redesigned optimization form.
// Separate from OptimizationRequest (the wire type) so the form can carry
// UI-only state (modes, dates, experiment notes) cleanly.
// ---------------------------------------------------------------------------
export interface OptimizationFormInput {
  // Section 1: Strategy
  strategy_name: string;

  // Section 2: Risk Profile
  risk_profile: 'conservative' | 'balanced' | 'aggressive';

  // Section 3: Market Selection
  exchange: string;
  quote_currency: string;
  pair_selection_mode: 'manual' | 'top';
  pairs: string;              // comma-separated
  top_pairs_count: 20 | 50 | 100;

  // Section 4: Time Configuration
  timeframe_mode: 'auto' | 'manual';
  timeframe: string;          // resolved timeframe
  timerange_mode: 'auto' | 'manual';
  timerange: string;          // resolved Freqtrade timerange e.g. 20240101-20241231
  start_date: string;         // YYYY-MM-DD for manual mode
  end_date: string;           // YYYY-MM-DD for manual mode

  // Section 5: Capital / Execution
  max_open_trades: number;
  stake_amount: number | string;
  stake_currency: string;

  // Hyperopt config
  epochs: number;
  spaces: string[];
  run_baseline_first: boolean;
  baseline_run_id?: string;
  apply_decision_to_run?: boolean;

  // Section 6: Experiment Notes
  experiment_notes: string;

  // Confirmation
  user_confirmed: boolean;
}

// Default timeframe per risk profile
export const RISK_PROFILE_TIMEFRAME: Record<string, string> = {
  conservative: '1h',
  balanced:     '30m',
  aggressive:   '15m',
};

// Default lookback days per risk profile
export const RISK_PROFILE_DAYS: Record<string, number> = {
  conservative: 365,  // 12 months
  balanced:     270,  // 9 months
  aggressive:   120,  // 4 months
};

// Format Date as YYYYMMDD for Freqtrade timerange
function fmtDate(d: Date): string {
  return d.toISOString().slice(0, 10).replace(/-/g, '');
}

/** Convert a number of days to a Freqtrade timerange string (start-end). */
export function daysToTimerange(days: number): string {
  const end = new Date();
  const start = new Date();
  start.setDate(start.getDate() - days);
  return `${fmtDate(start)}-${fmtDate(end)}`;
}

/** Convert two YYYY-MM-DD strings to a Freqtrade timerange. */
export function datesToTimerange(startDate: string, endDate: string): string {
  return `${startDate.replace(/-/g, '')}-${endDate.replace(/-/g, '')}`;
}

/** Today as YYYY-MM-DD. */
export function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

/** N days ago as YYYY-MM-DD. */
export function daysAgoStr(days: number): string {
  const d = new Date();
  d.setDate(d.getDate() - days);
  return d.toISOString().slice(0, 10);
}

/** Derive a human-readable timerange label. */
export function timerangeLabel(tr: string): string {
  if (!tr || !tr.includes('-')) return tr;
  const [start, end] = tr.split('-');
  if (start.length === 8 && end.length === 8) {
    return `${start.slice(0,4)}-${start.slice(4,6)}-${start.slice(6,8)} → ${end.slice(0,4)}-${end.slice(4,6)}-${end.slice(6,8)}`;
  }
  return tr;
}

export function buildBaselineRequest(input: BaselineFormInput): BaselineEvaluationRequest {
  const pairs = input.pairs
    .split(',')
    .map(p => p.trim().toUpperCase())
    .filter(p => p.length > 0);
  const uniquePairs = Array.from(new Set(pairs));

  const request: BaselineEvaluationRequest = {
    strategy_name: input.strategy_name.trim(),
    pairs: uniquePairs,
    timeframe: input.timeframe.trim(),
    user_confirmed: input.user_confirmed,
  };

  if (input.exchange && input.exchange.trim()) request.exchange = input.exchange.trim();
  if (input.days && input.days > 0) request.days = input.days;
  if (input.timerange && input.timerange.trim()) request.timerange = input.timerange.trim();
  if (input.risk_profile && ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    request.risk_profile = input.risk_profile;
  }
  if (input.stake_currency && input.stake_currency.trim()) request.stake_currency = input.stake_currency.trim().toUpperCase();
  if (input.stake_amount !== undefined && input.stake_amount !== null) request.stake_amount = input.stake_amount;
  if (input.max_open_trades && input.max_open_trades > 0) request.max_open_trades = input.max_open_trades;
  if (input.trading_mode && ALLOWED_TRADING_MODES.includes(input.trading_mode as 'spot')) request.trading_mode = input.trading_mode;
  if (input.download_missing_data !== undefined) request.download_missing_data = input.download_missing_data;
  if (input.apply_decision_to_run !== undefined) request.apply_decision_to_run = input.apply_decision_to_run;
  if (input.force_parse !== undefined) request.force_parse = input.force_parse;
  if (input.notes && input.notes.trim()) request.notes = input.notes.trim();

  return request;
}

export function buildOptimizationRequest(input: OptimizationFormInput): OptimizationRequest {
  const pairs = input.pairs
    .split(',')
    .map(p => p.trim().toUpperCase())
    .filter(p => p.length > 0);
  const uniquePairs = Array.from(new Set(pairs));

  // Resolve the final timerange string
  let resolvedTimerange: string | undefined;
  if (input.timerange_mode === 'manual' && input.start_date && input.end_date) {
    resolvedTimerange = datesToTimerange(input.start_date, input.end_date);
  } else {
    // Auto mode: derive from risk profile days
    const days = RISK_PROFILE_DAYS[input.risk_profile] ?? 270;
    resolvedTimerange = daysToTimerange(days);
  }

  const request: OptimizationRequest = {
    strategy_name: input.strategy_name.trim(),
    pairs: uniquePairs,
    timeframe: input.timeframe.trim(),
    user_confirmed: input.user_confirmed,
    // Always send download_missing_data=true — checkbox removed, data is auto-managed.
    download_missing_data: true,
  };

  if (input.exchange && input.exchange.trim()) request.exchange = input.exchange.trim();
  if (resolvedTimerange) request.timerange = resolvedTimerange;
  if (input.risk_profile && ALLOWED_RISK_PROFILES.includes(input.risk_profile)) {
    request.risk_profile = input.risk_profile;
  }
  if (input.baseline_run_id && input.baseline_run_id.trim()) request.baseline_run_id = input.baseline_run_id.trim();
  request.run_baseline_first = input.run_baseline_first;
  if (input.epochs && input.epochs > 0) request.epochs = Math.min(input.epochs, 200);
  if (input.spaces && input.spaces.length > 0) {
    request.spaces = input.spaces.filter(s => ALLOWED_SPACES.includes(s as 'buy' | 'sell'));
  }
  if (input.max_open_trades && input.max_open_trades > 0) request.max_open_trades = input.max_open_trades;
  if (input.stake_currency && input.stake_currency.trim()) request.stake_currency = input.stake_currency.trim().toUpperCase();
  if (input.stake_amount !== undefined && input.stake_amount !== null) request.stake_amount = input.stake_amount;
  if (input.apply_decision_to_run !== undefined) request.apply_decision_to_run = input.apply_decision_to_run;
  // Map UI 'experiment_notes' → backend 'notes' field
  if (input.experiment_notes && input.experiment_notes.trim()) {
    request.notes = input.experiment_notes.trim();
  }

  return request;
}
