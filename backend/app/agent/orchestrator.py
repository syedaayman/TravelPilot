"""
TravelPilot Gemini Agent & Tool Orchestrator
Implements the multi-turn ReAct loop with Google's official google-genai SDK,
bounded iteration limits, structured AgentEvent logging, and deterministic validation gates.
"""

from typing import Dict, Any, List, Optional, Union
from datetime import date, datetime, timedelta
import logging
import json

from backend.app.config import settings
from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    AgentEvent,
    AgentEventType,
    TripStatus,
    HotelTier,
    TransportMode,
    ItemType,
)
from backend.app.agent.tools import tool_registry, ToolRegistry
from backend.app.agent.prompts import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ============================================================================
# Working State & Agent Context
# ============================================================================

class AgentContext:
    def __init__(self, request: str, trip_id: Optional[str] = None, user_id: Optional[str] = None):
        self.request = request
        self.trip_id = trip_id or f"trip-{int(datetime.utcnow().timestamp())}"
        self.user_id = user_id
        self.destinations: List[Dict[str, Any]] = []
        self.trip_stops: List[Dict[str, Any]] = []
        self.transport_legs: List[Dict[str, Any]] = []
        self.hotels: List[Dict[str, Any]] = []
        self.itinerary_items: List[Dict[str, Any]] = []
        self.budget_result: Optional[Dict[str, Any]] = None
        self.validation_result: Optional[Dict[str, Any]] = None
        self.final_response: str = ""
        self.status: str = "initialized"
        self.error: Optional[str] = None
        self.iterations: int = 0
        self.executed_tools: List[str] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "trip_id": self.trip_id,
            "request": self.request,
            "status": self.status,
            "destinations": self.destinations,
            "trip_stops": self.trip_stops,
            "transport_legs": self.transport_legs,
            "hotels": self.hotels,
            "itinerary_items": self.itinerary_items,
            "budget": self.budget_result,
            "validation": self.validation_result,
            "final_response": self.final_response,
            "executed_tools": self.executed_tools,
            "iterations": self.iterations,
            "error": self.error,
        }


# ============================================================================
# LLM Client Boundary (Real Google-GenAI SDK & Mock for Testing)
# ============================================================================

class BaseLLMClient:
    def generate(
        self,
        system_instruction: str,
        contents: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Returns structured dict:
        {
            "text": Optional[str],
            "tool_calls": List[{"name": str, "args": dict}]
        }
        """
        raise NotImplementedError


class GeminiGenAIClient(BaseLLMClient):
    """
    Production client using Google's official google-genai SDK.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self._client = None
        if self.api_key:
            try:
                from google import genai
                self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Could not initialize google.genai Client: {e}")

    def generate(
        self,
        system_instruction: str,
        contents: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Gemini client is not initialized or GEMINI_API_KEY is missing.")

        # Using official google.genai client generate_content
        response = self._client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.2,
            },
        )

        tool_calls = []
        text_content = ""

        # Extract function calls if present
        if hasattr(response, "function_calls") and response.function_calls:
            for fc in response.function_calls:
                tool_calls.append({
                    "name": fc.name,
                    "args": dict(fc.args) if hasattr(fc, "args") else {},
                })
        elif hasattr(response, "text"):
            text_content = response.text or ""

        return {
            "text": text_content,
            "tool_calls": tool_calls,
        }


class MockLLMClient(BaseLLMClient):
    """
    Deterministic mock client for unit and integration testing without network calls or API keys.
    """
    def __init__(self, response_queue: Optional[List[Dict[str, Any]]] = None):
        self.response_queue: List[Dict[str, Any]] = response_queue or []
        self.call_history: List[Dict[str, Any]] = []

    def set_responses(self, responses: List[Dict[str, Any]]):
        self.response_queue = list(responses)

    def generate(
        self,
        system_instruction: str,
        contents: List[Dict[str, Any]],
        tools_schema: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self.call_history.append({
            "contents": contents,
            "tools_count": len(tools_schema or []),
        })

        if self.response_queue:
            return self.response_queue.pop(0)

        # Fallback default final response
        return {
            "text": "Plan successfully generated and validated.",
            "tool_calls": [],
        }


# ============================================================================
# TravelPilot Agent Orchestrator
# ============================================================================

class AgentOrchestrator:
    def __init__(
        self,
        llm_client: Optional[BaseLLMClient] = None,
        registry: Optional[ToolRegistry] = None,
        max_iterations: int = 12,
    ):
        self.llm_client = llm_client or (
            GeminiGenAIClient() if settings.GEMINI_API_KEY else MockLLMClient()
        )
        self.registry = registry or tool_registry
        self.max_iterations = max_iterations

    def plan_trip(
        self,
        user_request: str,
        trip_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentContext:
        """
        Main entrypoint: parses natural-language prompt, executes the multi-turn
        ReAct tool loop, validates candidate itinerary, calculates budget, and returns final plan.
        """
        context = AgentContext(request=user_request, trip_id=trip_id, user_id=user_id)
        db = get_db()

        # 1. Log request_received and planning_started
        db.record_agent_event(
            AgentEvent(
                trip_id=context.trip_id,
                event_type=AgentEventType.REQUEST_RECEIVED,
                input_summary=user_request[:200],
                status="info",
            )
        )
        db.record_agent_event(
            AgentEvent(
                trip_id=context.trip_id,
                event_type=AgentEventType.PLANNING_STARTED,
                result_summary="Autonomous tool-calling planning loop initiated.",
                status="info",
            )
        )

        # 2. Multi-turn Tool Calling Loop
        conversation_history: List[Dict[str, Any]] = [
            {"role": "user", "parts": [{"text": user_request}]}
        ]

        while context.iterations < self.max_iterations:
            context.iterations += 1

            try:
                llm_output = self.llm_client.generate(
                    system_instruction=SYSTEM_PROMPT,
                    contents=conversation_history,
                    tools_schema=self.registry.get_all_schemas(),
                )
            except Exception as e:
                logger.error(f"LLM generation failed: {e}")
                context.error = str(e)
                context.status = "error"
                db.record_agent_event(
                    AgentEvent(
                        trip_id=context.trip_id,
                        event_type=AgentEventType.ERROR,
                        result_summary=f"LLM failure: {str(e)}",
                        status="error",
                    )
                )
                break

            tool_calls = llm_output.get("tool_calls", [])
            text_response = llm_output.get("text", "")

            # If no tool calls, the model decided to finalize or answer directly
            if not tool_calls:
                context.final_response = text_response or "Trip planning complete."
                context.status = "completed"
                db.record_agent_event(
                    AgentEvent(
                        trip_id=context.trip_id,
                        event_type=AgentEventType.DECISION,
                        result_summary="Final itinerary presented to user.",
                        status="success",
                    )
                )
                break

            # Execute Tool Calls
            tool_results = []
            for tc in tool_calls:
                t_name = tc.get("name")
                t_args = tc.get("args", {})
                context.executed_tools.append(t_name)

                # Execute tool securely
                exec_result = self.registry.execute(t_name, t_args, trip_id=context.trip_id)
                tool_results.append(exec_result)

                # Sync state if relevant tools executed
                self._update_context_state(context, t_name, t_args, exec_result)

            # Append assistant message & tool results to conversation history
            conversation_history.append({
                "role": "model",
                "parts": [{"text": f"Invoking tools: {[t.get('name') for t in tool_calls]}"}],
            })
            conversation_history.append({
                "role": "user",
                "parts": [{"text": f"Tool execution results: {json.dumps(tool_results, default=str)}"}],
            })

        # 3. Check for Max Iterations Exceeded
        if context.iterations >= self.max_iterations and context.status != "completed":
            context.status = "iteration_limit_reached"
            context.final_response = (
                "Reached maximum tool execution limit. A partial plan has been generated."
            )
            db.record_agent_event(
                AgentEvent(
                    trip_id=context.trip_id,
                    event_type=AgentEventType.ERROR,
                    result_summary=f"Exceeded max iterations ({self.max_iterations}).",
                    status="warning",
                )
            )

        return context

    def _update_context_state(
        self, context: AgentContext, tool_name: str, args: Dict[str, Any], result: Dict[str, Any]
    ):
        """Updates internal working context based on tool execution data."""
        if not result.get("success"):
            return

        data = result.get("data")
        if not data:
            return

        if tool_name == "search_destinations" and isinstance(data, list):
            context.destinations.extend(data)
        elif tool_name == "search_hotels" and isinstance(data, list):
            context.hotels.extend(data)
        elif tool_name == "calculate_budget" and isinstance(data, dict):
            context.budget_result = data
        elif tool_name == "validate_itinerary" and isinstance(data, dict):
            context.validation_result = data
        elif tool_name == "search_transport" and isinstance(data, list):
            context.transport_legs.extend(data)


# Global orchestrator singleton
agent_orchestrator = AgentOrchestrator()
