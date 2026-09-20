"""
Unit Tests for Deterministic Plan Diff Engine
Covers all 8 required test scenarios with strongly typed assertions.
"""

import pytest
from datetime import date, datetime
from backend.app.models.entities import (
    ItineraryItem,
    TransportLeg,
    ItemType,
    ItemStatus,
    TransportMode,
    TransportLegStatus,
)
from backend.app.core.diff_engine import diff_engine


@pytest.fixture
def base_items():
    return [
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
            status=ItemStatus.PLANNED,
            travel_distance_km=8.5,
        ),
        ItineraryItem(
            id="item-2",
            trip_stop_id="stop-1",
            item_type=ItemType.PLACE,
            custom_title="Charminar",
            day_number=1,
            scheduled_date=date(2026, 10, 1),
            start_time="14:00",
            end_time="16:00",
            cost=25.0,
            status=ItemStatus.PLANNED,
            travel_distance_km=4.2,
        ),
    ]


@pytest.fixture
def base_legs():
    return [
        TransportLeg(
            id="91696f38-62e4-5ad2-9987-74896bcdfa7c",
            trip_id="trip-1",
            origin_stop_id="stop-1",
            destination_stop_id="stop-2",
            mode=TransportMode.TRAIN,
            departure_time=datetime(2026, 10, 2, 21, 0),
            arrival_time=datetime(2026, 10, 3, 6, 0),
            cost=650.0,
            status=TransportLegStatus.SCHEDULED,
        )
    ]


# 1. Identical Plans
def test_diff_identical_plans(base_items, base_legs):
    result = diff_engine.compare(
        before_items=base_items,
        after_items=base_items,
        before_legs=base_legs,
        after_legs=base_legs,
        before_budget_total=25000.0,
        after_budget_total=25000.0,
    )
    assert len(result.added_items) == 0
    assert len(result.removed_items) == 0
    assert len(result.modified_items) == 0
    assert len(result.unchanged_items) == 2
    assert result.budget_delta == 0.0
    assert result.travel_distance_delta_km == 0.0
    assert "No changes detected" in result.summary


# 2. Added Activity
def test_diff_added_activity(base_items):
    new_item = ItineraryItem(
        id="item-3",
        trip_stop_id="stop-1",
        custom_title="Chowmahalla Palace",
        day_number=1,
        scheduled_date=date(2026, 10, 1),
        start_time="16:30",
        end_time="18:00",
        cost=100.0,
    )
    after_items = base_items + [new_item]

    result = diff_engine.compare(
        before_items=base_items,
        after_items=after_items,
        before_budget_total=1000.0,
        after_budget_total=1100.0,
    )
    assert len(result.added_items) == 1
    assert result.added_items[0]["id"] == "item-3"
    assert "1 activity added" in result.summary


# 3. Removed Activity
def test_diff_removed_activity(base_items):
    after_items = [base_items[0]] # Removed item-2

    result = diff_engine.compare(
        before_items=base_items,
        after_items=after_items,
        before_budget_total=1000.0,
        after_budget_total=975.0,
    )
    assert len(result.removed_items) == 1
    assert result.removed_items[0]["id"] == "item-2"
    assert "1 activity removed" in result.summary


# 4. Time Modification
def test_diff_time_modification(base_items):
    modified_item = base_items[0].model_copy(
        update={"start_time": "10:00", "end_time": "13:00"}
    )
    after_items = [modified_item, base_items[1]]

    result = diff_engine.compare(
        before_items=base_items,
        after_items=after_items,
    )
    assert len(result.modified_items) == 1
    assert result.modified_items[0].item_id == "item-1"
    changes = result.modified_items[0].field_changes
    assert "start_time" in changes
    assert changes["start_time"].before == "09:30"
    assert changes["start_time"].after == "10:00"


# 5. Transport Modification
def test_diff_transport_modification(base_items, base_legs):
    modified_leg = base_legs[0].model_copy(
        update={"mode": TransportMode.FLIGHT, "cost": 3200.0}
    )
    result = diff_engine.compare(
        before_items=base_items,
        after_items=base_items,
        before_legs=base_legs,
        after_legs=[modified_leg],
        before_budget_total=5000.0,
        after_budget_total=7550.0,
    )
    assert len(result.modified_legs) == 1
    assert result.modified_legs[0].leg_id == "91696f38-62e4-5ad2-9987-74896bcdfa7c"
    leg_changes = result.modified_legs[0].field_changes
    assert leg_changes["mode"].before == TransportMode.TRAIN
    assert leg_changes["mode"].after == TransportMode.FLIGHT
    assert leg_changes["cost"].before == 650.0
    assert leg_changes["cost"].after == 3200.0


# 6. Status Modification
def test_diff_status_modification(base_items):
    rescheduled_item = base_items[0].model_copy(
        update={"status": ItemStatus.RESCHEDULED}
    )
    after_items = [rescheduled_item, base_items[1]]

    result = diff_engine.compare(
        before_items=base_items,
        after_items=after_items,
    )
    assert len(result.modified_items) == 1
    assert result.modified_items[0].field_changes["status"].before == ItemStatus.PLANNED
    assert result.modified_items[0].field_changes["status"].after == ItemStatus.RESCHEDULED


# 7. Budget Delta
def test_diff_budget_delta(base_items):
    result = diff_engine.compare(
        before_items=base_items,
        after_items=base_items,
        before_budget_total=25000.0,
        after_budget_total=22500.0,
    )
    assert result.budget_before == 25000.0
    assert result.budget_after == 22500.0
    assert result.budget_delta == -2500.0
    assert "budget decreased by ₹2,500.00" in result.summary


# 8. Multiple Simultaneous Changes
def test_diff_multiple_simultaneous_changes(base_items, base_legs):
    # 1 item modified, 1 item removed, 1 item added, 1 leg modified
    item_mod = base_items[0].model_copy(update={"cost": 50.0})
    item_new = ItineraryItem(
        id="item-new",
        trip_stop_id="stop-1",
        custom_title="New Museum",
        scheduled_date=date(2026, 10, 1),
        start_time="17:00",
        end_time="18:30",
        cost=150.0,
    )
    after_items = [item_mod, item_new] # item-2 removed

    leg_mod = base_legs[0].model_copy(update={"status": TransportLegStatus.DELAYED})

    result = diff_engine.compare(
        before_items=base_items,
        after_items=after_items,
        before_legs=base_legs,
        after_legs=[leg_mod],
        before_budget_total=10000.0,
        after_budget_total=10175.0,
    )

    assert len(result.added_items) == 1
    assert len(result.removed_items) == 1
    assert len(result.modified_items) == 1
    assert len(result.modified_legs) == 1
    assert result.budget_delta == 175.0
