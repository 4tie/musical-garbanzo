import { apiGetArray, apiGetRecord, apiPost } from './client';
import {
  StrategyDetail,
  StrategyImportRequest,
  StrategyImportResult,
  StrategyParamsSummary,
  StrategyReadiness,
  StrategySummary,
} from './types';

export interface ListStrategiesFilters {
  readiness?: StrategyReadiness;
  has_sidecar?: boolean;
  search?: string;
  limit?: number;
  offset?: number;
}

export function listStrategies(filters: ListStrategiesFilters = {}) {
  return apiGetArray<StrategySummary>('/api/strategies', {
    query: {
      readiness: filters.readiness,
      has_sidecar: filters.has_sidecar,
      search: filters.search,
      limit: filters.limit,
      offset: filters.offset,
    },
  });
}

export function getStrategy(strategyName: string) {
  return apiGetRecord<StrategyDetail>(`/api/strategies/${encodeURIComponent(strategyName)}`);
}

export function getStrategyParams(strategyName: string) {
  return apiGetRecord<StrategyParamsSummary>(
    `/api/strategies/${encodeURIComponent(strategyName)}/params`,
  );
}

export function validateStrategy(strategyName: string) {
  return apiPost<Record<string, never>, StrategyDetail>(
    `/api/strategies/${encodeURIComponent(strategyName)}/validate`,
    { body: {} },
  );
}

export function importStrategy(request: StrategyImportRequest) {
  return apiPost<StrategyImportRequest, StrategyImportResult>(
    '/api/strategies/import',
    { body: request },
  );
}
