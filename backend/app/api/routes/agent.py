"""
Agent API Routes
"""

from fastapi import APIRouter, HTTPException, Query, status

from backend.app.services.agent_service import agent_service
from backend.app.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentEventsResponse,
)

router = APIRouter(prefix="/agent", tags=["Agent"])


@router.post(
    "/chat",
    response_model=AgentChatResponse,
    summary="Agent interactive chat & modification",
    description="Context-aware conversational interface powered by Groq using the active trip state.",
)
def chat_with_agent(request: AgentChatRequest):
    try:
        return agent_service.chat(request)
    except KeyError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent interaction error: {str(e)}",
        )


@router.get(
    "/events/{trip_id}",
    response_model=AgentEventsResponse,
    summary="Get structured agent events",
    description="Retrieve structured execution audit trail for a trip. Excludes internal chain-of-thought.",
)
def get_agent_events(
    trip_id: str,
    limit: int = Query(default=50, ge=1, le=100, description="Max number of events to retrieve (1-100)"),
):
    try:
        return agent_service.get_events(trip_id=trip_id, limit=limit)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve events: {str(e)}",
        )
