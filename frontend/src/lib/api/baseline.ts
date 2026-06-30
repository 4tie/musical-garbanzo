import { apiGetRecord, apiPost } from './client';
import { listBaselineRuns } from './runs';
import {
  BaselineEvaluationRequest,
  BaselineEvaluationResult,
  BaselineReport,
  BaselineRunDetail,
  BaselineStatusResponse,
} from './types';

export { listBaselineRuns };

export function getBaselineRunDetail(runId: string) {
  return apiGetRecord<BaselineRunDetail>(`/api/baseline/runs/${encodeURIComponent(runId)}`);
}

export function getBaselineStatus(runId: string) {
  return apiGetRecord<BaselineStatusResponse>(
    `/api/baseline/runs/${encodeURIComponent(runId)}/status`,
  );
}

export function getBaselineReport(runId: string) {
  return apiGetRecord<BaselineReport>(`/api/baseline/runs/${encodeURIComponent(runId)}/report`);
}

export function startBaselineEvaluation(request: BaselineEvaluationRequest) {
  return apiPost<BaselineEvaluationRequest, BaselineEvaluationResult>(
    '/api/baseline/evaluate',
    { body: request },
  );
}
