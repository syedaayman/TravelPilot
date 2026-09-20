"""
TravelPilot Agent Application Service
Connects FastAPI routes to Phase 3's AgentOrchestrator and retrieves structured AgentEvents.
"""

from typing import Dict, Any, List
from backend.app.db.supabase_client import get_db
from backend.app.agent.orchestrator import agent_orchestrator
from backend.app.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentEventItem,
    AgentEventsResponse,
)


class AgentService:
    def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        db = get_db()
        trip = db.get_trip(request.trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{request.trip_id}' does not exist.")

        # Invoke Agent Orchestrator with trip context
        context = agent_orchestrator.plan_trip(request.message, trip_id=request.trip_id)

        return AgentChatResponse(
            success=True,
            trip_id=request.trip_id,
            reply=context.final_response,
            updated_trip=context.to_dict(),
            executed_tools=context.executed_tools,
        )

    def get_events(self, trip_id: str, limit: int = 50) -> AgentEventsResponse:
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        limit = min(max(1, limit), 100) # Enforce bounds [1, 100]
        raw_events = db.get_agent_events_for_trip(trip_id)
        events_slice = raw_events[-limit:] if len(raw_events) > limit else raw_events

        event_items = [
            AgentEventItem(
                id=e.id,
                event_type=e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                tool_name=e.tool_name,
                input_summary=e.input_summary,
                result_summary=e.result_summary,
                status=e.status,
                duration_ms=e.duration_ms,
                created_at=str(e.created_at),
            )
            for e in events_slice
        ]

        return AgentEventsResponse(
            trip_id=trip_id,
            events=event_items,
            count=len(event_items),
        )


agent_service = AgentService()
