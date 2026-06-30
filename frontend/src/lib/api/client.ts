import {
  ApiError,
  ApiResult,
  JsonObject,
  QueryParams,
  QueryValue,
} from './types';
import { invalidResponseError, isEmptyApiData, makeApiError } from './errors';

// When NEXT_PUBLIC_API_BASE_URL is set to empty string ("") the client uses
// relative paths so that Next.js rewrites (next.config.ts) can proxy the
// requests to the backend.  This is required on Replit where the browser
// cannot reach 127.0.0.1:8000 directly.
const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8000';
const DEFAULT_TIMEOUT_MS = 15000;

interface GetOptions {
  query?: QueryParams;
  timeoutMs?: number;
  signal?: AbortSignal;
}

interface PostOptions<TBody> {
  body: TBody;
  timeoutMs?: number;
  signal?: AbortSignal;
}

// If NEXT_PUBLIC_API_BASE_URL is explicitly set (even to empty string), use it.
// Empty string = relative-URL mode: Next.js rewrites (next.config.ts) proxy all
// /api/** and /health calls to the backend at 127.0.0.1:8000.  This is
// required on Replit where the browser cannot reach the backend directly.
// If the var is not defined at all, fall back to the default local URL.
export const API_BASE_URL = (() => {
  const env = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (env !== undefined) return env.replace(/\/+$/, ''); // '' = relative mode
  return DEFAULT_API_BASE_URL;
})();

export async function apiGetRecord<T>(
  path: string,
  options: GetOptions = {},
): Promise<ApiResult<T>> {
  const result = await apiGet<unknown>(path, options);
  if (!result.success) {
    return result;
  }
  if (!isJsonObject(result.data)) {
    return {
      success: false,
      status: result.status,
      empty: false,
      error: invalidResponseError(path, { expected: 'object' }),
    };
  }
  return {
    ...result,
    data: result.data as T,
  };
}

export async function apiGetArray<T>(
  path: string,
  options: GetOptions = {},
): Promise<ApiResult<T[]>> {
  const result = await apiGet<unknown>(path, options);
  if (!result.success) {
    return result;
  }
  if (!Array.isArray(result.data)) {
    return {
      success: false,
      status: result.status,
      empty: false,
      error: invalidResponseError(path, { expected: 'array' }),
    };
  }
  return {
    ...result,
    data: result.data as T[],
  };
}

export async function apiGet<T>(path: string, options: GetOptions = {}): Promise<ApiResult<T>> {
  const endpoint = buildUrl(path, options.query);
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  const clear = () => globalThis.clearTimeout(timeoutId);

  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  try {
    const response = await fetch(endpoint, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      signal: controller.signal,
    });
    clear();

    const parsed = await parseJsonSafely(response);
    if (!response.ok) {
      return {
        success: false,
        status: response.status,
        empty: false,
        error: normalizeHttpError(response.status, path, parsed),
      };
    }

    return {
      success: true,
      data: parsed as T,
      status: response.status,
      empty: isEmptyApiData(parsed),
    };
  } catch (error) {
    clear();
    return {
      success: false,
      empty: false,
      error: normalizeThrownError(path, error),
    };
  }
}

export async function apiPost<TBody, TResponse>(
  path: string,
  options: PostOptions<TBody>,
): Promise<ApiResult<TResponse>> {
  const endpoint = buildUrl(path);
  const timeoutMs = options.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const controller = new AbortController();
  const timeoutId = globalThis.setTimeout(() => controller.abort(), timeoutMs);

  const clear = () => globalThis.clearTimeout(timeoutId);

  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener('abort', () => controller.abort(), { once: true });
    }
  }

  try {
    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(options.body),
      signal: controller.signal,
    });
    clear();

    const parsed = await parseJsonSafely(response);
    if (!response.ok) {
      return {
        success: false,
        status: response.status,
        empty: false,
        error: normalizeHttpError(response.status, path, parsed),
      };
    }

    return {
      success: true,
      data: parsed as TResponse,
      status: response.status,
      empty: isEmptyApiData(parsed),
    };
  } catch (error) {
    clear();
    return {
      success: false,
      empty: false,
      error: normalizeThrownError(path, error),
    };
  }
}

// Dummy absolute base used only when API_BASE_URL is "" (relative mode).
// We build with a full URL so URLSearchParams works, then strip the origin.
const RELATIVE_URL_BASE = 'http://localhost';

function buildUrl(path: string, query?: QueryParams): string {
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  const urlBase = API_BASE_URL || RELATIVE_URL_BASE;
  const url = new URL(`${urlBase}${normalizedPath}`);

  if (query) {
    for (const [key, value] of Object.entries(query)) {
      appendQueryValue(url, key, value);
    }
  }

  // In relative mode, return only path + search so the browser sends the
  // request to its current origin (the Next.js dev server), which then
  // proxies it to the backend via the rewrites in next.config.ts.
  if (!API_BASE_URL) {
    return url.pathname + url.search;
  }

  return url.toString();
}

function appendQueryValue(url: URL, key: string, value: QueryValue): void {
  if (value === undefined || value === null || value === '') {
    return;
  }
  url.searchParams.set(key, String(value));
}

async function parseJsonSafely(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text.trim()) {
    return null;
  }

  try {
    return JSON.parse(text) as unknown;
  } catch {
    if (response.ok) {
      throw makeApiError('invalid_response', 'Backend returned invalid JSON.', {
        status: response.status,
      });
    }
    return { detail: 'Backend returned a non-JSON error response.' };
  }
}

function normalizeHttpError(status: number, endpoint: string, payload: unknown): ApiError {
  const message = extractMessage(payload) ?? `Backend request failed with status ${status}.`;

  if (status === 404) {
    return makeApiError('not_found', message, { status, endpoint, detail: payload });
  }

  if (isStrategyReadinessBlockedPayload(payload)) {
    return makeApiError('strategy_not_ready', message, { status, endpoint, detail: payload });
  }

  if (isControlledFailurePayload(payload) || message.toLowerCase().includes('controlled')) {
    return makeApiError('controlled_failure', message, { status, endpoint, detail: payload });
  }

  return makeApiError('http', message, { status, endpoint, detail: payload });
}

function normalizeThrownError(endpoint: string, error: unknown): ApiError {
  if (isApiError(error)) {
    return { ...error, endpoint };
  }

  if (error instanceof DOMException && error.name === 'AbortError') {
    return makeApiError('timeout', 'Backend request timed out.', { endpoint });
  }

  if (error instanceof TypeError) {
    return makeApiError('network', 'Network error while contacting the HER backend.', { endpoint });
  }

  return makeApiError('network', 'Unexpected error while contacting the HER backend.', { endpoint });
}

function extractMessage(payload: unknown): string | null {
  if (typeof payload === 'string') {
    return payload;
  }

  if (!isJsonObject(payload)) {
    return null;
  }

  const detail = payload.detail;
  if (typeof detail === 'string') {
    return detail;
  }

  if (isJsonObject(detail) && typeof detail.message === 'string') {
    return detail.message;
  }

  if (typeof payload.message === 'string') {
    return payload.message;
  }

  return null;
}

function isControlledFailurePayload(payload: unknown): boolean {
  if (!isJsonObject(payload)) {
    return false;
  }

  const status = payload.status;
  const errorCode = payload.error_code;
  const detail = payload.detail;

  return (
    status === 'failed_controlled' ||
    errorCode === 'failed_controlled' ||
    (isJsonObject(detail) && detail.status === 'failed_controlled')
  );
}

function isStrategyReadinessBlockedPayload(payload: unknown): boolean {
  if (!isJsonObject(payload)) {
    return false;
  }

  const detail = payload.detail;

  // Check if detail is the strategy_not_ready error object
  if (isJsonObject(detail)) {
    return (
      detail.code === 'strategy_not_ready' ||
      (detail.error === true && detail.readiness !== undefined)
    );
  }

  // Check if payload itself has the structure
  return (
    payload.code === 'strategy_not_ready' ||
    (payload.error === true && payload.readiness !== undefined)
  );
}

function isJsonObject(value: unknown): value is JsonObject {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function isApiError(value: unknown): value is ApiError {
  return isJsonObject(value) && typeof value.kind === 'string' && typeof value.message === 'string';
}
