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

export async function updateHotel(tripId: string, hotelId: string, stopId?: string): Promise<TripDetailResponse> {
  return fetchApi<TripDetailResponse>(`/api/trips/${tripId}/hotel`, {
    method: 'POST',
    body: JSON.stringify({ hotel_id: hotelId, stop_id: stopId }),
  });
}

export async function validateActivity(tripId: string, req: any): Promise<any> {
  return fetchApi<any>(`/api/trips/${tripId}/activity/validate`, {
    method: 'POST',
    body: JSON.stringify(req),
  });
}
