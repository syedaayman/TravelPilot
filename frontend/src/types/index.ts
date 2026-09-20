import type { components } from './api';

export type TripPlanRequest = components['schemas']['TripPlanRequest'];
export type TripDetailResponse = components['schemas']['TripDetailResponse'];
export type DestinationListResponse = components['schemas']['DestinationListResponse'];
export type DestinationDetailResponse = components['schemas']['DestinationDetailResponse'];
export type Destination = components['schemas']['DestinationSummaryResponse'];
export type AgentChatRequest = components['schemas']['AgentChatRequest'];
export type AgentChatResponse = components['schemas']['AgentChatResponse'];
export type AgentEventsResponse = components['schemas']['AgentEventsResponse'];
export type TriggerDisruptionRequest = components['schemas']['TriggerDisruptionRequest'];
export type TriggerDisruptionResponse = components['schemas']['TriggerDisruptionResponse'];
export type ApplyReplanResponse = components['schemas']['ApplyReplanResponse'];
export type TriggerSimulationRequest = components['schemas']['TriggerSimulationRequest'];
export type TriggerSimulationResponse = components['schemas']['TriggerSimulationResponse'];
export type ApplySimulationResponse = components['schemas']['ApplySimulationResponse'];

export type DisruptionAnalysisResult = components['schemas']['DisruptionAnalysisResult'];
export type ProposedReplan = components['schemas']['ProposedReplan'];
export type PlanDiffResult = components['schemas']['PlanDiffResult'];
export type WhatIfType = components['schemas']['WhatIfType'];
export type CoreDisruptionType = components['schemas']['CoreDisruptionType'];
export type AgentEvent = components['schemas']['AgentEventItem'];
export type ItemModification = components['schemas']['ItemModification'];
export type WhatIfSimulationResult = components['schemas']['TriggerSimulationResponse'];
