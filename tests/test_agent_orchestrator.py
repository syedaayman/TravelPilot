"""
Unit Tests for Agent Orchestrator & Tool Calling Loop
Tests all 14 required scenarios using deterministic MockLLMClient to verify
tool chaining, iteration bounds, event logging, validation gates, and destination-agnostic planning.
"""

import pytest
from datetime import date
from backend.app.agent.orchestrator import AgentOrchestrator, MockLLMClient
from backend.app.agent.tools import tool_registry
from backend.app.db.supabase_client import get_db
from backend.app.models.entities import AgentEventType


@pytest.fixture(autouse=True)
def init_db():
    db = get_db()
    db.load_seed_data()
    return db


# 1. Simple Conversational Response (Zero Tool Calls)
def test_orchestrator_simple_conversational_response():
    mock_llm = MockLLMClient([
        {"text": "Hello! I am TravelPilot. How can I assist with your trip planning today?", "tool_calls": []}
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Hello TravelPilot", trip_id="trip-test-1")
    assert context.status == "completed"
    assert "Hello! I am TravelPilot" in context.final_response
    assert context.iterations == 1
    assert len(context.executed_tools) == 0


# 2. One-Tool Execution
def test_orchestrator_one_tool_execution():
    mock_llm = MockLLMClient([
        # Turn 1: LLM calls search_destinations
        {
            "text": None,
            "tool_calls": [{"name": "search_destinations", "args": {"query": "Hyderabad"}}],
        },
        # Turn 2: LLM provides final answer
        {
            "text": "I found Hyderabad! It is ideal for a 3-day cultural and historical trip.",
            "tool_calls": [],
        },
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Tell me about Hyderabad", trip_id="trip-test-2")
    assert context.status == "completed"
    assert "search_destinations" in context.executed_tools
    assert len(context.destinations) >= 1
    assert context.destinations[0]["name"] == "Hyderabad"
    assert context.iterations == 2


# 3. Multi-Tool Chain
def test_orchestrator_multi_tool_chain():
    mock_llm = MockLLMClient([
        # Step 1: Resolve destination
        {
            "text": None,
            "tool_calls": [{"name": "search_destinations", "args": {"query": "Hampi"}}],
        },
        # Step 2: Retrieve attractions and hotels in parallel
        {
            "text": None,
            "tool_calls": [
                {"name": "search_places", "args": {"destination_id": "66c46096-b4bb-5cdf-8ee8-62642b00a456"}},
                {"name": "search_hotels", "args": {"destination_id": "66c46096-b4bb-5cdf-8ee8-62642b00a456", "tier": "budget"}},
            ],
        },
        # Step 3: Finalize
        {
            "text": "Found ruins and budget stays in Hampi.",
            "tool_calls": [],
        },
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Plan Hampi on a budget", trip_id="trip-test-3")
    assert context.status == "completed"
    assert "search_destinations" in context.executed_tools
    assert "search_places" in context.executed_tools
    assert "search_hotels" in context.executed_tools
    assert len(context.hotels) >= 1


# 4. Tool-Result Continuation
def test_orchestrator_tool_result_continuation():
    mock_llm = MockLLMClient([
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Goa"}}]},
        {"text": None, "tool_calls": [{"name": "search_places", "args": {"destination_id": "a3040500-6ee7-5c92-ab8c-a666e9b12555", "category": "beach"}}]},
        {"text": "Palolem beach is recommended for Goa.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Beaches in Goa", trip_id="trip-test-4")
    assert context.status == "completed"
    assert context.iterations == 3


# 5. Maximum Iteration Protection
def test_orchestrator_max_iteration_protection():
    # Loop that continuously requests tools forever
    infinite_tool_calls = [
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Bengaluru"}}]}
        for _ in range(20)
    ]
    mock_llm = MockLLMClient(infinite_tool_calls)
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry, max_iterations=4)

    context = orchestrator.plan_trip("Looping request", trip_id="trip-test-5")
    assert context.status == "iteration_limit_reached"
    assert context.iterations == 4
    assert "maximum tool execution limit" in context.final_response.lower()


# 6. Tool Failure Recovery
def test_orchestrator_tool_failure_recovery():
    mock_llm = MockLLMClient([
        # Step 1: Call invalid place id -> tool will return structured error
        {"text": None, "tool_calls": [{"name": "get_place_details", "args": {"place_id": "non-existent-id"}}]},
        # Step 2: Agent recovers and falls back to searching destinations
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Jaipur"}}]},
        # Step 3: Finalize
        {"text": "Recovered and found Jaipur.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Trip with error recovery", trip_id="trip-test-6")
    assert context.status == "completed"
    assert "get_place_details" in context.executed_tools
    assert "search_destinations" in context.executed_tools
    assert "Jaipur" in context.final_response


# 7. Malformed Tool Arguments Handling
def test_orchestrator_malformed_tool_args():
    mock_llm = MockLLMClient([
        # Call tool with missing or wrong types
        {"text": None, "tool_calls": [{"name": "calculate_travel_time", "args": {"origin_lat": "invalid_number"}}]},
        {"text": "Handled malformed input gracefully.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Malformed call", trip_id="trip-test-7")
    assert context.status == "completed"


# 8. Structured Agent Events Logging
def test_orchestrator_structured_agent_events():
    db = get_db()
    trip_id = "trip-event-audit-01"

    mock_llm = MockLLMClient([
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Varanasi"}}]},
        {"text": "Varanasi plan ready.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)
    orchestrator.plan_trip("Varanasi 2 days", trip_id=trip_id)

    events = db.get_agent_events_for_trip(trip_id)
    event_types = [e.event_type for e in events]

    assert AgentEventType.REQUEST_RECEIVED in event_types
    assert AgentEventType.PLANNING_STARTED in event_types
    assert AgentEventType.TOOL_CALL in event_types
    assert AgentEventType.TOOL_RESULT in event_types
    assert AgentEventType.DECISION in event_types


# 9. No Hidden Chain-of-Thought Logging
def test_orchestrator_no_hidden_chain_of_thought_logged():
    db = get_db()
    trip_id = "trip-cot-check-01"

    mock_llm = MockLLMClient([
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Munnar"}}]},
        {"text": "Munnar tea hills itinerary created.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)
    orchestrator.plan_trip("Munnar hills trip", trip_id=trip_id)

    events = db.get_agent_events_for_trip(trip_id)
    for ev in events:
        # Check that event payload only has structured audit summaries
        assert "chain_of_thought" not in ev.metadata
        assert "private_reasoning" not in ev.metadata


# 10. Single-City Planning Flow
def test_orchestrator_single_city_planning_flow():
    mock_llm = MockLLMClient([
        # 1. Resolve Hyderabad
        {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": "Hyderabad"}}]},
        # 2. Search places & budget hotel
        {"text": None, "tool_calls": [
            {"name": "search_places", "args": {"destination_id": "99852cd9-2775-52f3-8fe0-0a26c43a6c09"}},
            {"name": "search_hotels", "args": {"destination_id": "99852cd9-2775-52f3-8fe0-0a26c43a6c09", "tier": "mid-range"}},
        ]},
        # 3. Calculate budget
        {"text": None, "tool_calls": [{
            "name": "calculate_budget",
            "args": {
                "total_budget": 25000.0,
                "traveler_count": 1,
                "stops": [{"id": "s1", "trip_id": "t1", "destination_id": "99852cd9-2775-52f3-8fe0-0a26c43a6c09", "order_index": 0, "arrival_date": "2026-10-01", "departure_date": "2026-10-06"}],
            }
        }]},
        # 4. Validate
        {"text": None, "tool_calls": [{
            "name": "validate_itinerary",
            "args": {"items": [{"id": "i1", "trip_stop_id": "s1", "day_number": 1, "scheduled_date": "2026-10-01", "start_time": "10:00", "end_time": "12:30"}]}
        }]},
        # 5. Finalize
        {"text": "Your 6-day Hyderabad itinerary is complete and within budget!", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Plan 6 days in Hyderabad for ₹25,000", trip_id="trip-sc-01")
    assert context.status == "completed"
    assert context.budget_result is not None
    assert context.budget_result["within_budget"] is True
    assert context.validation_result is not None
    assert context.validation_result["valid"] is True


# 11. Multi-City Planning Flow
def test_orchestrator_multi_city_planning_flow():
    mock_llm = MockLLMClient([
        # 1. Resolve all destinations
        {"text": None, "tool_calls": [
            {"name": "search_destinations", "args": {"query": "Hyderabad"}},
            {"name": "search_destinations", "args": {"query": "Hampi"}},
            {"name": "search_destinations", "args": {"query": "Goa"}},
        ]},
        # 2. Search inter-city transport
        {"text": None, "tool_calls": [
            {"name": "search_transport", "args": {"origin_destination_id": "99852cd9-2775-52f3-8fe0-0a26c43a6c09", "dest_destination_id": "66c46096-b4bb-5cdf-8ee8-62642b00a456"}},
            {"name": "search_transport", "args": {"origin_destination_id": "66c46096-b4bb-5cdf-8ee8-62642b00a456", "dest_destination_id": "a3040500-6ee7-5c92-ab8c-a666e9b12555"}},
        ]},
        # 3. Calculate budget
        {"text": None, "tool_calls": [{
            "name": "calculate_budget",
            "args": {"total_budget": 40000.0, "traveler_count": 1}
        }]},
        # 4. Validate
        {"text": None, "tool_calls": [{
            "name": "validate_itinerary",
            "args": {"items": []}
        }]},
        # 5. Final response
        {"text": "Complete multi-city 8-day trip Hyderabad -> Hampi -> Goa planned!", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Plan 8 days Hyderabad -> Hampi -> Goa for ₹40,000", trip_id="trip-mc-01")
    assert context.status == "completed"
    assert len(context.transport_legs) >= 2


# 12. Validation-Before-Finalization Behavior
def test_orchestrator_validation_before_finalization():
    mock_llm = MockLLMClient([
        {"text": None, "tool_calls": [{"name": "validate_itinerary", "args": {"items": []}}]},
        {"text": "Validated successfully.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Verify itinerary", trip_id="trip-val-01")
    assert "validate_itinerary" in context.executed_tools
    assert context.validation_result["valid"] is True


# 13. Budget-Before-Finalization Behavior
def test_orchestrator_budget_before_finalization():
    mock_llm = MockLLMClient([
        {"text": None, "tool_calls": [{"name": "calculate_budget", "args": {"total_budget": 30000.0}}]},
        {"text": "Budget computed.", "tool_calls": []},
    ])
    orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)

    context = orchestrator.plan_trip("Calculate budget for trip", trip_id="trip-bud-01")
    assert "calculate_budget" in context.executed_tools
    assert context.budget_result["budget"] == 30000.0


# 14. Destination-Agnostic Behavior (Works for Delhi, Jaipur, Munnar, etc.)
def test_orchestrator_destination_agnostic_behavior():
    for city in ["Delhi", "Jaipur", "Munnar", "Varanasi"]:
        mock_llm = MockLLMClient([
            {"text": None, "tool_calls": [{"name": "search_destinations", "args": {"query": city}}]},
            {"text": f"Found destination {city} successfully.", "tool_calls": []},
        ])
        orchestrator = AgentOrchestrator(llm_client=mock_llm, registry=tool_registry)
        ctx = orchestrator.plan_trip(f"Plan trip to {city}", trip_id=f"trip-{city.lower()}")
        assert ctx.status == "completed"
        assert len(ctx.destinations) >= 1
        assert ctx.destinations[0]["name"] == city
