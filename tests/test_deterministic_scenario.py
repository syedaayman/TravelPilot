"""
End-to-End Deterministic Scenario: Hyderabad -> Hampi -> Goa (8 Days)
Verifies that all 4 deterministic engines (Budget, Schedule, Geo, Diff) cooperate
to represent, price, route, validate, and replan a multi-city trip without LLM dependencies.
"""

import pytest
from datetime import date, datetime
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
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator
from backend.app.core.geo_routing import geo_routing_engine, GeoPoint, RoutingMode
from backend.app.core.diff_engine import diff_engine
from backend.app.core.models import ValidationIssueType


def test_e2e_multi_city_deterministic_scenario():
    # -------------------------------------------------------------------------
    # 1. Represent the Trip: Hyderabad (Days 1-3) -> Hampi (Days 4-5) -> Goa (Days 6-8)
    # -------------------------------------------------------------------------
    trip = Trip(
        id="trip-multi-01",
        title="8 Days Hyderabad -> Hampi -> Goa",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 11, 8),
        total_budget=40000.0,
        interests=["history", "beaches"],
    )

    dest_hyd = Destination(id="d-hyd", name="Hyderabad", latitude=17.3850, longitude=78.4867, average_daily_cost=2800.0)
    dest_hampi = Destination(id="d-hampi", name="Hampi", latitude=15.3350, longitude=76.4600, average_daily_cost=2200.0)
    dest_goa = Destination(id="d-goa", name="Goa", latitude=15.2993, longitude=74.1240, average_daily_cost=3800.0)

    stop_hyd = TripStop(id="s-hyd", trip_id=trip.id, destination_id=dest_hyd.id, order_index=0, arrival_date=date(2026, 11, 1), departure_date=date(2026, 11, 3))
    stop_hampi = TripStop(id="s-hampi", trip_id=trip.id, destination_id=dest_hampi.id, order_index=1, arrival_date=date(2026, 11, 4), departure_date=date(2026, 11, 5))
    stop_goa = TripStop(id="s-goa", trip_id=trip.id, destination_id=dest_goa.id, order_index=2, arrival_date=date(2026, 11, 6), departure_date=date(2026, 11, 8))

    hotel_hyd = Hotel(id="h-hyd", destination_id=dest_hyd.id, name="Marigold Hyd", price_per_night=3500.0, latitude=17.43, longitude=78.45)
    hotel_hampi = Hotel(id="h-hampi", destination_id=dest_hampi.id, name="Heritage Hampi", price_per_night=2500.0, latitude=15.33, longitude=76.46)
    hotel_goa = Hotel(id="h-goa", destination_id=dest_goa.id, name="Santana Goa", price_per_night=3000.0, latitude=15.51, longitude=73.76)

    # -------------------------------------------------------------------------
    # 2. Inter-City Transport Legs
    # -------------------------------------------------------------------------
    leg1 = TransportLeg(
        id="7e9e60a9-ed1f-5e54-ba05-416f588b2ef5",
        trip_id=trip.id,
        origin_stop_id=stop_hyd.id,
        destination_stop_id=stop_hampi.id,
        mode=TransportMode.TRAIN,
        carrier="Amaravati Express",
        departure_time=datetime(2026, 11, 3, 21, 5),
        arrival_time=datetime(2026, 11, 4, 6, 0),
        cost=650.0,
    )

    leg2 = TransportLeg(
        id="f308fd2d-496d-539f-bcbb-f773534e443b",
        trip_id=trip.id,
        origin_stop_id=stop_hampi.id,
        destination_stop_id=stop_goa.id,
        mode=TransportMode.TRAIN,
        carrier="Vasco Amaravati Express",
        departure_time=datetime(2026, 11, 5, 6, 30),
        arrival_time=datetime(2026, 11, 5, 14, 0),
        cost=550.0,
    )

    # -------------------------------------------------------------------------
    # 3. Scheduled Itinerary Items with Real Geo Coordinates
    # -------------------------------------------------------------------------
    place_charminar = Place(id="p-char", destination_id=dest_hyd.id, name="Charminar", category="historical", latitude=17.3616, longitude=78.4747, open_time="09:30", close_time="17:30", entry_fee=25.0)
    place_golconda = Place(id="p-golc", destination_id=dest_hyd.id, name="Golconda Fort", category="historical", latitude=17.3833, longitude=78.4011, open_time="09:00", close_time="17:30", entry_fee=25.0)
    place_vittala = Place(id="p-vitt", destination_id=dest_hampi.id, name="Vijaya Vittala Temple", category="historical", latitude=15.3435, longitude=76.4756, open_time="08:30", close_time="17:30", entry_fee=40.0)
    place_palolem = Place(id="p-palo", destination_id=dest_goa.id, name="Palolem Beach", category="beach", latitude=15.0100, longitude=74.0232, open_time="06:00", close_time="22:00", entry_fee=0.0)

    places_map = {
        place_charminar.id: place_charminar,
        place_golconda.id: place_golconda,
        place_vittala.id: place_vittala,
        place_palolem.id: place_palolem,
    }

    # Day 1: Charminar (10:00 - 12:30) -> Golconda (14:30 - 17:00)
    # Distance: ~8.1km -> Cab takes ~25 mins
    dist_hyd = geo_routing_engine.calculate_distance(
        GeoPoint(latitude=place_charminar.latitude, longitude=place_charminar.longitude),
        GeoPoint(latitude=place_golconda.latitude, longitude=place_golconda.longitude),
    )
    est_travel = geo_routing_engine.estimate_travel_time(
        GeoPoint(latitude=place_charminar.latitude, longitude=place_charminar.longitude),
        GeoPoint(latitude=place_golconda.latitude, longitude=place_golconda.longitude),
        mode=RoutingMode.CAB,
    )

    item1 = ItineraryItem(
        id="item-1",
        trip_stop_id=stop_hyd.id,
        place_id=place_charminar.id,
        custom_title="Charminar",
        day_number=1,
        scheduled_date=date(2026, 11, 1),
        start_time="10:00",
        end_time="12:30",
        cost=25.0,
        travel_distance_km=0.0,
    )
    item2 = ItineraryItem(
        id="item-2",
        trip_stop_id=stop_hyd.id,
        place_id=place_golconda.id,
        custom_title="Golconda Fort",
        day_number=1,
        scheduled_date=date(2026, 11, 1),
        start_time="14:30", # 2 hour lunch + 25 min travel buffer
        end_time="17:00",
        cost=25.0,
        travel_time_from_prev_minutes=est_travel.duration_minutes,
        travel_distance_km=est_travel.distance_km,
    )

    # Day 4: Vittala Temple in Hampi
    item3 = ItineraryItem(
        id="item-3",
        trip_stop_id=stop_hampi.id,
        place_id=place_vittala.id,
        custom_title="Vijaya Vittala Temple",
        day_number=4,
        scheduled_date=date(2026, 11, 4),
        start_time="09:00",
        end_time="12:00",
        cost=40.0,
    )

    # Day 6: Palolem Beach in Goa
    item4 = ItineraryItem(
        id="item-4",
        trip_stop_id=stop_goa.id,
        place_id=place_palolem.id,
        custom_title="Palolem Beach",
        day_number=6,
        scheduled_date=date(2026, 11, 6),
        start_time="15:00",
        end_time="18:30",
        cost=0.0,
    )

    itinerary_items = [item1, item2, item3, item4]

    # -------------------------------------------------------------------------
    # 4. Deterministic Budget Calculation
    # -------------------------------------------------------------------------
    budget_result = budget_engine.calculate(
        total_budget=trip.total_budget,
        traveler_count=1,
        trip_stops=[stop_hyd, stop_hampi, stop_goa],
        hotels_by_stop={"s-hyd": hotel_hyd, "s-hampi": hotel_hampi, "s-goa": hotel_goa},
        transport_legs=[leg1, leg2],
        itinerary_items=itinerary_items,
        destinations_by_stop={"s-hyd": dest_hyd, "s-hampi": dest_hampi, "s-goa": dest_goa},
        daily_food_estimate_per_person=600.0,
        daily_local_transit_estimate_per_person=200.0,
    )

    # 2 nights hyd (7000) + 1 night hampi (2500) + 2 nights goa (6000) = 15500 accommodation
    assert budget_result.accommodation == 15500.0
    # Intercity: 650 + 550 = 1200
    assert budget_result.intercity_transport == 1200.0
    # Activities: 25 + 25 + 40 + 0 = 90
    assert budget_result.activities == 90.0
    # Total well within 40,000 budget
    assert budget_result.within_budget is True
    assert budget_result.total < 40000.0
    assert len(budget_result.daily_breakdowns) == 8 # 8 days total

    # -------------------------------------------------------------------------
    # 5. Deterministic Schedule Validation (Clean Plan)
    # -------------------------------------------------------------------------
    validation_clean = schedule_validator.validate(
        trip=trip,
        trip_stops=[stop_hyd, stop_hampi, stop_goa],
        itinerary_items=itinerary_items,
        transport_legs=[leg1, leg2],
        places_by_id=places_map,
    )
    assert validation_clean.valid is True
    assert len(validation_clean.errors) == 0

    # -------------------------------------------------------------------------
    # 6. Introduce Conflict (Golconda starts before Charminar finishes + travel)
    # -------------------------------------------------------------------------
    conflicted_item2 = item2.model_copy(
        update={"start_time": "12:40", "travel_time_from_prev_minutes": 25}
    )
    validation_conflicted = schedule_validator.validate(
        trip=trip,
        trip_stops=[stop_hyd, stop_hampi, stop_goa],
        itinerary_items=[item1, conflicted_item2, item3, item4],
        transport_legs=[leg1, leg2],
        places_by_id=places_map,
    )
    assert validation_conflicted.valid is False
    assert any(e.type == ValidationIssueType.TRAVEL_CONFLICT for e in validation_conflicted.errors)

    # -------------------------------------------------------------------------
    # 7. Compare Original Plan vs Modified Replanned Plan via Diff Engine
    # -------------------------------------------------------------------------
    # In modified plan, Golconda is moved to Day 2 and upgraded hotel in Goa
    replanned_item2 = item2.model_copy(
        update={"day_number": 2, "scheduled_date": date(2026, 11, 2), "start_time": "10:00", "end_time": "13:00"}
    )
    replanned_items = [item1, replanned_item2, item3, item4]

    diff = diff_engine.compare(
        before_items=itinerary_items,
        after_items=replanned_items,
        before_legs=[leg1, leg2],
        after_legs=[leg1, leg2],
        before_budget_total=budget_result.total,
        after_budget_total=budget_result.total,
    )

    assert len(diff.modified_items) == 1
    assert diff.modified_items[0].item_id == "item-2"
    assert "scheduled_date" in diff.modified_items[0].field_changes
    assert diff.modified_items[0].field_changes["scheduled_date"].before == date(2026, 11, 1)
    assert diff.modified_items[0].field_changes["scheduled_date"].after == date(2026, 11, 2)
