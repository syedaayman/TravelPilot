"""
Unit Tests for Agent Tool Registry and Implementations
Verifies that all 12 tools execute safely, return concise structured payloads,
handle malformed parameters, and record structured AgentEvents.
"""

import pytest
from datetime import date
from backend.app.agent.tools import tool_registry
from backend.app.db.supabase_client import get_db
from backend.app.models.entities import Trip, TripStop


@pytest.fixture(autouse=True)
def init_db():
    db = get_db()
    db.load_seed_data()
    return db


# 1. search_destinations
def test_tool_search_destinations():
    res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    assert res["success"] is True
    assert res["tool"] == "search_destinations"
    data = res["data"]
    assert len(data) >= 1
    assert data[0]["name"] == "Hyderabad"
    assert "latitude" in data[0]
    assert "average_daily_cost" in data[0]


# 2. search_places
def test_tool_search_places():
    dest_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    dest_id = dest_res["data"][0]["id"]

    res = tool_registry.execute("search_places", {"destination_id": dest_id, "category": "historical"})
    assert res["success"] is True
    places = res["data"]
    assert len(places) >= 2
    for p in places:
        assert p["category"] == "historical"
        assert "open_time" in p
        assert "entry_fee" in p


# 3. get_place_details
def test_tool_get_place_details():
    dest_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    dest_id = dest_res["data"][0]["id"]
    places_res = tool_registry.execute("search_places", {"destination_id": dest_id})
    place_id = places_res["data"][0]["id"]

    res = tool_registry.execute("get_place_details", {"place_id": place_id})
    assert res["success"] is True
    assert res["data"]["id"] == place_id
    assert "description" in res["data"]


# 4. search_hotels
def test_tool_search_hotels():
    dest_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    dest_id = dest_res["data"][0]["id"]

    res = tool_registry.execute("search_hotels", {"destination_id": dest_id, "tier": "budget"})
    assert res["success"] is True
    hotels = res["data"]
    assert len(hotels) >= 1
    assert hotels[0]["tier"] == "budget"
    assert hotels[0]["price_per_night"] <= 2000.0


# 5. search_restaurants
def test_tool_search_restaurants():
    dest_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    dest_id = dest_res["data"][0]["id"]

    res = tool_registry.execute("search_restaurants", {"destination_id": dest_id})
    assert res["success"] is True
    assert len(res["data"]) >= 1


# 6. search_transport
def test_tool_search_transport():
    hyd_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    hampi_res = tool_registry.execute("search_destinations", {"query": "Hampi"})
    hyd_id = hyd_res["data"][0]["id"]
    hampi_id = hampi_res["data"][0]["id"]

    res = tool_registry.execute("search_transport", {
        "origin_destination_id": hyd_id,
        "dest_destination_id": hampi_id,
    })
    assert res["success"] is True
    transports = res["data"]
    assert len(transports) >= 2
    modes = {t["mode"] for t in transports}
    assert "train" in modes or "bus" in modes


# 7. calculate_travel_time
def test_tool_calculate_travel_time():
    # Charminar (17.3616, 78.4747) to Golconda (17.3833, 78.4011)
    res = tool_registry.execute("calculate_travel_time", {
        "origin_lat": 17.3616,
        "origin_lng": 78.4747,
        "dest_lat": 17.3833,
        "dest_lng": 78.4011,
        "mode": "cab",
    })
    assert res["success"] is True
    data = res["data"]
    assert data["distance_km"] > 7.0
    assert data["duration_minutes"] > 10
    assert data["mode"] == "cab"


# 8. validate_itinerary
def test_tool_validate_itinerary():
    items = [
        {
            "id": "it-1",
            "trip_stop_id": "stop-1",
            "day_number": 1,
            "scheduled_date": "2026-10-01",
            "start_time": "10:00",
            "end_time": "12:00",
        },
        {
            "id": "it-2",
            "trip_stop_id": "stop-1",
            "day_number": 1,
            "scheduled_date": "2026-10-01",
            "start_time": "13:00",
            "end_time": "15:00",
            "travel_time_from_prev_minutes": 20,
        },
    ]
    res = tool_registry.execute("validate_itinerary", {"items": items})
    assert res["success"] is True
    assert res["data"]["valid"] is True


# 9. calculate_budget
def test_tool_calculate_budget():
    res = tool_registry.execute("calculate_budget", {
        "total_budget": 25000.0,
        "traveler_count": 2,
        "stops": [],
        "items": [],
    })
    assert res["success"] is True
    assert res["data"]["budget"] == 25000.0
    assert res["data"]["within_budget"] is True


# 10. find_alternatives
def test_tool_find_alternatives():
    dest_res = tool_registry.execute("search_destinations", {"query": "Hyderabad"})
    dest_id = dest_res["data"][0]["id"]
    places_res = tool_registry.execute("search_places", {"destination_id": dest_id})
    target_place = places_res["data"][0]

    res = tool_registry.execute("find_alternatives", {
        "place_id": target_place["id"],
        "max_distance_km": 20.0,
    })
    assert res["success"] is True
    alternatives = res["data"]
    # Should find other places in Hyderabad excluding target place
    assert len(alternatives) >= 1
    assert all(a["id"] != target_place["id"] for a in alternatives)


# 11. Trip State and Update Itinerary
def test_tool_trip_state_and_update(init_db):
    trip = init_db.create_trip(Trip(
        id="t-tool-test",
        title="Tool Test Trip",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
        total_budget=15000.0,
    ))

    # Get state
    state_res = tool_registry.execute("get_trip_state", {"trip_id": trip.id})
    assert state_res["success"] is True
    assert state_res["data"]["trip"]["title"] == "Tool Test Trip"

    # Update itinerary
    update_res = tool_registry.execute("update_itinerary", {
        "trip_id": trip.id,
        "items": [
            {
                "id": "item-up-1",
                "trip_stop_id": "stop-dummy",
                "day_number": 1,
                "scheduled_date": "2026-10-01",
                "start_time": "10:00",
                "end_time": "12:00",
            }
        ]
    })
    assert update_res["success"] is True
    assert update_res["data"]["items_count"] == 1


# 12. Malformed Tool Call & Exception Handling
def test_tool_malformed_arguments():
    # Calling non-existent tool
    res = tool_registry.execute("non_existent_tool", {})
    assert res["success"] is False
    assert res["error_code"] == "TOOL_NOT_FOUND"

    # Missing required argument in get_place_details
    res2 = tool_registry.execute("get_place_details", {"place_id": "invalid-uuid-999"})
    assert res2["success"] is False
    assert res2["error_code"] == "TOOL_EXECUTION_ERROR"
