import { fetchApi } from './client';
import type { DestinationListResponse, Destination } from '../types';

export async function getDestinations(query?: string): Promise<Destination[]> {
  const url = query ? `/api/destinations?q=${encodeURIComponent(query)}` : '/api/destinations';
  const res = await fetchApi<DestinationListResponse>(url);
  return res.items;
}

export async function getDestinationCulture(destinationIdOrName: string): Promise<any> {
  return fetchApi<any>(`/api/destinations/${encodeURIComponent(destinationIdOrName)}/culture`);
}

export async function getDestinationDetails(destinationId: string): Promise<any> {
  return fetchApi<any>(`/api/destinations/${encodeURIComponent(destinationId)}`);
}


