import { apiGetRecord, apiPost } from './client';

export interface FreqtradeStrategyFile {
  name: string;
  path: string;
  class_name?: string | null;
}

export interface FreqtradeStatusResponse {
  configured: boolean;
  executable_available: boolean;
  version: string | null;
  workspace_valid: boolean;
  allowed_commands: string[];
  forbidden_commands: string[];
  real_smoke_enabled: boolean;
  warnings: string[];
  error: string | null;
}

export interface FreqtradeStrategiesResponse {
  strategies: FreqtradeStrategyFile[];
  source: string;
  error: string | null;
}

export interface FreqtradeDataOverviewResponse {
  data_dir: string;
  exists: boolean;
  pairs_count: number;
  error: string | null;
}

export interface FreqtradeDataCheckRequest {
  run_id?: string;
  exchange: string;
  trading_mode: string;
  pairs: string[];
  timeframes: string[];
  timerange?: string;
  user_confirmed?: boolean;
}

export interface FreqtradeDataCheckResult {
  run_id: string;
  exchange: string;
  trading_mode: string;
  pairs: string[];
  source: string;
  freqtrade_visible: boolean;
  errors: string[];
}

export function getFreqtradeStatus() {
  return apiGetRecord<FreqtradeStatusResponse>('/api/freqtrade/status');
}

export function listFreqtradeStrategies() {
  return apiGetRecord<FreqtradeStrategiesResponse>('/api/freqtrade/strategies');
}

export function getFreqtradeDataOverview(
  exchange?: string,
  tradingMode?: string,
  timeframe?: string,
) {
  const query: Record<string, string | undefined> = {};
  if (exchange) query.exchange = exchange;
  if (tradingMode) query.trading_mode = tradingMode;
  if (timeframe) query.timeframe = timeframe;
  return apiGetRecord<FreqtradeDataOverviewResponse>('/api/freqtrade/data', { query });
}

export function checkDataAvailability(request: FreqtradeDataCheckRequest) {
  return apiPost<FreqtradeDataCheckRequest, FreqtradeDataCheckResult>(
    '/api/freqtrade/data/check',
    { body: request },
  );
}
