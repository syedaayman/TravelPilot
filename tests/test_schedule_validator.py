"""
Unit Tests for Deterministic Schedule & Conflict Validator
Covers all 10 required test scenarios with strongly typed assertions.
"""

import pytest
from datetime import date, datetime
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Place,
    Restaurant,
    ItemType,
    TransportMode,
)
from backend.app.core.schedule_validator import schedule_validator
from backend.app.core.models import ValidationIssueType, ValidationSeverity


@pytest.fixture
def places_catalog():
    # Salar Jung Museum closed on Friday (5 in schema: 0=Sun..5=Fri..6=Sat)
    # Friday 2026-10-02 -> weekday() = 4 -> schema day = 5 (Closed!)
    # Saturday 2026-10-03 -> weekday() = 5 -> schema day = 6 (Open!)
    salar_jung = Place(
        id="p-salar",
        destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4",
        name="Salar Jung Museum",
        category="museum",
        latitude=17.3713,
        longitude=78.4804,
        open_time="10:00:00",
        close_time="17:00:00",
        closed_days=[5], # Friday
    )
    golconda = Place(
        id="p-golconda",
        destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4",
        name="Golconda Fort",
        category="historical",
        latitude=17.3833,
        longitude=78.4011,
        open_time="09:00:00",
        close_time="17:30:00",
        closed_days=[],
    )
    return {"p-salar": salar_jung, "p-golconda": golconda}


# 1. Valid Schedule
def test_schedule_valid(places_catalog):
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    # Saturday Oct 3, 2026
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            place_id="p-salar",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="10:30",
            end_time="12:30",
        ),
        ItineraryItem(
            id="i2",
            trip_stop_id="s1",
            place_id="p-golconda",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="14:00",
            end_time="17:00",
            travel_time_from_prev_minutes=30,
        ),
    ]

    result = schedule_validator.validate(
        trip_stops=[stop],
        itinerary_items=items,
        places_by_id=places_catalog,
    )

    assert result.valid is True
    assert len(result.errors) == 0


# 2. Direct Overlap
def test_schedule_direct_overlap():
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="10:00",
            end_time="12:30",
        ),
        ItineraryItem(
            id="i2",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="12:00", # Overlaps with 10:00-12:30
            end_time="14:00",
        ),
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.OVERLAP for e in result.errors)


# 3. Travel-Time Conflict
def test_schedule_travel_time_conflict():
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="09:00",
            end_time="11:00",
        ),
        ItineraryItem(
            id="i2",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="11:15", # Only 15 mins gap, but requires 35 mins travel
            end_time="13:00",
            travel_time_from_prev_minutes=35,
        ),
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.TRAVEL_CONFLICT for e in result.errors)


# 4. Opening-Time Violation
def test_schedule_opening_time_violation(places_catalog):
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    # Salar Jung opens at 10:00:00, scheduled at 08:30
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            place_id="p-salar",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="08:30",
            end_time="11:00",
        )
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items, places_by_id=places_catalog)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.VENUE_CLOSED_HOURS for e in result.errors)


# 5. Closing-Time Violation
def test_schedule_closing_time_violation(places_catalog):
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    # Salar Jung closes at 17:00:00, scheduled until 18:30
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            place_id="p-salar",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="15:00",
            end_time="18:30",
        )
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items, places_by_id=places_catalog)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.VENUE_CLOSED_HOURS for e in result.errors)


# 6. Closed-Day Violation (Salar Jung on Friday)
def test_schedule_closed_day_violation(places_catalog):
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 2), departure_date=date(2026, 10, 2))
    # Friday Oct 2, 2026 -> Salar Jung is closed!
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            place_id="p-salar",
            day_number=1,
            scheduled_date=date(2026, 10, 2), # Friday
            start_time="11:00",
            end_time="13:00",
        )
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items, places_by_id=places_catalog)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.VENUE_CLOSED_DAY for e in result.errors)


# 7. Invalid Time Range (end <= start)
def test_schedule_invalid_time_range():
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="14:00",
            end_time="13:00", # End before start
        )
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.INVALID_TIME_RANGE for e in result.errors)


# 8. Trip Date Violation / Stop Boundary Violation
def test_schedule_stop_boundary_violation():
    stop = TripStop(
        id="s1",
        trip_id="t1",
        destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4",
        arrival_date=date(2026, 10, 1),
        departure_date=date(2026, 10, 3),
    )
    # Item scheduled on Oct 5 (outside stop duration)
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=5,
            scheduled_date=date(2026, 10, 5),
            start_time="10:00",
            end_time="12:00",
        )
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items)
    assert result.valid is False
    assert any(e.type == ValidationIssueType.STOP_BOUNDARY_VIOLATION for e in result.errors)


# 9. Multi-City Transport Conflict
def test_schedule_transport_conflict():
    stop1 = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 1), departure_date=date(2026, 10, 1))
    leg = TransportLeg(
        id="91696f38-62e4-5ad2-9987-74896bcdfa7c",
        trip_id="t1",
        origin_stop_id="s1",
        destination_stop_id="s1",
        mode=TransportMode.FLIGHT,
        departure_time=datetime(2026, 10, 1, 14, 0),
        arrival_time=datetime(2026, 10, 1, 16, 0),
        cost=3000.0,
    )
    # Activity scheduled during flight time 14:30 - 15:30
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 1),
            start_time="14:30",
            end_time="15:30",
        )
    ]

    result = schedule_validator.validate(
        trip_stops=[stop1],
        itinerary_items=items,
        transport_legs=[leg],
    )
    assert result.valid is False
    assert any(e.type == ValidationIssueType.TRANSPORT_CONFLICT for e in result.errors)


# 10. Warning vs Error Behaviour (Tight buffer creates Warning, not Error)
def test_schedule_warning_vs_error_behaviour():
    stop = TripStop(id="s1", trip_id="t1", destination_id="0f9bb92c-a095-5b32-8de5-1e70194d75a4", arrival_date=date(2026, 10, 3), departure_date=date(2026, 10, 3))
    # Available gap = 11:30 - 11:00 = 30 mins. Travel time = 25 mins.
    # Gap (30) >= travel (25) -> No error! But gap (30) < travel (25) + buffer (10) -> Warning!
    items = [
        ItineraryItem(
            id="i1",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="09:00",
            end_time="11:00",
        ),
        ItineraryItem(
            id="i2",
            trip_stop_id="s1",
            day_number=1,
            scheduled_date=date(2026, 10, 3),
            start_time="11:30",
            end_time="13:00",
            travel_time_from_prev_minutes=25,
        ),
    ]

    result = schedule_validator.validate(trip_stops=[stop], itinerary_items=items)
    # Technically valid (no errors), but emits a Warning for tight buffer
    assert result.valid is True
    assert len(result.errors) == 0
    assert len(result.warnings) == 1
    assert result.warnings[0].type == ValidationIssueType.INSUFFICIENT_BUFFER
    assert result.warnings[0].severity == ValidationSeverity.WARNING
