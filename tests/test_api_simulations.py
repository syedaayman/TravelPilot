"""
Phase 5 Tests: Simulations API
Validates what-if simulation triggering, apply/reject mechanics, and state protection.
"""

import pytest
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_simulation_lifecycle(client: TestClient):
    # 1. Create a trip
    payload = {
        "destinations": ["Hyderabad"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    assert trip_res.status_code == 201
    trip_id = trip_res.json()["id"]

    # 2. Trigger Simulation
    sim_req = {
        "trip_id": trip_id,
        "type": "ADD_DAY",
        "parameters": {
            "extra_days": 1
        }
    }
    trigger_res = client.post("/api/simulations/what-if", json=sim_req)
    assert trigger_res.status_code == 200
    trigger_data = trigger_res.json()
    
    assert trigger_data["success"] is True
    assert "simulation_id" in trigger_data
    assert trigger_data["feasible"] is True
    
    sim_id = trigger_data["simulation_id"]

    # 3. Apply Simulation
    apply_res = client.post(f"/api/simulations/{sim_id}/apply")
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["success"] is True
    assert apply_data["applied"] is True


def test_simulation_reject(client: TestClient):
    # Create trip
    payload = {
        "destinations": ["Goa"],
        "duration_days": 3,
        "budget": 20000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Trigger Simulation
    sim_req = {
        "trip_id": trip_id,
        "type": "BUDGET_CHANGE",
        "parameters": {
            "new_budget": 10000.0
        }
    }
    trigger_res = client.post("/api/simulations/what-if", json=sim_req)
    sim_id = trigger_res.json()["simulation_id"]

    # Reject Simulation
    reject_res = client.post(f"/api/simulations/{sim_id}/reject")
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["success"] is True
    assert reject_data["applied"] is False


def test_simulation_stale_proposal(client: TestClient):
    # Create trip
    payload = {
        "destinations": ["Jaipur"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    trip_res = client.post("/api/trips/plan", json=payload)
    trip_id = trip_res.json()["id"]

    # Trigger Simulation 1
    sim_req1 = {
        "trip_id": trip_id,
        "type": "ADD_DAY",
        "parameters": {"extra_days": 1}
    }
    trigger_res1 = client.post("/api/simulations/what-if", json=sim_req1)
    sim_id1 = trigger_res1.json()["simulation_id"]

    import time
    time.sleep(1.1)

    # Trigger Simulation 2 and Apply it (modifies trip state)
    sim_req2 = {
        "trip_id": trip_id,
        "type": "BUDGET_CHANGE",
        "parameters": {"budget_delta": 2000.0}
    }
    trigger_res2 = client.post("/api/simulations/what-if", json=sim_req2)
    sim_id2 = trigger_res2.json()["simulation_id"]
    client.post(f"/api/simulations/{sim_id2}/apply")

    # Try to apply Simulation 1 (should be stale)
    apply_res1 = client.post(f"/api/simulations/{sim_id1}/apply")
    assert apply_res1.status_code == 409
    assert apply_res1.json()["error"]["code"] == "STALE_PROPOSAL"
