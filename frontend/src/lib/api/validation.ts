import { apiGetRecord, apiGetArray, apiPost } from './client';
import type {
  ValidationRunRequest,
  ValidationRunResponse,
  ValidationRunListItem,
  ValidationRunDetail,
  ValidationStatusResponse,
  ValidationEvidenceResponse,
  ValidationReportResponse,
  QueryParams,
  ApiResult,
} from './types';

const VALIDATION_BASE = '/api/validation';

export async function startValidation(
  request: ValidationRunRequest
): Promise<ApiResult<ValidationRunResponse>> {
  const result = await apiPost(`${VALIDATION_BASE}/run`, { body: request });
  if (!result.success) {
    return result;
  }
  return {
    ...result,
    data: result.data as ValidationRunResponse,
  };
}

export async function listValidationRuns(
  params?: QueryParams
): Promise<ApiResult<ValidationRunListItem[]>> {
  return apiGetArray<ValidationRunListItem>(`${VALIDATION_BASE}/runs`, { query: params });
}

export async function getValidationRun(
  validationRunId: string
): Promise<ApiResult<ValidationRunDetail>> {
  return apiGetRecord<ValidationRunDetail>(`${VALIDATION_BASE}/runs/${validationRunId}`);
}

export async function getValidationStatus(
  validationRunId: string
): Promise<ApiResult<ValidationStatusResponse>> {
  return apiGetRecord<ValidationStatusResponse>(
    `${VALIDATION_BASE}/runs/${validationRunId}/status`
  );
}

export async function getValidationEvidence(
  validationRunId: string
): Promise<ApiResult<ValidationEvidenceResponse>> {
  return apiGetRecord<ValidationEvidenceResponse>(
    `${VALIDATION_BASE}/runs/${validationRunId}/evidence`
  );
}

export async function getValidationReport(
  validationRunId: string
): Promise<ApiResult<ValidationReportResponse>> {
  return apiGetRecord<ValidationReportResponse>(
    `${VALIDATION_BASE}/runs/${validationRunId}/report`
  );
}
