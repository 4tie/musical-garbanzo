import { apiGetArray, apiGetRecord, apiPost } from './client';
import {
  AvailablePairsResponse,
  OptimizationComparison,
  OptimizationReport,
  OptimizationRequest,
  OptimizationRunDetail,
  OptimizationRunListItem,
  OptimizationStartResponse,
  OptimizationStatusResponse,
  OptimizationTrial,
  OptimizationTrialDetail,
  SupportedExchange,
} from './types';

interface ListOptimizationRunsParams {
  limit?: number;
  offset?: number;
  status?: string;
}

interface ListTrialsParams {
  limit?: number;
  offset?: number;
  status?: string;
}

export function listOptimizationRuns(params: ListOptimizationRunsParams = {}) {
  return apiGetArray<OptimizationRunListItem>('/api/optimization/runs', {
    query: {
      limit: params.limit,
      offset: params.offset,
      status: params.status,
    },
  });
}

export function getOptimizationRunDetail(optimizationRunId: string) {
  return apiGetRecord<OptimizationRunDetail>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}`,
  );
}

export function getOptimizationStatus(optimizationRunId: string) {
  return apiGetRecord<OptimizationStatusResponse>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/status`,
  );
}

export async function listOptimizationTrials(
  optimizationRunId: string,
  params: ListTrialsParams = {},
) {
  const result = await apiGetArray<OptimizationTrial>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/trials`,
    {
      query: {
        limit: params.limit,
        offset: params.offset,
        status: params.status,
      },
    },
  );

  if (!result.success || !params.status) {
    return result;
  }

  const filtered = result.data.filter((trial) => trial.status === params.status);
  return {
    ...result,
    data: filtered,
    empty: filtered.length === 0,
  };
}

export function getOptimizationTrialDetail(optimizationRunId: string, trialId: string) {
  return apiGetRecord<OptimizationTrialDetail>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/trials/${encodeURIComponent(trialId)}`,
  );
}

export function getBestTrial(optimizationRunId: string) {
  return apiGetRecord<OptimizationTrial>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/best-trial`,
  );
}

export function getOptimizationComparison(optimizationRunId: string) {
  return apiGetRecord<OptimizationComparison>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/comparison`,
  );
}

export function getOptimizationReport(optimizationRunId: string) {
  return apiGetRecord<OptimizationReport>(
    `/api/optimization/runs/${encodeURIComponent(optimizationRunId)}/report`,
  );
}

export function startOptimization(request: OptimizationRequest) {
  return apiPost<OptimizationRequest, OptimizationStartResponse>(
    '/api/optimization/run',
    { body: request },
  );
}

export function listSupportedExchanges() {
  return apiGetRecord<{ exchanges: SupportedExchange[] }>('/api/optimization/exchanges');
}

export function getAvailablePairs(exchange: string, quote: string, limit: number = 100) {
  return apiGetRecord<AvailablePairsResponse>('/api/optimization/available-pairs', {
    query: { exchange, quote, limit },
  });
}
