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

export interface OptimizationFormInput {
  strategy_name: string;
  pairs: string;
  timeframe: string;
  exchange?: string;
  days?: number;
  timerange?: string;
  risk_profile?: string;
  baseline_run_id?: string;
  run_baseline_first?: boolean;
  download_missing_data?: boolean;
  user_confirmed: boolean;
  epochs?: number;
  spaces?: string[];
  max_open_trades?: number;
  stake_currency?: string;
  stake_amount?: number | string;
  trading_mode?: string;
  apply_decision_to_run?: boolean;
  notes?: string;
}

export function buildBaselineRequest(input: BaselineFormInput): BaselineEvaluationRequest {
  // Parse, normalize, and deduplicate pairs
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

  // Only include optional fields if they have meaningful values
  if (input.exchange && input.exchange.trim()) {
    request.exchange = input.exchange.trim();
  }
  if (input.days && input.days > 0) {
    request.days = input.days;
  }
  if (input.timerange && input.timerange.trim()) {
    request.timerange = input.timerange.trim();
  }
  if (input.risk_profile && ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    request.risk_profile = input.risk_profile;
  }
  if (input.stake_currency && input.stake_currency.trim()) {
    request.stake_currency = input.stake_currency.trim().toUpperCase();
  }
  if (input.stake_amount !== undefined && input.stake_amount !== null) {
    request.stake_amount = input.stake_amount;
  }
  if (input.max_open_trades && input.max_open_trades > 0) {
    request.max_open_trades = input.max_open_trades;
  }
  if (input.trading_mode && ALLOWED_TRADING_MODES.includes(input.trading_mode as 'spot')) {
    request.trading_mode = input.trading_mode;
  }
  if (input.download_missing_data !== undefined) {
    request.download_missing_data = input.download_missing_data;
  }
  if (input.apply_decision_to_run !== undefined) {
    request.apply_decision_to_run = input.apply_decision_to_run;
  }
  if (input.force_parse !== undefined) {
    request.force_parse = input.force_parse;
  }
  if (input.notes && input.notes.trim()) {
    request.notes = input.notes.trim();
  }

  return request;
}

export function buildOptimizationRequest(input: OptimizationFormInput): OptimizationRequest {
  // Parse, normalize, and deduplicate pairs
  const pairs = input.pairs
    .split(',')
    .map(p => p.trim().toUpperCase())
    .filter(p => p.length > 0);
  const uniquePairs = Array.from(new Set(pairs));

  const request: OptimizationRequest = {
    strategy_name: input.strategy_name.trim(),
    pairs: uniquePairs,
    timeframe: input.timeframe.trim(),
    user_confirmed: input.user_confirmed,
  };

  // Only include optional fields if they have meaningful values
  if (input.exchange && input.exchange.trim()) {
    request.exchange = input.exchange.trim();
  }
  if (input.days && input.days > 0) {
    request.days = input.days;
  }
  if (input.timerange && input.timerange.trim()) {
    request.timerange = input.timerange.trim();
  }
  if (input.risk_profile && ALLOWED_RISK_PROFILES.includes(input.risk_profile as 'conservative' | 'balanced' | 'aggressive')) {
    request.risk_profile = input.risk_profile;
  }
  if (input.baseline_run_id && input.baseline_run_id.trim()) {
    request.baseline_run_id = input.baseline_run_id.trim();
  }
  if (input.run_baseline_first !== undefined) {
    request.run_baseline_first = input.run_baseline_first;
  }
  if (input.download_missing_data !== undefined) {
    request.download_missing_data = input.download_missing_data;
  }
  if (input.epochs && input.epochs > 0) {
    request.epochs = Math.min(input.epochs, 200); // Max 200 epochs
  }
  if (input.spaces && input.spaces.length > 0) {
    // Filter to only allowed spaces (buy/sell only - locked spaces are not sent)
    request.spaces = input.spaces.filter(s => ALLOWED_SPACES.includes(s as 'buy' | 'sell'));
  }
  if (input.max_open_trades && input.max_open_trades > 0) {
    request.max_open_trades = input.max_open_trades;
  }
  if (input.stake_currency && input.stake_currency.trim()) {
    request.stake_currency = input.stake_currency.trim().toUpperCase();
  }
  if (input.stake_amount !== undefined && input.stake_amount !== null) {
    request.stake_amount = input.stake_amount;
  }
  if (input.apply_decision_to_run !== undefined) {
    request.apply_decision_to_run = input.apply_decision_to_run;
  }
  if (input.notes && input.notes.trim()) {
    request.notes = input.notes.trim();
  }

  return request;
}
