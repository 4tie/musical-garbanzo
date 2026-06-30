import { apiGetArray, apiGetRecord } from './client';
import {
  BacktestCombinedResult,
  JsonObject,
  MetricSnapshot,
  PairResult,
  ResultQualityReport,
  TradeSummary,
} from './types';

export function listMetricSnapshots(runId: string) {
  return apiGetArray<MetricSnapshot>(`/api/runs/${encodeURIComponent(runId)}/metrics`);
}

export function getLatestMetrics(runId: string) {
  return apiGetRecord<MetricSnapshot>(`/api/runs/${encodeURIComponent(runId)}/metrics/latest`);
}

export function listPairResults(runId: string) {
  return apiGetArray<PairResult>(`/api/runs/${encodeURIComponent(runId)}/pair-results`);
}

export function getTradeSummary(runId: string) {
  return apiGetRecord<TradeSummary>(`/api/runs/${encodeURIComponent(runId)}/trade-summary`);
}

export function getBacktestResults(runId: string) {
  return apiGetRecord<BacktestCombinedResult>(`/api/results/backtest/${encodeURIComponent(runId)}`);
}

export function getResultQuality(runId: string) {
  return apiGetRecord<ResultQualityReport>(
    `/api/results/backtest/${encodeURIComponent(runId)}/quality`,
  );
}

export function getRunResultQuality(runId: string) {
  return apiGetRecord<ResultQualityReport>(`/api/runs/${encodeURIComponent(runId)}/result-quality`);
}

export function getNormalizedBacktestResult(runId: string) {
  return apiGetRecord<JsonObject>(`/api/results/backtest/${encodeURIComponent(runId)}/normalized`);
}
