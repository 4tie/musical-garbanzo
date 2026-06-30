import { ApiError, ApiErrorKind, ApiResult } from './types';

export function makeApiError(
  kind: ApiErrorKind,
  message: string,
  options: Partial<Omit<ApiError, 'kind' | 'message'>> = {},
): ApiError {
  return {
    kind,
    message,
    ...options,
  };
}

export function emptyDataError(message = 'No data is available for this view.', endpoint?: string): ApiError {
  return makeApiError('empty_data', message, { endpoint });
}

export function invalidResponseError(endpoint: string, detail?: unknown): ApiError {
  return makeApiError('invalid_response', 'Backend response shape did not match the expected contract.', {
    endpoint,
    detail,
  });
}

export function rejectedStrategyError(message: string, endpoint?: string): ApiError {
  return makeApiError('rejected_strategy', message, { endpoint });
}

export function pipelineRejectedError(message: string, endpoint?: string): ApiError {
  return makeApiError('pipeline_rejected', message, { endpoint });
}

export function isEmptyApiData(value: unknown): boolean {
  if (value == null) {
    return true;
  }
  if (Array.isArray(value)) {
    return value.length === 0;
  }
  if (typeof value === 'object') {
    return Object.keys(value).length === 0;
  }
  return false;
}

export function mapEmptyResult<T>(result: ApiResult<T>, message: string): ApiResult<T> {
  if (!result.success || !result.empty) {
    return result;
  }

  return {
    success: false,
    status: result.status,
    empty: true,
    error: emptyDataError(message),
  };
}
