"""
Phase 5 Tests: Trips API
Validates single-city and multi-city trip planning, retrieval, error handling, and destination-agnostic behavior.
"""

import pytest
from datetime import date, timedelta
from fastapi.testclient import TestClient
from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_create_single_city_trip(client: TestClient):
    payload = {
        "destinations": ["Hyderabad"],
        "duration_days": 6,
        "budget": 25000.0,
        "travelers": 1,
        "interests": ["history", "food"],
    }
    response = client.post("/api/trips/plan", json=payload)
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert "stops" in data
    assert len(data["stops"]) == 1
    assert data["stops"][0]["destination_name"] == "Hyderabad"
    assert data["duration_days"] == 6
    assert data["total_budget"] == 25000.0
    assert "itinerary" in data
    assert len(data["itinerary"]) > 0
    assert "budget" in data
    assert data["budget"]["total"] > 0
    assert "validation" in data
    assert data["validation"]["valid"] is True


def test_create_multi_city_trip(client: TestClient):
    payload = {
        "destinations": ["Hyderabad", "Hampi", "Goa"],
        "duration_days": 8,
        "budget": 40000.0,
        "travelers": 2,
        "interests": ["history", "beaches"],
    }
    response = client.post("/api/trips/plan", json=payload)
    print("DEBUG MULTI CITY:", response.json())
    assert response.status_code == 201
    data = response.json()

    assert "id" in data
    assert len(data["stops"]) == 3
    stop_names = [s["destination_name"] for s in data["stops"]]
    assert stop_names == ["Hyderabad", "Hampi", "Goa"]
    assert "transport_legs" in data
    assert len(data["transport_legs"]) >= 2
    assert len(data["itinerary"]) > 0
    assert data["total_budget"] == 40000.0
    assert data["traveler_count"] == 2


def test_get_trip(client: TestClient):
    # Plan a trip first
    payload = {
        "destinations": ["Jaipur"],
        "duration_days": 3,
        "budget": 15000.0,
    }
    create_res = client.post("/api/trips/plan", json=payload)
    assert create_res.status_code == 201
    trip_id = create_res.json()["id"]

    # Retrieve trip
    get_res = client.get(f"/api/trips/{trip_id}")
    assert get_res.status_code == 200
    data = get_res.json()
    assert data["id"] == trip_id
    assert data["title"] == "3 Days in Jaipur"
    assert len(data["stops"]) == 1


def test_unknown_trip(client: TestClient):
    response = client.get("/api/trips/non-existent-trip-999")
    assert response.status_code == 404
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "TRIP_NOT_FOUND"


def test_invalid_trip_request(client: TestClient):
    # Empty destinations list
    payload = {
        "destinations": [],
        "duration_days": 4,
        "budget": 20000.0,
    }
    response = client.post("/api/trips/plan", json=payload)
    assert response.status_code in [400, 422]
    data = response.json()
    assert "error" in data


def test_destination_agnostic_planning(client: TestClient):
    # Test planning with multiple diverse destinations (Delhi, Varanasi)
    payload = {
        "destinations": ["Delhi", "Varanasi"],
        "duration_days": 5,
        "budget": 30000.0,
    }
    response = client.post("/api/trips/plan", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert len(data["stops"]) == 2
    assert data["stops"][0]["destination_name"] == "Delhi"
    assert data["stops"][1]["destination_name"] == "Varanasi"
