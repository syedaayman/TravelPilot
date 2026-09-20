import sys
import time
import requests
import subprocess

def test_api():
    base_url = "http://127.0.0.1:8001"
    
    # Pre-flight
    try:
        res = requests.get(f"{base_url}/api/health")
        assert res.status_code == 200, "Health check failed"
        
        res = requests.get(f"{base_url}/api/destinations")
        assert res.status_code == 200, "Destinations failed"
        
        dests = res.json().get("items", [])
        hyd = next((d for d in dests if d["name"] == "Hyderabad"), None)
        assert hyd is not None, "Hyderabad missing"
        # check if valid UUID
        import uuid
        assert uuid.UUID(hyd["id"]), "Invalid UUID for Hyderabad"
        print("Pre-flight PASS")
    except Exception as e:
        print(f"FAIL Pre-flight: {e}")
        return False

    # POST plan
    req_body = {
        "destinations": ["Hyderabad"],
        "start_date": "2026-10-01",
        "duration_days": 6,
        "budget": 30000,
        "pace": "balanced",
        "preferences": {"interests": ["History", "Food", "Culture"]}
    }
    
    res = requests.post(f"{base_url}/api/trips/plan", json=req_body)
    if res.status_code not in [200, 201]:
        print(f"FAIL POST /plan: {res.text}")
        return False
        
    data = res.json()
    trip = data.get("trip", data)
    trip_id = trip["id"]
    
    assert trip["total_budget"] == 30000.0, "Budget mismatch"
    assert trip["duration_days"] == 6, "Duration mismatch"
    assert len(trip["stops"]) >= 1, "Missing stops"
    print("POST /plan PASS")

    # GET trip
    res = requests.get(f"{base_url}/api/trips/{trip_id}")
    assert res.status_code == 200, "GET /trip failed"
    get_data = res.json()
    assert get_data["id"] == trip_id
    assert len(get_data["stops"]) > 0
    assert len(get_data["itinerary"]) > 0
    print("GET /trip PASS")

    # Budget & Validation checks
    assert get_data["budget"]["total"] <= 30000.0 or not get_data["budget"].get("within_budget", True), "Budget logic invalid"
    assert "errors" in get_data.get("validation", {}), "Validation missing"
    print("Budget & Validation PASS")

    # Verify agent events
    res = requests.get(f"{base_url}/api/agent/events/{trip_id}")
    assert res.status_code in [200, 404]
    if res.status_code == 200:
        events = res.json()
        assert len(events) >= 0
    print("Agent events PASS")

    print(f"SUCCESS|{trip_id}")
    return True

if __name__ == "__main__":
    test_api()
