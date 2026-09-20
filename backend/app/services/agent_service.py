"""TravelPilot Assistant chat and event application service."""

import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, List

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

try:
    from groq import Groq
    _MissingGroqClient = None
    _MissingGrokClient = None
except ImportError:  # pragma: no cover
    class _MissingGroqClient:
        """Fallback stub for Groq when the library is not installed."""
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Groq/Grok library is not installed. Install 'groq' to use Groq/Grok-powered chat.")

    Groq = _MissingGroqClient
    _MissingGrokClient = _MissingGroqClient

from backend.app.agent.orchestrator import agent_orchestrator
from backend.app.db.supabase_client import get_db
from backend.app.api.schemas.agent import (
    AgentChatRequest,
    AgentChatResponse,
    AgentEventItem,
    AgentEventsResponse,
)

GROQ_MODEL = "openai/gpt-oss-120b"
AI_PROVIDER_ENV = "AI_PROVIDER"

# Load the backend-local environment file
load_dotenv(Path(__file__).resolve().parents[2] / ".env")


def _get_groq_client() -> Groq:
    """Create the client only when chat is used, so startup remains deterministic."""
    api_key = os.getenv("GROK_API_KEY") or os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROK_API_KEY / GROQ_API_KEY is not configured.")
    return Groq(api_key=api_key, timeout=30.0)


def _compute_trip_schedule_gaps(trip_context: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Compute available free gaps between scheduled items for each day."""
    gaps_by_day = []
    itinerary = trip_context.get("itinerary", [])
    stops = trip_context.get("stops", [])

    days_map: Dict[int, List[Dict[str, Any]]] = {}
    for item in itinerary:
        d_num = item.get("day_number", 1)
        days_map.setdefault(d_num, []).append(item)

    for d_num in sorted(days_map.keys()):
        items = sorted(days_map[d_num], key=lambda x: x.get("start_time", ""))
        day_gaps = []
        for i in range(len(items) - 1):
            curr_end = items[i].get("end_time", "")
            next_start = items[i + 1].get("start_time", "")
            if curr_end and next_start:
                try:
                    cH, cM = map(int, curr_end.split(":"))
                    nH, nM = map(int, next_start.split(":"))
                    gap_min = (nH * 60 + nM) - (cH * 60 + cM)
                    if gap_min >= 30:
                        hrs = gap_min // 60
                        mins = gap_min % 60
                        dur_str = f"{hrs}h {mins}m" if hrs > 0 else f"{mins}m"
                        day_gaps.append({
                            "window": f"{curr_end} - {next_start}",
                            "duration_minutes": gap_min,
                            "formatted_duration": dur_str,
                            "after_item": items[i].get("custom_title") or items[i].get("category"),
                            "before_item": items[i + 1].get("custom_title") or items[i + 1].get("category"),
                        })
                except Exception:
                    pass

        gaps_by_day.append({
            "day_number": d_num,
            "free_gaps": day_gaps,
            "item_count": len(items)
        })
    return gaps_by_day


def _build_trip_system_prompt(trip_context: Dict[str, Any]) -> str:
    """Provide the model with complete, trusted context including computed schedule gaps."""
    schedule_gaps = _compute_trip_schedule_gaps(trip_context)

    return (
        "You are TravelPilot Assistant, an expert, friendly travel assistant for the user's active trip.\n"
        "Your goal is to answer questions accurately based on the current trip context provided below.\n\n"
        "INSTRUCTIONS FOR SCHEDULING / FIT QUESTIONS:\n"
        "- When the user asks 'Can I fit one more activity this afternoon?' or similar schedule questions:\n"
        "  1. Look at the free gaps for the current/relevant day below.\n"
        "  2. State the EXACT available time window and duration (e.g., 'You have approximately 1h 55m available between 17:35 and 19:30 before dinner').\n"
        "  3. Suggest 2-3 specific, relevant local cultural/food/craft activities or sights for that destination that fit comfortably within that window.\n\n"
        f"COMPUTED DAILY FREE TIME GAPS:\n{json.dumps(schedule_gaps, indent=2, ensure_ascii=False)}\n\n"
        f"COMPLETE ACTIVE TRIP DETAILS:\n{json.dumps(trip_context, default=str, ensure_ascii=False)}"
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
        default_provider = "groq" if (Groq is not None and Groq is not _MissingGroqClient and has_grok_key) else "gemini"
        provider = os.getenv(AI_PROVIDER_ENV, default_provider).lower()

        if provider in {"groq", "grok"}:
            try:
                client = _get_groq_client()
            except RuntimeError as exc:
                logger.warning(f"Groq client initialization failed: {exc}. Falling back to Gemini.")
                provider = "gemini"

        if provider not in {"groq", "grok"}:
            try:
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
            except Exception as err:
                logger.warning(f"Gemini orchestrator call failed: {err}")
                return AgentChatResponse(
                    success=False,
                    trip_id=request.trip_id,
                    reply=f"TravelPilot Assistant error: {str(err)}",
                    updated_trip=trip_context,
                    executed_tools=[],
                )

        messages = [{"role": "system", "content": _build_trip_system_prompt(trip_context)}]
        for message in request.history:
            role = "assistant" if message.role in {"assistant", "agent", "model"} else "user"
            messages.append({"role": role, "content": message.content})
        messages.append({"role": "user", "content": request.message})

        try:
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
            logger.warning(f"TravelPilot Assistant call failed: {err}")
            return AgentChatResponse(
                success=False,
                trip_id=request.trip_id,
                reply=f"TravelPilot Assistant error: {str(err)}",
                updated_trip=trip_context,
                executed_tools=[],
            )

    def get_events(self, trip_id: str, limit: int = 50) -> AgentEventsResponse:
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        limit = min(max(1, limit), 100)
        raw_events = db.get_agent_events_for_trip(trip_id)
        events_slice = raw_events[-limit:] if len(raw_events) > limit else raw_events

        event_items = [
            AgentEventItem(
                id=e.id,
                event_type=e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                tool_name=e.tool_name,
                input_summary=e.input_summary,
                output_summary=e.output_summary,
                timestamp=e.timestamp,
                status=e.status,
            )
            for e in events_slice
        ]

        return AgentEventsResponse(
            success=True,
            trip_id=trip_id,
            events=event_items,
            count=len(event_items),
        )


agent_service = AgentService()
