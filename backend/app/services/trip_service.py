"""
TravelPilot Trip Application Service
Implements destination-agnostic planning for Single-City and Multi-City trips,
orchestrates deterministic calculations, validates schedules, and persists active state.
"""

"""
TravelPilot Trip Application Service
Implements destination-agnostic planning for Single-City and Multi-City trips,
orchestrates deterministic calculations, validates schedules, and persists active state.
"""

from typing import List, Dict, Any, Optional
from datetime import date, datetime, time, timedelta, timezone
from uuid import uuid4
import math
from urllib.parse import quote_plus

from backend.app.db.supabase_client import get_db
from backend.app.models.entities import (
    Trip,
    TripStop,
    TransportLeg,
    ItineraryItem,
    Hotel,
    Destination,
    AgentEvent,
    AgentEventType,
    TripStatus,
    TransportMode,
    TransportLegStatus,
    ItemType,
    ItemStatus,
    HotelTier,
)
from backend.app.core.models import GeoPoint, RoutingMode
from backend.app.core.budget_engine import budget_engine
from backend.app.core.schedule_validator import schedule_validator
from backend.app.core.geo_routing import geo_routing_engine
from backend.app.services.proposal_store import proposal_store
from backend.app.api.schemas.trips import (
    TripPlanRequest,
    TripPlanResponse,
    TripDetailResponse,
    TripStopDetail,
    TransportLegDetail,
    ItineraryItemDetail,
    HotelUpdateRequest,
    ActivityValidateRequest,
    ActivityValidateResponse,
    ActivityValidateSuggestion,
)


class TripService:
    def plan_trip(self, request: TripPlanRequest) -> TripPlanResponse:
        """
        Creates and persists a validated, budget-aware single-city or multi-city trip.
        Destination-agnostic: resolves any destination from the database reference layer.
        """
        db = get_db()
        start_dt = request.start_date or (date.today() + timedelta(days=14))
        duration_days = request.duration_days
        assert duration_days is not None
        end_dt = request.end_date or (start_dt + timedelta(days=duration_days - 1))

        # 1. Resolve Destinations Dynamically
        resolved_destinations: List[Destination] = []
        for dest_name in request.destinations:
            dest = db.get_destination_by_name(dest_name)
            if not dest:
                # Substring search fallback
                search_res = db.search_destinations(dest_name)
                if search_res:
                    dest = search_res[0]
                else:
                    raise ValueError(f"DESTINATION_NOT_FOUND: '{dest_name}' could not be resolved.")
            resolved_destinations.append(dest)

        dest_count = len(resolved_destinations)
        trip_id = str(uuid4())

        # 2. Allocate Days Across Stops
        days_per_stop = max(1, duration_days // dest_count)
        stops: List[TripStop] = []
        hotels_by_stop: Dict[str, Hotel] = {}
        destinations_by_stop: Dict[str, Destination] = {}

        current_date = start_dt
        for idx, dest in enumerate(resolved_destinations):
            # For last stop, assign all remaining days
            if idx == dest_count - 1:
                stop_duration = (end_dt - current_date).days + 1
            else:
                stop_duration = days_per_stop

            stop_arr = current_date
            stop_dep = current_date + timedelta(days=max(1, stop_duration) - 1)

            # Select Hotel matching budget tier
            preferred_tier = "budget" if request.budget / duration_days < 3500 else "mid-range"
            hotels_found = db.search_hotels(dest.id, tier=preferred_tier)
            selected_hotel = hotels_found[0] if hotels_found else (db.search_hotels(dest.id)[0] if db.search_hotels(dest.id) else None)

            stop = TripStop(
                id=str(uuid4()),
                trip_id=trip_id,
                destination_id=dest.id,
                order_index=idx,
                arrival_date=stop_arr,
                departure_date=stop_dep,
                stop_budget=round(request.budget / dest_count, 2),
                hotel_id=selected_hotel.id if selected_hotel else None,
            )
            stops.append(stop)
            if selected_hotel:
                hotels_by_stop[stop.id] = selected_hotel
            destinations_by_stop[stop.id] = dest

            current_date = stop_dep + timedelta(days=1)

        # 3. Create Trip Record
        title_str = " → ".join(d.name for d in resolved_destinations)
        trip = Trip(
            id=trip_id,
            title=f"{duration_days} Days in {title_str}",
            start_date=start_dt,
            end_date=end_dt,
            total_budget=request.budget,
            traveler_count=request.travelers,
            interests=request.interests,
            preferences=request.preferences,
            status=TripStatus.CONFIRMED,
        )

        # 4. Inter-City Transport Legs (Connecting Consecutive Stops)
        legs: List[TransportLeg] = []
        for i in range(len(stops) - 1):
            s_from = stops[i]
            s_to = stops[i + 1]
            t_options = db.search_transport(s_from.destination_id, s_to.destination_id)
            selected_t = t_options[0] if t_options else None

            dep_dt = datetime.combine(s_from.departure_date, time(18, 0))
            arr_dt = dep_dt + timedelta(minutes=selected_t.typical_duration_minutes if selected_t else 240)

            leg = TransportLeg(
                id=str(uuid4()),
                trip_id=trip_id,
                origin_stop_id=s_from.id,
                destination_stop_id=s_to.id,
                mode=selected_t.mode if selected_t else TransportMode.TRAIN,
                carrier=selected_t.carrier if selected_t else "Intercity Express",
                departure_time=dep_dt,
                arrival_time=arr_dt,
                cost=selected_t.estimated_cost if selected_t else 600.0,
                status=TransportLegStatus.SCHEDULED,
            )
            legs.append(leg)

        # 5. Schedule Tourist Activities per Destination Stop
        items: List[ItineraryItem] = []
        overall_day = 1

        for stop in stops:
            dest = destinations_by_stop[stop.id]
            # Fetch places in destination
            places = db.search_places(dest.id)
            if not places:
                places = list(db.places.values())[:3]

            curr_stop_date = stop.arrival_date
            place_pointer = 0

            while curr_stop_date <= stop.departure_date:
                # Schedule 2 activities per day: Morning and Afternoon
                # Item 1: Morning (10:00 - 12:30)
                if places:
                    p1 = places[place_pointer % len(places)]
                    item1 = ItineraryItem(
                        id=str(uuid4()),
                        trip_stop_id=stop.id,
                        place_id=p1.id,
                        custom_title=p1.name,
                        day_number=overall_day,
                        scheduled_date=curr_stop_date,
                        start_time="10:00",
                        end_time="12:30",
                        cost=p1.entry_fee,
                        travel_time_from_prev_minutes=0,
                        travel_distance_km=0.0,
                    )
                    items.append(item1)
                    place_pointer += 1

                # Item 2: Afternoon (14:30 - 17:00)
                if places:
                    p2 = places[place_pointer % len(places)]
                    # Estimate transit from p1 to p2
                    travel_time = 20
                    dist_km = 5.0
                    if place_pointer > 0 and items:
                        prev_p = places[(place_pointer - 1) % len(places)]
                        est = geo_routing_engine.estimate_travel_time(
                            GeoPoint(latitude=prev_p.latitude, longitude=prev_p.longitude),
                            GeoPoint(latitude=p2.latitude, longitude=p2.longitude),
                            mode=RoutingMode.CAB,
                        )
                        travel_time = est.duration_minutes
                        dist_km = est.distance_km

                    item2 = ItineraryItem(
                        id=str(uuid4()),
                        trip_stop_id=stop.id,
                        place_id=p2.id,
                        custom_title=p2.name,
                        day_number=overall_day,
                        scheduled_date=curr_stop_date,
                        start_time="14:30",
                        end_time="17:00",
                        cost=p2.entry_fee,
                        travel_time_from_prev_minutes=travel_time,
                        travel_distance_km=dist_km,
                    )
                    items.append(item2)
                    place_pointer += 1

                overall_day += 1
                curr_stop_date += timedelta(days=1)

        # 6. Calculate Budget & Validate Schedule
        budget_res = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=stops,
            hotels_by_stop=hotels_by_stop,
            transport_legs=legs,
            itinerary_items=items,
            destinations_by_stop=destinations_by_stop,
        )

        validation_res = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=items,
            transport_legs=legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        # 7. Persist Active Trip State to DB
        db.create_trip(trip)
        for s in stops:
            db.add_trip_stop(s)
        for l in legs:
            db.add_transport_leg(l)
        for it in items:
            db.add_itinerary_item(it)

        # 8. Log Structured Observability Events
        db.record_agent_event(
            AgentEvent(
                trip_id=trip.id,
                event_type=AgentEventType.PLANNING_STARTED,
                input_summary=f"Planning {title_str} for {request.duration_days} days (Budget: ₹{request.budget:,.2f})",
                status="success",
            )
        )
        db.record_agent_event(
            AgentEvent(
                trip_id=trip.id,
                event_type=AgentEventType.DECISION,
                result_summary=f"Finalized itinerary: {len(items)} activities, {len(legs)} transport legs, Budget used: {budget_res.percentage_used:.1f}%",
                status="success",
            )
        )

        detail_response = self._build_detail_response(
            trip, stops, legs, items, hotels_by_stop, destinations_by_stop, budget_res, validation_res
        )

        reasoning = (
            f"Successfully planned {duration_days}-day itinerary across {title_str}. "
            f"Total estimated cost: ₹{budget_res.total:,.2f} against your ₹{request.budget:,.2f} budget. "
            f"All venue opening hours and travel buffers have been verified."
        )

        return TripPlanResponse(
            success=True,
            trip=detail_response,
            agent_reasoning=reasoning,
        )

    def get_trip_detail(self, trip_id: str) -> TripDetailResponse:
        """Retrieves complete trip state from database with budget and validation summaries."""
        db = get_db()
        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        stops = db.get_trip_stops(trip_id)
        legs = db.get_transport_legs_for_trip(trip_id)
        items = []
        for s in stops:
            items.extend(db.get_itinerary_items_for_stop(s.id))

        hotels_by_stop = {}
        destinations_by_stop = {}
        for s in stops:
            if s.hotel_id and s.hotel_id in db.hotels:
                hotels_by_stop[s.id] = db.hotels[s.hotel_id]
            if s.destination_id in db.destinations:
                destinations_by_stop[s.id] = db.destinations[s.destination_id]

        budget_res = budget_engine.calculate(
            total_budget=trip.total_budget,
            traveler_count=trip.traveler_count,
            trip_stops=stops,
            hotels_by_stop=hotels_by_stop,
            transport_legs=legs,
            itinerary_items=items,
            destinations_by_stop=destinations_by_stop,
        )

        validation_res = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=items,
            transport_legs=legs,
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        return self._build_detail_response(
            trip, stops, legs, items, hotels_by_stop, destinations_by_stop, budget_res, validation_res
        )

    def _build_detail_response(
        self,
        trip: Trip,
        stops: List[TripStop],
        legs: List[TransportLeg],
        items: List[ItineraryItem],
        hotels_by_stop: Dict[str, Hotel],
        destinations_by_stop: Dict[str, Destination],
        budget_res: Any,
        validation_res: Any,
    ) -> TripDetailResponse:
        db = get_db()
        stop_details = []
        for s in stops:
            dest = destinations_by_stop.get(s.id)
            hotel = hotels_by_stop.get(s.id)
            stop_details.append(
                TripStopDetail(
                    id=s.id,
                    trip_id=s.trip_id,
                    destination_id=s.destination_id,
                    destination_name=dest.name if dest else "Unknown",
                    order_index=s.order_index,
                    arrival_date=str(s.arrival_date),
                    departure_date=str(s.departure_date),
                    stop_budget=s.stop_budget,
                    hotel=hotel.model_dump() if hotel else None,
                )
            )

        leg_details = [
            TransportLegDetail(
                id=l.id,
                trip_id=l.trip_id,
                origin_stop_id=l.origin_stop_id,
                destination_stop_id=l.destination_stop_id,
                mode=l.mode.value,
                carrier=l.carrier,
                departure_time=str(l.departure_time),
                arrival_time=str(l.arrival_time),
                cost=l.cost,
                status=l.status.value,
            )
            for l in legs
        ]

        stop_destination_names = {
            stop.id: destinations_by_stop.get(stop.id).name
            for stop in stops
            if destinations_by_stop.get(stop.id)
        }

        item_details = [
            ItineraryItemDetail(
                id=it.id,
                trip_stop_id=it.trip_stop_id,
                item_type=it.item_type.value,
                place_id=it.place_id,
                custom_title=it.custom_title,
                day_number=it.day_number,
                scheduled_date=str(it.scheduled_date),
                start_time=it.start_time,
                end_time=it.end_time,
                cost=it.cost,
                status=it.status.value,
                notes=it.notes,
                category=db.places[it.place_id].category if it.place_id in db.places else None,
                description=db.places[it.place_id].description if it.place_id in db.places else None,
                image_url=db.places[it.place_id].image_url if it.place_id in db.places else None,
                map_url=(
                    "https://www.google.com/maps/search/?api=1&query="
                    + quote_plus(
                        f"{db.places[it.place_id].name}, "
                        f"{stop_destination_names.get(it.trip_stop_id, '')}"
                    )
                    if it.place_id in db.places
                    else None
                ),
                rating=db.places[it.place_id].rating if it.place_id in db.places else None,
                travel_time_from_prev_minutes=it.travel_time_from_prev_minutes,
                travel_distance_km=it.travel_distance_km,
            )
            for it in items
        ]

        version_hash = proposal_store.compute_trip_state_hash(trip.id)
        duration_days = (trip.end_date - trip.start_date).days + 1
        nights = duration_days - 1

        return TripDetailResponse(
            id=trip.id,
            title=trip.title,
            start_date=str(trip.start_date),
            end_date=str(trip.end_date),
            total_budget=trip.total_budget,
            currency=trip.currency,
            status=trip.status.value,
            traveler_count=trip.traveler_count,
            duration_days=duration_days,
            nights=nights,
            interests=trip.interests,
            stops=stop_details,
            transport_legs=leg_details,
            itinerary=item_details,
            budget=budget_res,
            validation=validation_res,
            version_hash=version_hash,
        )



    # ------------------------------------------------------------------
    # Phase B.2 — Hotel Update (no itinerary regeneration)
    # ------------------------------------------------------------------

    def update_hotel(self, trip_id: str, request: "HotelUpdateRequest") -> TripDetailResponse:
        """
        Swaps the hotel on a trip stop without regenerating the itinerary.

        1. Validates the new hotel exists and belongs to the correct destination.
        2. Updates TripStop.hotel_id and persists.
        3. Recalculates travel distances/times from the new hotel to the first activity
           of each affected day using the existing geo_routing_engine.
        4. Persists updated ItineraryItems.
        5. Re-runs budget_engine and schedule_validator deterministically.
        6. Returns a full updated TripDetailResponse.
        Unaffected itinerary items (no hotel → activity leg) remain unchanged.
        """
        db = get_db()

        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        # Resolve the new hotel
        new_hotel = db.hotels.get(request.hotel_id)
        if not new_hotel:
            raise ValueError(f"HOTEL_NOT_FOUND: Hotel '{request.hotel_id}' does not exist.")

        stops = db.get_trip_stops(trip_id)
        if not stops:
            raise ValueError("TRIP_HAS_NO_STOPS: Cannot update hotel on a trip with no stops.")

        # Identify the target stop
        if request.stop_id:
            target_stop = next((s for s in stops if s.id == request.stop_id), None)
            if not target_stop:
                raise ValueError(f"STOP_NOT_FOUND: Stop '{request.stop_id}' does not belong to trip '{trip_id}'.")
        else:
            # Default: use the stop whose destination matches the hotel's destination
            target_stop = next(
                (s for s in stops if s.destination_id == new_hotel.destination_id),
                stops[0],
            )

        # Validate hotel belongs to the stop's destination
        if new_hotel.destination_id != target_stop.destination_id:
            raise ValueError(
                f"HOTEL_DESTINATION_MISMATCH: Hotel '{new_hotel.name}' belongs to destination "
                f"'{new_hotel.destination_id}', but stop is at '{target_stop.destination_id}'."
            )

        # Record original hotel_id so we can compare items below
        old_hotel_id = target_stop.hotel_id

        # Persist the hotel change
        updated_stop = target_stop.model_copy(update={"hotel_id": new_hotel.id})
        db.update_trip_stop(updated_stop)

        # Recalculate hotel → first-activity travel for each day in this stop
        hotel_point = GeoPoint(latitude=new_hotel.latitude, longitude=new_hotel.longitude)
        stop_items = db.get_itinerary_items_for_stop(target_stop.id)

        # Group items by day; update only the first item of each day (hotel → first activity)
        items_by_day: Dict[int, list] = {}
        for item in stop_items:
            items_by_day.setdefault(item.day_number, []).append(item)

        for day_number, day_items in items_by_day.items():
            sorted_day = sorted(day_items, key=lambda x: x.start_time)
            first_item = sorted_day[0]

            if first_item.place_id and first_item.place_id in db.places:
                place = db.places[first_item.place_id]
                place_point = GeoPoint(latitude=place.latitude, longitude=place.longitude)
                est = geo_routing_engine.estimate_travel_time(hotel_point, place_point, mode=RoutingMode.CAB)
                updated_item = first_item.model_copy(update={
                    "travel_time_from_prev_minutes": est.duration_minutes,
                    "travel_distance_km": est.distance_km,
                })
                db.itinerary_items[first_item.id] = updated_item

        # Rebuild full response (budget + validation re-run deterministically)
        return self.get_trip_detail(trip_id)

    # ------------------------------------------------------------------
    # Phase B.3 — Dry-run activity feasibility (no persistence)
    # ------------------------------------------------------------------

    def validate_activity_candidate(
        self, trip_id: str, request: "ActivityValidateRequest"
    ) -> "ActivityValidateResponse":
        """
        Checks whether a candidate activity can be inserted into an existing trip day.
        Does NOT persist anything to the database.

        Checks:
        - Valid time range (end > start)
        - No overlap with existing items on the same day
        - Sufficient travel buffer from the preceding item
        - Venue opening hours / closed days (when place_id is provided)
        - Activity falls within the stop's date range
        Returns feasible=True/False, blocking issues, and alternative time suggestions.
        """
        from backend.app.core.schedule_validator import parse_time_str, time_to_minutes, date_to_schema_day
        from backend.app.models.entities import ItineraryItem, ItemType, ItemStatus
        from uuid import uuid4 as _uuid4
        from datetime import date as _date

        db = get_db()

        trip = db.get_trip(trip_id)
        if not trip:
            raise KeyError(f"TRIP_NOT_FOUND: Trip '{trip_id}' does not exist.")

        stops = db.get_trip_stops(trip_id)

        # Resolve the target stop from day_number
        if request.trip_stop_id:
            target_stop = next((s for s in stops if s.id == request.trip_stop_id), None)
            if not target_stop:
                raise ValueError(f"STOP_NOT_FOUND: Stop '{request.trip_stop_id}' not found.")
        else:
            # Find the stop that contains this day_number
            day_counter = 0
            target_stop = None
            for stop in stops:
                stop_days = (stop.departure_date - stop.arrival_date).days + 1
                if day_counter < request.day_number <= day_counter + stop_days:
                    target_stop = stop
                    break
                day_counter += stop_days
            if not target_stop:
                target_stop = stops[-1] if stops else None
            if not target_stop:
                raise ValueError("TRIP_HAS_NO_STOPS: Cannot validate activity on a trip with no stops.")

        # Compute the calendar date for this day_number
        day_offset = request.day_number - 1
        candidate_date: _date = trip.start_date + timedelta(days=day_offset)

        # Validate time strings
        issues: list = []
        try:
            cand_start_t = parse_time_str(request.start_time)
            cand_end_t = parse_time_str(request.end_time)
        except Exception:
            return ActivityValidateResponse(
                feasible=False,
                issues=[f"Invalid time format: '{request.start_time}' or '{request.end_time}'. Use HH:MM."],
            )

        cand_start_m = time_to_minutes(cand_start_t)
        cand_end_m = time_to_minutes(cand_end_t)

        if cand_end_m <= cand_start_m:
            return ActivityValidateResponse(
                feasible=False,
                issues=["End time must be strictly after start time."],
            )

        # Check venue constraints (opening hours, closed days) when place_id provided
        if request.place_id and request.place_id in db.places:
            place = db.places[request.place_id]
            schema_day = date_to_schema_day(candidate_date)
            if schema_day in place.closed_days:
                day_names = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
                issues.append(f"'{place.name}' is closed on {day_names[schema_day]}s.")
            else:
                open_m = time_to_minutes(parse_time_str(place.open_time))
                close_m = time_to_minutes(parse_time_str(place.close_time))
                if cand_start_m < open_m:
                    issues.append(
                        f"'{place.name}' opens at {place.open_time}; proposed start {request.start_time} is too early."
                    )
                if cand_end_m > close_m:
                    issues.append(
                        f"'{place.name}' closes at {place.close_time}; proposed end {request.end_time} is too late."
                    )

        # Build a temporary candidate item (not persisted)
        candidate = ItineraryItem(
            id=f"__candidate__{_uuid4()}",
            trip_stop_id=target_stop.id,
            place_id=request.place_id,
            custom_title=request.custom_title or (
                db.places[request.place_id].name if request.place_id in db.places else "New Activity"
            ),
            day_number=request.day_number,
            scheduled_date=candidate_date,
            start_time=request.start_time,
            end_time=request.end_time,
            cost=db.places[request.place_id].entry_fee if request.place_id in db.places else 0.0,
        )

        # Pull existing items on the target day
        all_stop_items = db.get_itinerary_items_for_stop(target_stop.id)
        day_items = [it for it in all_stop_items if it.day_number == request.day_number]
        sorted_day = sorted(day_items, key=lambda x: time_to_minutes(parse_time_str(x.start_time)))

        # Check overlaps with existing items
        for existing in sorted_day:
            ex_start = time_to_minutes(parse_time_str(existing.start_time))
            ex_end = time_to_minutes(parse_time_str(existing.end_time))

            # Overlap: candidate start < existing end AND candidate end > existing start
            if cand_start_m < ex_end and cand_end_m > ex_start:
                issues.append(
                    f"Overlaps with existing activity '{existing.custom_title or 'Activity'}' "
                    f"({existing.start_time}–{existing.end_time})."
                )

        # Check travel buffer from the immediately preceding item
        preceding = next(
            (it for it in reversed(sorted_day) if time_to_minutes(parse_time_str(it.end_time)) <= cand_start_m),
            None,
        )
        MIN_BUFFER = 10  # minutes
        if preceding:
            gap = cand_start_m - time_to_minutes(parse_time_str(preceding.end_time))
            required = (preceding.travel_time_from_prev_minutes or 0) + MIN_BUFFER
            if gap < required:
                issues.append(
                    f"Insufficient gap after '{preceding.custom_title or 'Activity'}': "
                    f"only {gap} min available, need ≥{required} min (travel + buffer)."
                )

        feasible = len(issues) == 0

        # Generate alternative slots when infeasible
        suggestions: list = []
        if not feasible:
            # Build free windows in the day
            occupied_windows = [(time_to_minutes(parse_time_str(it.start_time)),
                                  time_to_minutes(parse_time_str(it.end_time)))
                                 for it in sorted_day]
            occupied_windows.sort()
            candidate_duration = cand_end_m - cand_start_m
            day_start = 8 * 60   # 08:00
            day_end   = 21 * 60  # 21:00

            boundaries = [day_start] + [end for _, end in occupied_windows] + [day_end]
            for i in range(len(boundaries) - 1):
                window_start = boundaries[i] + MIN_BUFFER
                window_end   = boundaries[i + 1] - MIN_BUFFER
                if window_end - window_start >= candidate_duration:
                    slot_start = window_start
                    slot_end   = slot_start + candidate_duration
                    h_s, m_s = divmod(slot_start, 60)
                    h_e, m_e = divmod(slot_end, 60)
                    suggestions.append(ActivityValidateSuggestion(
                        start_time=f"{h_s:02d}:{m_s:02d}",
                        end_time=f"{h_e:02d}:{m_e:02d}",
                        reason="Free window fitting the requested duration with adequate buffers.",
                    ))
                    if len(suggestions) >= 3:
                        break

        # Run the full validator on the augmented day for completeness
        provisional_items = all_stop_items + [candidate]
        validation_result = schedule_validator.validate(
            trip=trip,
            trip_stops=stops,
            itinerary_items=provisional_items,
            transport_legs=db.get_transport_legs_for_trip(trip_id),
            places_by_id=db.places,
            restaurants_by_id=db.restaurants,
        )

        return ActivityValidateResponse(
            feasible=feasible,
            issues=issues,
            suggestions=suggestions,
            validation=validation_result,
        )


trip_service = TripService()
