import { fetchApi } from './client';
import type { AgentChatRequest, AgentChatResponse, AgentEventsResponse } from '../types';

export async function chatWithAgent(request: AgentChatRequest): Promise<AgentChatResponse> {
  return fetchApi<AgentChatResponse>('/api/agent/chat', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

export async function getAgentEvents(tripId: string, limit: number = 50): Promise<AgentEventsResponse> {
  return fetchApi<AgentEventsResponse>(`/api/agent/events/${tripId}?limit=${limit}`);
}
