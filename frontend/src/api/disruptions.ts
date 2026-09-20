import { fetchApi } from './client';
import type { TriggerDisruptionRequest, TriggerDisruptionResponse, ApplyReplanResponse } from '../types';

export async function triggerDisruption(request: TriggerDisruptionRequest): Promise<TriggerDisruptionResponse> {
  return fetchApi<TriggerDisruptionResponse>('/api/disruptions/trigger', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function applyReplan(replanId: string): Promise<ApplyReplanResponse> {
  return fetchApi<ApplyReplanResponse>(`/api/disruptions/${replanId}/apply`, {
    method: 'POST',
  });
}

export async function rejectReplan(replanId: string): Promise<any> {
  return fetchApi<any>(`/api/disruptions/${replanId}/reject`, {
    method: 'POST',
  });
}
