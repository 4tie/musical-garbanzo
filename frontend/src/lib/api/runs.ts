import { apiGetArray, apiGetRecord } from './client';
import {
  RunListItem,
  RunLog,
  RunRead,
  RunStageRead,
  RetryHistoryItem,
} from './types';

interface ListRunsParams {
  status?: string;
  classification?: string;
  strategyId?: string;
  limit?: number;
  offset?: number;
}

interface ListLogsParams {
  stageKey?: string;
  level?: string;
  limit?: number;
  offset?: number;
}

export function listRuns(params: ListRunsParams = {}) {
  return apiGetArray<RunListItem>('/api/runs', {
    query: {
      status: params.status,
      classification: params.classification,
      strategy_id: params.strategyId,
      limit: params.limit,
      offset: params.offset,
    },
  });
}

export async function listBaselineRuns(params: Omit<ListRunsParams, 'classification'> = {}) {
  const result = await listRuns(params);
  if (!result.success) {
    return result;
  }

  return {
    ...result,
    data: result.data.filter(isBaselineRun),
    empty: result.data.filter(isBaselineRun).length === 0,
  };
}

export function getRun(runId: string) {
  return apiGetRecord<RunRead>(`/api/runs/${encodeURIComponent(runId)}`);
}

export function listRunStages(runId: string) {
  return apiGetArray<RunStageRead>(`/api/runs/${encodeURIComponent(runId)}/stages`);
}

export function getRunStage(runId: string, stageKey: string) {
  return apiGetRecord<RunStageRead>(
    `/api/runs/${encodeURIComponent(runId)}/stages/${encodeURIComponent(stageKey)}`,
  );
}

export function listRunLogs(runId: string, params: ListLogsParams = {}) {
  return apiGetArray<RunLog>(`/api/runs/${encodeURIComponent(runId)}/logs`, {
    query: {
      stage_key: params.stageKey,
      level: params.level,
      limit: params.limit,
      offset: params.offset,
    },
  });
}

export function listRetryHistory(runId: string) {
  return apiGetArray<RetryHistoryItem>(`/api/runs/${encodeURIComponent(runId)}/retry-history`);
}

function isBaselineRun(run: RunListItem): boolean {
  const haystack = `${run.mode} ${run.name} ${run.classification ?? ''}`.toLowerCase();
  return haystack.includes('baseline');
}
