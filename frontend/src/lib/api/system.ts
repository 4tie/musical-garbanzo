import { apiGetRecord } from './client';
import {
  HealthResponse,
  PublicSettingsResponse,
  SystemStatusResponse,
} from './types';

export function fetchHealth() {
  return apiGetRecord<HealthResponse>('/health');
}

export function fetchSystemStatus() {
  return apiGetRecord<SystemStatusResponse>('/api/system/status');
}

export function fetchPublicSettings() {
  return apiGetRecord<PublicSettingsResponse>('/api/settings/public');
}
