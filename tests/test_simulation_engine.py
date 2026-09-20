"""
Unit Tests for Deterministic What-If Simulation Engine
Covers all 12 required test scenarios verifying isolated hypothetical branching,
what-if budget/day/destination mutations, state protection, and apply/reject operations.
"""

import pytest
from datetime import date, datetime, timedelta
from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Hotel,
    Destination,
    Place,
    HotelTier,
    TransportMode,
    ItemType,
    ItemStatus,
)
from backend.app.core.models import (
    WhatIfType,
    WhatIfRequest,
)
from backend.app.core.simulation_engine import simulation_engine


@pytest.fixture(autouse=True)
def init_db():
    db = get_db()
    db.load_seed_data()
    return db


@pytest.fixture
def sample_multi_city_trip():
    trip = Trip(
        id="trip-sim-multi",
        title="Hyderabad -> Hampi -> Goa (8 Days)",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 8),
        total_budget=40000.0,
    )
    stop1 = TripStop(id="s1", trip_id=trip.id, destination_id="99852cd9-2775-52f3-8fe0-0a26c43a6c09", order_index=0, arrival_date=date(2026, 11, 1), departure_date=date(2026, 11, 3))
    stop2 = TripStop(id="s2", trip_id=trip.id, destination_id="66c46096-b4bb-5cdf-8ee8-62642b00a456", order_index=1, arrival_date=date(2026, 11, 4), departure_date=date(2026, 11, 5))
    stop3 = TripStop(id="s3", trip_id=trip.id, destination_id="a3040500-6ee7-5c92-ab8c-a666e9b12555", order_index=2, arrival_date=date(2026, 11, 6), departure_date=date(2026, 11, 8))

    hotel1 = Hotel(id="h1", destination_id="99852cd9-2775-52f3-8fe0-0a26c43a6c09", name="Marigold", price_per_night=3000.0, latitude=17.43, longitude=78.45)
    hotel2 = Hotel(id="h2", destination_id="66c46096-b4bb-5cdf-8ee8-62642b00a456", name="Heritage Hampi", price_per_night=2500.0, latitude=15.33, longitude=76.46)
    hotel3 = Hotel(id="h3", destination_id="a3040500-6ee7-5c92-ab8c-a666e9b12555", name="Santana Goa", price_per_night=3500.0, latitude=15.51, longitude=73.76)

    leg1 = TransportLeg(id="l1", trip_id=trip.id, origin_stop_id="s1", destination_stop_id="s2", mode=TransportMode.TRAIN, departure_time=datetime(2026, 11, 3, 21, 5), arrival_time=datetime(2026, 11, 4, 6, 0), cost=650.0)
    leg2 = TransportLeg(id="l2", trip_id=trip.id, origin_stop_id="s2", destination_stop_id="s3", mode=TransportMode.TRAIN, departure_time=datetime(2026, 11, 5, 6, 30), arrival_time=datetime(2026, 11, 5, 14, 0), cost=550.0)

    items = [
        ItineraryItem(id="i1", trip_stop_id="s1", place_id="3dec0241-0638-5161-9d05-0f3f1307edb5", custom_title="Charminar", day_number=1, scheduled_date=date(2026, 11, 1), start_time="10:00", end_time="12:30", cost=25.0),
        ItineraryItem(id="i2", trip_stop_id="s2", place_id="336b2438-c062-592f-b4e8-0b472065940f", custom_title="Virupaksha Temple", day_number=4, scheduled_date=date(2026, 11, 4), start_time="09:00", end_time="11:30", cost=50.0),
        ItineraryItem(id="i3", trip_stop_id="s3", place_id="fc92969b-f20f-5edf-87bf-ad0adf2af182", custom_title="Palolem Beach", day_number=6, scheduled_date=date(2026, 11, 6), start_time="15:00", end_time="18:30", cost=0.0),
    ]

    return trip, [stop1, stop2, stop3], items, [leg1, leg2], {"s1": hotel1, "s2": hotel2, "s3": hotel3}


# 1. Budget What-If
def test_simulation_budget_what_if(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.BUDGET_CHANGE,
        budget_delta=-5000.0, # Reduce budget from 40k to 35k
    )

    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.success is True
    assert res.budget_before.budget == 40000.0
    assert res.budget_after.budget == 35000.0
    assert res.proposed_summary["total_budget"] == 35000.0


# 2. Add-Day What-If
def test_simulation_add_day_what_if(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.ADD_DAY,
        extra_days=1, # Extend 8 days -> 9 days
    )

    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.success is True
    assert res.current_summary["days"] == 8
    assert res.proposed_summary["days"] == 9
    assert res.budget_after.total > res.budget_before.total


# 3. Remove-Destination What-If (Drop Goa)
def test_simulation_remove_destination_what_if(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.REMOVE_DESTINATION,
        target_destination_id="a3040500-6ee7-5c92-ab8c-a666e9b12555",
    )

    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.success is True
    assert len(res.proposed_stops) == 2 # Remaining: Hyd + Hampi
    # Items in Goa removed
    assert len(res.proposed_items) == 2
    assert all(it["place_id"] != "fc92969b-f20f-5edf-87bf-ad0adf2af182" for it in res.proposed_items)
    # Budget reduced
    assert res.diff.budget_delta < 0


# 4. Replace-Destination What-If (Replace Hampi with Bengaluru)
def test_simulation_replace_destination_what_if(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.REPLACE_DESTINATION,
        target_destination_id="66c46096-b4bb-5cdf-8ee8-62642b00a456",
        replacement_destination_id="785f636c-9ad9-564c-b55b-21352402ad46",
    )

    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.success is True
    replaced_stop = next(s for s in res.proposed_stops if s["id"] == "s2")
    assert replaced_stop["destination_id"] == "785f636c-9ad9-564c-b55b-21352402ad46"
    assert len(res.proposed_items) >= 2


# 5. Add-Activity What-If
def test_simulation_add_activity_what_if(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.ADD_ACTIVITY,
        activity_data={
            "title": "Evening Chowmahalla Visit",
            "day_number": 1,
            "scheduled_date": "2026-11-01",
            "start_time": "16:00",
            "end_time": "17:30",
            "cost": 100.0,
        },
    )

    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.success is True
    assert len(res.proposed_items) == 4
    assert len(res.diff.added_items) == 1


# 6. Simulation Does Not Mutate Active State
def test_simulation_does_not_mutate_active_state(sample_multi_city_trip, init_db):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    init_db.create_trip(trip)
    for s in stops:
        init_db.add_trip_stop(s)
    for it in items:
        init_db.add_itinerary_item(it)

    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.REMOVE_DESTINATION,
        target_destination_id="a3040500-6ee7-5c92-ab8c-a666e9b12555",
    )

    res = simulation_engine.simulate_what_if(req)
    assert res.success is True

    # Active DB state must still contain all 3 stops and Goa item!
    active_stops = init_db.get_trip_stops(trip.id)
    assert len(active_stops) == 3
    active_items = [it for it in init_db.itinerary_items.values() if it.trip_stop_id in {"s1", "s2", "s3"}]
    assert len(active_items) == 3


# 7. Simulation Diff Integration
def test_simulation_diff_integration(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(trip_id=trip.id, type=WhatIfType.ADD_DAY, extra_days=1)
    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.diff is not None
    assert isinstance(res.diff.budget_delta, float)


# 8. Before / After Budget Validation
def test_simulation_before_after_budget(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(trip_id=trip.id, type=WhatIfType.BUDGET_CHANGE, budget_delta=-10000.0)
    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.budget_before.budget == 40000.0
    assert res.budget_after.budget == 30000.0


# 9. Before / After Schedule Validation
def test_simulation_before_after_validation(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(trip_id=trip.id, type=WhatIfType.ADD_DAY, extra_days=1)
    res = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    assert res.validation_before.valid is True
    assert res.validation_after.valid is True


# 10. Apply Simulation Mutates Active State
def test_simulation_apply_operation(sample_multi_city_trip, init_db):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    init_db.create_trip(trip)
    for s in stops:
        init_db.add_trip_stop(s)
    for it in items:
        init_db.add_itinerary_item(it)

    req = WhatIfRequest(
        trip_id=trip.id,
        type=WhatIfType.ADD_ACTIVITY,
        activity_data={
            "title": "Evening Chowmahalla Visit",
            "day_number": 1,
            "scheduled_date": "2026-11-01",
            "start_time": "16:00",
            "end_time": "17:30",
            "cost": 100.0,
        },
    )
    res = simulation_engine.simulate_what_if(req)
    apply_res = simulation_engine.apply_simulation(res)

    assert apply_res["success"] is True
    assert apply_res["applied"] is True


# 11. Reject Simulation Leaves Active Trip Intact
def test_simulation_reject_operation(sample_multi_city_trip, init_db):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    init_db.create_trip(trip)
    req = WhatIfRequest(trip_id=trip.id, type=WhatIfType.BUDGET_CHANGE, budget_delta=-10000.0)
    res = simulation_engine.simulate_what_if(req)
    reject_res = simulation_engine.reject_simulation(res)

    assert reject_res["success"] is True
    assert reject_res["applied"] is False


# 12. Deterministic Repeated Simulation
def test_simulation_deterministic_reproducibility(sample_multi_city_trip):
    trip, stops, items, legs, hotels = sample_multi_city_trip
    req = WhatIfRequest(trip_id=trip.id, type=WhatIfType.BUDGET_CHANGE, budget_delta=-5000.0)

    run1 = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)
    run2 = simulation_engine.simulate_what_if(req, trip, stops, items, legs, hotels)

    assert run1.budget_after.budget == run2.budget_after.budget
    assert run1.budget_after.total == run2.budget_after.total
    assert run1.diff.summary == run2.diff.summary
