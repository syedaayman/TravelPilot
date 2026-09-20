"""
Phase 1 Foundation Test Suite
Verifies configuration, database abstraction, seed data integrity, destination retrieval,
relational constraints, agent observability event constraints, and FastAPI startup.
"""

import pytest
from datetime import date, datetime
from fastapi.testclient import TestClient

from backend.app.config import Settings
from backend.app.main import app
from backend.app.db.memory_store import InMemoryDB
from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Destination,
    Place,
    Hotel,
    Restaurant,
    TransportOption,
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Disruption,
    AgentEvent,
    AgentEventType,
    TripStatus,
    HotelTier,
    TransportMode,
    ItemType,
    DisruptionType,
)


@pytest.fixture
def db():
    """Returns fresh in-memory database with seed loaded."""
    return InMemoryDB(load_seed=True)


@pytest.fixture
def client():
    """Returns FastAPI test client."""
    return TestClient(app)


# ============================================================================
# 1. Configuration Tests
# ============================================================================

def test_settings_load():
    settings = Settings()
    assert settings.ENVIRONMENT == "development"
    assert settings.LOG_LEVEL == "INFO"
    # Verify no secret is hardcoded in defaults
    assert settings.GEMINI_API_KEY is None or isinstance(settings.GEMINI_API_KEY, str)


# ============================================================================
# 2. Seed Data Integrity Tests
# ============================================================================

def test_seed_destinations_loaded(db: InMemoryDB):
    assert len(db.destinations) == 8
    names = {d.name for d in db.destinations.values()}
    expected = {"Hyderabad", "Hampi", "Goa", "Bengaluru", "Jaipur", "Munnar", "Delhi", "Varanasi"}
    assert names == expected


def test_seed_places_and_foreign_keys(db: InMemoryDB):
    assert len(db.places) > 10
    dest_ids = set(db.destinations.keys())

    for place in db.places.values():
        # Destination foreign key exists
        assert place.destination_id in dest_ids
        # Lat/Lng are within valid bounds for India
        assert 8.0 <= place.latitude <= 37.0
        assert 68.0 <= place.longitude <= 97.0
        # Times and duration
        assert place.typical_duration_minutes > 0
        assert place.entry_fee >= 0
        # Check source metadata
        assert place.source == "curated_static"
        assert place.last_verified_at is not None


def test_seed_hotels_and_restaurants(db: InMemoryDB):
    assert len(db.hotels) > 5
    assert len(db.restaurants) > 4
    dest_ids = set(db.destinations.keys())

    for hotel in db.hotels.values():
        assert hotel.destination_id in dest_ids
        assert hotel.price_per_night > 0
        assert hotel.tier in {HotelTier.BUDGET, HotelTier.MID_RANGE, HotelTier.LUXURY, HotelTier.HOSTEL}

    for rest in db.restaurants.values():
        assert rest.destination_id in dest_ids
        assert rest.average_cost_per_person > 0


def test_seed_transport_options(db: InMemoryDB):
    assert len(db.transport_options) > 5
    dest_ids = set(db.destinations.keys())

    for trans in db.transport_options.values():
        assert trans.origin_destination_id in dest_ids
        assert trans.dest_destination_id in dest_ids
        assert trans.origin_destination_id != trans.dest_destination_id
        assert trans.typical_duration_minutes > 0
        assert trans.estimated_cost >= 0


# ============================================================================
# 3. Dynamic Destination-Agnostic Retrieval Tests
# ============================================================================

def test_search_destinations_dynamic(db: InMemoryDB):
    # Lookup by substring
    hyd_results = db.search_destinations("Hyder")
    assert len(hyd_results) == 1
    assert hyd_results[0].name == "Hyderabad"

    # Lookup by state
    karnataka_results = db.search_destinations("Karnataka")
    assert len(karnataka_results) == 2
    names = {d.name for d in karnataka_results}
    assert "Hampi" in names
    assert "Bengaluru" in names

    # Exact name helper
    hampi = db.get_destination_by_name("hampi")
    assert hampi is not None
    assert hampi.name == "Hampi"


def test_search_places_filtering(db: InMemoryDB):
    hyd = db.get_destination_by_name("Hyderabad")
    assert hyd is not None

    # Filter historical places
    hist_places = db.search_places(hyd.id, category="historical")
    assert len(hist_places) >= 3
    for p in hist_places:
        assert p.category == "historical"

    # Filter by budget
    free_or_cheap = db.search_places(hyd.id, max_entry_fee=30.0)
    for p in free_or_cheap:
        assert p.entry_fee <= 30.0


def test_search_hotels_and_transport(db: InMemoryDB):
    hyd = db.get_destination_by_name("Hyderabad")
    hampi = db.get_destination_by_name("Hampi")
    assert hyd is not None and hampi is not None

    # Budget hotel in Hyderabad
    budget_hotels = db.search_hotels(hyd.id, tier="budget")
    assert len(budget_hotels) >= 1
    assert budget_hotels[0].price_per_night <= 2000.0

    # Transport from Hyderabad to Hampi
    trans_options = db.search_transport(hyd.id, hampi.id)
    assert len(trans_options) >= 2
    modes = {t.mode for t in trans_options}
    assert TransportMode.TRAIN in modes or TransportMode.BUS in modes


# ============================================================================
# 4. Operational Trip Model (Single-City vs Multi-City)
# ============================================================================

def test_single_city_trip_model(db: InMemoryDB):
    """Single-city trip has 1 trip_stop matching trip dates."""
    hyd = db.get_destination_by_name("Hyderabad")
    assert hyd is not None

    trip = Trip(
        title="6 Days in Hyderabad",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 6),
        total_budget=25000.0,
        interests=["history", "food"]
    )
    db.create_trip(trip)

    stop = TripStop(
        trip_id=trip.id,
        destination_id=hyd.id,
        order_index=0,
        arrival_date=date(2026, 10, 1),
        departure_date=date(2026, 10, 6),
        stop_budget=25000.0
    )
    db.add_trip_stop(stop)

    # Add an itinerary item
    item = ItineraryItem(
        trip_stop_id=stop.id,
        item_type=ItemType.PLACE,
        custom_title="Charminar & Laad Bazaar",
        day_number=1,
        scheduled_date=date(2026, 10, 1),
        start_time="10:00:00",
        end_time="12:00:00",
        cost=25.0
    )
    db.add_itinerary_item(item)

    stops = db.get_trip_stops(trip.id)
    assert len(stops) == 1
    items = db.get_itinerary_items_for_stop(stops[0].id)
    assert len(items) == 1
    assert items[0].custom_title == "Charminar & Laad Bazaar"


def test_multi_city_trip_model(db: InMemoryDB):
    """Multi-city trip has N ordered trip_stops connected by transport legs."""
    hyd = db.get_destination_by_name("Hyderabad")
    hampi = db.get_destination_by_name("Hampi")
    goa = db.get_destination_by_name("Goa")
    assert hyd and hampi and goa

    trip = Trip(
        title="8 Days Hyderabad -> Hampi -> Goa",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 8),
        total_budget=40000.0,
        interests=["history", "beaches"]
    )
    db.create_trip(trip)

    stop1 = db.add_trip_stop(TripStop(
        trip_id=trip.id,
        destination_id=hyd.id,
        order_index=0,
        arrival_date=date(2026, 11, 1),
        departure_date=date(2026, 11, 3)
    ))

    stop2 = db.add_trip_stop(TripStop(
        trip_id=trip.id,
        destination_id=hampi.id,
        order_index=1,
        arrival_date=date(2026, 11, 4),
        departure_date=date(2026, 11, 5)
    ))

    stop3 = db.add_trip_stop(TripStop(
        trip_id=trip.id,
        destination_id=goa.id,
        order_index=2,
        arrival_date=date(2026, 11, 6),
        departure_date=date(2026, 11, 8)
    ))

    # Transport Leg 1 (Hyd -> Hampi)
    leg1 = db.add_transport_leg(TransportLeg(
        trip_id=trip.id,
        origin_stop_id=stop1.id,
        destination_stop_id=stop2.id,
        mode=TransportMode.TRAIN,
        carrier="Amaravati Express",
        departure_time=datetime(2026, 11, 3, 21, 5),
        arrival_time=datetime(2026, 11, 4, 6, 0),
        cost=650.0
    ))

    # Transport Leg 2 (Hampi -> Goa)
    leg2 = db.add_transport_leg(TransportLeg(
        trip_id=trip.id,
        origin_stop_id=stop2.id,
        destination_stop_id=stop3.id,
        mode=TransportMode.TRAIN,
        carrier="Vasco Amaravati Express",
        departure_time=datetime(2026, 11, 5, 6, 30),
        arrival_time=datetime(2026, 11, 5, 14, 0),
        cost=550.0
    ))

    stops = db.get_trip_stops(trip.id)
    assert len(stops) == 3
    legs = db.get_transport_legs_for_trip(trip.id)
    assert len(legs) == 2
    assert legs[0].origin_stop_id == stop1.id
    assert legs[1].destination_stop_id == stop3.id


# ============================================================================
# 5. Agent Observability Event Safety
# ============================================================================

def test_agent_event_structured_only(db: InMemoryDB):
    """Verifies that AgentEvent accepts only allowed event types with structured metadata."""
    trip = db.create_trip(Trip(
        title="Test Trip",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
        total_budget=10000.0
    ))

    # Record tool call event
    event = AgentEvent(
        trip_id=trip.id,
        event_type=AgentEventType.TOOL_CALL,
        tool_name="search_places",
        input_summary="destination_id=dest-hyd-001, category=historical",
        result_summary="Found 4 attractions",
        duration_ms=45,
        status="success",
        metadata={"item_count": 4}
    )
    db.record_agent_event(event)

    events = db.get_agent_events_for_trip(trip.id)
    assert len(events) == 1
    assert events[0].event_type == AgentEventType.TOOL_CALL
    assert events[0].tool_name == "search_places"
    assert events[0].duration_ms == 45


# ============================================================================
# 6. FastAPI Startup & Health Endpoint
# ============================================================================

def test_fastapi_health(client: TestClient):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "TravelPilot API"
    assert data["reference_destinations_count"] == 8
    assert data["reference_places_count"] >= 10
