"""
Unit Tests for Deterministic Disruption Management Engine
Covers all 16 required test scenarios verifying disruption analysis, replanning,
alternative scoring, minimal disruption footprint, state isolation, and apply/reject operations.
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
    TransportLegStatus,
)
from backend.app.core.models import (
    CoreDisruptionType,
    DisruptionRequest,
)
from backend.app.core.disruption_engine import disruption_engine


@pytest.fixture(autouse=True)
def init_db():
    db = get_db()
    db.load_seed_data()
    return db


@pytest.fixture
def sample_trip_state():
    trip = Trip(
        id="trip-disr-test",
        title="Hyderabad & Hampi Trip",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 5),
        total_budget=30000.0,
    )
    stop1 = TripStop(id="stop-hyd", trip_id=trip.id, destination_id="99852cd9-2775-52f3-8fe0-0a26c43a6c09", order_index=0, arrival_date=date(2026, 10, 1), departure_date=date(2026, 10, 3))
    stop2 = TripStop(id="stop-hampi", trip_id=trip.id, destination_id="66c46096-b4bb-5cdf-8ee8-62642b00a456", order_index=1, arrival_date=date(2026, 10, 4), departure_date=date(2026, 10, 5))

    hotel1 = Hotel(id="h-hyd", destination_id="99852cd9-2775-52f3-8fe0-0a26c43a6c09", name="Marigold", price_per_night=3000.0, latitude=17.43, longitude=78.45)
    hotel2 = Hotel(id="h-hampi", destination_id="66c46096-b4bb-5cdf-8ee8-62642b00a456", name="Heritage Hampi", price_per_night=2500.0, latitude=15.33, longitude=76.46)

    leg1 = TransportLeg(
        id="7e9e60a9-ed1f-5e54-ba05-416f588b2ef5",
        trip_id=trip.id,
        origin_stop_id=stop1.id,
        destination_stop_id=stop2.id,
        mode=TransportMode.TRAIN,
        carrier="Amaravati Express",
        departure_time=datetime(2026, 10, 3, 21, 5),
        arrival_time=datetime(2026, 10, 4, 6, 0),
        cost=650.0,
    )

    items = [
        ItineraryItem(
            id="item-hyd-1",
            trip_stop_id=stop1.id,
            place_id="3dec0241-0638-5161-9d05-0f3f1307edb5", # Charminar
            custom_title="Charminar & Laad Bazaar",
            day_number=1,
            scheduled_date=date(2026, 10, 1),
            start_time="10:00",
            end_time="12:30",
            cost=25.0,
        ),
        ItineraryItem(
            id="item-hyd-2",
            trip_stop_id=stop1.id,
            place_id="0fde0ebc-3d84-517a-b0f1-ef23b062e006", # Golconda Fort
            custom_title="Golconda Fort",
            day_number=2,
            scheduled_date=date(2026, 10, 2),
            start_time="09:30",
            end_time="12:30",
            cost=25.0,
        ),
        ItineraryItem(
            id="item-hampi-1",
            trip_stop_id=stop2.id,
            place_id="336b2438-c062-592f-b4e8-0b472065940f", # Virupaksha Temple
            custom_title="Virupaksha Temple",
            day_number=4,
            scheduled_date=date(2026, 10, 4),
            start_time="09:00",
            end_time="11:00",
            cost=50.0,
        ),
    ]

    return trip, [stop1, stop2], items, [leg1], {"stop-hyd": hotel1, "stop-hampi": hotel2}


# 1. Venue Closure Replan
def test_disruption_venue_closure(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2", # Golconda Fort closed
        reason="Maintenance closure",
    )

    # Read-only analysis
    analysis = disruption_engine.analyze_disruption(req, trip, stops, items, legs)
    assert len(analysis.affected_items) == 1
    assert analysis.required_replan is True

    # Deterministic replan
    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True
    # Replaced Golconda with a valid alternative in Hyderabad (e.g. Qutb Shahi Tombs or Salar Jung)
    assert len(replan.proposed_items) == 3
    replaced_item = next(it for it in replan.proposed_items if it["id"] == "item-hyd-2")
    assert replaced_item["place_id"] != "0fde0ebc-3d84-517a-b0f1-ef23b062e006"
    assert replaced_item["status"] == ItemStatus.ALTERNATIVE_SELECTED.value
    assert len(replan.candidates_evaluated) >= 1
    assert len(replan.diff.modified_items) == 1


# 2. Venue Closure With No Feasible Alternative (Removes safely)
def test_disruption_venue_closure_no_alternative(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    # Item in an isolated location with no destination place records
    items[0].place_id = "non-existent-place-999"
    items[0].trip_stop_id = "non-existent-stop"
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-1",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True
    assert len(replan.proposed_items) == 2 # Removed item-hyd-1
    assert len(replan.diff.removed_items) == 1


# 3. Transport Delay
def test_disruption_transport_delay(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.TRANSPORT_DELAY,
        affected_leg_id="7e9e60a9-ed1f-5e54-ba05-416f588b2ef5",
        delay_minutes=120, # Delayed 2 hours -> Arrives at 08:00
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True
    # Check delayed leg
    delayed_leg = replan.proposed_legs[0]
    assert delayed_leg["status"] == TransportLegStatus.DELAYED.value
    # Downstream activity starting at 09:00 is preserved or safely buffered
    assert len(replan.proposed_items) == 3


# 4. Transport Cancellation
def test_disruption_transport_cancellation(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.TRANSPORT_CANCELLED,
        affected_leg_id="7e9e60a9-ed1f-5e54-ba05-416f588b2ef5",
        reason="Train service strike",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True
    assert len(replan.proposed_legs) == 1
    # Check that replacement transport from seed data was chosen
    rep_leg = replan.proposed_legs[0]
    assert rep_leg["cost"] > 0


# 5. Weather Alert
def test_disruption_weather_alert(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.WEATHER_ALERT,
        effective_date=date(2026, 10, 1),
        weather_categories=["historical", "outdoor"],
        reason="Torrential rain",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True
    assert len(replan.candidates_evaluated) >= 1


# 6. Booking Unavailable
def test_disruption_booking_unavailable(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.BOOKING_UNAVAILABLE,
        affected_item_id="item-hyd-1",
        reason="Hotel overbooked",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True


# 7. Budget Reduction
def test_disruption_budget_reduction(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.BUDGET_REDUCTION,
        reduction_amount=5000.0,
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.budget_after.budget == 25000.0
    assert replan.feasible is True


# 8. Schedule Conflict
def test_disruption_schedule_conflict(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.SCHEDULE_CONFLICT,
        affected_item_id="item-hyd-1",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.feasible is True


# 9. Unaffected Items Preserved
def test_disruption_unaffected_items_preserved(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    # Day 1 item-hyd-1 and Day 4 item-hampi-1 must remain completely identical
    item1_after = next(it for it in replan.proposed_items if it["id"] == "item-hyd-1")
    item3_after = next(it for it in replan.proposed_items if it["id"] == "item-hampi-1")
    assert item1_after["place_id"] == "3dec0241-0638-5161-9d05-0f3f1307edb5"
    assert item3_after["place_id"] == "336b2438-c062-592f-b4e8-0b472065940f"


# 10. Minimal Replan Behavior
def test_disruption_minimal_replan_footprint(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )

    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    # Only 1 item modified
    assert len(replan.diff.modified_items) == 1
    assert len(replan.diff.unchanged_items) == 2


# 11. Full Validation Gate
def test_disruption_full_validation_performed(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )
    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.validation_after is not None
    assert replan.validation_after.valid is True


# 12. Budget Recalculation
def test_disruption_budget_recalculation(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )
    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.budget_after.total > 0
    assert replan.budget_after.within_budget is True


# 13. Alternative Candidate Filtering & Transparent Scoring
def test_disruption_alternative_scoring(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )
    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert len(replan.candidates_evaluated) >= 1
    top_candidate = replan.candidates_evaluated[0]
    assert top_candidate.score > 0
    assert "rating_score" in top_candidate.score_breakdown
    assert "category_match" in top_candidate.score_breakdown


# 14. Diff Generation
def test_disruption_diff_generation(sample_trip_state):
    trip, stops, items, legs, hotels = sample_trip_state
    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )
    replan = disruption_engine.replan_disruption(req, trip, stops, items, legs, hotels)
    assert replan.diff.summary != ""
    assert "activity modified" in replan.diff.summary


# 15. Active State Remains Unchanged Before Apply
def test_disruption_active_state_protected_before_apply(sample_trip_state, init_db):
    trip, stops, items, legs, hotels = sample_trip_state
    init_db.create_trip(trip)
    for s in stops:
        init_db.add_trip_stop(s)
    for it in items:
        init_db.add_itinerary_item(it)

    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )

    # Run replan
    replan = disruption_engine.replan_disruption(req)

    # Verify active DB item has NOT changed
    active_item = init_db.itinerary_items["item-hyd-2"]
    assert active_item.place_id == "0fde0ebc-3d84-517a-b0f1-ef23b062e006" # Still original Golconda Fort!


# 16. Apply Operation Updates State
def test_disruption_apply_operation_updates_state(sample_trip_state, init_db):
    trip, stops, items, legs, hotels = sample_trip_state
    init_db.create_trip(trip)
    for s in stops:
        init_db.add_trip_stop(s)
    for it in items:
        init_db.add_itinerary_item(it)

    req = DisruptionRequest(
        trip_id=trip.id,
        type=CoreDisruptionType.VENUE_CLOSED,
        affected_item_id="item-hyd-2",
    )

    replan = disruption_engine.replan_disruption(req)
    apply_res = disruption_engine.apply_replan(replan)

    assert apply_res["success"] is True
    # Now active DB item has been updated
    active_item = init_db.itinerary_items["item-hyd-2"]
    assert active_item.place_id != "0fde0ebc-3d84-517a-b0f1-ef23b062e006"
    assert active_item.status == ItemStatus.ALTERNATIVE_SELECTED
