import { apiGetArray, apiGetRecord } from './client';
import { DecisionPolicySummary, DecisionRecord, JsonObject } from './types';

export function listDecisionPolicies() {
  return apiGetArray<DecisionPolicySummary>('/api/decisions/policies');
}

export function getDecisionPolicy(policyName: string) {
  return apiGetRecord<JsonObject>(`/api/decisions/policies/${encodeURIComponent(policyName)}`);
}

export function listRunDecisions(runId: string) {
  return apiGetArray<DecisionRecord>(`/api/decisions/runs/${encodeURIComponent(runId)}`);
}

export function getLatestRunDecision(runId: string) {
  return apiGetRecord<DecisionRecord>(`/api/decisions/runs/${encodeURIComponent(runId)}/latest`);
}

export function getBacktestDecision(runId: string) {
  return apiGetRecord<DecisionRecord>(
    `/api/results/backtest/${encodeURIComponent(runId)}/decision`,
  );
}

export function getRunDecision(runId: string) {
  return apiGetRecord<DecisionRecord>(`/api/runs/${encodeURIComponent(runId)}/decision`);
}
