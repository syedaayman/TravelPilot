"""
Phase 5 Tests: Disruptions API
Validates disruption triggering, applying replans, rejecting replans, and state protection (stale proposals).
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_disruption_lifecycle(client: TestClient):
    # 1. Create a trip
    payload = {
        "destinations": ["Hyderabad"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    assert trip_res.status_code == 201
    trip_id = trip_res.json()["id"]

    # 2. Trigger Disruption
    disrupt_req = {
        "trip_id": trip_id,
        "type": "BUDGET_REDUCTION",
        "reduction_amount": 2000.0
    }
    trigger_res = client.post("/api/disruptions/trigger", json=disrupt_req)
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.json()
    
    assert trigger_data["success"] is True
    assert "replan_id" in trigger_data
    assert "disruption_analysis" in trigger_data
    assert "proposed_replan" in trigger_data
    
    replan_id = trigger_data["replan_id"]

    # 3. Apply Replan
    apply_res = client.post(f"/api/disruptions/{replan_id}/apply")
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["success"] is True
    assert apply_data["trip_id"] == trip_id
    assert "applied_items_count" in apply_data


def test_disruption_reject(client: TestClient):
    # Create trip
    payload = {
        "destinations": ["Goa"],
        "duration_days": 3,
        "budget": 20000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Trigger Disruption
    disrupt_req = {
        "trip_id": trip_id,
        "type": "WEATHER_ALERT"
    }
    trigger_res = client.post("/api/disruptions/trigger", json=disrupt_req)
    replan_id = trigger_res.json()["replan_id"]

    # Reject Replan
    reject_res = client.post(f"/api/disruptions/{replan_id}/reject")
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["success"] is True
    assert "unchanged" in reject_data["message"].lower()


def test_stale_proposal(client: TestClient):
    # Create trip
    payload = {
        "destinations": ["Jaipur"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Trigger Disruption 1
    disrupt_req1 = {
        "trip_id": trip_id,
        "type": "BUDGET_REDUCTION",
        "reduction_amount": 1000.0
    }
    trigger_res1 = client.post("/api/disruptions/trigger", json=disrupt_req1)
    replan_id1 = trigger_res1.json()["replan_id"]

    import time
    time.sleep(1.1)
    
    # Trigger Disruption 2 and Apply it (modifies trip state)
    disrupt_req2 = {
        "trip_id": trip_id,
        "type": "BUDGET_REDUCTION",
        "reduction_amount": 2000.0
    }
    trigger_res2 = client.post("/api/disruptions/trigger", json=disrupt_req2)
    replan_id2 = trigger_res2.json()["replan_id"]
    client.post(f"/api/disruptions/{replan_id2}/apply")

    # Try to apply Disruption 1 (should be stale)
    apply_res1 = client.post(f"/api/disruptions/{replan_id1}/apply")
    print("DEBUG:", apply_res1.json())
    assert apply_res1.status_code == 409
    assert apply_res1.json()["error"]["code"] == "STALE_PROPOSAL"
