"""
Phase 5 Tests: E2E API Integration
Validates end-to-end flows spanning across Trips, Disruptions, and Agent endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.agent.orchestrator import agent_orchestrator, MockLLMClient


@pytest.fixture
def client():
    return TestClient(app)


def test_e2e_trip_disruption_agent_flow(client: TestClient):
    # Setup MockLLM for the agent chat step
    agent_orchestrator.llm_client = MockLLMClient([
        {
            "text": "I see you have applied the budget reduction. Your new budget is 20,000.",
            "tool_calls": []
        }
    ])

    # 1. Plan Trip
    payload = {
        "destinations": ["Hyderabad"],
        "duration_days": 4,
        "budget": 25000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    assert trip_res.status_code == 201
    trip_id = trip_res.json()["id"]

    # 2. Trigger Disruption
    disrupt_req = {
        "trip_id": trip_id,
        "type": "BUDGET_REDUCTION",
        "reduction_amount": 5000.0
    }
    trigger_res = client.post("/api/disruptions/trigger", json=disrupt_req)
    assert trigger_res.status_code == 200
    replan_id = trigger_res.json()["replan_id"]

    # 3. Apply Replan
    apply_res = client.post(f"/api/disruptions/{replan_id}/apply")
    assert apply_res.status_code == 200

    # 4. Verify Trip State Changed
    get_trip_res = client.get(f"/api/trips/{trip_id}")
    assert get_trip_res.status_code == 200
    assert get_trip_res.json()["total_budget"] == 20000.0

    # 5. Chat with Agent
    chat_payload = {
        "trip_id": trip_id,
        "message": "What is my new budget?"
    }
    chat_res = client.post("/api/agent/chat", json=chat_payload)
    assert chat_res.status_code == 200
    assert "20,000" in chat_res.json()["reply"]

    # 6. Retrieve Agent Events
    events_res = client.get(f"/api/agent/events/{trip_id}")
    assert events_res.status_code == 200
    events = events_res.json()["events"]
    assert len(events) >= 2  # Planning started, chat tool result, replan completed, etc.
    event_types = [e["event_type"] for e in events]
    assert "replan_completed" in event_types
