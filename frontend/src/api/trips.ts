import { fetchApi } from './client';
import type { TripPlanRequest, TripDetailResponse } from '../types';

export async function planTrip(request: TripPlanRequest): Promise<TripDetailResponse> {
  return fetchApi<TripDetailResponse>('/api/trips/plan', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getTrip(tripId: string): Promise<TripDetailResponse> {
  return fetchApi<TripDetailResponse>(`/api/trips/${tripId}`);
}
