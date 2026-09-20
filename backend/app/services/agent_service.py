"""TravelPilot Assistant chat and event application service."""

import json
import os
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv
try:
    from groq import Groq
except ImportError:  # pragma: no cover
    class _MissingGroqClient:
        """Fallback stub for Groq when the library is not installed.
        It raises a clear error only if actually used, allowing the rest of the
        backend (which rarely calls Groq in unit tests) to load without issues.
        """

        def __init__(self, *args, **kwargs):
            raise RuntimeError("Groq library is not installed. Install 'groq' to use Groq-powered chat.")

    Groq = _MissingGroqClient

from backend.app.agent.orchestrator import agent_orchestrator
from backend.app.db.supabase_client import get_db
from backend.app.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentEventItem,
    AgentEventsResponse,
)


# Groq deprecated llama-3.3-70b-versatile for developer-tier accounts.
GROQ_MODEL = "openai/gpt-oss-120b"
AI_PROVIDER_ENV = "AI_PROVIDER"

# The backend may be launched from either the repository root or backend/.
# Load the backend-local environment file before reading GROQ_API_KEY.
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _get_groq_client() -> Groq:
    """Create the client only when chat is used, so startup remains deterministic."""
    api_key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROK_API_KEY / GROQ_API_KEY is not configured.")
    return Groq(api_key=api_key, timeout=30.0)


def _build_trip_system_prompt(trip_context: Dict[str, Any]) -> str:
    """Provide the model with the complete, current trip as trusted context."""
    return (
        "You are TravelPilot Assistant, an expert, friendly travel assistant for the user's "
        "active trip. Answer questions accurately using current trip data below, plus your general "
        "travel knowledge for food, culture, heritage, local specialties, and recommendations.\n\n"
        "ACTIVE TRIP DATA:\n"
        f"{json.dumps(trip_context, default=str, ensure_ascii=False)}"
    )


class AgentService:
    def chat(self, request: AgentChatRequest) -> AgentChatResponse:
        from backend.app.services.trip_service import trip_service

        db = get_db()
        trip = db.get_trip(request.trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{request.trip_id}' does not exist.")

        # The server-side trip state is always the source of truth for the LLM.
        full_trip_detail = trip_service.get_trip_detail(request.trip_id)
        trip_context = full_trip_detail.model_dump(mode="json")

        has_grok_key = bool(os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY"))
        default_provider = "groq" if has_grok_key else "gemini"
        provider = os.getenv(AI_PROVIDER_ENV, default_provider).lower()
        if provider not in {"groq", "grok"}:
            context = agent_orchestrator.plan_trip(
                user_request=request.message,
                trip_id=request.trip_id,
                history=request.history,
                trip_context=trip_context,
            )
            return AgentChatResponse(
                success=True,
                trip_id=request.trip_id,
                reply=context.final_response,
                updated_trip=context.to_dict(),
                executed_tools=context.executed_tools,
            )

        messages = [{"role": "system", "content": _build_trip_system_prompt(trip_context)}]
        for message in request.history:
            role = "assistant" if message.role in {"assistant", "agent", "model"} else "user"
            messages.append({"role": role, "content": message.content})
        messages.append({"role": "user", "content": request.message})

        try:
            client = _get_groq_client()
            model_name = os.getenv("GROK_MODEL") or os.getenv("GROQ_MODEL") or GROQ_MODEL
            completion = client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.2,
            )
            reply = completion.choices[0].message.content if completion.choices else None
            if not reply:
                raise RuntimeError("Groq/Grok returned an empty chat response.")

            return AgentChatResponse(
                success=True,
                trip_id=request.trip_id,
                reply=reply,
                updated_trip=trip_context,
                executed_tools=[],
            )
        except Exception as err:
            import logging
            logging.getLogger(__name__).warning(f"TravelPilot Assistant call failed: {err}")
            return AgentChatResponse(
                success=False,
                trip_id=request.trip_id,
                reply="TravelPilot Assistant is temporarily unavailable. Your itinerary and planning tools are still available.",
                updated_trip=trip_context,
                executed_tools=[],
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
