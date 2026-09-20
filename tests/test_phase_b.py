"""
Phase B tests — Date/Duration, Hotel Update, Activity Validation

Covers:
- nights = duration_days - 1 for same-day, 2-day, 7-day, 11-day trips
- end_date before start_date raises validation error
- hotel update preserves itinerary items; only first-item travel fields change
- hotel update with wrong destination raises ValueError
- validate_activity_candidate feasible path
- validate_activity_candidate infeasible (overlap) with suggestions returned
- validate_activity_candidate with invalid time format
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.db.supabase_client import get_db

client = TestClient(app)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _plan_trip(destinations=None, start="2027-01-10", end="2027-01-16", budget=30000):
    payload = {
        "destinations": destinations or ["Hyderabad"],
        "start_date": start,
        "end_date": end,
        "budget": budget,
        "travelers": 2,
        "interests": ["Heritage", "Food"],
        "preferences": {},
    }
    r = client.post("/api/trips/plan", json=payload)
    assert r.status_code == 201, f"Plan failed: {r.text}"
    return r.json()


# ===========================================================================
# 1. NIGHTS FIELD
# ===========================================================================

class TestNightsField:
    def test_same_day_trip_zero_nights(self):
        trip = _plan_trip(start="2027-09-09", end="2027-09-09")
        assert trip["duration_days"] == 1
        assert trip["nights"] == 0

    def test_two_day_trip(self):
        trip = _plan_trip(start="2027-09-09", end="2027-09-10")
        assert trip["duration_days"] == 2
        assert trip["nights"] == 1

    def test_seven_day_trip(self):
        trip = _plan_trip(start="2027-09-09", end="2027-09-15")
        assert trip["duration_days"] == 7
        assert trip["nights"] == 6

    def test_eleven_day_trip(self):
        trip = _plan_trip(start="2027-09-10", end="2027-09-20")
        assert trip["duration_days"] == 11
        assert trip["nights"] == 10

    def test_nights_invariant(self):
        trip = _plan_trip(start="2027-03-01", end="2027-03-05")
        assert trip["nights"] == trip["duration_days"] - 1

    def test_itinerary_has_exactly_duration_days(self):
        trip = _plan_trip(start="2027-09-09", end="2027-09-15")
        day_numbers = sorted({item["day_number"] for item in trip["itinerary"]})
        assert len(day_numbers) == 7, f"Expected 7 days, got {len(day_numbers)}: {day_numbers}"
        assert day_numbers[0] == 1
        assert day_numbers[-1] == 7

    def test_two_day_itinerary_has_two_days(self):
        trip = _plan_trip(start="2027-10-01", end="2027-10-02")
        day_numbers = sorted({item["day_number"] for item in trip["itinerary"]})
        assert 1 in day_numbers
        assert 2 in day_numbers
        assert len(day_numbers) == 2

    def test_invalid_end_before_start_rejected(self):
        payload = {
            "destinations": ["Hyderabad"],
            "start_date": "2027-09-15",
            "end_date": "2027-09-10",
            "budget": 10000,
            "travelers": 1,
            "preferences": {},
        }
        r = client.post("/api/trips/plan", json=payload)
        assert r.status_code in (400, 422), f"Expected 400/422, got {r.status_code}: {r.text}"

    def test_nights_in_get_trip(self):
        trip = _plan_trip(start="2027-05-01", end="2027-05-03")
        r = client.get(f"/api/trips/{trip['id']}")
        assert r.status_code == 200
        data = r.json()
        assert "nights" in data
        assert data["nights"] == data["duration_days"] - 1


# ===========================================================================
# 2. HOTEL UPDATE
# ===========================================================================

class TestHotelUpdate:
    def _second_hotel(self, trip):
        db = get_db()
        stop = trip["stops"][0]
        current_id = stop["hotel"]["id"] if stop.get("hotel") else None
        dest_id = stop["destination_id"]
        hotels = db.search_hotels(dest_id)
        if not hotels:
            pytest.skip("No hotels seeded.")
        return next((h for h in hotels if h.id != current_id), hotels[0])

    def test_hotel_id_changes(self):
        trip = _plan_trip(start="2027-06-01", end="2027-06-03")
        new_hotel = self._second_hotel(trip)
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": new_hotel.id})
        assert r.status_code == 200, r.text
        assert r.json()["stops"][0]["hotel"]["id"] == new_hotel.id

    def test_itinerary_count_preserved(self):
        trip = _plan_trip(start="2027-06-01", end="2027-06-05")
        count_before = len(trip["itinerary"])
        new_hotel = self._second_hotel(trip)
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": new_hotel.id})
        assert r.status_code == 200
        assert len(r.json()["itinerary"]) == count_before

    def test_non_first_items_unchanged(self):
        trip = _plan_trip(start="2027-07-01", end="2027-07-04")
        new_hotel = self._second_hotel(trip)
        from collections import defaultdict
        by_day = defaultdict(list)
        for item in sorted(trip["itinerary"], key=lambda x: (x["day_number"], x["start_time"])):
            by_day[item["day_number"]].append(item)
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": new_hotel.id})
        assert r.status_code == 200
        by_id = {it["id"]: it for it in r.json()["itinerary"]}
        for day_items in by_day.values():
            for orig in day_items[1:]:
                upd = by_id[orig["id"]]
                assert upd["start_time"] == orig["start_time"]
                assert upd["place_id"] == orig["place_id"]

    def test_first_item_travel_distance_set(self):
        trip = _plan_trip(start="2027-08-01", end="2027-08-03")
        new_hotel = self._second_hotel(trip)
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": new_hotel.id})
        assert r.status_code == 200
        from collections import defaultdict
        by_day = defaultdict(list)
        for it in sorted(r.json()["itinerary"], key=lambda x: (x["day_number"], x["start_time"])):
            by_day[it["day_number"]].append(it)
        for day_items in by_day.values():
            assert day_items[0]["travel_distance_km"] >= 0.0

    def test_nights_returned_after_hotel_update(self):
        trip = _plan_trip(start="2027-11-01", end="2027-11-04")
        new_hotel = self._second_hotel(trip)
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": new_hotel.id})
        assert r.status_code == 200
        data = r.json()
        assert data["nights"] == data["duration_days"] - 1

    def test_wrong_destination_rejected(self):
        trip = _plan_trip(destinations=["Hyderabad"], start="2027-12-01", end="2027-12-03")
        dest_id = trip["stops"][0]["destination_id"]
        db = get_db()
        alien = next((h for h in db.hotels.values() if h.destination_id != dest_id), None)
        if alien is None:
            pytest.skip("Only one destination seeded.")
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": alien.id})
        assert r.status_code == 400

    def test_nonexistent_hotel_rejected(self):
        trip = _plan_trip(start="2027-12-10", end="2027-12-12")
        r = client.post(f"/api/trips/{trip['id']}/hotel", json={"hotel_id": "no-such-hotel"})
        assert r.status_code == 400

    def test_nonexistent_trip_rejected(self):
        r = client.post("/api/trips/fake-trip-id/hotel", json={"hotel_id": "any"})
        assert r.status_code == 404


# ===========================================================================
# 3. ACTIVITY VALIDATE (DRY-RUN)
# ===========================================================================

class TestActivityValidate:
    def _make_trip(self):
        trip = _plan_trip(start="2027-03-10", end="2027-03-14")
        return trip, trip["id"]

    def test_free_slot_feasible(self):
        trip, tid = self._make_trip()
        r = client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1, "start_time": "18:00", "end_time": "19:30",
            "custom_title": "Evening Walk",
        })
        assert r.status_code == 200
        assert r.json()["feasible"] is True

    def test_overlapping_infeasible(self):
        trip, tid = self._make_trip()
        r = client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1, "start_time": "10:30", "end_time": "12:00",
            "custom_title": "Overlapping Visit",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["feasible"] is False
        assert len(data["issues"]) > 0

    def test_infeasible_provides_suggestions(self):
        trip, tid = self._make_trip()
        r = client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1, "start_time": "10:00", "end_time": "12:00",
            "custom_title": "Full Overlap",
        })
        assert r.status_code == 200
        data = r.json()
        assert data["feasible"] is False
        assert isinstance(data["suggestions"], list)

    def test_end_before_start_infeasible(self):
        trip, tid = self._make_trip()
        r = client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1, "start_time": "15:00", "end_time": "13:00",
            "custom_title": "Reversed",
        })
        assert r.status_code == 200
        assert r.json()["feasible"] is False

    def test_does_not_mutate_trip(self):
        trip, tid = self._make_trip()
        original_count = len(trip["itinerary"])
        client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1, "start_time": "18:00", "end_time": "19:00",
            "custom_title": "Ghost",
        })
        r2 = client.get(f"/api/trips/{tid}")
        assert len(r2.json()["itinerary"]) == original_count

    def test_nonexistent_trip_404(self):
        r = client.post("/api/trips/no-such-trip/activity/validate", json={
            "day_number": 1, "start_time": "10:00", "end_time": "11:00",
        })
        assert r.status_code == 404

    def test_place_id_venue_hours_respected(self):
        trip, tid = self._make_trip()
        db = get_db()
        if not db.places:
            pytest.skip("No places seeded.")
        place = next(iter(db.places.values()))
        r = client.post(f"/api/trips/{tid}/activity/validate", json={
            "day_number": 1,
            "start_time": place.open_time[:5],
            "end_time": place.close_time[:5],
            "place_id": place.id,
        })
        assert r.status_code == 200
        hour_issues = [i for i in r.json()["issues"] if "opens at" in i or "closes at" in i]
        assert hour_issues == []
