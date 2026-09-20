"""
Phase 5 Tests: Agent API
Validates the agent chat endpoint and structured event retrieval, ensuring no internal
chain-of-thought is exposed, using a deterministic MockLLMClient.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.agent.orchestrator import agent_orchestrator, MockLLMClient


@pytest.fixture
def client():
    return TestClient(app)


def test_agent_chat_simple(client: TestClient):
    # Setup mock LLM for this test
    agent_orchestrator.llm_client = MockLLMClient([
        {
            "text": "Hello! I am TravelPilot. How can I help you?",
            "tool_calls": []
        }
    ])
    
    # Need a trip first
    payload = {
        "destinations": ["Hyderabad"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Chat
    chat_payload = {
        "trip_id": trip_id,
        "message": "Hello!"
    }
    response = client.post("/api/agent/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert data["trip_id"] == trip_id
    assert "Hello! I am TravelPilot" in data["reply"]
    assert len(data["executed_tools"]) == 0
    
    # Ensure no internal thoughts leaked
    assert "chain-of-thought" not in str(data).lower()
    assert "thought:" not in str(data).lower()


def test_agent_chat_with_tools(client: TestClient):
    agent_orchestrator.llm_client = MockLLMClient([
        {
            "text": None,
            "tool_calls": [{"name": "search_destinations", "args": {"query": "Goa"}}]
        },
        {
            "text": "I found Goa in the database.",
            "tool_calls": []
        }
    ])
    
    # Need a trip first
    payload = {
        "destinations": ["Goa"],
        "duration_days": 3,
        "budget": 20000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    chat_payload = {
        "trip_id": trip_id,
        "message": "Tell me about Goa."
    }
    response = client.post("/api/agent/chat", json=chat_payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["success"] is True
    assert "I found Goa" in data["reply"]
    assert "search_destinations" in data["executed_tools"]


def test_agent_events_retrieval(client: TestClient):
    # Assume the previous test created some events for the trip
    payload = {
        "destinations": ["Jaipur"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Get events
    response = client.get(f"/api/agent/events/{trip_id}?limit=2")
    assert response.status_code == 200
    data = response.json()
    
    assert data["trip_id"] == trip_id
    assert "events" in data
    assert data["count"] <= 2
    assert len(data["events"]) <= 2
    
    if len(data["events"]) > 0:
        event = data["events"][0]
        assert "event_type" in event
        assert "chain_of_thought" not in event  # Ensure no CoT exposed
