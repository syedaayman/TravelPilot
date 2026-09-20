"""
TravelPilot Deterministic Schedule & Conflict Validator
Validates time ranges, overlaps, opening/closing hours, closed days,
inter-item transit buffers, trip stop date bounds, and inter-city transport conflicts.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import date, time, datetime, timedelta
import re

from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Place,
    Restaurant,
    ItemType,
)
from backend.app.core.models import (
    ScheduleValidationResult,
    ValidationIssue,
    ValidationIssueType,
    ValidationSeverity,
)


def parse_time_str(t: str) -> time:
    """Parses 'HH:MM:SS' or 'HH:MM' string into time object."""
    if isinstance(t, time):
        return t
    parts = str(t).strip().split(":")
    hours = int(parts[0])
    minutes = int(parts[1]) if len(parts) > 1 else 0
    seconds = int(parts[2]) if len(parts) > 2 else 0
    return time(hour=hours, minute=minutes, second=seconds)


def time_to_minutes(t: time) -> int:
    return t.hour * 60 + t.minute


def date_to_schema_day(d: date) -> int:
    """
    Converts Python date (0=Monday..6=Sunday) to Schema day (0=Sunday, 1=Monday..6=Saturday).
    """
    return (d.weekday() + 1) % 7


class ScheduleValidator:
    @staticmethod
    def validate(
        trip: Optional[Trip] = None,
        trip_stops: Optional[List[TripStop]] = None,
        itinerary_items: Optional[List[ItineraryItem]] = None,
        transport_legs: Optional[List[TransportLeg]] = None,
        places_by_id: Optional[Dict[str, Place]] = None,
        restaurants_by_id: Optional[Dict[str, Restaurant]] = None,
        minimum_transit_buffer_minutes: int = 10,
    ) -> ScheduleValidationResult:
        """
        Validates entire itinerary and inter-city transit deterministically.
        Returns structured ScheduleValidationResult with errors and warnings.
        """
        errors: List[ValidationIssue] = []
        warnings: List[ValidationIssue] = []

        trip_stops = trip_stops or []
        itinerary_items = itinerary_items or []
        transport_legs = transport_legs or []
        places_by_id = places_by_id or {}
        restaurants_by_id = restaurants_by_id or {}

        stops_by_id = {s.id: s for s in trip_stops}

        # 1. Validate Trip Stops Boundary & Trip Dates
        if trip:
            for stop in trip_stops:
                if stop.arrival_date < trip.start_date or stop.departure_date > trip.end_date:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.STOP_BOUNDARY_VIOLATION,
                            severity=ValidationSeverity.ERROR,
                            message=f"TripStop dates ({stop.arrival_date} - {stop.departure_date}) exceed trip bounds ({trip.start_date} - {trip.end_date}).",
                            suggested_fix="Adjust trip stop arrival/departure dates to fall within overall trip dates.",
                        )
                    )

        # 2. Group items by scheduled_date
        items_by_date: Dict[date, List[ItineraryItem]] = {}
        for item in itinerary_items:
            items_by_date.setdefault(item.scheduled_date, []).append(item)

        # 3. Validate Each Item Individually
        for item in itinerary_items:
            # 3.1 Start / End time validity
            try:
                start_t = parse_time_str(item.start_time)
                end_t = parse_time_str(item.end_time)
            except Exception as e:
                errors.append(
                    ValidationIssue(
                        type=ValidationIssueType.INVALID_TIME_RANGE,
                        severity=ValidationSeverity.ERROR,
                        item_id=item.id,
                        day_number=item.day_number,
                        message=f"Invalid time format in item: {item.start_time} - {item.end_time}.",
                    )
                )
                continue

            start_m = time_to_minutes(start_t)
            end_m = time_to_minutes(end_t)

            if end_m <= start_m:
                errors.append(
                    ValidationIssue(
                        type=ValidationIssueType.INVALID_TIME_RANGE,
                        severity=ValidationSeverity.ERROR,
                        item_id=item.id,
                        day_number=item.day_number,
                        message=f"Item end time ({item.end_time}) must be strictly after start time ({item.start_time}).",
                        suggested_fix="Adjust start or end time so end time is greater than start time.",
                    )
                )

            # 3.2 TripStop boundary check
            stop = stops_by_id.get(item.trip_stop_id)
            if stop:
                if item.scheduled_date < stop.arrival_date or item.scheduled_date > stop.departure_date:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.STOP_BOUNDARY_VIOLATION,
                            severity=ValidationSeverity.ERROR,
                            item_id=item.id,
                            day_number=item.day_number,
                            message=f"Item date {item.scheduled_date} is outside stop duration ({stop.arrival_date} to {stop.departure_date}).",
                            suggested_fix="Reschedule item to a date when traveler is at this destination.",
                        )
                    )

            # 3.3 Venue Opening / Closing Hours & Closed Days Check
            if item.place_id and item.place_id in places_by_id:
                place = places_by_id[item.place_id]
                schema_day = date_to_schema_day(item.scheduled_date)

                # Check Closed Day
                if schema_day in place.closed_days:
                    day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                    day_name = day_names[schema_day]
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.VENUE_CLOSED_DAY,
                            severity=ValidationSeverity.ERROR,
                            item_id=item.id,
                            day_number=item.day_number,
                            message=f"'{place.name}' is closed on {day_name}s.",
                            suggested_fix=f"Move '{place.name}' to another day or select an alternative activity.",
                        )
                    )

                # Check Opening / Closing Hours
                open_t = parse_time_str(place.open_time)
                close_t = parse_time_str(place.close_time)
                open_m = time_to_minutes(open_t)
                close_m = time_to_minutes(close_t)

                if start_m < open_m:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.VENUE_CLOSED_HOURS,
                            severity=ValidationSeverity.ERROR,
                            item_id=item.id,
                            day_number=item.day_number,
                            message=f"'{place.name}' opens at {place.open_time}, but is scheduled to start at {item.start_time}.",
                            suggested_fix=f"Shift start time to {place.open_time} or later.",
                        )
                    )

                if end_m > close_m:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.VENUE_CLOSED_HOURS,
                            severity=ValidationSeverity.ERROR,
                            item_id=item.id,
                            day_number=item.day_number,
                            message=f"'{place.name}' closes at {place.close_time}, but is scheduled until {item.end_time}.",
                            suggested_fix=f"Shorten duration or start earlier so activity ends by {place.close_time}.",
                        )
                    )

            elif item.restaurant_id and item.restaurant_id in restaurants_by_id:
                rest = restaurants_by_id[item.restaurant_id]
                open_t = parse_time_str(rest.open_time)
                close_t = parse_time_str(rest.close_time)
                open_m = time_to_minutes(open_t)
                close_m = time_to_minutes(close_t)

                if start_m < open_m or end_m > close_m:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.VENUE_CLOSED_HOURS,
                            severity=ValidationSeverity.ERROR,
                            item_id=item.id,
                            day_number=item.day_number,
                            message=f"'{rest.name}' operating hours are {rest.open_time} - {rest.close_time}, but scheduled at {item.start_time} - {item.end_time}.",
                            suggested_fix=f"Adjust dining slot to within {rest.open_time} - {rest.close_time}.",
                        )
                    )

        # 4. Intra-Day Sequence & Travel Buffer Validation
        for s_date, day_items in items_by_date.items():
            # Sort items by start_time
            sorted_items = sorted(day_items, key=lambda x: time_to_minutes(parse_time_str(x.start_time)))

            for i in range(len(sorted_items) - 1):
                item_a = sorted_items[i]
                item_b = sorted_items[i + 1]

                end_a = time_to_minutes(parse_time_str(item_a.end_time))
                start_b = time_to_minutes(parse_time_str(item_b.start_time))

                # Direct overlap check
                if end_a > start_b:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.OVERLAP,
                            severity=ValidationSeverity.ERROR,
                            item_id=item_a.id,
                            conflicting_item_id=item_b.id,
                            day_number=item_a.day_number,
                            message=f"Schedule overlap: Item ends at {item_a.end_time} while next item starts at {item_b.start_time}.",
                            suggested_fix="Reschedule one of the items to eliminate overlap.",
                        )
                    )
                    continue

                # Travel time conflict check
                required_travel = item_b.travel_time_from_prev_minutes or 0
                available_gap = start_b - end_a

                if available_gap < required_travel:
                    errors.append(
                        ValidationIssue(
                            type=ValidationIssueType.TRAVEL_CONFLICT,
                            severity=ValidationSeverity.ERROR,
                            item_id=item_a.id,
                            conflicting_item_id=item_b.id,
                            day_number=item_a.day_number,
                            message=f"Insufficient travel time between activities. Requires {required_travel} mins, but only {available_gap} mins available.",
                            suggested_fix=f"Delay second activity start time by at least {required_travel - available_gap} minutes.",
                        )
                    )
                elif available_gap < (required_travel + minimum_transit_buffer_minutes) and required_travel > 0:
                    warnings.append(
                        ValidationIssue(
                            type=ValidationIssueType.INSUFFICIENT_BUFFER,
                            severity=ValidationSeverity.WARNING,
                            item_id=item_a.id,
                            conflicting_item_id=item_b.id,
                            day_number=item_a.day_number,
                            message=f"Tight transit buffer ({available_gap} mins for {required_travel} min travel).",
                            suggested_fix="Consider adding a 10-15 minute buffer for traffic delays.",
                        )
                    )

        # 5. Inter-City Transport Leg Conflicts
        for leg in transport_legs:
            leg_dep = leg.departure_time
            leg_arr = leg.arrival_time
            leg_date = leg_dep.date()

            # Find items on the same day as inter-city travel
            if leg_date in items_by_date:
                for item in items_by_date[leg_date]:
                    item_start_dt = datetime.combine(item.scheduled_date, parse_time_str(item.start_time))
                    item_end_dt = datetime.combine(item.scheduled_date, parse_time_str(item.end_time))

                    # If item overlaps with transit leg
                    if not (item_end_dt <= leg_dep or item_start_dt >= leg_arr):
                        errors.append(
                            ValidationIssue(
                                type=ValidationIssueType.TRANSPORT_CONFLICT,
                                severity=ValidationSeverity.ERROR,
                                item_id=item.id,
                                day_number=item.day_number,
                                message=f"Activity '{item.custom_title or 'Activity'}' conflicts with inter-city transport ({leg.mode.value} {leg_dep.strftime('%H:%M')} - {leg_arr.strftime('%H:%M')}).",
                                suggested_fix="Schedule activity before departure or after arrival.",
                            )
                        )

        is_valid = len(errors) == 0

        return ScheduleValidationResult(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )


schedule_validator = ScheduleValidator()
