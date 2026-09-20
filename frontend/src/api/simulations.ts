import { fetchApi } from './client';
import type { TriggerSimulationRequest, TriggerSimulationResponse, ApplySimulationResponse } from '../types';

export async function triggerSimulation(request: TriggerSimulationRequest): Promise<TriggerSimulationResponse> {
  return fetchApi<TriggerSimulationResponse>('/api/simulations/what-if', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function applySimulation(simulationId: string): Promise<ApplySimulationResponse> {
  return fetchApi<ApplySimulationResponse>(`/api/simulations/${simulationId}/apply`, {
    method: 'POST',
  });
}

export async function rejectSimulation(simulationId: string): Promise<any> {
  return fetchApi<any>(`/api/simulations/${simulationId}/reject`, {
    method: 'POST',
  });
}
