"""
Unit Tests for Deterministic Budget Engine
Covers all 10 required test scenarios with strongly typed assertions.
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
    HotelTier,
    TransportMode,
    ItemType,
)
from backend.app.core.budget_engine import budget_engine


@pytest.fixture
def sample_destination():
    return Destination(
        id="99852cd9-2775-52f3-8fe0-0a26c43a6c09",
        name="Hyderabad",
        latitude=17.3850,
        longitude=78.4867,
        average_daily_cost=3000.0,
    )


# 1. Empty Itinerary
def test_budget_empty_itinerary():
    result = budget_engine.calculate(total_budget=20000.0)
    assert result.total == 0.0
    assert result.budget == 20000.0
    assert result.remaining == 20000.0
    assert result.variance == -20000.0
    assert result.percentage_used == 0.0
    assert result.within_budget is True
    assert len(result.daily_breakdowns) == 0


# 2. Single-City Trip
def test_budget_single_city_trip(sample_destination: Destination):
    stop = TripStop(
        id="stop-1",
        trip_id="trip-1",
        destination_id=sample_destination.id,
        order_index=0,
        arrival_date=date(2026, 10, 1),
        departure_date=date(2026, 10, 4), # 3 nights, 4 calendar days (Oct 1, 2, 3, 4)
    )
    hotel = Hotel(
        id="61f90f03-e97c-5587-9dac-1a7070681dcc",
        destination_id=sample_destination.id,
        name="Marigold Hotel",
        tier=HotelTier.MID_RANGE,
        price_per_night=3000.0,
        latitude=17.4338,
        longitude=78.4552,
    )
    items = [
        ItineraryItem(
            id="item-1",
            trip_stop_id="stop-1",
            item_type=ItemType.PLACE,
            custom_title="Golconda Fort",
            day_number=1,
            scheduled_date=date(2026, 10, 1),
            start_time="09:30",
            end_time="12:30",
            cost=25.0,
        ),
        ItineraryItem(
            id="item-2",
            trip_stop_id="stop-1",
            item_type=ItemType.PLACE,
            custom_title="Chowmahalla Palace",
            day_number=2,
            scheduled_date=date(2026, 10, 2),
            start_time="10:00",
            end_time="12:00",
            cost=100.0,
        ),
    ]

    result = budget_engine.calculate(
        total_budget=25000.0,
        traveler_count=1,
        trip_stops=[stop],
        hotels_by_stop={stop.id: hotel},
        itinerary_items=items,
        destinations_by_stop={stop.id: sample_destination},
        daily_food_estimate_per_person=500.0,
        daily_local_transit_estimate_per_person=200.0,
    )

    # 3 nights * 3000 = 9000 accommodation
    assert result.accommodation == 9000.0
    # 25 + 100 = 125 activities
    assert result.activities == 125.0
    # 4 days * 500 = 2000 food
    assert result.food == 2000.0
    # 4 days * 200 = 800 local transit
    assert result.local_transport == 800.0
    # Total = 9000 + 125 + 2000 + 800 = 11925.0
    assert result.total == 11925.0
    assert result.within_budget is True
    assert result.remaining == 13075.0
    assert len(result.daily_breakdowns) == 4


# 3. Multi-City Trip
def test_budget_multi_city_trip():
    dest1 = Destination(id="d1", name="Hyderabad", latitude=17.38, longitude=78.48)
    dest2 = Destination(id="d2", name="Hampi", latitude=15.33, longitude=76.46)

    stop1 = TripStop(id="s1", trip_id="t1", destination_id="d1", order_index=0, arrival_date=date(2026, 10, 1), departure_date=date(2026, 10, 2))
    stop2 = TripStop(id="s2", trip_id="t1", destination_id="d2", order_index=1, arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 4))

    hotel1 = Hotel(id="h1", destination_id="d1", name="H1", price_per_night=2000.0, latitude=17.38, longitude=78.48)
    hotel2 = Hotel(id="h2", destination_id="d2", name="H2", price_per_night=1500.0, latitude=15.33, longitude=76.46)

    leg = TransportLeg(
        id="91696f38-62e4-5ad2-9987-74896bcdfa7c",
        trip_id="t1",
        origin_stop_id="s1",
        destination_stop_id="s2",
        mode=TransportMode.TRAIN,
        departure_time=datetime(2026, 10, 2, 21, 0),
        arrival_time=datetime(2026, 10, 3, 6, 0),
        cost=650.0,
    )

    result = budget_engine.calculate(
        total_budget=30000.0,
        traveler_count=1,
        trip_stops=[stop1, stop2],
        hotels_by_stop={"s1": hotel1, "s2": hotel2},
        transport_legs=[leg],
        destinations_by_stop={"s1": dest1, "s2": dest2},
        daily_food_estimate_per_person=400.0,
        daily_local_transit_estimate_per_person=150.0,
    )

    # Accommodation: (1 night * 2000) + (1 night * 1500) = 3500
    assert result.accommodation == 3500.0
    # Intercity: 650
    assert result.intercity_transport == 650.0
    assert result.within_budget is True


# 4. Multiple Travelers
def test_budget_multiple_travelers():
    stop = TripStop(id="s1", trip_id="t1", destination_id="d1", order_index=0, arrival_date=date(2026, 10, 1), departure_date=date(2026, 10, 2))
    hotel = Hotel(id="h1", destination_id="d1", name="H1", price_per_night=4000.0, latitude=17.38, longitude=78.48)
    leg = TransportLeg(id="l1", trip_id="t1", origin_stop_id="s1", destination_stop_id="s1", mode=TransportMode.FLIGHT, departure_time=datetime(2026, 10, 1, 10, 0), arrival_time=datetime(2026, 10, 1, 12, 0), cost=3000.0)

    # 4 travelers -> 2 rooms, 4 tickets
    result = budget_engine.calculate(
        total_budget=50000.0,
        traveler_count=4,
        trip_stops=[stop],
        hotels_by_stop={"s1": hotel},
        transport_legs=[leg],
        daily_food_estimate_per_person=600.0,
        daily_local_transit_estimate_per_person=200.0,
    )

    # Accommodation: 1 night * 4000 * 2 rooms = 8000
    assert result.accommodation == 8000.0
    # Intercity: 3000 * 4 = 12000
    assert result.intercity_transport == 12000.0
    assert result.traveler_count == 4
    assert result.cost_per_traveler == round(result.total / 4, 2)


# 5. Within Budget
def test_budget_within_budget():
    result = budget_engine.calculate(
        total_budget=10000.0,
        miscellaneous_cost=4000.0
    )
    assert result.within_budget is True
    assert result.remaining == 6000.0
    assert result.variance == -6000.0


# 6. Exactly At Budget
def test_budget_exactly_at_budget():
    result = budget_engine.calculate(
        total_budget=5000.0,
        miscellaneous_cost=5000.0
    )
    assert result.total == 5000.0
    assert result.remaining == 0.0
    assert result.variance == 0.0
    assert result.percentage_used == 100.0
    assert result.within_budget is True


# 7. Over Budget
def test_budget_over_budget():
    result = budget_engine.calculate(
        total_budget=5000.0,
        miscellaneous_cost=7500.0
    )
    assert result.total == 7500.0
    assert result.remaining == -2500.0
    assert result.variance == 2500.0
    assert result.percentage_used == 150.0
    assert result.within_budget is False


# 8. Budget Percentage Calculation
def test_budget_percentage_calculation():
    result = budget_engine.calculate(
        total_budget=40000.0,
        miscellaneous_cost=30000.0
    )
    assert result.percentage_used == 75.0


# 9. Daily Breakdown Integrity
def test_budget_daily_breakdown():
    stop = TripStop(id="s1", trip_id="t1", destination_id="d1", order_index=0, arrival_date=date(2026, 10, 1), departure_date=date(2026, 10, 3))
    result = budget_engine.calculate(
        total_budget=20000.0,
        trip_stops=[stop],
        daily_food_estimate_per_person=500.0,
        daily_local_transit_estimate_per_person=200.0,
    )
    assert len(result.daily_breakdowns) == 3
    for day in result.daily_breakdowns:
        assert day.food_cost == 500.0
        assert day.local_transport_cost == 200.0
        assert day.total_cost >= 700.0


# 10. Missing Optional Costs (Zero Handling)
def test_budget_missing_optional_costs():
    result = budget_engine.calculate(
        total_budget=15000.0,
        trip_stops=[],
        hotels_by_stop=None,
        transport_legs=None,
        itinerary_items=None,
    )
    assert result.total == 0.0
    assert result.within_budget is True
