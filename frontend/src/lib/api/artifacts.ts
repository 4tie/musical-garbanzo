import { apiGetArray, apiGetRecord } from './client';
import { ArtifactListItem, ArtifactRead, AuditLog } from './types';

interface ListArtifactsParams {
  runId?: string;
  strategyId?: string;
  artifactType?: string;
  limit?: number;
  offset?: number;
}

interface ListAuditLogsParams {
  runId?: string;
  actionType?: string;
  limit?: number;
  offset?: number;
}

export function listArtifacts(params: ListArtifactsParams = {}) {
  return apiGetArray<ArtifactListItem>('/api/artifacts', {
    query: {
      run_id: params.runId,
      strategy_id: params.strategyId,
      artifact_type: params.artifactType,
      limit: params.limit,
      offset: params.offset,
    },
  });
}

export function getArtifact(artifactId: string) {
  return apiGetRecord<ArtifactRead>(`/api/artifacts/${encodeURIComponent(artifactId)}`);
}

export function listRunArtifacts(runId: string) {
  return apiGetArray<ArtifactListItem>(`/api/runs/${encodeURIComponent(runId)}/artifacts`);
}

export function listAuditLogs(params: ListAuditLogsParams = {}) {
  return apiGetArray<AuditLog>('/api/audit-logs', {
    query: {
      run_id: params.runId,
      action_type: params.actionType,
      limit: params.limit,
      offset: params.offset,
    },
  });
}
